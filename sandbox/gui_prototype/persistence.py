"""
Split persistence: science state (the fittable model) vs session state
(console text, window geometry, ...), saved and loaded independently.

Today's .mtft format pickles both into one dict (datastore, console
history, settings, requirements.txt) in a single pickle.dump call. If
anything in the science half fails to pickle -- e.g. a Spline's cached
scipy PchipInterpolator holding a stale module reference, which is a
real, currently-reproducible bug in the production app -- the whole
save fails, including the session state that had nothing to do with it.
Splitting them means a science-state failure doesn't also cost you your
console log, and vice versa.
"""

import pickle
from pathlib import Path


def save_model(reflect_model, path):
    """Science state: just the fittable model, same idea as the
    production app's existing (and unaffected) actionSave_Model."""
    with open(path, "wb") as f:
        pickle.dump(reflect_model, f)


def load_model(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_session(geometry: bytes, console_text: str, path):
    """Session state: UI-only, never touches refnx/scipy objects, so it
    can't be broken by anything happening on the science side."""
    state = {"geometry": geometry, "console": console_text}
    with open(path, "wb") as f:
        pickle.dump(state, f)


def load_session(path):
    if not Path(path).exists():
        return {"geometry": None, "console": ""}
    with open(path, "rb") as f:
        return pickle.load(f)
