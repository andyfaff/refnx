"""
Split persistence: science state (datasets, models, and everything
needed to recreate the analysis) vs session state (window geometry and
dock layout), saved and loaded independently.

Production's .mtft format pickles both into one dict (datastore,
console history, settings, requirements.txt) in a single pickle.dump
call. If anything in the science half fails to pickle -- e.g. a
Spline's cached scipy PchipInterpolator holding a stale module
reference, which is a real, currently-reproducible bug in the
production app -- the whole save fails, including the session state
that had nothing to do with it. Splitting them means a science-state
failure doesn't also cost you your window layout, and vice versa.

Session state also doesn't need pickle at all -- QMainWindow.saveState()
/ saveGeometry() already produce opaque Qt byte blobs, so QSettings
(Qt's own small per-OS-native store: an .ini file on Linux, the
registry on Windows, a plist on macOS) is a better fit than a custom
pickle file for that half.
"""

import pickle

import refnx
from qtpy.QtCore import QSettings

# Every module a legitimate model/experiment file needs a class or
# function from: refnx's own objects (models, parameters, bounds,
# datasets), numpy/scipy (array data, PDF-bounded parameters'
# distributions), pathlib (a dataset's remembered source file), and
# this prototype's own DataObject/DataStore.
_SAFE_MODULE_ROOTS = ("refnx", "numpy", "scipy", "pathlib", "datastore")


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickling isn't "loading data" -- the file gets to name any
    importable callable it likes and have it invoked with attacker-
    chosen arguments (the standard pickle RCE technique: reduce to
    e.g. os.system("...") or builtins.eval("...")), which matters here
    because .mtft/.pkl files are the kind of thing that gets emailed
    or shared between collaborators, not just written by yourself.
    Restricting find_class() to modules a model/experiment file
    actually needs closes that off, without needing to enumerate every
    individual class -- new refnx/scipy/numpy classes are allowed
    automatically, only classes from *other* modules (the ones no
    legitimate file has a reason to reference) are refused."""

    def find_class(self, module, name):
        root = module.split(".", 1)[0]
        if root not in _SAFE_MODULE_ROOTS:
            raise pickle.UnpicklingError(
                f"Refusing to unpickle {module}.{name}: {root!r} isn't "
                f"one of {_SAFE_MODULE_ROOTS}, so this doesn't look like "
                f"a legitimate experiment/model file."
            )
        return super().find_class(module, name)


def _restricted_load(f):
    return _RestrictedUnpickler(f).load()


def save_model(reflect_model, path):
    """Just a single fittable model, same idea as the production app's
    existing (and unaffected) actionSave_Model -- handy for reusing one
    dataset's model as a starting point elsewhere, distinct from
    save_experiment's "recreate everything" below."""
    with open(path, "wb") as f:
        pickle.dump(reflect_model, f)


def load_model(path):
    with open(path, "rb") as f:
        return _restricted_load(f)


def save_experiment(datastore, transform_form, path):
    """Science state: every loaded dataset and its model (structure,
    parameters, bounds, constraints), which datasets are checked for
    fitting (DataObject.in_fit, part of the datastore itself), and the
    transform analysis is being done with -- everything needed to
    recreate the whole analysis, as a single pickle."""
    state = {
        "datastore": datastore,
        "transform_form": transform_form,
        "refnx.version": refnx.version.version,
    }
    with open(path, "wb") as f:
        pickle.dump(state, f)


def load_experiment(path):
    with open(path, "rb") as f:
        state = _restricted_load(f)

    if not isinstance(state, dict) or "datastore" not in state:
        raise ValueError(f"{path} is not an experiment file")

    return state["datastore"], state.get("transform_form", "lin")


_SETTINGS_ORGANISATION = "refnx"
_SETTINGS_APPLICATION = "motofit-prototype"


def save_window_state(window):
    """Session state: dock layout and window geometry. Deliberately
    not called from MainWindow itself (e.g. closeEvent) -- every test
    in test_prototype.py constructs a bare MainWindow, and having that
    read/write the developer's real, OS-level QSettings on every test
    run would make the suite depend on (and clobber) whatever's
    actually saved there. Only main() calls this, via
    app.aboutToQuit, so persistence is opt-in to the real app rather
    than tied to the widget's own lifecycle."""
    settings = QSettings(_SETTINGS_ORGANISATION, _SETTINGS_APPLICATION)
    settings.setValue("geometry", window.saveGeometry())
    settings.setValue("windowState", window.saveState())


def restore_window_state(window):
    settings = QSettings(_SETTINGS_ORGANISATION, _SETTINGS_APPLICATION)
    geometry = settings.value("geometry")
    if geometry is not None:
        window.restoreGeometry(geometry)
    window_state = settings.value("windowState")
    if window_state is not None:
        window.restoreState(window_state)
