"""
Minimal runnable demo wiring DataStore + DataStoreTreeModel +
ParameterTableModel + FitController + PlotController together. Not a
replacement for Motofit, just a concrete illustration of the
architecture sketch.

Structure tree (top-left) lists every loaded dataset, checkable to
control whether it's included in the next fit, expandable to see its
layers. The parameter tree (bottom-left) always shows *every*
parameter from *every* checked dataset at once, grouped by Component
and expandable/collapsible per group -- select rows across groups and
datasets and hit "Link Selected" to constrain them together.
Reflectivity and SLD plots (right) overlay every dataset. Fit runs
CurveFitter (a plain Objective for one dataset, a GlobalObjective for
several) on a background thread via FitController.

Run with:
    QT_QPA_PLATFORM=offscreen python3 main.py     # headless smoke test
    python3 main.py                                # normal, with a window
"""

import sys
from copy import deepcopy
from importlib import resources
from pathlib import Path

import numpy as np

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.compat import getopenfilename, getopenfilenames, getsavefilename

import refnx.analysis
from refnx.dataset import ReflectDataset
from refnx.reflect import SLD, ReflectModel, Stack
from refnx.analysis import Objective, GlobalObjective, Parameter, Transform

from datastore import DataObject, DataStore
from models import (
    DataStoreTreeModel,
    ParameterTableModel,
    StructureEditError,
    equivalent_parameter,
    same_model_shape,
    unlink_dependents,
)
from controllers import FitController
from plotting import PlotController
from dialogs import (
    AddComponentDialog,
    DatasetMultiSelectDialog,
    LipidLeafletDialog,
    default_component,
)
from delegates import SelectAllDelegate
import persistence


def _default_model():
    structure = SLD(0)(0, 0) | SLD(4.0)(0, 3)
    return ReflectModel(structure)


