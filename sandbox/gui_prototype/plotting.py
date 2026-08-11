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

from qtpy.QtWidgets import QApplication, QSizePolicy
from qtpy.QtGui import QPalette

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
        self._apply_palette()

        # Matplotlib figures default to a white background regardless
        # of the OS/Qt theme, so switching to e.g. dark mode leaves the
        # plots looking wrong on their own -- follow the app's palette
        # instead, live, the same way the rest of the window already
        # does. QApplication is a singleton that outlives any one
        # PlotController (e.g. one per test in test_prototype.py), so
        # this connection must be torn down explicitly -- see close()
        # -- or it keeps every PlotController (and its now-deleted Qt
        # canvases) referenced for the rest of the process, and a later
        # theme change would call back into a dead widget: the same
        # class of bug as the production app's MyReflectivityGraphs
        # "already deleted" crash (draw_idle firing after the C++
        # object was destroyed).
        QApplication.instance().paletteChanged.connect(self._apply_palette)

    def close(self):
        """Disconnects from the application's paletteChanged signal.
        Must be called before this PlotController's canvases are
        destroyed (MainWindow.closeEvent does this) -- see the note in
        __init__ for why leaving the connection live is unsafe."""
        app = QApplication.instance()
        if app is not None:
            try:
                app.paletteChanged.disconnect(self._apply_palette)
            except (RuntimeError, TypeError):
                pass

    def _apply_palette(self, *_args):
        """Recolors the figure/axes chrome -- background, ticks, axis
        labels, spines, and any existing legend -- to match the current
        Qt palette. Only chrome colors change; plotted line colors are
        left alone, since those come from matplotlib's own color cycle
        and don't depend on the theme.

        Uses Base/Text, not Window/WindowText -- Window is the *outer*
        chrome color (toolbars, menus, dock titlebars), a light grey
        rather than white on most light-mode desktop themes; Base is
        the role actually meant for a content/document area like this
        one (the same role a QLineEdit or QListView's own background
        uses), white in light mode and dark in dark mode as expected.
        """
        palette = QApplication.instance().palette()
        bg = palette.color(QPalette.ColorRole.Base).name()
        fg = palette.color(QPalette.ColorRole.Text).name()

        for fig, ax in (
            (self.reflectivity_fig, self.reflectivity_ax),
            (self.sld_fig, self.sld_ax),
        ):
            fig.patch.set_facecolor(bg)
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            for spine in ax.spines.values():
                spine.set_color(fg)

            legend = ax.get_legend()
            if legend is not None:
                legend.get_frame().set_facecolor(bg)
                legend.get_frame().set_edgecolor(fg)
                for text in legend.get_texts():
                    text.set_color(fg)

        self.reflectivity_canvas.draw_idle()
        self.sld_canvas.draw_idle()

    def _reset_axes(self, transform=None):
        self.reflectivity_ax.cla()
        self.reflectivity_ax.set_xlabel(r"Q / $\AA^{-1}$")
        self.reflectivity_ax.set_ylabel("R")
        # 'logY' already pulls R onto a roughly linear scale itself, so
        # the axis stays linear there; everything else -- untransformed
        # data ('lin', and no transform at all) and 'YX4' alike -- still
        # spans many orders of magnitude and needs a log axis to be
        # readable.
        form = transform.form if transform is not None else "lin"
        if form == "logY":
            self.reflectivity_ax.set_yscale("linear")
        else:
            self.reflectivity_ax.set_yscale("log")

        self.sld_ax.cla()
        self.sld_ax.set_xlabel(r"z / $\AA$")
        self.sld_ax.set_ylabel(r"SLD / $10^{-6}\AA^{-2}$")

    def update(self, datastore, transform=None):
        self._reset_axes(transform)

        for data_object in datastore:
            dataset = data_object.dataset
            model = data_object.model
            x, y, y_err = dataset.x, dataset.y, dataset.y_err
            yfit = model(x)
            if transform is not None:
                y, y_err = transform(x, y, y_err)
                yfit, _ = transform(x, yfit)

            # only datasets with real uncertainties get error bars --
            # a dataset without them (y_err is None) just shows points,
            # rather than errorbar() drawing zero-length bars that look
            # like real (perfect) measurements.
            if y_err is None:
                (line,) = self.reflectivity_ax.plot(
                    x, y, "o", ms=3, label=f"{data_object.name} (data)"
                )
                color = line.get_color()
            else:
                container = self.reflectivity_ax.errorbar(
                    x,
                    y,
                    yerr=y_err,
                    marker="o",
                    ms=3,
                    linestyle="",
                    label=f"{data_object.name} (data)",
                )
                color = container[0].get_color()

            self.reflectivity_ax.plot(
                x,
                yfit,
                "-",
                color=color,
                label=f"{data_object.name} (fit)",
            )

            z, sld = model.structure.sld_profile()
            self.sld_ax.plot(z, sld, color=color, label=data_object.name)

        if len(datastore):
            self.reflectivity_ax.legend(fontsize="small")
            self.sld_ax.legend(fontsize="small")

        self.reflectivity_ax.relim()
        self.reflectivity_ax.autoscale_view()

        self.sld_ax.relim()
        self.sld_ax.autoscale_view()

        # cla() in _reset_axes() above wipes axes-level styling
        # (facecolor, ticks, spines), and the legend just created didn't
        # exist yet the last time colors were applied -- reapply now
        # that both axes are back in their final state for this
        # update(). Also issues the draw_idle() calls for both canvases.
        self._apply_palette()
