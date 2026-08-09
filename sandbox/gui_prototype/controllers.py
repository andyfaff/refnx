"""
FitController: reusable, testable wrapper around running a refnx fit on
a background thread.

The production retrofit (refnx/reflect/_app/view.py, FitWorker +
_run_in_thread) had to stay *synchronous* from the caller's point of
view, because it was bolted onto existing callers and a test that
expected fit_data_objects() to block until finished. Built from scratch,
there's no such constraint: this is a proper fire-and-forget controller
with `started`/`progress`/`finished` signals, no nested QEventLoop. The
thread-teardown ordering that caused the sequential-fit deadlock in the
retrofit (waiting on the worker's `finished` instead of the QThread's
own `finished`) is still the right lesson and is reused here.
"""

from qtpy import QtCore

from refnx.analysis import CurveFitter


class _FitWorker(QtCore.QObject):
    finished = QtCore.Signal(object)  # Exception or None
    progress = QtCore.Signal(float, int)  # chi2, iteration count

    def __init__(self, objective, method, fit_kws):
        super().__init__()
        self.objective = objective
        self.method = method
        self.fit_kws = dict(fit_kws)
        self._abort = False
        self._iterations = 0

    def request_abort(self):
        # plain bool write/read across threads is fine under the GIL for
        # a single-writer/single-reader flag like this.
        self._abort = True

    def _callback(self, xk, *a, **kw):
        self._iterations += 1
        self.progress.emit(float(self.objective.chisqr(xk)), self._iterations)
        return self._abort

    @QtCore.Slot()
    def run(self):
        exc = None
        try:
            fitter = CurveFitter(self.objective)
            kws = dict(self.fit_kws)
            if self.method != "least_squares":
                kws["callback"] = self._callback
            fitter.fit(method=self.method, **kws)
        except Exception as e:
            exc = e
        self.finished.emit(exc)


class FitController(QtCore.QObject):
    """
    Usage
    -----
    controller = FitController(self)
    controller.progress.connect(on_progress)
    controller.finished.connect(on_finished)
    controller.start(objective, method="differential_evolution", maxiter=100)
    ...
    controller.abort()
    """

    started = QtCore.Signal()
    progress = QtCore.Signal(float, int)
    finished = QtCore.Signal(object)  # Exception or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None

    @property
    def running(self):
        return self._thread is not None

    def start(self, objective, method="differential_evolution", **fit_kws):
        if self.running:
            raise RuntimeError("A fit is already running on this controller")

        # parented to `self` so the QThread's C++ lifetime is anchored by
        # Qt's ownership tree, independent of whether we still hold a
        # Python reference to it once the fit finishes.
        self._thread = QtCore.QThread(self)
        self._worker = _FitWorker(objective, method, fit_kws)
        self._worker.moveToThread(self._thread)
        self._result = {}

        def _capture(exc):
            self._result["exception"] = exc

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress)
        self._worker.finished.connect(_capture)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        # Report "done" only once the QThread has genuinely finished,
        # not as soon as the worker's callable returns: thread.quit()
        # (connected above) still has to be delivered to, and processed
        # by, the worker thread's own event loop before the OS thread
        # actually exits. Reporting done too early risks a dangling
        # QThread that's still tearing down when the next fit starts (or
        # the interpreter exits) -- this exact bug caused a
        # sequential-fit deadlock in the production app's equivalent
        # code before an identical fix.
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()
        self.started.emit()

    def abort(self):
        if self._worker is not None:
            self._worker.request_abort()

    def _on_thread_finished(self):
        exc = self._result.get("exception")
        self._thread = None
        self._worker = None
        self.finished.emit(exc)
