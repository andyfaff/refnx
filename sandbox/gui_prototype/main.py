"""
Minimal runnable demo wiring DataStore + DataStoreTreeModel +
ParameterTableModel + FitController + PlotController together. Not a
replacement for Motofit, just a concrete illustration of the
architecture sketch.

Structure tree (top-left) lists every loaded dataset, checkable to
control whether it's included in the next fit, expandable to see its
layers. The parameter table (bottom-left) always shows *every*
parameter from *every* loaded dataset at once -- select rows across
datasets and hit "Link Selected" to constrain them together. Reflectivity
and SLD plots (right) overlay every dataset. Fit runs CurveFitter (a
plain Objective for one dataset, a GlobalObjective for several) on a
background thread via FitController.

Run with:
    QT_QPA_PLATFORM=offscreen python3 main.py     # headless smoke test
    python3 main.py                                # normal, with a window
"""

import sys
from copy import deepcopy
from importlib import resources

import numpy as np

from qtpy import QtWidgets, QtCore
from qtpy.compat import getopenfilename, getopenfilenames, getsavefilename

import refnx.analysis
from refnx.dataset import ReflectDataset
from refnx.reflect import SLD, ReflectModel
from refnx.analysis import Objective, GlobalObjective

from datastore import DataObject, DataStore
from models import (
    DataStoreTreeModel,
    ParameterTableModel,
    StructureEditError,
    unlink_dependents,
)
from controllers import FitController
from plotting import PlotController
from dialogs import AddComponentDialog, default_component
import persistence


def _default_model():
    structure = SLD(0)(0, 0) | SLD(4.0)(0, 3)
    return ReflectModel(structure)


