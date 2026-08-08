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

import refnx.analysis
from refnx.dataset import ReflectDataset
from refnx.reflect import SLD, ReflectModel
from refnx.analysis import Objective

from models import StructureTreeModel, ParameterTableModel
from controllers import FitController
from plotting import PlotController


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
