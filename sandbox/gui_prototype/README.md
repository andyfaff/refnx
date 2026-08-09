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
the parameter tree shows *every* parameter from *every* loaded dataset
at once, all the time. That wasn't the first design: the first version
filtered the table down to whatever was selected in the tree, which
turned out to be a real problem, not just a cosmetic tradeoff — you
can't multi-select two parameters to link them if they're never visible
at the same time, and linking parameters *across* datasets is a core
co-refinement workflow. So the parameter tree doesn't filter by
navigation-tree *selection* — clicking a tree row expands and highlights
the matching rows without hiding any others. It does filter by the
tree's fit-inclusion *checkbox*, though: unchecking a dataset removes
its parameters entirely, on the basis that if you're not fitting it
right now you don't want its rows cluttering the view. A constraint made
while a dataset was checked survives being unchecked -- constraints live
on the `Parameter` objects, not in the model -- so linking against a
currently-unchecked dataset just means checking it first.

The parameter view is itself a second tree, not a flat table: each
dataset's parameters are grouped by Component (and its own
scale/bkg/dq/q_offset under a synthetic "Model" group), expandable and
collapsible per group, so a large `Structure`'s parameters don't have to
be disambiguated from one long undifferentiated list. Grouping only
changes how rows are organised, not which ones exist — expanding
everything shows exactly the old flat set, and multi-selecting rows to
link them still works across groups and across datasets, since
selection is keyed on `Parameter` identity, never on position in a flat
list.

- **`datastore.py`** — `DataObject` (name + dataset + model + whether
  it's included in the next fit) and `DataStore` (an ordered collection
  of them). The thing the single-dataset version of this prototype was
  missing entirely.
