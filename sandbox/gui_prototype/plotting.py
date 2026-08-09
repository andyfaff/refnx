"""
PlotController: owns the reflectivity + SLD matplotlib canvases and
redraws them from a DataStore. Knows nothing about tree models or the
rest of the GUI -- it's handed the datastore and draws every dataset in
it. Contrast with the production app, where
MotofitMainWindow.redraw_data_object_graphs reaches directly into
self.treeModel.datastore.

Uses draw_idle(), not draw() -- see the slider-performance fix in the
production app for why.

Always clears and redraws both axes from scratch on every update() call,
rather than caching line artists and updating their data in place. That
caching (kept from the single-dataset version of this prototype) is a
real optimisation when you're redrawing the *same* dataset repeatedly
(e.g. dragging a slider), but a datastore's contents can change shape
between calls -- a new dataset added, one removed, a differently-sized
file loaded -- and full-redraw is simpler and correct in all those
cases. At this scale (a handful of datasets, no per-frame dragging) the
extra draw cost doesn't matter.
"""

from qtpy.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import (
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure


class PlotController:
    def __init__(self):
        self.reflectivity_fig = Figure()
        self.reflectivity_canvas = FigureCanvas(self.reflectivity_fig)
        self.reflectivity_ax = self.reflectivity_fig.add_subplot(111)
        self.reflectivity_toolbar = NavigationToolbar(self.reflectivity_canvas)

        self.sld_fig = Figure()
        self.sld_canvas = FigureCanvas(self.sld_fig)
        self.sld_ax = self.sld_fig.add_subplot(111)
        self.sld_toolbar = NavigationToolbar(self.sld_canvas)

        # FigureCanvasQTAgg defaults to a Preferred size policy, not
        # Expanding -- Preferred only grows past its size *hint* when a
        # layout has nothing better to do with the space, which isn't
        # a strong enough claim in a QTabWidget/QVBoxLayout stack for
        # the canvas to reliably fill whatever room the tab actually
        # has (e.g. after undocking a QDockWidget frees up space
        # elsewhere in the QMainWindow). Expanding makes that explicit.
        for canvas in (self.reflectivity_canvas, self.sld_canvas):
            canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

        self._reset_axes()

    def _reset_axes(self):
        self.reflectivity_ax.cla()
        self.reflectivity_ax.set_xlabel(r"Q / $\AA^{-1}$")
        self.reflectivity_ax.set_ylabel("R")
        self.reflectivity_ax.set_yscale("log")

        self.sld_ax.cla()
        self.sld_ax.set_xlabel(r"z / $\AA$")
        self.sld_ax.set_ylabel(r"SLD / $10^{-6}\AA^{-2}$")

    def update(self, datastore):
        self._reset_axes()

        for data_object in datastore:
            dataset = data_object.dataset
            model = data_object.model
            x, y = dataset.x, dataset.y

            (line,) = self.reflectivity_ax.plot(
                x, y, "o", ms=3, label=f"{data_object.name} (data)"
            )
            self.reflectivity_ax.plot(
                x,
                model(x),
                "-",
                color=line.get_color(),
                label=f"{data_object.name} (fit)",
            )

            z, sld = model.structure.sld_profile()
            self.sld_ax.plot(
                z, sld, color=line.get_color(), label=data_object.name
            )

        if len(datastore):
            self.reflectivity_ax.legend(fontsize="small")
            self.sld_ax.legend(fontsize="small")

        self.reflectivity_ax.relim()
        self.reflectivity_ax.autoscale_view()
        self.reflectivity_canvas.draw_idle()

        self.sld_ax.relim()
        self.sld_ax.autoscale_view()
        self.sld_canvas.draw_idle()
