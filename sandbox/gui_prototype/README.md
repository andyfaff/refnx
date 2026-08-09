# Motofit GUI architecture prototype

A from-scratch sketch of an alternative to `refnx.reflect._app`'s GUI
architecture, written during a review of the existing app, then
generalized to multi-dataset co-refinement after early feedback showed
the single-dataset version couldn't support cross-dataset parameter
linking. **Not a replacement for Motofit** — it's a standalone, runnable
demonstration of a few specific structural changes.

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

This prototype splits navigation from editing instead — and, crucially,
the parameter table shows *every* parameter from *every* loaded dataset
at once, all the time. That wasn't the first design: the first version
filtered the table down to whatever was selected in the tree, which
turned out to be a real problem, not just a cosmetic tradeoff — you
can't multi-select two parameters to link them if they're never visible
at the same time, and linking parameters *across* datasets is a core
co-refinement workflow. So the table doesn't filter by tree *selection*
— clicking a tree row highlights the matching table rows without hiding
any others. It does filter by the tree's fit-inclusion *checkbox*,
though: unchecking a dataset removes its parameters from the table
entirely, on the basis that if you're not fitting it right now you
don't want its rows cluttering the view. A constraint made while a
dataset was checked survives being unchecked -- constraints live on the
`Parameter` objects, not in the table -- so linking against a
currently-unchecked dataset just means checking it first.

- **`datastore.py`** — `DataObject` (name + dataset + model + whether
  it's included in the next fit) and `DataStore` (an ordered collection
  of them). The thing the single-dataset version of this prototype was
  missing entirely.
- **`models.py`** — `DataStoreTreeModel` (pure navigation: one generic
  node class per row, `DataObject` at the top level with a checkbox
  controlling `in_fit`, `Component` rows nested underneath, recursing
  into `Stack`s automatically) and `ParameterTableModel` (flat, one row
  per `Parameter`, across *every* `DataObject` in the store, with a
  `Dataset` column so you can tell which one each row belongs to).
  Dependency propagation, including across datasets, lives in exactly
  one place: `ParameterTableModel._rows_depending_on` — it only ever
  looks at `Parameter` identity, never which dataset a parameter came
  from, so cross-dataset linking falls out of the flat-table design for
  free rather than needing special-case code. `link()`/`unlink()`
  constrain a set of selected rows to the first one.
- **`controllers.py`** — `FitController`, a reusable `QObject` wrapping
  `CurveFitter` on a background `QThread`. Properly async
  (`started`/`progress`/`finished` signals) — no nested `QEventLoop`,
  which the production retrofit needed only to preserve old synchronous
  callers. Works identically whether it's handed a plain `Objective`
  (one dataset) or a `GlobalObjective` (several) — `CurveFitter` doesn't
  care, so the controller doesn't need to either.
- **`plotting.py`** — `PlotController`, redraws reflectivity/SLD from a
  whole `DataStore`, overlaying every dataset with a shared legend.
  Doesn't know about tree models, unlike
  `MotofitMainWindow.redraw_data_object_graphs` today. Uses
  `draw_idle()`, not `draw()`. Always clears and redraws from scratch
  rather than caching line artists, because a datastore's shape (how
  many datasets, how many points each) can change between calls in a
  way a single fixed dataset never did.
- **`persistence.py`** — model state and session state (console text,
  window geometry) saved independently, so a pickling failure in one
  can't take down the other. Motivated by a real, reproducible bug: an
  `.mtft` save currently fails entirely if a `Spline`'s cached scipy
  `PchipInterpolator` holds a stale module reference, taking the console
  history down with it even though that has nothing to do with the
  spline.
- **`main.py`** — wires it all into a `QMainWindow`: dataset tree
  (top-left, checkboxes control fit inclusion) drives highlighting in
  the parameter table (bottom-left, always shows everything — select
  rows across datasets and hit **Link Selected**), reflectivity and SLD
  plots overlaying every dataset (right), a Fit button that builds a
  `GlobalObjective` from whichever datasets are checked and runs DE on a
  background thread. Starts up with two datasets (`e361r.txt` and
  `e365r.txt` from `refnx.analysis.tests`) so multi-dataset behaviour is
  visible immediately. **File** menu: *Load Data...* (adds one or more
  new datasets — doesn't replace what's already loaded — each starting
  from a copy of the currently-selected dataset's model, or a bare
  default if none is selected), *Load Model...* / *Save Model...*
  (apply to whichever dataset is currently selected in the tree),
  *Remove Selected Dataset*.

## What's deliberately not here

No MCMC, no drag-and-drop layer reordering, no lipid/spline component
editors, no undo, no session save/restore UI even though
`persistence.py` supports it, no per-dataset visibility toggle separate
from fit-inclusion (checking a dataset plots it, fits it, *and* shows
its parameters in the table -- deliberately, per feedback while building
this: the production app treats "visible on the plot" and "currently
fitting" as separate concerns, but here a single checkbox controls
plot/fit/table visibility together. Splitting them back out into
independent toggles is a reasonable next step if "shown but not fitted"
turns out to matter in practice).
The point was to prove out the model-splitting, multi-dataset, and
threading ideas cheaply, not to rebuild the whole app.

## Running it

```bash
cd sandbox/gui_prototype
python3 main.py                              # normal, with a window
QT_QPA_PLATFORM=offscreen python3 main.py     # headless
```

## Tests

`test_prototype.py` (pytest + pytest-qt) covers the things worth proving
actually work, not just compile:

- both startup datasets are loaded and *all* of their parameters are in
  the table at once, not just one dataset's;
- selecting a tree row highlights (scrolls to/selects) the right table
  rows without hiding any others — proving the "always show everything"
  design actually holds;
- linking two parameters *across* datasets works, including dependency
  propagation on edit;
- unchecking a dataset in the tree removes it from
  `DataStore.fitted_objects()` *and* hides its rows in the parameter
  table, and a constraint made before unchecking survives (it lives on
  the `Parameter`, not the table) and reappears when re-checked;
- `FitController` runs a `GlobalObjective` built from the checked
  datasets asynchronously, and total chi² drops;
- Load Data *adds* a dataset rather than replacing the store, and
  survives a dataset with a different number of points (the actual bug
  this exposed: `PlotController` used to cache line artists and update
  them in place, which breaks the moment the x-array's shape changes —
  now it always redraws from scratch);
- Load Model / Save Model apply only to the selected dataset, leaving
  others untouched;
- removing a dataset actually removes it from the tree and table.

```bash
pip install pytest-qt   # if not already installed
QT_QPA_PLATFORM=offscreen python3 -m pytest sandbox/gui_prototype/test_prototype.py -v
```
