"""
Minimal runnable demo wiring StructureTreeModel + ParameterTableModel +
FitController + PlotController together. Not a replacement for Motofit,
just a concrete illustration of the architecture sketch: structure tree
on the left drives a flat parameter table below it, a Fit button runs
CurveFitter on a background thread via FitController, and edits/fits
both funnel through PlotController.update() to redraw.

Run with:
    QT_QPA_PLATFORM=offscreen python3 main.py     # headless smoke test
    python3 main.py                                # normal, with a window
"""

import sys
from importlib import resources

from qtpy import QtWidgets, QtCore
from qtpy.compat import getopenfilename, getsavefilename

import refnx.analysis
from refnx.dataset import ReflectDataset
from refnx.reflect import SLD, ReflectModel
from refnx.analysis import Objective

from models import StructureTreeModel, ParameterTableModel
from controllers import FitController
from plotting import PlotController
import persistence


def build_demo_objective():
    pth = resources.files(refnx.analysis)
    f_data = pth / "tests" / "e361r.txt"
    dataset = ReflectDataset(f_data)

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

    return Objective(model, dataset, use_weights=True)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, objective):
        super().__init__()
        self.setWindowTitle("Motofit prototype -- architecture sketch")
        self.objective = objective

        structure = objective.model.structure
        self.structure_model = StructureTreeModel(structure)
        self.parameter_model = ParameterTableModel()
        self.parameter_model.set_parameters(structure.parameters.flattened())

        self.plot_controller = PlotController()
        self.fit_controller = FitController(self)
        self.fit_controller.progress.connect(self.on_fit_progress)
        self.fit_controller.finished.connect(self.on_fit_finished)

        self._build_ui()
        self._build_menus()
        self.plot_controller.update(self.objective)

    def _build_ui(self):
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setModel(self.structure_model)
        self.tree_view.expandAll()
        self.tree_view.selectionModel().currentChanged.connect(
            self.on_tree_selection
        )

        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.parameter_model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.parameter_model.dataChanged.connect(self.on_parameter_changed)

        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        left_splitter.addWidget(self.tree_view)
        left_splitter.addWidget(self.table_view)
        left_splitter.setStretchFactor(1, 1)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.plot_controller.reflectivity_canvas, "Reflectivity")
        tabs.addTab(self.plot_controller.sld_canvas, "SLD")

        main_splitter = QtWidgets.QSplitter()
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(tabs)
        main_splitter.setStretchFactor(1, 1)

        self.fit_button = QtWidgets.QPushButton("Fit (differential evolution)")
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

    def msg(self, text, timeout=8000):
        # non-modal, same reasoning as the production app: routine
        # messages shouldn't interrupt the workflow with a dialog.
        self.statusBar().showMessage(text, timeout)
        print(text)

    def _set_objective(self, new_objective):
        """
        Swap in a new Objective (new data and/or new model) and refresh
        every view from it. This is the one place that needs to know
        about the tree/table/plot all at once -- everywhere else they're
        independent.
        """
        self.objective = new_objective
        structure = new_objective.model.structure

        self.structure_model.set_structure(structure)
        self.tree_view.expandAll()
        self.parameter_model.set_parameters(structure.parameters.flattened())

        self.plot_controller.reset()
        self.plot_controller.update(new_objective)

    def on_load_data_triggered(self):
        path, ok = getopenfilename(
            self, caption="Select a reflectivity dataset"
        )
        if not ok or not path:
            return

        try:
            dataset = ReflectDataset(path)
        except Exception as e:
            self.msg(f"Couldn't load {path!r} as a dataset: {e!r}")
            return

        # keep the current model, just point it at the new dataset
        new_objective = Objective(
            self.objective.model, dataset, use_weights=True
        )
        self._set_objective(new_objective)
        self.msg(f"Loaded dataset from {path}")

    def on_load_model_triggered(self):
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

        # keep the current dataset, just point it at the new model
        new_objective = Objective(model, self.objective.data, use_weights=True)
        self._set_objective(new_objective)
        self.msg(f"Loaded model from {path}")

    def on_save_model_triggered(self):
        path, ok = getsavefilename(
            self, caption="Save model as", basedir="model.pkl"
        )
        if not ok or not path:
            return

        try:
            persistence.save_model(self.objective.model, path)
        except Exception as e:
            self.msg(f"Couldn't save model to {path!r}: {e!r}")
            return

        self.msg(f"Saved model to {path}")

    def on_tree_selection(self, current, previous):
        component = self.structure_model.component_for_index(current)
        if component is None:
            parameters = self.objective.model.structure.parameters.flattened()
        else:
            parameters = component.parameters.flattened()
        self.parameter_model.set_parameters(parameters)

    def on_parameter_changed(self, top_left, bottom_right, roles):
        self.plot_controller.update(self.objective)

    def on_fit_clicked(self):
        if self.fit_controller.running:
            self.fit_controller.abort()
            return
        self.fit_button.setText("Abort")
        self.statusBar().showMessage("Fitting...")
        self.fit_controller.start(
            self.objective,
            method="differential_evolution",
            maxiter=50,
            popsize=10,
            seed=1,
        )

    def on_fit_progress(self, chi2, iterations):
        self.statusBar().showMessage(
            f"chi2={chi2:.6g}   iteration={iterations}"
        )

    def on_fit_finished(self, exc):
        self.fit_button.setText("Fit (differential evolution)")
        if exc is not None:
            self.statusBar().showMessage(f"Fit failed: {exc!r}", 8000)
        else:
            self.statusBar().showMessage("Fit complete", 5000)
            # whatever's currently shown may have changed value
            top_left = self.parameter_model.index(0, 0)
            bottom_right = self.parameter_model.index(
                self.parameter_model.rowCount() - 1,
                self.parameter_model.columnCount() - 1,
            )
            self.parameter_model.dataChanged.emit(top_left, bottom_right)
        self.plot_controller.update(self.objective)


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    objective = build_demo_objective()
    win = MainWindow(objective)
    win.resize(1000, 600)
    win.show()
    return app, win


if __name__ == "__main__":
    app, win = main()
    sys.exit(app.exec())
