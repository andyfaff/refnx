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
  constrain a set of selected rows to the first one. `auto_limits()`
  mirrors the production app's "Auto adjust limits" button exactly: on
  every currently-*varying* parameter, sets bounds to `[0, 2*value]`
  (or `[2*value, 0]` if `value` is negative — same shape, reflected
  around zero), including the original's quirk of not special-casing
  `value == 0` (a zero-width `[0, 0]` bound).

  `_boundary_slab_hidden_parameters(structure)` is what keeps
  thickness/iSLD/roughness for the fronting medium, and thickness/iSLD
  for the backing medium, out of `ParameterTableModel` entirely (they're
  not physically meaningful for a semi-infinite Slab) — used by
  `set_datastore()` to filter the flattened parameter list before
  building `self._rows`. Only applies to a Slab that's an actual
  top-level Structure boundary (`structure[0]`/`structure[-1]`); a Slab
  nested inside a `Stack` is never affected, and neither is a `Stack`
  itself (which, as it turns out, refnx doesn't allow as a Structure's
  first/last Component anyway — only `Slab` and friends can go there).
  Since it's the *position* that's hidden, not a specific Parameter,
  dragging a different Slab into the first/last slot correctly hides
  its thickness/iSLD/roughness instead and un-hides the old one's, the
  next time the table rebuilds.

  Not every editable thing on a Component is a `Parameter` --
  `LipidLeaflet.reverse_monolayer` and `Spline.zgrad` are plain bools
  set directly on the object, so `.parameters.flattened()` (which is
  all `ParameterTableModel` used to look at) can never see them, no
  matter how the table's filtering changes. `ComponentProperty` wraps
  one such attribute so it can sit in `self._rows` next to ordinary
  `Parameter` rows, rendered as a checkbox in the Value column exactly
  like the `Vary` column already does for `Parameter.vary`.
  `COMPONENT_PROPERTIES` is a small, explicit registry (component type
  -> attribute names) rather than auto-discovering "interesting-looking"
  attributes by introspection, which would as easily surface internal
  implementation details as something worth editing — mirrors the
  production app's `PropertyNode` usage in `LipidLeafletNode`/
  `SplineNode`. Everywhere a `Parameter`-only operation exists --
  linking, `auto_limits()`, dependency propagation -- a
  `ComponentProperty` row in the selection is silently skipped rather
  than crashing, since none of those concepts apply to a plain
  attribute. `_iter_components()` walks into `Stack`s by hand to find
  properties nested inside one, since (unlike `Parameter`s, which
  `Component.parameters` already flattens through a `Stack`
  automatically) a plain attribute has no such built-in flattening.

  `DataStoreTreeModel` also owns structural editing of a Structure:
  `insert_component()`, `remove_component()`, `move_component()`, plus
  drag-and-drop (`mimeData()`/`dropMimeData()`) for reordering top-level
  Components by dragging them in the tree. All three funnel through one
  `_check_boundary()` check (a Structure's first and last Component must
  be a `Slab`; a nested `Stack` has no such rule) rather than
  reimplementing that rule three times. The drag-and-drop implementation
  deliberately doesn't serialise row-index *paths* into the dragged MIME
  data the way `treeview_gui_model.dropMimeData` does today — that's
  brittle if the tree's shape changes between drag-start and drop.
  Since the drag and the drop happen inside the same running model
  instance, it just remembers the live `Component` object being dragged
  as a plain attribute instead, so a move is always resolved against
  current, valid state. `models.unlink_dependents(datastore,
  removed_parameters)` is a free function, not a method on
  `ParameterTableModel`, because it has to search *every* dataset for a
  dependent parameter, including ones currently hidden by an unchecked
  fit-inclusion box — `ParameterTableModel` only ever knows about
  checked datasets. Used both when a Component is removed and (see
  `main.py`) whenever a dataset's whole model is replaced — Load Model
  had the same gap for a while: it swapped `data_object.model` for a
  new one without unlinking whatever used to depend on the old one's
  parameters, found and fixed while wiring up Copy Model (below), which
  is the same operation with a different source.
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
- **`dialogs.py`** — `AddComponentDialog` (pick a dataset, a Component
  type, and a position) and `default_component(kind)`. Doesn't have
  per-type parameter-entry fields — a real `LipidLeaflet` needs nine
  required numbers, `Spline` needs knot arrays, and replicating the
  production app's dedicated `LipidLeafletDialog`/`SplineDialog` is a
  separate, larger piece of work. Instead it builds the Component with
  reasonable placeholder values, adds it, and lets you edit every one of
  those values afterward through the ordinary parameter table — since
  that table is generic (it just flattens whatever `.parameters` a
  Component happens to expose), no bespoke editing UI is needed once the
  object exists, only a bespoke *constructor* for the ones that need it.