def _plot_tab(canvas, toolbar):
    """A plot canvas with its matplotlib navigation toolbar (pan/zoom/
    save) stacked above it -- both PlotController's Reflectivity and
    SLD tabs get one, since a QTabWidget page can only hold a single
    widget."""
    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)
    return container


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
        # Used both for the reflectivity plot (data and fit are shown
        # transformed, axis scale flipped to match -- see
        # PlotController._reset_axes) and for chi2 (both the tree's
        # column and the Objective a fit runs against), so switching it
        # from the Transform menu keeps everything that depends on the
        # data in sync, exactly like the production app's
        # settransformoption().
        self.transform = Transform(None)

        self.tree_model = DataStoreTreeModel(datastore)
        self.tree_model.dataChanged.connect(self.on_tree_model_changed)
        # add/remove/move a Component all end with tree_model resetting
        # itself (see models.py) -- catching that one signal here means
        # the parameter table and plots refresh after any of them
        # without each needing its own explicit refresh call, including
        # the drag-and-drop path, which doesn't go through a main.py
        # handler at all.
        self.tree_model.modelReset.connect(self.on_structure_changed)
        self.parameter_model = ParameterTableModel()
        self.parameter_model.set_datastore(datastore)
        # remembers whichever datasets were last picked in the Link
        # Equivalent Parameters dialog, so repeated linking (a common
        # workflow: link one parameter, then the next, against the same
        # set of datasets) doesn't need re-picking them every time
        self._last_link_equivalent_targets = []

        self.plot_controller = PlotController()
        self.fit_controller = FitController(self)
        self.fit_controller.progress.connect(self.on_fit_progress)
        self.fit_controller.finished.connect(self.on_fit_finished)

        self._build_ui()
        self._build_menus()
        self._update_plots_and_chi2()

    def _build_ui(self):
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.header().setStretchLastSection(True)
        self._refresh_navigation_tree_view()
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

        self.table_view = QtWidgets.QTreeView()
        self.table_view.setModel(self.parameter_model)
        self.table_view.header().setStretchLastSection(True)
        # select-all on entering edit mode -- typing immediately
        # replaces the whole value instead of inserting into whatever
        # got (inconsistently, platform-dependently) selected around
        # the click, which is what made precise/small values like
        # 2.123e-5 hard to enter cleanly
        self.table_view.setItemDelegate(SelectAllDelegate(self.table_view))
        self.table_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        # everything visible at once by default, same as the old flat
        # table -- collapsing a group is opt-in, not the starting state
        self._refresh_parameter_tree_view()
        self.parameter_model.dataChanged.connect(self.on_parameter_changed)

        # Link/Unlink Selected and Link Equivalent Parameters are
        # actions now (see _build_menus), not buttons -- Ctrl+1/2/3,
        # matching the production app's shortcuts exactly
        self.auto_limits_button = QtWidgets.QPushButton("Auto Limits")
        self.auto_limits_button.setToolTip(
            "Set bounds on every varying parameter to [0, 2x value] "
            "(reflected around zero if value is negative)."
        )
        self.auto_limits_button.clicked.connect(self.on_auto_limits_clicked)
        link_row = QtWidgets.QHBoxLayout()
        link_row.addWidget(self.auto_limits_button)

        # lives in the Parameters dock, not alongside the plots -- it's
        # a parameter-tree action (which datasets get fitted is read
        # straight off the Structure dock's checkboxes, but the
        # button itself belongs with the parameters it changes)
        self.fit_button = QtWidgets.QPushButton(
            "Fit checked datasets (differential evolution)"
        )
        self.fit_button.clicked.connect(self.on_fit_clicked)

        table_container = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table_view)
        table_layout.addLayout(link_row)
        table_layout.addWidget(self.fit_button)

        # QDockWidgets, not a fixed QSplitter panel -- each of the two
        # left-hand panes can be dragged out into its own floating
        # window, dragged to a different edge of the main window, or
        # tabified with the other, independently of the plots. Qt's
        # own dock machinery (not a splitter) is what makes any of
        # that possible; a QSplitter panel never floats loose.
        self.structure_dock = QtWidgets.QDockWidget("Structure", self)
        self.structure_dock.setObjectName("structure_dock")
        self.structure_dock.setWidget(self.tree_view)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.structure_dock
        )

        self.parameters_dock = QtWidgets.QDockWidget("Parameters", self)
        self.parameters_dock.setObjectName("parameters_dock")
        self.parameters_dock.setWidget(table_container)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.parameters_dock
        )
        # stack Parameters below Structure in the left dock area, same
        # top-to-bottom order the old fixed splitter panel had
        self.splitDockWidget(
            self.structure_dock,
            self.parameters_dock,
            QtCore.Qt.Orientation.Vertical,
        )
        # QMainWindowLayout doesn't always recompute how much space the
        # central widget owns the instant a dock's floating state
        # flips -- undocking (or redocking) can leave the plots either
        # not reclaiming the freed space, or not giving it back,
        # rather than continuously tracking window resizes the way
        # they should from then on. Nudging a relayout on the next
        # event-loop tick, every time either dock's floating state
        # changes, is the standard workaround.
        self.structure_dock.topLevelChanged.connect(
            self._relayout_central_widget
        )
        self.parameters_dock.topLevelChanged.connect(
            self._relayout_central_widget
        )
        # Qt's default dock sizing is based on each pane's size hint,
        # which leaves them cramped even though their content (once
        # columns are auto-sized to fit, see _refresh_parameter_tree_view)
        # genuinely needs more room -- start noticeably wider than that.
        self.resizeDocks(
            [self.structure_dock, self.parameters_dock],
            [500, 500],
            QtCore.Qt.Orientation.Horizontal,
        )

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(
            _plot_tab(
                self.plot_controller.reflectivity_canvas,
                self.plot_controller.reflectivity_toolbar,
            ),
            "Reflectivity",
        )
        tabs.addTab(
            _plot_tab(
                self.plot_controller.sld_canvas,
                self.plot_controller.sld_toolbar,
            ),
            "SLD",
        )

        # tabs is the whole central widget now -- nothing else needs
        # to share space with it, so it gets the entirety of whatever
        # room the QMainWindow layout leaves once dock widgets (and
        # any that get undocked) are accounted for
        self.setCentralWidget(tabs)

        self.setStatusBar(QtWidgets.QStatusBar())

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")

        load_data_action = file_menu.addAction("Load Data...")
        load_data_action.triggered.connect(self.on_load_data_triggered)

        load_model_action = file_menu.addAction("Load Model...")
        load_model_action.triggered.connect(self.on_load_model_triggered)

        load_experiment_action = file_menu.addAction("Load Experiment...")
        load_experiment_action.triggered.connect(
            self.on_load_experiment_triggered
        )

        reload_data_action = file_menu.addAction("Reload Datasets")
        reload_data_action.setShortcut(QtGui.QKeySequence("Ctrl+R"))
        reload_data_action.triggered.connect(self.on_reload_data_triggered)

        file_menu.addSeparator()

        save_model_action = file_menu.addAction("Save Model...")
        save_model_action.triggered.connect(self.on_save_model_triggered)

        save_experiment_action = file_menu.addAction("Save Experiment...")
        save_experiment_action.triggered.connect(
            self.on_save_experiment_triggered
        )

        file_menu.addSeparator()

        remove_action = file_menu.addAction("Remove Selected Dataset")
        remove_action.triggered.connect(self.on_remove_dataset_triggered)

        structure_menu = self.menuBar().addMenu("&Structure")

        add_component_action = structure_menu.addAction("Add Component...")
        add_component_action.setShortcut(QtGui.QKeySequence("Ctrl++"))
        add_component_action.triggered.connect(self.on_add_component_triggered)

        remove_component_action = structure_menu.addAction(
            "Remove Selected Component"
        )
        remove_component_action.setShortcut(QtGui.QKeySequence("Ctrl+-"))
        remove_component_action.triggered.connect(
            self.on_remove_component_triggered
        )

        transform_menu = self.menuBar().addMenu("&Transform")
        transform_group = QtGui.QActionGroup(self)
        transform_group.setExclusive(True)
        # keyed by form string so on_transform_changed can keep the
        # checked action in sync even when it's called other than by
        # the user clicking one of these directly (QActionGroup only
        # updates checked state for the action that was actually
        # clicked, not for a same-effect call from elsewhere)
        self._transform_actions = {}
        for label, form in (
            ("linY", "lin"),
            ("logY", "logY"),
            ("YX4", "YX4"),
        ):
            action = transform_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(form == "lin")
            action.triggered.connect(
                lambda checked, form=form: self.on_transform_changed(form)
            )
            transform_group.addAction(action)
            self._transform_actions[form] = action

        parameters_menu = self.menuBar().addMenu("&Parameters")

        link_action = parameters_menu.addAction("Link Selected Parameters")
        link_action.setShortcut(QtGui.QKeySequence("Ctrl+1"))
        link_action.triggered.connect(self.on_link_clicked)

        unlink_action = parameters_menu.addAction("Unlink Selected Parameters")
        unlink_action.setShortcut(QtGui.QKeySequence("Ctrl+2"))
        unlink_action.triggered.connect(self.on_unlink_clicked)

        link_equivalent_action = parameters_menu.addAction(
            "Link Equivalent Parameters..."
        )
        link_equivalent_action.setShortcut(QtGui.QKeySequence("Ctrl+3"))
        link_equivalent_action.triggered.connect(
            self.on_link_equivalent_triggered
        )

        # everything in these three menus mutates a DataObject's model
        # (or the datastore itself) -- see _set_fit_running_ui_state
        self._model_mutating_menus = [
            file_menu,
            structure_menu,
            parameters_menu,
        ]

    def msg(self, text, timeout=8000):
        # non-modal, same reasoning as the production app: routine
        # messages shouldn't interrupt the workflow with a dialog.
        self.statusBar().showMessage(text, timeout)
        print(text)

    def _update_plots_and_chi2(self):
        """Redraws the plots and refreshes the navigation tree's chi2
        column together -- they go stale at exactly the same moments
        (anything that changes a model's parameters or structure), so
        every call site that used to just update the plots now does
        both in one place instead of risking the two drifting apart."""
        self.plot_controller.update(self.datastore, transform=self.transform)
        self.tree_model.set_transform(self.transform)

    def on_transform_changed(self, form):
        self.transform = Transform(form)
        action = self._transform_actions.get(form)
        if action is not None:
            action.setChecked(True)
        self._update_plots_and_chi2()
        self.msg(f"Transform set to {form!r}")

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

    def _refresh_parameter_tree_view(self):
        """Expand everything and size each column to fit its content.
        A QTreeView's default column widths are small, fixed pixel
        values unrelated to what's actually in them -- left alone, the
        Name/Value/σ/Lower/Upper columns all show up too narrow to
        read (truncated to "t...", "2.1234...", etc.) on every startup
        and after every structural change, forcing a manual drag to
        widen them each time. Called everywhere the parameter tree's
        shape or content changes, not just once at startup."""
        self.table_view.expandAll()
        last_col = self.parameter_model.columnCount() - 1
        for col in range(last_col):  # last column already stretches
            self.table_view.resizeColumnToContents(col)

    def _refresh_navigation_tree_view(self):
        """Same reasoning as _refresh_parameter_tree_view: expand
        everything and size the Dataset column to fit its content --
        Qt's default column width has no relation to what's actually in
        it. The chi2 column stretches (see header().setStretchLastSection
        in _build_ui) rather than being sized to content -- it's always
        short, so fitting it exactly would just leave a large blank gap
        after it instead."""
        self.tree_view.expandAll()
        self.tree_view.resizeColumnToContents(0)

    def closeEvent(self, event):
        # plot_controller.close() disconnects it from the application's
        # paletteChanged signal -- see PlotController.__init__ for why
        # that connection must not outlive this window's canvases.
        self.plot_controller.close()
        super().closeEvent(event)

    def resizeEvent(self, event):
        # belt-and-suspenders alongside _relayout_central_widget below:
        # once both left-hand docks are floating, QMainWindowLayout was
        # observed to stop tracking *further* window resizes altogether
        # (not just miss the first one right after undocking) --
        # updateGeometry() alone (only invalidates the cached size
        # *hint*) wasn't enough to make it recompute; forcing a real
        # layout pass on every resize, not just on a dock's
        # topLevelChanged, is what actually keeps the plots in sync
        # continuously rather than only immediately after undocking.
        super().resizeEvent(event)
        self._do_relayout_central_widget()

    def _relayout_central_widget(self, floating):
        # queued for the next event-loop tick rather than done inline
        # -- topLevelChanged fires partway through Qt's own dock-float
        # transition, before it's necessarily finished reshuffling the
        # QMainWindowLayout itself, so asking for updated geometry
        # immediately can still see stale sizes
        QtCore.QTimer.singleShot(0, self._do_relayout_central_widget)

    def _do_relayout_central_widget(self):
        layout = self.layout()
        if layout is not None:
            # invalidate() + activate() forces Qt to actually redo the
            # geometry pass right now -- updateGeometry() alone only
            # marks the cached size *hint* dirty, it doesn't force an
            # immediate recomputation of who owns how much space.
            layout.invalidate()
            layout.activate()
        central = self.centralWidget()
        central.updateGeometry()

        # Confirmed by hand: QMainWindowLayout keeps the central
        # widget's *position* correct even while a dock is floating
        # (it still starts flush against whichever dock, if any, is
        # still actually docked), but stops recomputing its *size* on
        # ordinary window resizes the moment any dock is floating --
        # invalidate()/activate() above don't reach whatever internal
        # state causes that, only redocking every floating pane does.
        # So: while that state holds, take over sizing it explicitly,
        # using its own (still-correct) top-left corner and the window's
        # own bottom-right, minus the status bar QMainWindow itself owns.
        if (
            self.structure_dock.isFloating()
            or self.parameters_dock.isFloating()
        ):
            available_width = self.width() - central.x()
            available_height = (
                self.height() - central.y() - self.statusBar().height()
            )
            central.resize(max(0, available_width), max(0, available_height))

    def on_structure_changed(self):
        self._refresh_navigation_tree_view()
        self.parameter_model.set_datastore(self.datastore)
        self._refresh_parameter_tree_view()
        self._update_plots_and_chi2()

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

    def on_reload_data_triggered(self):
        """Re-reads every loaded dataset from whatever file it was
        originally loaded from -- e.g. a live experiment still
        appending counts to the same file. No separate path-tracking
        needed: ReflectDataset already records its own source file as
        `.filename` when constructed from one (`build_demo_datastore`'s
        datasets included, since they're loaded from real files too),
        and `.refresh()` re-reads from exactly that path. A dataset
        that isn't backed by a file (constructed purely in memory) is
        just skipped, not an error."""
        reloaded, skipped, failed = [], [], []
        for data_object in self.datastore:
            filename = getattr(data_object.dataset, "filename", None)
            if filename is None:
                skipped.append(data_object.name)
                continue
            try:
                data_object.dataset.refresh()
            except Exception as e:
                failed.append(f"{data_object.name} ({e!r})")
            else:
                reloaded.append(data_object.name)

        self._update_plots_and_chi2()

        if not reloaded and not failed:
            self.msg("No loaded dataset has a file to reload from.")
            return

        parts = [f"Reloaded {len(reloaded)} dataset(s)"]
        if skipped:
            parts.append(f"{len(skipped)} skipped (no source file)")
        if failed:
            parts.append(f"{len(failed)} failed: {'; '.join(failed)}")
        self.msg(", ".join(parts))

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

    def on_load_experiment_triggered(self):
        """Replaces the whole datastore (every dataset, model, and
        which ones are checked for fitting) and the active transform
        from a single saved experiment -- everything Save Experiment
        wrote out, recreated in one go. Unlike Load Model, which
        overwrites one dataset's model in place, this discards
        whatever's currently loaded entirely."""
        path, ok = getopenfilename(
            self,
            caption="Select an experiment file",
            filters="Experiment Files (*.mtft)",
        )
        if not ok or not path:
            return

        try:
            datastore, transform_form = persistence.load_experiment(path)
        except Exception as e:
            self.msg(f"Couldn't load experiment from {path!r}: {e!r}")
            return

        self.datastore = datastore
        action = self._transform_actions.get(transform_form)
        if action is not None:
            action.setChecked(True)
        self.transform = Transform(transform_form)
        self._refresh()
        self.msg(f"Loaded experiment from {path}")

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

    def on_save_experiment_triggered(self):
        """Saves everything needed to recreate the analysis: every
        loaded dataset and its model (parameters, bounds, constraints,
        which ones are varying), which datasets are checked for
        fitting, and the active transform. Doesn't need a dataset
        selected first, unlike Save Model -- it's the whole datastore,
        not any one dataset's model."""
        path, ok = getsavefilename(
            self, caption="Save experiment as", basedir="experiment.mtft"
        )
        if not ok or not path:
            return

        efp = Path(path)
        if efp.suffix != ".mtft":
            path = str(efp.parent / (efp.stem + ".mtft"))

        try:
            persistence.save_experiment(
                self.datastore, self.transform.form, path
            )
        except Exception as e:
            self.msg(f"Couldn't save experiment to {path!r}: {e!r}")
            return

        self.msg(f"Saved experiment to {path}")

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
        # spinbox fiddling. If a Stack (or something nested inside one)
        # is selected, default to adding *into* that Stack instead of
        # the top level -- that's the only way anything ever ends up
        # inside a Stack's own contents.
        default_container = None
        default_position = 0
        selected_obj = self.tree_model.object_for_index(current)
        if isinstance(selected_obj, Stack):
            default_container = selected_obj
            default_position = len(selected_obj)
        elif selected_obj is not None and not isinstance(
            selected_obj, DataObject
        ):
            parent_obj = self.tree_model.object_for_index(
                self.tree_model.parent(current)
            )
            if isinstance(parent_obj, Stack):
                default_container = parent_obj
                default_position = current.row() + 1
            elif isinstance(parent_obj, DataObject):
                default_position = current.row() + 1

        dialog = AddComponentDialog(
            self.datastore,
            default_dataset=default_dataset_name,
            default_position=default_position,
            default_container=default_container,
            parent=self,
        )
        if not dialog.exec():
            return

        data_object = self.datastore[dialog.dataset_name()]
        kind = dialog.kind()

        if kind == "LipidLeaflet":
            # a specific lipid, not just a placeholder, has to be
            # chosen for this one Component type -- cancelling here
            # cancels the whole Add Component operation, same as
            # cancelling the position/container dialog itself would
            lipid_dialog = LipidLeafletDialog(parent=self)
            if not lipid_dialog.exec():
                return
            component = lipid_dialog.component()
        else:
            component = default_component(kind)

        try:
            self.tree_model.insert_component(
                data_object, dialog.position(), component, dialog.container()
            )
        except StructureEditError as e:
            self.msg(str(e))
            return

        self.msg(
            f"Added a {kind} to {data_object.name} at "
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
        Just expands whatever group(s) it's in, scrolls to, and
        highlights, whatever was clicked."""
        obj = self.tree_model.object_for_index(current)
        data_object = self.tree_model.data_object_for_index(current)
        if obj is None or data_object is None:
            return

        if isinstance(obj, DataObject):
            wanted = set(obj.model.parameters.flattened())
        else:
            wanted = set(obj.parameters.flattened())

        last_col = self.parameter_model.columnCount() - 1
        indexes = []
        selection = QtCore.QItemSelection()
        for p in wanted:
            top_left = self.parameter_model.index_for(p)
            if not top_left.isValid():
                continue
            indexes.append(top_left)
            bottom_right = self.parameter_model.index(
                top_left.row(), last_col, top_left.parent()
            )
            selection.select(top_left, bottom_right)
            self.table_view.expand(top_left.parent())

        if not indexes:
            return

        self.table_view.selectionModel().select(
            selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        self.table_view.scrollTo(indexes[0])

    def on_parameter_changed(self, top_left, bottom_right, roles):
        self._update_plots_and_chi2()

    def on_tree_model_changed(self, top_left, bottom_right, roles):
        # tree_model.dataChanged fires for three different things: a
        # dataset's checkbox being (un)checked (ParameterTableModel
        # only shows parameters for currently-checked datasets, so it
        # needs rebuilding), a Component being renamed (its group label
        # in the parameter tree needs to pick up the new name), or just
        # the chi2 column refreshing (tree_model.refresh_chi2(), fired
        # on every parameter edit -- far too often to also rebuild the
        # entire parameter tree for). The chi2 column is the last one,
        # so a change confined to it alone is never a checkbox/rename
        # and needs nothing further here -- data() already recomputes
        # chi2 on demand, that's the whole point of the signal.
        if top_left.column() == self.tree_model.COLUMNS.index("chi2"):
            return
        self.parameter_model.set_datastore(self.datastore)
        self._refresh_parameter_tree_view()

    def _selected_table_rows(self):
        """One QModelIndex (column 0) per selected row, deduplicated --
        SelectRows means selectedIndexes() returns one index per
        *column* of each selected row, and with a tree, `.row()` alone
        can't dedupe them since it's relative to each row's own parent,
        not global."""
        seen = set()
        result = []
        for idx in self.table_view.selectedIndexes():
            node = idx.sibling(idx.row(), 0).internalPointer()
            if node in seen:
                continue
            seen.add(node)
            result.append(
                self.parameter_model.index(idx.row(), 0, idx.parent())
            )
        return result

    def on_link_clicked(self):
        indexes = self._selected_table_rows()
        if len(indexes) < 2:
            self.msg("Select two or more parameter rows to link.")
            return
        self.parameter_model.link(indexes)
        self._update_plots_and_chi2()

    def on_unlink_clicked(self):
        indexes = self._selected_table_rows()
        if not indexes:
            self.msg("Select one or more parameter rows to unlink.")
            return
        self.parameter_model.unlink(indexes)
        self._update_plots_and_chi2()

    def on_link_equivalent_triggered(self):
        """Mirrors the production app's Link Equivalent Parameters
        (Ctrl+3): link every currently-selected parameter to the
        parameter occupying the *same structural position* in each of
        a chosen set of other datasets -- assumes those datasets share
        the same model shape. Every selected parameter, plus every
        equivalent found for it, ends up constrained to a single
        master (the first selected parameter) -- same flattening the
        production app does, so selecting parameters that represent
        genuinely different physical quantities in one go will link
        them to each other too, not just to their own equivalents."""
        indexes = self._selected_table_rows()
        par_nodes = [
            idx.internalPointer()
            for idx in indexes
            if isinstance(self.parameter_model.parameter_at(idx), Parameter)
        ]
        if not par_nodes:
            self.msg("Select one or more parameters in the tree first.")
            return

        if len(self.datastore) < 2:
            self.msg("Load at least one more dataset to link across.")
            return

        dialog = DatasetMultiSelectDialog(
            self.datastore.names,
            title="Select equivalent datasets to link",
            preselected=self._last_link_equivalent_targets,
            parent=self,
        )
        if not dialog.exec():
            return
        target_names = dialog.selected_names()
        self._last_link_equivalent_targets = target_names
        if not target_names:
            self.msg(
                "Select at least one dataset to link equivalent "
                "parameters to."
            )
            return
        target_data_objects = [self.datastore[n] for n in target_names]

        source_data_objects = {
            node.dataset_name: self.datastore[node.dataset_name]
            for node in par_nodes
        }
        if not same_model_shape(
            list(source_data_objects.values()) + target_data_objects
        ):
            self.msg(
                "All models must have the same number of Components and "
                "parameters for equivalent linking -- no linking done."
            )
            return

        to_link = []
        seen = set()
        for node in par_nodes:
            parameter = node.obj
            if id(parameter) not in seen:
                seen.add(id(parameter))
                to_link.append(parameter)
            source_do = self.datastore[node.dataset_name]
            for target_do in target_data_objects:
                equivalent = equivalent_parameter(
                    source_do, parameter, target_do
                )
                if equivalent is not None and id(equivalent) not in seen:
                    seen.add(id(equivalent))
                    to_link.append(equivalent)

        if len(to_link) < 2:
            self.msg("Nothing new to link.")
            return

        master = to_link[0]
        master.constraint = None  # avoid recursion if it's already linked
        for p in to_link[1:]:
            p.constraint = master

        self.parameter_model.set_datastore(self.datastore)
        self._refresh_parameter_tree_view()
        self._update_plots_and_chi2()
        self.msg(
            f"Linked {len(to_link)} equivalent parameter(s) across "
            f"{len(target_data_objects)} dataset(s)."
        )

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
            Objective(
                do.model,
                do.dataset,
                use_weights=True,
                transform=self.transform,
            )
            for do in fitted
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
        self._set_fit_running_ui_state(True)
        names = ", ".join(do.name for do in fitted)
        self.msg(f"Fitting {names}...")
        self.fit_controller.start(
            objective,
            method=method,
            maxiter=50,
            popsize=10,
            seed=1,
        )

    def _set_fit_running_ui_state(self, running):
        """While a fit runs on FitController's background thread, the
        optimizer is continuously reading *and writing* the fitted
        model's Parameter objects (Objective.setp() every iteration,
        chisqr() every progress callback) -- editing, renaming,
        linking, or restructuring the same models from the GUI thread
        at the same time is a real, unsynchronized data race between
        two threads touching the same Python/refnx objects, not just a
        cosmetic inconsistency, and has been implicated in crashes
        after repeated fit runs. Disable everything that could touch a
        DataObject's model while a fit is in flight; only Fit/Abort
        itself, and read-only things like switching plot tabs, stay
        live. Re-enabled once on_fit_finished confirms the background
        thread has actually stopped -- not any earlier."""
        self.tree_view.setEnabled(not running)
        self.table_view.setEnabled(not running)
        self.auto_limits_button.setEnabled(not running)
        for menu in self._model_mutating_menus:
            menu.setEnabled(not running)

    def on_fit_progress(self, chi2, iterations):
        self.statusBar().showMessage(
            f"chi2={chi2:.6g}   iteration={iterations}"
        )

    def on_fit_finished(self, exc):
        self.fit_button.setText(
            "Fit checked datasets (differential evolution)"
        )
        self._set_fit_running_ui_state(False)
        if exc is not None:
            self.msg(f"Fit failed: {exc!r}")
        else:
            self.msg("Fit complete")
            # values changed under the table's feet; whatever's shown
            # may now be stale -- a full rebuild is simplest since the
            # changed rows are scattered across the tree rather than
            # one contiguous range
            self.parameter_model.set_datastore(self.datastore)
            self._refresh_parameter_tree_view()
        self._update_plots_and_chi2()


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    win.resize(1200, 650)
    # restored after the default resize above, so it only has an effect
    # once something's actually been saved -- otherwise the default
    # stands. Deliberately done here rather than in MainWindow itself
    # (e.g. __init__/closeEvent): every test in test_prototype.py
    # constructs a bare MainWindow, and persistence tied to its own
    # lifecycle would make the suite read/write the developer's real
    # QSettings on every run. aboutToQuit (rather than closeEvent) is
    # used to save, since it fires once per app exit regardless of
    # which window (there's only one here, but the same reasoning
    # applies) triggered it, and while everything's still alive.
    persistence.restore_window_state(win)
    app.aboutToQuit.connect(lambda: persistence.save_window_state(win))
    win.show()
    return app, win


if __name__ == "__main__":
    app, win = main()
    sys.exit(app.exec())