- **`models.py`** — `DataStoreTreeModel` (pure navigation: one generic
  node class per row, `DataObject` at the top level with a checkbox
  controlling `in_fit`, `Component` rows nested underneath, recursing
  into `Stack`s automatically). A second column shows each `DataObject`
  row's chi-squared (`Objective(data_object.model,
  data_object.dataset).chisqr()`, formatted `.4g`) — blank for
  `Component` rows, which don't have one of their own. Not cached:
  `data()` computes it fresh on every call, so `refresh_chi2()` (which
  just emits `dataChanged` for that column) is all a caller needs to
  pick up the latest parameter values, without the far more expensive
  full tree rebuild `set_datastore()` would do. `main.py`'s
  `_update_plots_and_chi2()` calls it alongside every
  `plot_controller.update()` — the two go stale at exactly the same
  moments (any change to a model's parameters or structure) — and
  `on_tree_model_changed` explicitly ignores `dataChanged` confined to
  the chi2 column, since that fires on *every* parameter edit and would
  otherwise trigger an unnecessary parameter-tree rebuild each time.
  `ParameterTableModel` is a second tree:
  Dataset -> [a "Model" group for scale/bkg/dq/q_offset, one group per
  top-level Component, recursing into `Stack`s] -> individual `Parameter`/
  `ComponentProperty` rows, across *every* `DataObject` in the store).
  A `Stack`'s own group holds only its `repeats` Parameter; its children
  get their own nested groups rather than having their parameters
  flattened into the `Stack`'s row, so expand/collapse can tell a
  `Stack`'s own parameter apart from what's inside it. Dependency
  propagation, including across datasets and across groups, lives in
  exactly one place: `ParameterTableModel._notify_dependents` — it only
  ever looks at `Parameter` identity, never which dataset or group a
  parameter came from, so cross-dataset linking falls out of the design
  for free rather than needing special-case code. `link()`/`unlink()`
  constrain a set of selected rows (as `QModelIndex`es, not row numbers —
  a row number alone doesn't identify a row uniquely once rows have
  different parents) to the first one. `index_for(obj)` looks up the
  `QModelIndex` for a specific `Parameter`/`ComponentProperty` directly,
  for driving selection or `setData()` without walking the tree by hand.
  `auto_limits()` mirrors the production app's "Auto adjust limits"
  button exactly: on every currently-*varying* parameter, sets bounds to
  `[0, 2*value]` (or `[2*value, 0]` if `value` is negative — same shape,
  reflected around zero), including the original's quirk of not
  special-casing `value == 0` (a zero-width `[0, 0]` bound).

  `Lower`/`Upper` are blank, and not editable, for any parameter that
  isn't currently varying — a fixed parameter's bounds don't mean
  anything (nothing's being fitted against them), so there's nothing
  worth showing or letting you edit until `Vary` is checked. Toggling
  `Vary` doesn't just refresh its own cell: `setData()` also emits
  `dataChanged` across the `lb`/`ub` columns for that row, so the
  bounds actually appear (or disappear) immediately rather than only
  on the next full rebuild.

  A `σ` column shows `Parameter.stderr`, blank until it's actually been
  set — `CurveFitter.fit()` already computes and sets it on every
  varying parameter after a successful fit, so this needed no new
  fitting logic, only somewhere in the GUI to show it. It goes stale
  the moment anything about the dataset's model changes after that fit,
  though, so editing a parameter's *value* by hand clears `stderr` for
  every parameter in that dataset (`_clear_dataset_stderr`, mirroring
  the production app's `clear_data_object_uncertainties`) — not just
  the one that was touched, since a correlated parameter's uncertainty
  shifts too even though its own value didn't change. Toggling `Vary`
  or nudging a bound doesn't itself invalidate an already-run fit, so
  neither of those touches `stderr`.

  `lb`/`ub` are formatted as strings (`f"{...:.6g}"`), same as `value`
  already was — not just for display consistency, but because it fixes
  a real editing bug: Qt's default delegate inspects the *type* of a
  cell's `EditRole` data to decide what editor to create, and a raw
  Python `float` gets a `QDoubleSpinBox` (2 decimal places, no
  scientific-notation input at all) instead of a plain `QLineEdit`.
  `lb`/`ub` used to return `p.bounds.lb`/`.ub` directly, so typing a
  small bound like `2.123e-5` silently got truncated to `2.12` the
  moment the spinbox's default two-decimal-place validator saw the
  `e-5` it couldn't parse. Formatting as a string keeps every editable
  numeric cell on the same `QLineEdit` path `value` was already using.

  `_boundary_slab_hidden_parameters(structure)` is what keeps
  thickness/iSLD/roughness/volfrac solvent for the fronting medium, and
  thickness/iSLD/volfrac solvent for the backing medium, out of
  `ParameterTableModel` entirely (they're not physically meaningful for
  a semi-infinite Slab) — used while building each Component's group to
  filter its flattened parameter list. Only applies to a Slab that's an
  actual top-level Structure boundary (`structure[0]`/`structure[-1]`);
  a Slab nested inside a `Stack` is never affected, and neither is a
  `Stack` itself (which, as it turns out, refnx doesn't allow as a
  Structure's first/last Component anyway — only `Slab` and friends can
  go there). Since it's the *position* that's hidden, not a specific
  Parameter, dragging a different Slab into the first/last slot correctly
  hides its thickness/iSLD/roughness/volfrac instead and un-hides the old
  one's, the next time the tree rebuilds.

  Not every editable thing on a Component is a `Parameter` --
  `LipidLeaflet.reverse_monolayer` and `Spline.zgrad` are plain bools
  set directly on the object, so `.parameters.flattened()` (which is
  what each Component's group otherwise looks at) can never see them, no
  matter how the filtering changes. `ComponentProperty` wraps one such
  attribute so it can sit in a Component's group alongside its ordinary
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
  attribute.

  `DataStoreTreeModel` rows are also directly editable: double-click a
  Component (not a `DataObject` — its name is a fixed identity, the
  `DataStore`'s key) to rename it, e.g. "Slab" → "Silicon". That's
  just `component.name = value` in `setData()`; nothing separate has
  to propagate the new name into the parameter tree, since
  `ParameterTableModel`'s group label (`_group_label`/
  `_component_label`) reads the same live `.name` off the same
  `Component` object -- the two trees just both end up looking at it.
  Clearing the name back to `""` falls back to the type name again
  (`_component_label`'s existing behaviour for an unnamed Component),
  rather than showing a blank row.

  `DataStoreTreeModel` also owns structural editing of a Structure:
  `insert_component()`, `remove_component()`, `move_component()`, plus
  drag-and-drop (`mimeData()`/`dropMimeData()`) for reordering top-level
  Components by dragging them in the tree. The top-level fronting/backing
  Slabs are *pinned*: `insert_component()`, `remove_component()`, and
  `move_component()` all refuse, unconditionally, to touch position 0 or
  -1 of a top-level Structure — not "only if the result wouldn't have a
  Slab there" but "never, period" — so neither of those two Slabs can
  ever be removed, dragged elsewhere, displaced by another Component
  being dragged into their slot, or displaced by a *new* Component being
  inserted into their slot either. `insert_component()` optionally takes
  a `container` argument — a `Stack` found somewhere within the
  Structure — to insert into, since a `Stack` is a list in its own right
  (`UserList`) and has no first/last restriction at all; that's the only
  way anything ever ends up *inside* a `Stack`'s own contents (fixed a
  real gap: Add Component previously only ever inserted into the
  top-level Structure, so a `Stack` could be added to the GUI but nothing
  could ever be added *to* it). The drag-and-drop implementation
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

  `_FitWorker` has no C++ parent — `moveToThread()` requires that, Qt
  refuses to move a parented object to another thread — so PySide's
  shiboken bindings govern its C++ lifetime by Python reference count
  rather than a parent-child tree. `worker.finished` is connected to
  `worker.deleteLater()`, which only *schedules* a deferred deletion;
  the fix for a real, reported segfault after repeated fits was
  realising `FitController` was clearing its own `self._worker`
  reference (in `_on_thread_finished`) before that scheduled deletion
  had actually run — so Python's GC deleted the C++ object directly
  instead, out from under the still-pending deferred delete
  ("`QObject: shared QObject was deleted directly`", then a segfault
  the next time anything touched the dangling pointer). `self._worker`
  is now only cleared from `_on_worker_destroyed`, connected to the
  worker's own `destroyed` signal — which Qt emits synchronously as
  part of the object's actual destruction — so the Python reference
  never gets dropped ahead of Qt's own teardown. The `QThread` itself
  doesn't have this problem: it's parented to the controller (`self`),
  so its C++ lifetime is anchored by Qt's ownership tree regardless of
  what Python references still point to it.
- **`plotting.py`** — `PlotController`, redraws reflectivity/SLD from a
  whole `DataStore`, overlaying every dataset with a shared legend.
  Doesn't know about tree models, unlike
  `MotofitMainWindow.redraw_data_object_graphs` today. Uses
  `draw_idle()`, not `draw()`. Always clears and redraws from scratch
  rather than caching line artists, because a datastore's shape (how
  many datasets, how many points each) can change between calls in a
  way a single fixed dataset never did. Also owns
  `reflectivity_toolbar`/`sld_toolbar` — matplotlib's standard
  pan/zoom/save `NavigationToolbar2QT`, one per canvas — since a
  toolbar is inherently plot-specific, not part of the rest of the
  GUI's concerns; `main.py`'s `_plot_tab()` just stacks each canvas
  under its own toolbar for the two `QTabWidget` pages (a tab page can
  only hold one widget, so canvas+toolbar need a small container).
- **`persistence.py`** — model state and session state (console text,
  window geometry) saved independently, so a pickling failure in one
  can't take down the other. Motivated by a real, reproducible bug: an
  `.mtft` save currently fails entirely if a `Spline`'s cached scipy
  `PchipInterpolator` holds a stale module reference, taking the console
  history down with it even though that has nothing to do with the
  spline.
- **`dialogs.py`** — `AddComponentDialog` (pick a dataset, a *container*
  — the top level of its Structure, or any `Stack` found anywhere within
  it, listed by `_containers()`/`_iter_stacks()` — a Component type, and
  a position within that container) and `default_component(kind)`. Each
  `Stack` in the container dropdown is labelled with its *structural
  position* (e.g. "stack (Stack at position 1)", or "position 1 → 0"
  for one nested inside another) rather than just its `.name` — a
  `Stack`'s name is just a label a user typed in (or left blank), not a
  unique identifier, so two Stacks sharing a name (or both unnamed)
  would otherwise be indistinguishable in the list. The
  position spinbox's range depends on the chosen container: `[1, N-1]`
  for the top level (position 0 or N would create a new first/last
  Component — pinned, so not offered at all), `[0, N]` for a `Stack`
  (no such restriction). Mostly doesn't have per-type parameter-entry
  fields — `Spline` needs knot arrays, and replicating the production
  app's dedicated `SplineDialog` is a separate, larger piece of work.
  Instead it builds most Component types with reasonable placeholder
  values from `default_component(kind)`, adds it, and lets you edit
  every one of those values afterward through the ordinary parameter
  tree — since that tree is generic (it just flattens whatever
  `.parameters` a Component happens to expose), no bespoke editing UI
  is needed once the object exists, only a bespoke *constructor* for
  the ones that need it.

  `LipidLeaflet` is the exception: choosing it in `AddComponentDialog`
  brings up `LipidLeafletDialog` (a follow-up dialog, not inline —
  cancelling it cancels the whole Add Component operation, same as
  cancelling the position dialog itself would) to pick a known lipid,
  and a measurement condition, from refnx's own library
  (`refnx/reflect/_app/lipids.json` — 22 lipids with literature
  head/tail volumes, chemical formulas, and references) rather than
  always landing with the same fixed placeholder. It reuses that
  library's own `Lipid` class directly
  (`refnx.reflect._app._lipid_leaflet.Lipid` — pure Python, no Qt
  dependency despite living next to the dialog that uses it) for the
  neutron-scattering-length calculation, rather than reimplementing
  formula parsing and SLD-from-formula physics that already exist and
  are already correct. Deliberately a lighter dialog than the
  production one, though: no structure-image display, no x-ray/energy
  toggle (neutron-only), no live cross-updating spinboxes between area-
  per-molecule and thickness — a picked lipid is only a starting point,
  same as every other Component's placeholder values, and every
  resulting value (including `reverse_monolayer`, which the production
  dialog doesn't expose either) is still editable afterward through the
  ordinary parameter tree once it's actually been added.
- **`delegates.py`** — `SelectAllDelegate`, installed as the parameter
  tree's item delegate. Selects the existing text the moment a cell
  starts editing, so typing immediately replaces the whole value
  instead of merging with whatever was (inconsistently, in a way that
  depends on platform double-click word-boundary behaviour) selected
  around the click — motivated by small, precise values like `2.123e-5`
  being hard to enter cleanly into the Value box.
- **`main.py`** — wires it all into a `QMainWindow`: dataset tree
  (top-left, checkboxes control fit inclusion, drag Components to
  reorder them) drives expanding and highlighting rows in the parameter
  tree (bottom-left, grouped by Component and collapsible per group,
  always shows everything for every checked dataset — select rows across
  groups and datasets and use **Link Selected**/**Unlink Selected**/**Link
  Equivalent Parameters...** to constrain them). `_refresh_parameter_tree_view()`
  — called everywhere the parameter tree's shape or content changes,
  including at startup — expands everything and sizes every column but
  the last to fit its content: a `QTreeView`'s default column widths
  are small, fixed pixel values with no relation to what's actually in
  them, so left alone every column (Name, Value, `σ`, Lower, Upper)
  shows up truncated on every launch, needing a manual drag to widen
  each one every single time. Sizing the columns to content isn't
  enough on its own, though — Qt's default splitter split is based on
  each side's size *hint*, which still leaves the whole left pane
  cramped regardless of what's inside it, so `main_splitter.setSizes()`
  starts it off noticeably wider than an even split too. Reflectivity and SLD
  plots overlaying every dataset (right), a Fit button that builds a
  `GlobalObjective` from whichever datasets are checked and runs DE on a
  background thread — first checking that every varying parameter in
  that objective has finite bounds (DE can't work without them), and
  refusing to start, with a status-bar message naming the offending
  parameters, if not. `_set_fit_running_ui_state()` disables the
  navigation tree, parameter tree, Auto Limits, and the File/Structure/
  Parameters menus for the duration of a fit — not cosmetic:
  `CurveFitter.fit()` continuously reads *and writes* the fitted
  model's `Parameter` objects from the background thread
  (`Objective.setp()` every iteration, `chisqr()` every progress
  callback), so editing/renaming/linking/restructuring the same models
  from the GUI thread at the same time is a real, unsynchronized data
  race between two threads touching the same Python/refnx objects —
  implicated in a reported crash after running several fits in a row.
  Re-enabled only once `on_fit_finished` confirms the background thread
  has actually stopped, not any earlier. Starts up with two datasets
  (`e361r.txt` and
  `e365r.txt` from `refnx.analysis.tests`) so multi-dataset behaviour is
  visible immediately. **File** menu: *Load Data...* (adds one or more new
  datasets — doesn't replace what's already loaded — each starting from
  a copy of the currently-selected dataset's model, or a bare default if
  none is selected), *Reload Datasets* (`Ctrl+R`; re-reads every loaded
  dataset from whatever file it was originally loaded from — a live
  experiment still appending counts to the same file, say. No separate
  path-tracking needed for this: `ReflectDataset`/`Data1D` already
  record their own source file as `.filename` when constructed from
  one, and already have a `.refresh()` that re-reads from exactly that
  path — `on_reload_data_triggered()` just calls it per dataset,
  skipping (not erroring on) any dataset that isn't backed by a file,
  and catching a failed reload for one dataset without stopping the
  rest), *Load Model...* / *Save Model...* (apply to
  whichever dataset is currently selected in the tree), *Remove Selected
  Dataset*. **Structure** menu: *Add Component...* (`Ctrl++`; choose
  dataset, container, type, and position — a `QSpinBox`, not just
  "append"), *Remove Selected Component* (`Ctrl+-`; also unlinks any
  parameter, anywhere, that depended on something in the removed
  Component, via `unlink_dependents`).
  **Parameters** menu: *Link Selected Parameters* (`Ctrl+1`), *Unlink
  Selected Parameters* (`Ctrl+2`) — plain menu actions now, not buttons,
  same shortcuts as the production app — and *Link Equivalent
  Parameters...* (`Ctrl+3`, see below).
  `on_structure_changed`, connected to `DataStoreTreeModel.modelReset`,
  is what refreshes the parameter tree and plots after *any* structural
  edit — add, remove, or a drag-and-drop reorder — without each of those
  three call sites needing to remember to do it themselves.

  *Link Equivalent Parameters...* mirrors the production app's action of
  the same name: select one or more parameters, pick which other loaded
  datasets to link across in a checklist dialog
  (`DatasetMultiSelectDialog`, which remembers and pre-selects whichever
  datasets were picked last time — linking several parameters in a row
  against the same set of datasets is the common case, and re-picking
  that set from scratch every time would be tedious), and it locates
  the parameter at the same *structural position* in each of them and
  links everything together —
  assuming those datasets share the same model shape (same number of
  Components, same total parameter count; `models.same_model_shape()`
  checks this up front and refuses with one clear message rather than
  linking the wrong thing). `models.equivalent_parameter(source,
  parameter, target)` does the actual lookup: it builds an address for
  `parameter` — which top-level Component (recursing into `Stack`s) and
  which of that Component's own parameters/properties — via
  `_dataset_parameter_addresses()`, then resolves that same address
  against the target dataset. Deliberately structural rather than
  positional-in-the-visible-tree, so it's unaffected by which rows
  `_boundary_slab_hidden_parameters()` happens to be hiding. Matches the
  production app's actual (slightly surprising) semantics exactly:
  *every* selected parameter, plus every equivalent found for each of
  them, all end up constrained to one master — the first selected
  parameter — rather than each selected parameter getting its own
  independent link group. Select parameters representing the same
  physical quantity (that's the intended use), and this is exactly what
  you want; select two different quantities in one go and they'll get
  linked to *each other* too, same as production.

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

No MCMC, no dedicated `Spline` parameter-entry dialog (see `dialogs.py`
above — you can still add one, just with placeholder values you then
edit in the parameter tree; `LipidLeaflet` *does* get a real, if
lighter-weight, dialog now — see `LipidLeafletDialog` above), no undo,
no session
save/restore UI even though `persistence.py` supports it, no per-dataset
visibility toggle separate from fit-inclusion (checking a dataset plots
it, fits it, *and* shows its parameters in the tree -- deliberately, per
feedback while building this: the production app treats "visible on the
plot" and "currently fitting" as separate concerns, but here a single
checkbox controls plot/fit/tree visibility together. Splitting them
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
  the tree at once, not just one dataset's;
- the navigation tree's chi2 column matches `Objective(...).chisqr()`
  for each dataset and is blank for Component rows; editing a value
  updates it without triggering a full parameter-tree rebuild;
- every parameter tree column but the last (which stretches) gets sized
  to fit its content on startup, rather than sitting at Qt's default
  fixed width;
- the left pane starts out noticeably wider than an even split, not
  just at Qt's size-hint-driven default;
- the Reflectivity and SLD tabs each carry their own matplotlib
  `NavigationToolbar2QT`, wired to the right canvas and actually
  parented into the window, not just constructed and discarded;
- parameters are grouped by Component (a "Model" group for
  scale/bkg/dq/q_offset, one group per top-level Component in Structure
  order) with only each Component's own rows as its children -- and a
  `Stack`'s own group holds just `repeats`, with its child Components
  getting their own nested groups rather than having their parameters
  flattened in;
- selecting a tree row expands and highlights (scrolls to/selects) the
  right rows in the parameter tree without hiding any others — proving
  the "always show everything" design actually holds, now across
  groups as well as datasets;
- linking two parameters *across* datasets (and across different
  Component groups) works, including dependency propagation on edit;
- the first Slab's thickness/iSLD/roughness/volfrac and the last
  Slab's thickness/iSLD/volfrac are hidden from the tree, a middle
  Slab is untouched, a Slab nested in a `Stack` is never treated as a
  boundary even if the `Stack` itself sits mid-structure, and dragging
  a different Slab into the first slot moves *which* parameters are
  hidden rather than being tied to a fixed Slab;
- `LipidLeaflet.reverse_monolayer` and `Spline.zgrad` show up as
  editable checkbox rows and actually flip the real attribute when
  toggled through the model; a `ComponentProperty` row mixed into a
  `link()`/`auto_limits()` selection is skipped rather than crashing;
- Auto Limits sets `[0, 2*value]` (or reflected, for a negative value)
  on every *varying* parameter and leaves fixed ones alone, both called
  directly and through an actual button click;
- `Lower`/`Upper` are blank and not editable for a fixed parameter, show
  the real bounds and become editable the moment it's varying, and
  toggling `Vary` refreshes both columns immediately rather than only
  on the next rebuild;
- Fit refuses to start, and never touches `FitController`, if any
  varying parameter has a non-finite bound — and doesn't false-positive
  on the demo datastore's already-finite bounds;
- unchecking a dataset in the tree removes it from
  `DataStore.fitted_objects()` *and* hides its rows in the parameter
  tree, and a constraint made before unchecking survives (it lives on
  the `Parameter`, not the tree) and reappears when re-checked;
- `FitController` runs a `GlobalObjective` built from the checked
  datasets asynchronously, and total chi² drops;
- a real fit sets and displays `Parameter.stderr` in the `σ` column
  (blank beforehand), and editing a value by hand afterward clears
  `stderr` for every parameter in *that* dataset but leaves another
  dataset's untouched, while toggling `Vary` or a bound leaves it
  alone;
- the navigation tree, parameter tree, Auto Limits, and the
  model-mutating menus are all disabled the moment a fit starts and
  re-enabled only once it's genuinely finished;
- running several full fit cycles back to back (start, wait for
  `finished`, force a GC pass, repeat) settles into the same clean
  state every time — the regression test for a reported segfault after
  clicking Fit several times in a row; the GC pass matters, since the
  actual bug was a premature Python-side reference drop racing Qt's
  own `deleteLater()`-scheduled deletion of the fit worker;
- Load Data *adds* a dataset rather than replacing the store, and
  survives a dataset with a different number of points (the actual bug
  this exposed: `PlotController` used to cache line artists and update
  them in place, which breaks the moment the x-array's shape changes —
  now it always redraws from scratch);
- Reload Datasets calls `.refresh()` on every dataset that has a source
  file, skips (without erroring on) one that doesn't, and a failed
  reload for one dataset doesn't stop the rest from reloading; the
  action carries the `Ctrl+R` shortcut;
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
- removing a dataset actually removes it from the navigation tree and
  the parameter tree.

`test_structure_editing.py` covers Add/Remove/reorder Component:

- adding a Component through the (faked, non-modal) dialog inserts it
  at the chosen position and the parameter tree picks up its
  parameters automatically, with no explicit refresh call in the
  handler -- proving the `modelReset` → `on_structure_changed` cascade
  actually does its job;
- inserting at position 0, or at `len(structure)` (the new-last
  position), is rejected regardless of Component type and the
  Structure is left untouched;
- adding a Component *into* a Stack grows the Stack, not the top-level
  Structure, and position 0 (or the very end) of a Stack is allowed --
  no first/last restriction there;
- `AddComponentDialog` itself: the container dropdown lists "Top
  level" plus every `Stack` found in the chosen dataset's Structure
  (including nested ones), and the position spinbox's range is `[1,
  N-1]` for the top level vs `[0, N]` for a `Stack`;
- two Stacks sharing a name stay distinguishable in that dropdown --
  each is labelled with its own structural position (e.g. "position 1"
  vs "position 1 → 1" for one nested inside the other);
- removing a Component works, is refused when a dataset row (not a
  Component) is selected, and unlinks a dependent parameter in a
  *different* dataset;
- the top-level fronting and backing Slab can each never be removed,
  no matter what would end up taking their place;
- a drag-and-drop reorder (driven directly through
  `mimeData()`/`dropMimeData()`, since simulating real mouse-drag events
  isn't practical headless) between two *interior* positions produces
  the expected new order and triggers the same tree/plot refresh;
- a reorder that would put a non-`Slab` first or last is rejected
  (`dropMimeData` returns `False`, order unchanged);
- the fronting Slab itself can't be dragged elsewhere, and no other
  Component can be dragged into the first or last position, even
  another `Slab` — the boundary Slabs are pinned, not just type-checked;
- a Component nested inside a `Stack` can't be dragged at all
  (`mimeData()` returns `None` for it);
- renaming a Component through the navigation tree updates `.name` and
  is picked up by the parameter tree's group label for it; clearing the
  name falls back to the type name; a dataset row isn't editable at all.

`test_link_equivalent.py` covers Link Equivalent Parameters:

- `equivalent_parameter()` finds the matching Parameter by structural
  position across two same-shape datasets (both a Component parameter
  and a top-level model parameter like `bkg`), and returns `None` for a
  `Parameter` that isn't part of either model at all;
- `same_model_shape()` catches a Component-count mismatch;
- selecting a parameter, picking a target dataset in the (faked,
  non-modal) checklist dialog, and triggering the action links the
  selected parameter to its equivalent in the target;
- a pre-existing constraint on the about-to-become-master parameter is
  cleared first, avoiding constraint recursion;
- the dataset picker opens with nothing pre-selected the first time,
  then with whichever datasets were picked last time pre-selected on
  every subsequent open;
- mismatched model shapes refuse with a message and link nothing;
- no selection, or only one dataset loaded, refuses before even opening
  the dataset picker;
- a `ComponentProperty` row in the selection is skipped rather than
  crashing, same as ordinary Link Selected;
- the **Parameters** menu has all three actions with the right
  `Ctrl+1`/`Ctrl+2`/`Ctrl+3` shortcuts, and Link/Unlink Selected still
  work the same as before now that they're actions instead of buttons.

`test_delegates.py` covers the small-value-entry fix:

- `SelectAllDelegate` selects a cell's existing text the moment editing
  starts;
- typing a small value like `2.123e-6` immediately after opening the
  editor (no manual select-all first) replaces the old text cleanly
  and commits correctly;
- the `lb`/`ub` cells use a plain `QLineEdit`, not a `QDoubleSpinBox` —
  the regression test for the actual bug: Qt's default delegate
  creates a spinbox (2 decimal places, no scientific-notation support)
  whenever a cell's `EditRole` data is a raw `float` rather than a
  string, which silently truncated a typed bound like `2.123e-5` down
  to `2.12`;
- `data()` for `lb`/`ub` returns a formatted string, not a raw float.

`test_lipid_leaflet_dialog.py` covers the lipid picker:

- the lipid combo lists all 22 lipids from `lipids.json` plus the
  blank placeholder; OK stays disabled until a real lipid is chosen;
- picking a lipid populates its conditions and chemical name;
- `component()` builds a `LipidLeaflet` whose head/tail volumes,
  thicknesses (derived from the chosen area-per-molecule), and
  scattering lengths match what `Lipid.neutron_scattering_lengths()`
  computes directly, not just what the dialog displays;
- choosing "LipidLeaflet" in `AddComponentDialog` brings up the lipid
  picker as a follow-up dialog, and the Component it returns is what
  actually gets inserted; cancelling the picker aborts the whole Add
  Component operation, adding nothing.

```bash
pip install pytest-qt   # if not already installed
QT_QPA_PLATFORM=offscreen python3 -m pytest sandbox/gui_prototype/ -v
```
