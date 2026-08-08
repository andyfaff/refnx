# Motofit GUI architecture prototype

A from-scratch sketch of an alternative to `refnx.reflect._app`'s GUI
architecture, written during a review of the existing app. **Not a
replacement for Motofit** — it's a standalone, runnable demonstration of
a few specific structural changes, scoped to one dataset/model so the
ideas are easy to see without wading through the full app.

## What this replaces, and why

`refnx/reflect/_app/treeview_gui_model.py` has one `QAbstractItemModel`
where every component type (`SlabNode`, `LipidLeafletNode`, `ParNode`,
`PropertyNode`, ...) is a hand-written subclass with its own
`data()`/`setData()`/`flags()`. That's the root of several bugs found
during the review: hardcoded row/column filtering
(`TreeFilter.filterAcceptsRow` assuming `row == 2` means "the dq/q
row"), and linked-parameter `dataChanged` propagation reimplemented
separately in `unlink_dependent_parameters`, `link_action`, and the
params-slider handler (and missing entirely in one of those three until
this review caught it).

This prototype splits navigation from editing instead:

- **`models.py`** — `StructureTreeModel` (pure navigation: one generic
  node class, recurses into `Stack`s automatically, no parameter data)
  and `ParameterTableModel` (flat, one row per `Parameter`, built by
  calling `.parameters.flattened()` on whatever's selected). Dependency
  propagation lives in exactly one place:
  `ParameterTableModel._rows_depending_on`.
- **`controllers.py`** — `FitController`, a reusable `QObject` wrapping
  `CurveFitter` on a background `QThread`. Properly async
  (`started`/`progress`/`finished` signals) — no nested `QEventLoop`,
  which the production retrofit needed only to preserve old synchronous
  callers.
- **`plotting.py`** — `PlotController`, redraws reflectivity/SLD from an
  `Objective`. Doesn't know about tree models or datastores, unlike
  `MotofitMainWindow.redraw_data_object_graphs` today. Uses
  `draw_idle()`, not `draw()`.
- **`persistence.py`** — model state and session state (console text,
  window geometry) saved independently, so a pickling failure in one
  can't take down the other. Motivated by a real, reproducible bug: an
  `.mtft` save currently fails entirely if a `Spline`'s cached scipy
  `PchipInterpolator` holds a stale module reference, taking the console
  history down with it even though that has nothing to do with the
  spline.
- **`main.py`** — wires it all into a `QMainWindow`: structure tree
  (top-left) drives a flat parameter table (bottom-left), reflectivity
  and SLD plots in tabs (right), a Fit button running DE on a background
  thread. Starts up with `e361r.txt` from `refnx.analysis.tests` (same
  dataset the main test suite already uses), and has a **File** menu —
  *Load Data...* (swap in a new dataset, keep the current model), *Load
  Model...* (swap in a pickled `ReflectModel`, keep the current
  dataset), *Save Model...* (via `persistence.save_model`).

## What's deliberately not here

Single dataset/model at a time only (no `DataObject`/`DataStore` layer,
no multi-dataset global fits, no MCMC, no drag-and-drop reordering, no
lipid/spline component editors, no undo, no session save/restore UI even
though `persistence.py` supports it). The point was to prove out the
model-splitting and threading ideas cheaply, not to rebuild the whole
app. If this direction is worth pursuing for real, those are the next
things to design, not to copy-paste from here.

## Running it

```bash
cd sandbox/gui_prototype
python3 main.py                              # normal, with a window
QT_QPA_PLATFORM=offscreen python3 main.py     # headless
```

## Tests

`test_prototype.py` (pytest + pytest-qt) covers the things worth proving
actually work, not just compile:

- selecting a tree row narrows the parameter table to that component;
- editing a value updates both the edited row *and* a row that's
  constrained to depend on it;
- `FitController.start()` returns immediately (genuinely async) and a
  real DE fit against `e361r.txt` reduces chi²;
- loading a dataset with a *different* number of points doesn't crash
  the next redraw (this is what `PlotController.reset()` exists for —
  its `update()` fast path assumes the x-array is unchanged since the
  last call, so a genuinely different dataset needs its cached line
  artists dropped first);
- loading a model keeps the current dataset, and vice versa;
- a saved model round-trips through `persistence.load_model`.

```bash
pip install pytest-qt   # if not already installed
QT_QPA_PLATFORM=offscreen python3 -m pytest sandbox/gui_prototype/test_prototype.py -v
```
