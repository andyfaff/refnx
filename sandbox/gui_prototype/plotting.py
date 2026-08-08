"""
PlotController: owns the reflectivity + SLD matplotlib canvases and
redraws them from an Objective. Knows nothing about tree models,
datastores, or anything else in the GUI -- it's handed an objective and
draws it. Contrast with the production app, where
MotofitMainWindow.redraw_data_object_graphs reaches directly into
self.treeModel.datastore.

Uses draw_idle(), not draw() -- see the slider-performance fix in the
production app for why.
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PlotController:
    def __init__(self):
        self.reflectivity_fig = Figure()
        self.reflectivity_canvas = FigureCanvas(self.reflectivity_fig)
        self.reflectivity_ax = self.reflectivity_fig.add_subplot(111)
        self.reflectivity_ax.set_xlabel(r"Q / $\AA^{-1}$")
        self.reflectivity_ax.set_ylabel("R")
        self.reflectivity_ax.set_yscale("log")
        self._data_line = None
        self._fit_line = None

        self.sld_fig = Figure()
        self.sld_canvas = FigureCanvas(self.sld_fig)
        self.sld_ax = self.sld_fig.add_subplot(111)
        self.sld_ax.set_xlabel(r"z / $\AA$")
        self.sld_ax.set_ylabel(r"SLD / $10^{-6}\AA^{-2}$")
        self._sld_line = None

    def update(self, objective):
        dataset = objective.data
        x, y = dataset.x, dataset.y

        if self._data_line is None:
            (self._data_line,) = self.reflectivity_ax.plot(
                x, y, "o", ms=3, label="data"
            )
            (self._fit_line,) = self.reflectivity_ax.plot(
                x, objective.model(x), "-", label="fit"
            )
            self.reflectivity_ax.legend()
        else:
            self._fit_line.set_ydata(objective.model(x))

        self.reflectivity_ax.relim()
        self.reflectivity_ax.autoscale_view()
        self.reflectivity_canvas.draw_idle()

        structure = objective.model.structure
        z, sld = structure.sld_profile()
        if self._sld_line is None:
            (self._sld_line,) = self.sld_ax.plot(z, sld)
        else:
            self._sld_line.set_data(z, sld)

        self.sld_ax.relim()
        self.sld_ax.autoscale_view()
        self.sld_canvas.draw_idle()