- **`main.py`** — wires it all into a `QMainWindow`: dataset tree
  (top-left, checkboxes control fit inclusion, drag Components to
  reorder them) drives highlighting in the parameter table (bottom-left,
  always shows everything — select rows across datasets and hit **Link
  Selected**/**Unlink Selected**/**Auto Limits**), reflectivity and SLD
  plots overlaying every dataset (right), a Fit button that builds a
  `GlobalObjective` from whichever datasets are checked and runs DE on a
  background thread — first checking that every varying parameter in
  that objective has finite bounds (DE can't work without them), and
  refusing to start, with a status-bar message naming the offending
  parameters, if not. Starts up with two datasets (`e361r.txt` and
  `e365r.txt` from `refnx.analysis.tests`) so multi-dataset behaviour is
  visible immediately. **File** menu: *Load Data...* (adds one or more new
  datasets — doesn't replace what's already loaded — each starting from
  a copy of the currently-selected dataset's model, or a bare default if
  none is selected), *Load Model...* / *Save Model...* (apply to
  whichever dataset is currently selected in the tree), *Remove Selected
  Dataset*. **Structure** menu: *Add Component...* (choose dataset, type,
  and position — a `QSpinBox`, not just "append"), *Remove Selected
  Component* (also unlinks any parameter, anywhere, that depended on
  something in the removed Component, via `unlink_dependents`).
  `on_structure_changed`, connected to `DataStoreTreeModel.modelReset`,
  is what refreshes the parameter table and plots after *any* structural
  edit — add, remove, or a drag-and-drop reorder — without each of those
  three call sites needing to remember to do it themselves.

  Right-clicking the tree shows a context menu with **Copy a model to
  here** — deliberately matching the production app's
  `OpenMenu`/`copy_from_action` rather than the File-menu dialog this
  started as: pick which dataset's model to copy via a plain
  `QInputDialog.getItem` (a "which model?" combo, same as the production
  app), and it overwrites the model of *every* dataset currently
  selected in the tree (right-click extends whatever multi-selection was
  already made, same as native platform context menus), batched into one
  refresh at the end rather than one per target. Goes through the same
  `unlink_dependents` logic as Component removal — and as Load Model,
  which had the identical gap for a while: it swapped
  `data_object.model` for a new one without unlinking whatever used to
  depend on the old one's parameters, caught and fixed while building
  this. `on_copy_model_to_here()` and `_build_tree_context_menu()` are
  split out from `on_tree_context_menu()` specifically so tests can
  drive the actual copy logic and check the menu's contents without
  calling the real `QMenu.exec()` — that's a blocking, modal call to
  actual Qt/C++ event-loop machinery, not something monkeypatching from
  Python reaches, and the only way found for it to fail on this was
  silently hanging forever in a headless test run instead of raising.

## What's deliberately not here

No MCMC, no dedicated LipidLeaflet/Spline parameter-entry dialogs (see
`dialogs.py` above — you can still add either, just with placeholder
values you then edit in the table), no undo, no session save/restore UI
even though `persistence.py` supports it, no per-dataset visibility
toggle separate from fit-inclusion (checking a dataset plots it, fits
it, *and* shows its parameters in the table -- deliberately, per
feedback while building this: the production app treats "visible on the
plot" and "currently fitting" as separate concerns, but here a single
checkbox controls plot/fit/table visibility together. Splitting them
back out into independent toggles is a reasonable next step if "shown
but not fitted" turns out to matter in practice). Drag-and-drop
reordering only works on *top-level* Components of a Structure, not
ones nested inside a `Stack` -- *removing* a nested Component does work
(via the same "Remove Selected Component" action; the Slab-boundary
rule just doesn't apply there, since Stacks don't require one at either
end), but there's no way to drag one, or to move a Component between
datasets, or into/out of a Stack. The point was to prove out the
model-splitting,
multi-dataset, structural-editing, and threading ideas cheaply, not to
rebuild the whole app.

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
- the first Slab's thickness/iSLD/roughness and the last Slab's
  thickness/iSLD are hidden from the table, a middle Slab is untouched,
  a Slab nested in a `Stack` is never treated as a boundary even if the
  `Stack` itself sits mid-structure, and dragging a different Slab into
  the first slot moves *which* parameters are hidden rather than being
  tied to a fixed Slab;
- `LipidLeaflet.reverse_monolayer` and `Spline.zgrad` show up as
  editable checkbox rows and actually flip the real attribute when
  toggled through the model; a `ComponentProperty` row mixed into a
  `link()`/`auto_limits()` selection is skipped rather than crashing;
- Auto Limits sets `[0, 2*value]` (or reflected, for a negative value)
  on every *varying* parameter and leaves fixed ones alone, both called
  directly and through an actual button click;
- Fit refuses to start, and never touches `FitController`, if any
  varying parameter has a non-finite bound — and doesn't false-positive
  on the demo datastore's already-finite bounds;
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
- Load Model unlinks any parameter, in any dataset, that depended on
  the model it's replacing (the pre-existing gap fixed alongside Copy
  Model);
- the tree's right-click menu offers "Copy a model to here" (checked by
  inspecting the built `QMenu`'s contents directly, not by driving a
  real click through the blocking `QMenu.exec()`);
- Copy Model copies by value, not reference (mutating the source
  afterward doesn't touch the copy), applies to *every* dataset selected
  in the tree at once (not just one), does nothing (rather than
  crashing) if nothing's selected, and also unlinks dependents of
  whatever model it's replacing;
- removing a dataset actually removes it from the tree and table.

`test_structure_editing.py` covers Add/Remove/reorder Component:

- adding a Component through the (faked, non-modal) dialog inserts it
  at the chosen position and the parameter table picks up its
  parameters automatically, with no explicit refresh call in the
  handler -- proving the `modelReset` → `on_structure_changed` cascade
  actually does its job;
- adding a non-`Slab` Component at position 0 is rejected and the
  Structure is left untouched;
- removing a Component works, is refused when a dataset row (not a
  Component) is selected, and unlinks a dependent parameter in a
  *different* dataset;
- a drag-and-drop reorder (driven directly through
  `mimeData()`/`dropMimeData()`, since simulating real mouse-drag events
  isn't practical headless) produces the expected new order and
  triggers the same table/plot refresh;
- a reorder that would put a non-`Slab` first or last is rejected
  (`dropMimeData` returns `False`, order unchanged);
- a Component nested inside a `Stack` can't be dragged at all
  (`mimeData()` returns `None` for it).

```bash
pip install pytest-qt   # if not already installed
QT_QPA_PLATFORM=offscreen python3 -m pytest sandbox/gui_prototype/ -v
```