def build_demo_datastore():
    """
    Two datasets sharing a similar (but independently-editable) model,
    so linking a parameter across them is immediately demonstrable.
    """
    pth = resources.files(refnx.analysis)

    datastore = DataStore()
    for name, filename in [("e361r", "e361r.txt"), ("e365r", "e365r.txt")]:
        dataset = ReflectDataset(pth / "tests" / filename)

        si = SLD(2.07)
        sio2 = SLD(3.47)
        polymer = SLD(1.0)
        d2o = SLD(6.36)
        structure = si | sio2(15, 3) | polymer(210, 3) | d2o(0, 3)

        model = ReflectModel(structure)
        model.bkg.value = 3e-6
        model.bkg.setp(vary=True, bounds=(1e-6, 5e-6))
        structure[-2].thick.setp(vary=True, bounds=(200, 300))
        structure[-2].sld.real.setp(vary=True, bounds=(0.0, 2.0))

        datastore.add(DataObject(name, dataset, model))

    return datastore


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, datastore):
        super().__init__()
        self.setWindowTitle("Motofit prototype -- architecture sketch")
        self.datastore = datastore

        self.tree_model = DataStoreTreeModel(datastore)
        self.tree_model.dataChanged.connect(self.on_fit_selection_changed)
        # add/remove/move a Component all end with tree_model resetting
        # itself (see models.py) -- catching that one signal here means
        # the parameter table and plots refresh after any of them
        # without each needing its own explicit refresh call, including
        # the drag-and-drop path, which doesn't go through a main.py
        # handler at all.
        self.tree_model.modelReset.connect(self.on_structure_changed)
        self.parameter_model = ParameterTableModel()
        self.parameter_model.set_datastore(datastore)

        self.plot_controller = PlotController()
        self.fit_controller = FitController(self)
        self.fit_controller.progress.connect(self.on_fit_progress)
        self.fit_controller.finished.connect(self.on_fit_finished)

        self._build_ui()
        self._build_menus()
        self.plot_controller.update(self.datastore)

    def _build_ui(self):
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.expandAll()
        self.tree_view.selectionModel().currentChanged.connect(
            self.on_tree_selection
        )
        # reordering top-level Components within a Structure (see
        # DataStoreTreeModel.flags/mimeData/dropMimeData -- only
        # top-level rows are drag-enabled, dropping is only accepted
        # onto a DataObject's own children)
        self.tree_view.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self.tree_view.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.tree_view.setDropIndicatorShown(True)
        # right-click a dataset for "Copy a model to here", matching the
        # production app's OpenMenu/copy_from_action
        self.tree_view.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.tree_view.customContextMenuRequested.connect(
            self.on_tree_context_menu
        )

        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.parameter_model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.parameter_model.dataChanged.connect(self.on_parameter_changed)

        self.link_button = QtWidgets.QPushButton("Link Selected")
        self.link_button.clicked.connect(self.on_link_clicked)
        self.unlink_button = QtWidgets.QPushButton("Unlink Selected")
        self.unlink_button.clicked.connect(self.on_unlink_clicked)
        self.auto_limits_button = QtWidgets.QPushButton("Auto Limits")
        self.auto_limits_button.setToolTip(
            "Set bounds on every varying parameter to [0, 2x value] "
            "(reflected around zero if value is negative)."
        )
        self.auto_limits_button.clicked.connect(self.on_auto_limits_clicked)
        link_row = QtWidgets.QHBoxLayout()
        link_row.addWidget(self.link_button)
        link_row.addWidget(self.unlink_button)
        link_row.addWidget(self.auto_limits_button)

        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        left_splitter.addWidget(self.tree_view)

        table_container = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table_view)
        table_layout.addLayout(link_row)
        left_splitter.addWidget(table_container)
        left_splitter.setStretchFactor(1, 1)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.plot_controller.reflectivity_canvas, "Reflectivity")
        tabs.addTab(self.plot_controller.sld_canvas, "SLD")

        main_splitter = QtWidgets.QSplitter()
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(tabs)
        main_splitter.setStretchFactor(1, 1)

        self.fit_button = QtWidgets.QPushButton(
            "Fit checked datasets (differential evolution)"
        )
        self.fit_button.clicked.connect(self.on_fit_clicked)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(main_splitter)
        layout.addWidget(self.fit_button)
        self.setCentralWidget(central)

        self.setStatusBar(QtWidgets.QStatusBar())

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")

        load_data_action = file_menu.addAction("Load Data...")
        load_data_action.triggered.connect(self.on_load_data_triggered)

        load_model_action = file_menu.addAction("Load Model...")
        load_model_action.triggered.connect(self.on_load_model_triggered)

        file_menu.addSeparator()

        save_model_action = file_menu.addAction("Save Model...")
        save_model_action.triggered.connect(self.on_save_model_triggered)

        file_menu.addSeparator()

        remove_action = file_menu.addAction("Remove Selected Dataset")
        remove_action.triggered.connect(self.on_remove_dataset_triggered)

        structure_menu = self.menuBar().addMenu("&Structure")

        add_component_action = structure_menu.addAction("Add Component...")
        add_component_action.triggered.connect(self.on_add_component_triggered)

        remove_component_action = structure_menu.addAction(
            "Remove Selected Component"
        )
        remove_component_action.triggered.connect(
            self.on_remove_component_triggered
        )

    def msg(self, text, timeout=8000):
        # non-modal, same reasoning as the production app: routine
        # messages shouldn't interrupt the workflow with a dialog.
        self.statusBar().showMessage(text, timeout)
        print(text)

    def _refresh(self):
        """Refresh every view from the current state of self.datastore.
        tree_model.set_datastore() resetting itself triggers
        on_structure_changed (see __init__), which handles re-expanding
        the tree and refreshing the table/plot -- this is what to call
        when self.datastore's *contents* changed (a dataset added or
        removed, a whole model swapped in). Structural edits within a
        single Structure (add/remove/move a Component) go through
        tree_model directly and get the same refresh for free, since
        those methods also end by resetting tree_model."""
        self.tree_model.set_datastore(self.datastore)

    def on_structure_changed(self):
        self.tree_view.expandAll()
        self.parameter_model.set_datastore(self.datastore)
        self.plot_controller.update(self.datastore)

    def _selected_data_object(self):
        """The DataObject owning whatever's currently selected in the
        tree, or the only one if there's just one dataset loaded, or
        None."""
        index = self.tree_view.currentIndex()
        data_object = self.tree_model.data_object_for_index(index)
        if data_object is None and len(self.datastore) == 1:
            data_object = next(iter(self.datastore))
        return data_object

    def on_load_data_triggered(self):
        paths, ok = getopenfilenames(self, caption="Select dataset(s)")
        if not ok or not paths:
            return

        # new datasets start from a copy of an existing model if there
        # is one, otherwise a bare default -- so they're immediately
        # editable/fittable rather than landing with no model at all.
        template = self._selected_data_object()

        for path in paths:
            try:
                dataset = ReflectDataset(path)
            except Exception as e:
                self.msg(f"Couldn't load {path!r} as a dataset: {e!r}")
                continue

            model = deepcopy(template.model) if template else _default_model()
            name = dataset.name or "dataset"
            data_object = self.datastore.add(DataObject(name, dataset, model))
            self.msg(f"Loaded {data_object.name} from {path}")

        self._refresh()

    def on_load_model_triggered(self):
        data_object = self._selected_data_object()
        if data_object is None:
            self.msg("Select a dataset in the tree first.")
            return

        path, ok = getopenfilename(
            self, caption="Select a pickled ReflectModel"
        )
        if not ok or not path:
            return

        try:
            model = persistence.load_model(path)
        except Exception as e:
            self.msg(f"Couldn't load {path!r} as a model: {e!r}")
            return

        self._replace_model(data_object, model, str(path))

    def on_tree_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid() or not len(self.datastore):
            return

        # Qt already selects the item under the cursor before emitting
        # customContextMenuRequested (standard platform right-click
        # behaviour), so self.tree_view.selectedIndexes() below reflects
        # whatever was clicked -- including a multi-selection made
        # beforehand, if the click landed inside it.
        menu, copy_action = self._build_tree_context_menu()
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))

        if action is copy_action:
            self.on_copy_model_to_here()

    def _build_tree_context_menu(self):
        # split out from on_tree_context_menu so tests can check the
        # menu's contents without calling the real (blocking, can't be
        # driven headlessly) QMenu.exec().
        menu = QtWidgets.QMenu(self.tree_view)
        copy_action = menu.addAction("Copy a model to here")
        return menu, copy_action

    def on_copy_model_to_here(self):
        """Mirrors the production app's copy_from_action: ask which
        dataset's model to copy, then overwrite the model of every
        dataset currently selected in the tree with a copy of it."""
        which, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Which model did you want to copy?",
            "model",
            self.datastore.names,
            editable=False,
        )
        if not ok:
            return
        source_model = self.datastore[which].model

        targets = []
        seen = set()
        for index in self.tree_view.selectedIndexes():
            data_object = self.tree_model.data_object_for_index(index)
            if data_object is not None and data_object.name not in seen:
                seen.add(data_object.name)
                targets.append(data_object)

        if not targets:
            self.msg("Select a dataset (or datasets) to copy the model to.")
            return

        # batched like the production app's _hold_updating: unlink and
        # swap every target's model first, refresh/report once at the
        # end, rather than doing a full refresh per target.
        unlinked = []
        for target in targets:
            old_parameters = list(target.model.parameters.flattened())
            unlinked.extend(unlink_dependents(self.datastore, old_parameters))

            new_model = deepcopy(source_model)
            new_model.name = target.name
            target.model = new_model

        self._refresh()

        names = ", ".join(t.name for t in targets)
        if unlinked:
            self.msg(
                f"Copied {which}'s model to {names}; unlinked "
                f"{len(unlinked)} dependent parameter(s) elsewhere."
            )
        else:
            self.msg(f"Copied {which}'s model to {names}")

    def _replace_model(self, data_object, new_model, source_description):
        """Swap `data_object`'s model out entirely, unlinking any
        parameter elsewhere -- including in a different, currently
        unchecked dataset -- that was constrained to depend on one of
        the parameters going away. Used by Load Model; Copy Model
        (on_copy_model_to_here) does the same unlink-then-swap for
        potentially several targets at once, so it batches that logic
        itself rather than calling this once per target."""
        old_parameters = list(data_object.model.parameters.flattened())
        unlinked = unlink_dependents(self.datastore, old_parameters)

        data_object.model = new_model
        self._refresh()

        if unlinked:
            self.msg(
                f"Set {data_object.name}'s model from {source_description}; "
                f"unlinked {len(unlinked)} dependent parameter(s) elsewhere."
            )
        else:
            self.msg(
                f"Set {data_object.name}'s model from {source_description}"
            )

    def on_save_model_triggered(self):
        data_object = self._selected_data_object()
        if data_object is None:
            self.msg("Select a dataset in the tree first.")
            return

        path, ok = getsavefilename(
            self, caption="Save model as", basedir=f"{data_object.name}.pkl"
        )
        if not ok or not path:
            return

        try:
            persistence.save_model(data_object.model, path)
        except Exception as e:
            self.msg(f"Couldn't save model to {path!r}: {e!r}")
            return

        self.msg(f"Saved {data_object.name}'s model to {path}")

    def on_remove_dataset_triggered(self):
        data_object = self._selected_data_object()
        if data_object is None:
            self.msg("Select a dataset in the tree first.")
            return

        self.datastore.remove(data_object.name)
        self._refresh()
        self.msg(f"Removed {data_object.name}")

    def on_add_component_triggered(self):
        if not len(self.datastore):
            self.msg("Load a dataset first.")
            return

        current = self.tree_view.currentIndex()
        default_dataset = self._selected_data_object()
        default_dataset_name = (
            default_dataset.name if default_dataset is not None else None
        )

        # default to "just after whatever's selected", so the common
        # case (select a layer, add a similar one next to it) needs no
        # spinbox fiddling. Only applies when a *top-level* Component is
        # selected -- Add Component always targets the top level, so a
        # selection nested inside a Stack has no directly-usable
        # position here; leave the default at 0 and let the spinbox
        # speak for itself.
        default_position = 0
        selected_obj = self.tree_model.object_for_index(current)
        if selected_obj is not None and not isinstance(
            selected_obj, DataObject
        ):
            parent_obj = self.tree_model.object_for_index(
                self.tree_model.parent(current)
            )
            if isinstance(parent_obj, DataObject):
                default_position = current.row() + 1

        dialog = AddComponentDialog(
            self.datastore,
            default_dataset=default_dataset_name,
            default_position=default_position,
            parent=self,
        )
        if not dialog.exec():
            return

        data_object = self.datastore[dialog.dataset_name()]
        component = default_component(dialog.kind())

        try:
            self.tree_model.insert_component(
                data_object, dialog.position(), component
            )
        except StructureEditError as e:
            self.msg(str(e))
            return

        self.msg(
            f"Added a {dialog.kind()} to {data_object.name} at "
            f"position {dialog.position()}"
        )

    def on_remove_component_triggered(self):
        index = self.tree_view.currentIndex()
        obj = self.tree_model.object_for_index(index)
        if obj is None or isinstance(obj, DataObject):
            self.msg("Select a Component (not a dataset) to remove.")
            return

        try:
            removed = self.tree_model.remove_component(index)
        except StructureEditError as e:
            self.msg(str(e))
            return

        removed_parameters = list(removed.parameters.flattened())
        unlinked = unlink_dependents(self.datastore, removed_parameters)

        name = getattr(removed, "name", None) or type(removed).__name__
        if unlinked:
            self.msg(
                f"Removed {name}; unlinked {len(unlinked)} dependent "
                f"parameter(s) elsewhere."
            )
        else:
            self.msg(f"Removed {name}")

    def on_tree_selection(self, current, previous):
        """Doesn't filter the table -- everything stays visible, since
        that's what makes cross-dataset multi-select-to-link possible.
        Just scrolls to, and highlights, whatever was clicked."""
        obj = self.tree_model.object_for_index(current)
        data_object = self.tree_model.data_object_for_index(current)
        if obj is None or data_object is None:
            return

        if isinstance(obj, DataObject):
            wanted = set(obj.model.parameters.flattened())
        else:
            wanted = set(obj.parameters.flattened())

        rows = [
            r
            for r, (name, p) in enumerate(self.parameter_model._rows)
            if name == data_object.name and p in wanted
        ]
        if not rows:
            return

        selection = QtCore.QItemSelection()
        for r in rows:
            top_left = self.parameter_model.index(r, 0)
            bottom_right = self.parameter_model.index(
                r, self.parameter_model.columnCount() - 1
            )
            selection.select(top_left, bottom_right)

        self.table_view.selectionModel().select(
            selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        self.table_view.scrollTo(self.parameter_model.index(rows[0], 0))

    def on_parameter_changed(self, top_left, bottom_right, roles):
        self.plot_controller.update(self.datastore)

    def on_fit_selection_changed(self, top_left, bottom_right, roles):
        # a dataset's checkbox was (un)checked -- ParameterTableModel
        # only shows parameters for currently-checked datasets, so it
        # needs rebuilding. Cheap enough at this scale to just do it
        # unconditionally rather than checking whether `roles` was
        # actually CheckStateRole.
        self.parameter_model.set_datastore(self.datastore)

    def _selected_table_rows(self):
        rows = {idx.row() for idx in self.table_view.selectedIndexes()}
        return sorted(rows)

    def on_link_clicked(self):
        rows = self._selected_table_rows()
        if len(rows) < 2:
            self.msg("Select two or more parameter rows to link.")
            return
        self.parameter_model.link(rows)
        self.plot_controller.update(self.datastore)

    def on_unlink_clicked(self):
        rows = self._selected_table_rows()
        if not rows:
            self.msg("Select one or more parameter rows to unlink.")
            return
        self.parameter_model.unlink(rows)
        self.plot_controller.update(self.datastore)

    def on_auto_limits_clicked(self):
        touched = self.parameter_model.auto_limits()
        if touched:
            self.msg(f"Auto-set bounds on {touched} varying parameter(s).")
        else:
            self.msg("No varying parameters to set bounds on.")

    def on_fit_clicked(self):
        if self.fit_controller.running:
            self.fit_controller.abort()
            return

        fitted = self.datastore.fitted_objects()
        if not fitted:
            self.msg("Check at least one dataset in the tree to fit it.")
            return

        objectives = [
            Objective(do.model, do.dataset, use_weights=True) for do in fitted
        ]
        objective = (
            objectives[0]
            if len(objectives) == 1
            else GlobalObjective(objectives)
        )

        method = "differential_evolution"
        if method == "differential_evolution":
            unbounded = [
                p
                for p in objective.varying_parameters()
                if not (np.isfinite(p.bounds.lb) and np.isfinite(p.bounds.ub))
            ]
            if unbounded:
                unbounded_names = ", ".join(p.name for p in unbounded)
                self.msg(
                    "Differential evolution needs finite bounds on every "
                    f"varying parameter. Missing on: {unbounded_names}. Use Auto "
                    "Limits, or set bounds manually, then try again."
                )
                return

        self._fit_objective = objective  # keep alive for the callback

        self.fit_button.setText("Abort")
        names = ", ".join(do.name for do in fitted)
        self.msg(f"Fitting {names}...")
        self.fit_controller.start(
            objective,
            method=method,
            maxiter=50,
            popsize=10,
            seed=1,
        )

    def on_fit_progress(self, chi2, iterations):
        self.statusBar().showMessage(
            f"chi2={chi2:.6g}   iteration={iterations}"
        )

    def on_fit_finished(self, exc):
        self.fit_button.setText(
            "Fit checked datasets (differential evolution)"
        )
        if exc is not None:
            self.msg(f"Fit failed: {exc!r}")
        else:
            self.msg("Fit complete")
            # values changed under the table's feet; whatever's shown
            # may now be stale
            top_left = self.parameter_model.index(0, 0)
            bottom_right = self.parameter_model.index(
                self.parameter_model.rowCount() - 1,
                self.parameter_model.columnCount() - 1,
            )
            self.parameter_model.dataChanged.emit(top_left, bottom_right)
        self.plot_controller.update(self.datastore)


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    win.resize(1200, 650)
    win.show()
    return app, win


if __name__ == "__main__":
    app, win = main()
    sys.exit(app.exec())
