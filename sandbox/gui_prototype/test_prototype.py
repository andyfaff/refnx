import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import gc
import sys
from importlib import resources

sys.path.insert(0, os.path.dirname(__file__))

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

import refnx.reflect.tests
from refnx.reflect import SLD, ReflectModel
from refnx.analysis import Objective

import persistence
from datastore import DataObject
from main import build_demo_datastore, MainWindow, _default_model


def _chisqr(data_object):
    return Objective(data_object.model, data_object.dataset).chisqr()


def test_multiple_datasets_all_displayed(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    # two datasets loaded at startup, both shown in the tree...
    assert win.tree_model.rowCount() == 2

    # ...and every one of their parameters visible in the table at once,
    # not just whichever is currently selected
    dataset_names_in_table = {name for name, _ in win.parameter_model._rows}
    assert dataset_names_in_table == set(datastore.names)
    # 24 params x 2 datasets, minus 7 hidden per dataset (thick/isld/
    # rough/vfsolv for the first Slab, thick/isld/vfsolv for the last)
    assert win.parameter_model.leaf_count() == 34


def test_navigation_tree_shows_chi2_per_dataset(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    chi2_col = win.tree_model.COLUMNS.index("chi2")
    for row, name in enumerate(datastore.names):
        idx = win.tree_model.index(row, chi2_col)
        assert win.tree_model.data(idx) == f"{_chisqr(datastore[name]):.4g}"

    # a Component row (nested under a dataset) has no chi2 of its own
    do_index = win.tree_model.index(0, 0)
    component_index = win.tree_model.index(0, chi2_col, do_index)
    assert win.tree_model.data(component_index) is None


def test_editing_a_value_refreshes_chi2_without_rebuilding_parameter_tree(
    qtbot, monkeypatch
):
    # chi2 changing is just data() being re-queried for one column, not
    # a reason to tear down and rebuild the (much more expensive)
    # parameter tree -- that only needs to happen for a checkbox toggle
    # or a rename, see on_tree_model_changed
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    rebuild_calls = []
    monkeypatch.setattr(
        win.parameter_model,
        "set_datastore",
        lambda ds: rebuild_calls.append(ds),
    )

    chi2_col = win.tree_model.COLUMNS.index("chi2")
    chi2_idx = win.tree_model.index(0, chi2_col)
    before = win.tree_model.data(chi2_idx)

    thick = datastore["e361r"].model.structure[-2].thick
    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index_for(thick, value_col)
    win.parameter_model.setData(idx, str(thick.value + 50))

    after = win.tree_model.data(chi2_idx)
    assert after != before
    assert rebuild_calls == []


def test_parameter_tree_columns_sized_to_content_on_startup(
    qtbot, monkeypatch
):
    # a QTreeView's default column widths are small, fixed pixel values
    # unrelated to content -- left alone, Name/Value/sigma/Lower/Upper
    # all show up too narrow to read on startup, forcing a manual drag
    # to widen them every time. Both the parameter tree and the
    # navigation tree are QTreeViews, so the patch is class-wide --
    # filter to just the one under test.
    resized = []
    monkeypatch.setattr(
        QtWidgets.QTreeView,
        "resizeColumnToContents",
        lambda self, col: resized.append((self, col)),
    )

    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    last_col = win.parameter_model.columnCount() - 1  # stretches, not resized
    table_resized = [col for view, col in resized if view is win.table_view]
    assert table_resized == list(range(last_col))


def test_navigation_tree_dataset_column_sized_to_content_on_startup(
    qtbot, monkeypatch
):
    resized = []
    monkeypatch.setattr(
        QtWidgets.QTreeView,
        "resizeColumnToContents",
        lambda self, col: resized.append((self, col)),
    )

    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    tree_resized = [col for view, col in resized if view is win.tree_view]
    assert tree_resized == [0]  # chi2 (the last column) stretches instead


def test_left_panes_are_independently_dockable(qtbot):
    # each left-hand pane is a real QDockWidget, not a fixed splitter
    # panel -- a splitter panel can never float loose of the main
    # window, a QDockWidget can, and can do so independently of the
    # other one
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert isinstance(win.structure_dock, QtWidgets.QDockWidget)
    assert isinstance(win.parameters_dock, QtWidgets.QDockWidget)
    assert win.structure_dock.widget() is win.tree_view
    assert (
        win.parameters_dock.widget().findChild(QtWidgets.QTreeView)
        is win.table_view
    )

    assert (
        win.dockWidgetArea(win.structure_dock)
        == QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
    )
    assert (
        win.dockWidgetArea(win.parameters_dock)
        == QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
    )

    floatable = QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
    for dock in (win.structure_dock, win.parameters_dock):
        assert dock.features() & floatable

    # undocking actually works, not just the feature flag being set
    assert not win.structure_dock.isFloating()
    win.structure_dock.setFloating(True)
    assert win.structure_dock.isFloating()
    # the parameters pane is untouched by floating the structure one
    assert not win.parameters_dock.isFloating()


def test_left_panes_start_wider_than_the_plots(qtbot):
    # Qt's default dock sizing is based on each pane's size hint, which
    # leaves them cramped even once their columns are auto-sized to fit
    # -- the docks need to start off wider, not just the columns
    # within them
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)

    assert win.structure_dock.width() > 400
    assert win.parameters_dock.width() > 400


def test_plot_canvases_use_an_expanding_size_policy(qtbot):
    # FigureCanvasQTAgg defaults to Preferred, not Expanding -- that's
    # not a strong enough claim on space for the canvas to reliably
    # fill a QTabWidget page, especially once undocking a QDockWidget
    # frees up room elsewhere in the QMainWindow that the canvas is
    # supposed to grow into
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    expanding = QtWidgets.QSizePolicy.Policy.Expanding
    for canvas in (
        win.plot_controller.reflectivity_canvas,
        win.plot_controller.sld_canvas,
    ):
        sp = canvas.sizePolicy()
        assert sp.horizontalPolicy() == expanding
        assert sp.verticalPolicy() == expanding


def test_plots_expand_into_the_space_a_floated_dock_frees_up(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)

    central = win.centralWidget()
    width_before = central.width()

    win.structure_dock.setFloating(True)
    win.parameters_dock.setFloating(True)
    qtbot.wait(50)

    assert central.width() > width_before
    # the central widget is the whole window's width now that neither
    # dock is claiming any of it
    assert central.width() == win.width()


def test_plots_keep_tracking_window_resizes_after_undocking(qtbot):
    # regression test for feedback that the graph area stopped
    # dynamically expanding/contracting with the window once both
    # left-hand panes were undocked -- not just a one-off snapshot
    # right after undocking, but continuing to track further resizes
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)

    win.structure_dock.setFloating(True)
    win.parameters_dock.setFloating(True)
    qtbot.wait(50)

    central = win.centralWidget()

    win.resize(1600, 900)
    qtbot.wait(50)
    assert central.width() == win.width()
    assert central.width() > 1500

    win.resize(900, 600)
    qtbot.wait(50)
    assert central.width() == win.width()
    assert central.width() < 950


def test_plots_keep_tracking_resizes_with_only_one_pane_undocked(qtbot):
    # distinct from the "both undocked" case above: with the other
    # pane still docked, the central widget's left edge sits flush
    # against it (not against the window edge), and needs to keep
    # tracking window resizes relative to *that* moving target
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)

    win.structure_dock.setFloating(True)
    qtbot.wait(50)

    central = win.centralWidget()
    left_edge = central.x()
    assert left_edge > 0  # flush against the still-docked Parameters pane

    win.resize(1600, 900)
    qtbot.wait(50)
    assert central.x() == left_edge  # position unaffected
    assert central.width() == win.width() - left_edge

    win.resize(900, 600)
    qtbot.wait(50)
    assert central.width() == win.width() - left_edge


def test_plots_track_resizes_again_after_redocking(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)

    win.structure_dock.setFloating(True)
    win.parameters_dock.setFloating(True)
    qtbot.wait(50)
    win.structure_dock.setFloating(False)
    win.parameters_dock.setFloating(False)
    qtbot.wait(50)

    central = win.centralWidget()
    win.resize(1500, 850)
    qtbot.wait(50)
    assert central.width() < win.width()  # docks are back, sharing space
    assert central.width() > 0


def test_undocking_triggers_a_central_widget_relayout(qtbot, monkeypatch):
    # topLevelChanged is what's supposed to prompt QMainWindowLayout to
    # reconsider how much space the central widget owns -- this checks
    # the wiring fires, independent of what the actual resulting size
    # ends up being (covered by the tests above)
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    calls = []
    monkeypatch.setattr(
        win, "_do_relayout_central_widget", lambda: calls.append(1)
    )

    win.structure_dock.setFloating(True)
    qtbot.wait(10)
    assert calls == [1]

    win.parameters_dock.setFloating(True)
    qtbot.wait(10)
    assert calls == [1, 1]


def test_every_window_resize_forces_a_real_layout_pass(qtbot, monkeypatch):
    # regression test: QMainWindowLayout was observed to stop tracking
    # *further* window resizes for the central widget once both
    # left-hand docks were floating -- not just miss the first one
    # right after undocking, but stay stuck from then on. resizeEvent()
    # forces layout().invalidate()+activate() on every resize now,
    # rather than trusting QMainWindowLayout to recompute on its own.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    win.show()

    calls = []
    monkeypatch.setattr(
        win, "_do_relayout_central_widget", lambda: calls.append(1)
    )

    win.resize(1000, 700)
    qtbot.wait(10)
    assert calls  # at least one relayout forced by the resize itself

    calls.clear()
    win.resize(800, 600)
    qtbot.wait(10)
    assert calls  # and again on a second, independent resize


def test_fit_button_lives_in_the_parameters_dock(qtbot):
    # fitting is a parameter-tree action -- the button belongs with the
    # parameters it changes, not with the plots, so it travels with the
    # Parameters dock if that gets undocked
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert win.parameters_dock.widget().isAncestorOf(win.fit_button)
    assert not win.centralWidget().isAncestorOf(win.fit_button)


def test_reflectivity_and_sld_tabs_have_a_matplotlib_toolbar(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

    assert win.plot_controller.reflectivity_toolbar.canvas is (
        win.plot_controller.reflectivity_canvas
    )
    assert (
        win.plot_controller.sld_toolbar.canvas
        is win.plot_controller.sld_canvas
    )
    assert isinstance(
        win.plot_controller.reflectivity_toolbar, NavigationToolbar2QT
    )
    # both toolbars are actually parented into the tab widgets, not just
    # constructed and discarded
    assert set(win.findChildren(NavigationToolbar2QT)) == {
        win.plot_controller.reflectivity_toolbar,
        win.plot_controller.sld_toolbar,
    }


def test_boundary_slab_parameters_hidden(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    structure = datastore["e361r"].model.structure
    first, last = structure[0], structure[-1]
    shown = win.parameter_model._row_of  # Parameter -> row, only shown ones

    # first Slab: thickness, iSLD, roughness, and volfrac solvent are
    # all hidden
    assert first.thick not in shown
    assert first.sld.imag not in shown
    assert first.rough not in shown
    assert first.vfsolv not in shown
    # ...but its SLD is still shown
    assert first.sld.real in shown

    # last Slab: thickness, iSLD, and volfrac solvent are hidden, but
    # roughness stays -- that's a physically meaningful interface,
    # unlike the first Slab's
    assert last.thick not in shown
    assert last.sld.imag not in shown
    assert last.vfsolv not in shown
    assert last.rough in shown
    assert last.sld.real in shown

    # a middle Slab is untouched
    middle = structure[1]
    assert middle.thick in shown
    assert middle.sld.imag in shown
    assert middle.rough in shown


def test_boundary_hiding_survives_a_rejected_reorder(qtbot):
    # the first/last Slab can never be displaced (see
    # test_structure_editing.py's boundary-pinning tests), so dragging a
    # different Slab into the first position is rejected outright, and
    # the original boundary hiding is left exactly as it was.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    structure = datastore["e361r"].model.structure
    original_first = structure[0]
    polymer = structure[2]

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(2, 0, do_index)  # polymer
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, QtCore.Qt.DropAction.MoveAction, 0, 0, do_index
    )
    assert not ok
    assert structure[0] is original_first

    shown = win.parameter_model._row_of
    assert original_first.sld.real in shown
    assert original_first.thick not in shown
    assert polymer.thick in shown  # still an ordinary, visible middle Slab


def test_nested_stack_slab_not_treated_as_boundary(qtbot):
    from refnx.reflect import SLD, Stack

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    inner_slab = SLD(4.0)(5, 1)
    stack = Stack([inner_slab], name="stack")
    # a Stack can only legally sit in the *middle* of a Structure --
    # refnx itself requires the first/last Component to be a Slab (or
    # MixedSlab/MagneticSlab) -- so this inserts it between the first
    # and second components, not at position 0.
    do.model.structure.insert(1, stack)

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    shown = win.parameter_model._row_of
    # the Stack itself isn't a Slab, so nothing about it is hidden, and
    # the Slab *inside* it -- despite being "first" within the Stack --
    # isn't a top-level Structure boundary, so it's untouched too
    assert inner_slab.thick in shown
    assert inner_slab.sld.imag in shown
    assert inner_slab.rough in shown


def test_lipid_leaflet_reverse_monolayer_exposed_and_editable(qtbot):
    # LipidLeaflet.reverse_monolayer is a plain bool attribute, not a
    # Parameter -- .parameters.flattened() would never see it, so this
    # is what ComponentProperty exists for.
    from dialogs import default_component

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    leaflet = default_component("LipidLeaflet")
    assert leaflet.reverse_monolayer is False
    do.model.structure.insert(2, leaflet)  # a legal, middle position

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    props = [
        obj
        for name, obj in win.parameter_model._rows
        if name == "e361r"
        and getattr(obj, "attr_name", None) == "reverse_monolayer"
    ]
    assert len(props) == 1
    prop = props[0]

    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index_for(prop, value_col)

    assert (
        win.parameter_model.data(idx, Qt.ItemDataRole.CheckStateRole)
        == Qt.CheckState.Unchecked
    )

    ok = win.parameter_model.setData(
        idx, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole
    )
    assert ok
    assert leaflet.reverse_monolayer is True
    assert (
        win.parameter_model.data(idx, Qt.ItemDataRole.CheckStateRole)
        == Qt.CheckState.Checked
    )


def test_spline_zgrad_exposed(qtbot):
    from dialogs import default_component

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    spline = default_component("Spline")
    do.model.structure.insert(2, spline)

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    rows = [
        (name, obj)
        for name, obj in win.parameter_model._rows
        if getattr(obj, "attr_name", None) == "zgrad"
    ]
    assert len(rows) == 1


def test_component_property_rows_ignored_by_link_and_auto_limits(qtbot):
    # a property row mixed into a selection shouldn't crash link() or
    # auto_limits() -- they only apply to real Parameters
    from dialogs import default_component

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    leaflet = default_component("LipidLeaflet")
    do.model.structure.insert(2, leaflet)

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    property_obj = next(
        obj
        for name, obj in win.parameter_model._rows
        if name == "e361r"
        and getattr(obj, "attr_name", None) == "reverse_monolayer"
    )
    parameter_obj = next(
        obj
        for name, obj in win.parameter_model._rows
        if name == "e361r" and hasattr(obj, "vary")
    )
    property_index = win.parameter_model.index_for(property_obj)
    parameter_index = win.parameter_model.index_for(parameter_obj)

    # should not raise, and the property row is simply skipped
    win.parameter_model.link([property_index, parameter_index])
    win.parameter_model.auto_limits()


def test_parameters_grouped_by_component(qtbot):
    # the point of the tree restructuring: each top-level Component
    # gets its own collapsible group row, with only *its own*
    # parameters as children -- not one large flat list mixing
    # everything together.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do_index = win.parameter_model.index(0, 0)  # e361r dataset row
    structure = datastore["e361r"].model.structure

    # children: one "Model" group, then one group per top-level
    # Component, in Structure order
    assert win.parameter_model.rowCount(do_index) == 1 + len(structure)

    model_group_index = win.parameter_model.index(0, 0, do_index)
    assert win.parameter_model.data(model_group_index) == "Model"
    assert win.parameter_model.rowCount(model_group_index) == 4

    # si (fronting, boundary-hidden down to just `sld`), sio2 and
    # polymer (untouched middle Slabs, 5 params each), d2o (backing,
    # hidden down to `sld` + `rough`)
    expected_counts = [1, 5, 5, 2]
    for i, (component, count) in enumerate(zip(structure, expected_counts)):
        comp_index = win.parameter_model.index(i + 1, 0, do_index)
        assert comp_index.internalPointer().obj is component
        assert win.parameter_model.rowCount(comp_index) == count


def test_stack_group_nests_its_children_separately(qtbot):
    # a Stack's own group holds only `repeats` -- its children's
    # parameters don't get flattened into the Stack's own group, they
    # get their own nested group, so expand/collapse can tell a
    # Stack's own parameter apart from what's inside it.
    from refnx.reflect import SLD, Stack

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    inner = SLD(4.0)(5, 1)
    stack = Stack([inner], name="stack", repeats=2)
    do.model.structure.insert(1, stack)  # a legal, middle position

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do_index = win.parameter_model.index(0, 0)
    stack_group_index = win.parameter_model.index(2, 0, do_index)
    assert win.parameter_model.data(stack_group_index) == "stack"
    # 2 children: the `repeats` leaf, plus the inner Slab's own nested
    # group -- not the inner Slab's 5 parameters flattened in here too
    assert win.parameter_model.rowCount(stack_group_index) == 2

    repeats_index = win.parameter_model.index(0, 0, stack_group_index)
    assert repeats_index.internalPointer().obj is stack.repeats

    inner_group_index = win.parameter_model.index(1, 0, stack_group_index)
    assert inner_group_index.internalPointer().obj is inner
    assert win.parameter_model.rowCount(inner_group_index) == 5


def test_tree_selection_highlights_without_hiding_other_rows(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    total_before = win.parameter_model.leaf_count()

    # select the second dataset's third component (polymer)
    e365_index = win.tree_model.index(1, 0)
    polymer_index = win.tree_model.index(2, 0, e365_index)
    win.tree_view.setCurrentIndex(polymer_index)

    # nothing should have been hidden/filtered out of the table
    assert win.parameter_model.leaf_count() == total_before

    # but the table's selection should now be exactly that component's
    # rows, and they should all belong to e365r
    selected_nodes = {
        idx.sibling(idx.row(), 0).internalPointer()
        for idx in win.table_view.selectedIndexes()
    }
    assert len(selected_nodes) == 5  # thick, sld, isld, rough, vfsolv
    for node in selected_nodes:
        assert node.dataset_name == "e365r"


def test_link_parameters_across_datasets(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick_e361 = datastore["e361r"].model.structure[-2].thick
    thick_e365 = datastore["e365r"].model.structure[-2].thick
    idx_361 = win.parameter_model._row_of[thick_e361]
    idx_365 = win.parameter_model._row_of[thick_e365]

    win.parameter_model.link([idx_361, idx_365])

    assert thick_e365.constraint is thick_e361

    # editing the master should propagate to the linked row's dataChanged,
    # even though it lives in a different dataset
    seen_nodes = []
    win.parameter_model.dataChanged.connect(
        lambda tl, br, roles: seen_nodes.append(tl.internalPointer())
    )
    value_col = win.parameter_model.COLUMNS.index("value")
    value_idx = win.parameter_model.index_for(thick_e361, value_col)
    win.parameter_model.setData(value_idx, "260.0")

    assert thick_e361.value == 260.0
    assert (
        idx_365.internalPointer() in seen_nodes
    ), "linked row in the OTHER dataset wasn't notified"

    win.parameter_model.unlink([idx_365])
    assert thick_e365.constraint is None


def test_auto_limits_sets_bounds_from_value(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick  # varying, positive
    thick.value = 42.0

    sld_real = datastore["e361r"].model.structure[-2].sld.real  # varying
    sld_real.value = -3.5

    touched = win.parameter_model.auto_limits()

    assert thick.bounds.lb == 0
    assert thick.bounds.ub == 84.0
    # negative value -> reversed: [2*value, 0]
    assert sld_real.bounds.lb == -7.0
    assert sld_real.bounds.ub == 0
    assert touched > 0


def test_auto_limits_only_touches_varying_parameters(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    fixed = datastore["e361r"].model.structure[1].thick  # not set to vary
    assert not fixed.vary
    original_bounds = (fixed.bounds.lb, fixed.bounds.ub)

    win.parameter_model.auto_limits()

    assert (fixed.bounds.lb, fixed.bounds.ub) == original_bounds


def test_bounds_hidden_and_uneditable_unless_varying(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    fixed = datastore["e361r"].model.structure[1].thick  # not set to vary
    assert not fixed.vary
    lb_col = win.parameter_model.COLUMNS.index("lb")
    ub_col = win.parameter_model.COLUMNS.index("ub")
    lb_idx = win.parameter_model.index_for(fixed, lb_col)
    ub_idx = win.parameter_model.index_for(fixed, ub_col)

    assert win.parameter_model.data(lb_idx) == ""
    assert win.parameter_model.data(ub_idx) == ""
    assert not (win.parameter_model.flags(lb_idx) & Qt.ItemFlag.ItemIsEditable)
    assert not (win.parameter_model.flags(ub_idx) & Qt.ItemFlag.ItemIsEditable)

    varying = datastore["e361r"].model.structure[-2].thick  # set to vary
    assert varying.vary
    lb_idx2 = win.parameter_model.index_for(varying, lb_col)
    ub_idx2 = win.parameter_model.index_for(varying, ub_col)

    assert win.parameter_model.data(lb_idx2) == f"{varying.bounds.lb:.6g}"
    assert win.parameter_model.data(ub_idx2) == f"{varying.bounds.ub:.6g}"
    assert win.parameter_model.flags(lb_idx2) & Qt.ItemFlag.ItemIsEditable
    assert win.parameter_model.flags(ub_idx2) & Qt.ItemFlag.ItemIsEditable


def test_toggling_vary_refreshes_bounds_visibility(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    fixed = datastore["e361r"].model.structure[1].thick
    assert not fixed.vary

    vary_col = win.parameter_model.COLUMNS.index("vary")
    lb_col = win.parameter_model.COLUMNS.index("lb")
    vary_idx = win.parameter_model.index_for(fixed, vary_col)
    lb_idx = win.parameter_model.index_for(fixed, lb_col)

    assert win.parameter_model.data(lb_idx) == ""

    seen = []
    win.parameter_model.dataChanged.connect(
        lambda tl, br, roles: seen.append((tl.column(), br.column()))
    )
    win.parameter_model.setData(
        vary_idx, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole
    )

    assert fixed.vary
    assert win.parameter_model.data(lb_idx) == f"{fixed.bounds.lb:.6g}"
    # the lb/ub columns were told to refresh, not just the checkbox cell
    assert (lb_col, win.parameter_model.COLUMNS.index("ub")) in seen


def test_auto_limits_button_click(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    thick.value = 42.0

    qtbot.mouseClick(win.auto_limits_button, Qt.MouseButton.LeftButton)

    assert thick.bounds.lb == 0
    assert thick.bounds.ub == 84.0


def test_fit_selection_controls_which_datasets_are_fitted(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert {do.name for do in datastore.fitted_objects()} == set(
        datastore.names
    )

    # uncheck e365r via the tree model directly (mirrors clicking its
    # checkbox in the tree)
    e365_index = win.tree_model.index(1, 0)
    win.tree_model.setData(
        e365_index,
        Qt.CheckState.Unchecked.value,
        Qt.ItemDataRole.CheckStateRole,
    )
    assert {do.name for do in datastore.fitted_objects()} == {"e361r"}


def test_unchecking_a_dataset_hides_its_parameters_from_the_table(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert win.parameter_model.leaf_count() == 34

    e365_index = win.tree_model.index(1, 0)
    win.tree_model.setData(
        e365_index,
        Qt.CheckState.Unchecked.value,
        Qt.ItemDataRole.CheckStateRole,
    )

    # e365r's rows should be gone, e361r's should still be there
    assert win.parameter_model.leaf_count() == 17
    assert {name for name, _ in win.parameter_model._rows} == {"e361r"}

    # a constraint made while it was checked should survive being
    # unchecked, even though its row is no longer shown
    thick_e361 = datastore["e361r"].model.structure[-2].thick
    thick_e365 = datastore["e365r"].model.structure[-2].thick
    thick_e365.constraint = thick_e361
    assert thick_e365.constraint is thick_e361

    # re-checking should bring it back
    win.tree_model.setData(
        e365_index,
        Qt.CheckState.Checked.value,
        Qt.ItemDataRole.CheckStateRole,
    )
    assert win.parameter_model.leaf_count() == 34
    assert thick_e365.constraint is thick_e361


def test_fit_controller_runs_global_objective_async(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    before = sum(_chisqr(do) for do in datastore.fitted_objects())

    with qtbot.waitSignal(
        win.fit_controller.finished, timeout=30000
    ) as blocker:
        win.on_fit_clicked()
        assert win.fit_button.text() == "Abort"

    exc = blocker.args[0]
    assert exc is None, f"fit raised: {exc!r}"

    after = sum(_chisqr(do) for do in datastore.fitted_objects())
    print(f"total chi2 before={before:.4g} after={after:.4g}")
    assert after <= before
    assert win.fit_button.text().startswith("Fit")


def test_fit_sets_and_displays_parameter_stderr(qtbot):
    # CurveFitter.fit() itself computes and sets Parameter.stderr for
    # every varying parameter after a successful fit -- this just needs
    # to be visible in the table afterward
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    assert thick.stderr is None

    with qtbot.waitSignal(win.fit_controller.finished, timeout=30000):
        win.on_fit_clicked()

    assert thick.stderr is not None

    stderr_col = win.parameter_model.COLUMNS.index("stderr")
    idx = win.parameter_model.index_for(thick, stderr_col)
    assert idx.isValid()
    displayed = win.parameter_model.data(idx)
    assert displayed == f"{thick.stderr:.3g}"


def test_stderr_column_blank_when_not_yet_fitted(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    stderr_col = win.parameter_model.COLUMNS.index("stderr")
    idx = win.parameter_model.index_for(thick, stderr_col)
    assert win.parameter_model.data(idx) == ""


def test_editing_a_value_clears_stale_stderr_for_that_dataset(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick_e361 = datastore["e361r"].model.structure[-2].thick
    sld_e361 = datastore["e361r"].model.structure[-2].sld.real
    bkg_e365 = datastore["e365r"].model.bkg

    # pretend a previous fit already ran
    thick_e361.stderr = 1.23
    sld_e361.stderr = 0.045
    bkg_e365.stderr = 1e-7

    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index_for(thick_e361, value_col)
    win.parameter_model.setData(idx, "220.0")

    # every stderr in e361r is now stale and cleared...
    assert thick_e361.stderr is None
    assert sld_e361.stderr is None
    # ...but e365r's is untouched, since nothing there changed
    assert bkg_e365.stderr == 1e-7


def test_editing_vary_or_bounds_does_not_clear_stderr(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    thick.stderr = 1.23

    lb_col = win.parameter_model.COLUMNS.index("lb")
    idx = win.parameter_model.index_for(thick, lb_col)
    win.parameter_model.setData(idx, "0.0")

    assert thick.stderr == 1.23


def test_fit_warns_and_refuses_on_infinite_bounds(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    # a varying parameter with the refnx default (unbounded) bounds
    thick = datastore["e361r"].model.structure[-2].thick
    thick.bounds.lb = -float("inf")
    thick.bounds.ub = float("inf")

    win.on_fit_clicked()

    # should have refused to start -- button never flips to "Abort",
    # and the controller never actually starts running
    assert not win.fit_controller.running
    assert win.fit_button.text().startswith("Fit")


def test_fit_proceeds_when_bounds_are_finite(qtbot):
    # sanity check that the new bounds check doesn't false-positive and
    # block an otherwise-normal fit (the demo datastore's varying
    # parameters all have finite bounds already)
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    with qtbot.waitSignal(win.fit_controller.finished, timeout=30000):
        win.on_fit_clicked()
        assert win.fit_button.text() == "Abort"


def test_editing_controls_disabled_while_fit_is_running(qtbot):
    # the background fit thread continuously reads *and writes* the
    # fitted model's Parameter objects (Objective.setp() every
    # iteration) -- editing/renaming/linking/restructuring the same
    # models from the GUI thread at the same time is a real,
    # unsynchronized data race, so everything that could touch a
    # DataObject's model is disabled for the duration
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert win.tree_view.isEnabled()
    assert win.table_view.isEnabled()
    assert all(m.isEnabled() for m in win._model_mutating_menus)

    with qtbot.waitSignal(win.fit_controller.started, timeout=5000):
        win.on_fit_clicked()

    assert not win.tree_view.isEnabled()
    assert not win.table_view.isEnabled()
    assert not win.auto_limits_button.isEnabled()
    assert not any(m.isEnabled() for m in win._model_mutating_menus)

    with qtbot.waitSignal(win.fit_controller.finished, timeout=30000):
        pass

    assert win.tree_view.isEnabled()
    assert win.table_view.isEnabled()
    assert win.auto_limits_button.isEnabled()
    assert all(m.isEnabled() for m in win._model_mutating_menus)


def test_repeated_fits_do_not_crash_or_leave_stale_state(qtbot):
    # regression test for a reported segfault after clicking Fit
    # several times in a row -- runs several full start-to-finish fit
    # cycles back to back, forcing a GC pass after each, and checks the
    # UI settles correctly every time. The GC pass matters: the actual
    # bug was that _FitWorker (parentless, as moveToThread() requires)
    # had its Python reference cleared before Qt's own deleteLater()-
    # scheduled deletion had run, so Python's GC deleted the C++ object
    # directly instead -- "QObject: shared QObject was deleted
    # directly" -- out from under the still-pending deferred delete.
    # Forcing gc.collect() between cycles reproduces the timing that
    # triggered it.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    for i in range(4):
        assert not win.fit_controller.running
        with qtbot.waitSignal(win.fit_controller.finished, timeout=30000):
            win.on_fit_clicked()
            assert win.fit_button.text() == "Abort"
        gc.collect()
        assert win.fit_button.text().startswith("Fit")
        assert not win.fit_controller.running
        assert win.tree_view.isEnabled()
        assert win.table_view.isEnabled()


def test_load_data_adds_rather_than_replaces(monkeypatch, qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert len(win.datastore) == 2

    pth = resources.files(refnx.reflect.tests)
    other_data_path = str(pth / "smeared_theoretical.txt")

    monkeypatch.setattr(
        "main.getopenfilenames", lambda *a, **k: ([other_data_path], True)
    )
    win.on_load_data_triggered()

    assert len(win.datastore) == 3
    # this is the actual thing that would previously crash: update()
    # called again after a dataset of a different length was loaded
    win.plot_controller.update(win.datastore)
    assert win.tree_model.rowCount() == 3


def test_reload_data_calls_refresh_on_datasets_with_a_file(qtbot, monkeypatch):
    # build_demo_datastore's datasets are loaded from real files, so
    # they already carry their own source path as dataset.filename --
    # no separate path-tracking needed, refresh() re-reads from exactly
    # that path
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    assert all(do.dataset.filename is not None for do in datastore)

    refreshed = []
    for do in datastore:
        monkeypatch.setattr(
            do.dataset, "refresh", lambda name=do.name: refreshed.append(name)
        )

    win.on_reload_data_triggered()

    assert set(refreshed) == set(datastore.names)


def test_reload_data_skips_datasets_without_a_file(qtbot):
    import numpy as np
    from refnx.dataset import ReflectDataset

    datastore = build_demo_datastore()
    in_memory = ReflectDataset(
        data=(np.array([0.01, 0.02]), np.array([1.0, 0.5]))
    )
    assert in_memory.filename is None
    datastore.add(DataObject("in-memory", in_memory, _default_model()))

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    win.on_reload_data_triggered()  # should not raise


def test_reload_data_reports_failures_without_stopping_others(
    qtbot, monkeypatch
):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do1 = datastore["e361r"]
    do2 = datastore["e365r"]

    def boom():
        raise OSError("file vanished")

    monkeypatch.setattr(do1.dataset, "refresh", boom)
    refreshed = []
    monkeypatch.setattr(
        do2.dataset, "refresh", lambda: refreshed.append(do2.name)
    )

    win.on_reload_data_triggered()  # should not raise despite do1 failing

    assert refreshed == [do2.name]


def test_reload_datasets_action_has_ctrl_r_shortcut(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    actions = {a.text(): a for a in win.menuBar().actions()}
    file_menu = actions["&File"].menu()
    by_text = {a.text(): a for a in file_menu.actions()}
    assert by_text["Reload Datasets"].shortcut().toString() == "Ctrl+R"


def test_load_model_applies_only_to_selected_dataset(
    qtbot, tmp_path, monkeypatch
):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    e365_index = win.tree_model.index(1, 0)
    win.tree_view.setCurrentIndex(e365_index)

    new_structure = SLD(2.07) | SLD(4.5)(20, 2) | SLD(6.36)(0, 3)
    new_model = ReflectModel(new_structure)
    mpath = tmp_path / "other_model.pkl"
    persistence.save_model(new_model, mpath)

    monkeypatch.setattr(
        "main.getopenfilename", lambda *a, **k: (str(mpath), True)
    )
    win.on_load_model_triggered()

    # e365r got the new model...
    assert datastore["e365r"].model.structure[1].sld.real.value == 4.5
    assert len(datastore["e365r"].model.structure) == 3
    # ...e361r's model is untouched
    assert len(datastore["e361r"].model.structure) == 4


def test_load_model_unlinks_cross_dataset_dependents(
    qtbot, tmp_path, monkeypatch
):
    # a real, pre-existing gap fixed alongside Copy Model: replacing a
    # dataset's model via Load Model used to leave dangling constraints
    # on whatever used to depend on its old parameters.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    old_thick = datastore["e365r"].model.structure[-2].thick
    dependent = datastore["e361r"].model.structure[-2].thick
    dependent.constraint = old_thick

    e365_index = win.tree_model.index(1, 0)
    win.tree_view.setCurrentIndex(e365_index)

    new_model = ReflectModel(SLD(2.07) | SLD(4.5)(20, 2) | SLD(6.36)(0, 3))
    mpath = tmp_path / "other_model.pkl"
    persistence.save_model(new_model, mpath)
    monkeypatch.setattr(
        "main.getopenfilename", lambda *a, **k: (str(mpath), True)
    )
    win.on_load_model_triggered()

    assert dependent.constraint is None


def test_tree_context_menu_has_copy_action(qtbot):
    # Verifies the menu on_tree_context_menu would show, without calling
    # the real QMenu.exec() -- that's a genuinely blocking, modal C++
    # call that can't be driven or intercepted headlessly (confirmed by
    # trying: a monkeypatched QMenu.exec never got called, and the real
    # one hung waiting for a click that can't come). Same category of
    # limitation as not being able to simulate real mouse drags for the
    # drag-and-drop tests elsewhere in this suite -- the *logic* behind
    # the menu (on_copy_model_to_here) is what's actually worth testing,
    # and is covered directly below.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    menu, copy_action = win._build_tree_context_menu()
    assert copy_action.text() == "Copy a model to here"
    assert copy_action in menu.actions()


def test_copy_model_to_selected_dataset(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do1 = datastore["e361r"]
    do2 = datastore["e365r"]
    do1.model.bkg.value = 1.23e-6

    # select e365r -- that's the target "here" the model gets copied to
    e365_index = win.tree_model.index(1, 0)
    win.tree_view.setCurrentIndex(e365_index)

    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem", lambda *a, **k: ("e361r", True)
    )
    win.on_copy_model_to_here()

    # e365r's model now matches e361r's values...
    assert do2.model.bkg.value == 1.23e-6
    # ...but it's an independent copy, not the same object, renamed to
    # match its new dataset
    assert do2.model is not do1.model
    assert do2.model.name == "e365r"
    do1.model.bkg.value = 9.9e-6
    assert do2.model.bkg.value == 1.23e-6


def test_copy_model_to_multiple_selected_datasets(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    do3_dataset = datastore["e361r"].dataset
    datastore.add(DataObject("e999r", do3_dataset, _default_model()))
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    source = datastore["e361r"]
    source.model.bkg.value = 4.56e-6

    # select both other datasets as targets
    selection_model = win.tree_view.selectionModel()
    for row in (1, 2):  # e365r, e999r
        selection_model.select(
            win.tree_model.index(row, 0),
            QtCore.QItemSelectionModel.SelectionFlag.Select,
        )

    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem", lambda *a, **k: ("e361r", True)
    )
    win.on_copy_model_to_here()

    assert datastore["e365r"].model.bkg.value == 4.56e-6
    assert datastore["e999r"].model.bkg.value == 4.56e-6
    assert datastore["e365r"].model is not datastore["e999r"].model


def test_copy_model_no_target_selected_does_nothing(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do2 = datastore["e365r"]
    original_model = do2.model

    win.tree_view.selectionModel().clearSelection()
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem", lambda *a, **k: ("e361r", True)
    )
    win.on_copy_model_to_here()  # should just message, not crash

    assert do2.model is original_model


def test_copy_model_unlinks_cross_dataset_dependents(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do1 = datastore["e361r"]
    do2 = datastore["e365r"]

    old_target_thick = do2.model.structure[-2].thick
    dependent = do1.model.structure[-2].sld.real
    dependent.constraint = old_target_thick

    e365_index = win.tree_model.index(1, 0)
    win.tree_view.setCurrentIndex(e365_index)

    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem", lambda *a, **k: ("e361r", True)
    )
    win.on_copy_model_to_here()

    assert dependent.constraint is None


def test_save_model_round_trips(qtbot, tmp_path, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    e361_index = win.tree_model.index(0, 0)
    win.tree_view.setCurrentIndex(e361_index)

    mpath = tmp_path / "saved.pkl"
    monkeypatch.setattr(
        "main.getsavefilename", lambda *a, **k: (str(mpath), True)
    )
    win.on_save_model_triggered()

    reloaded = persistence.load_model(mpath)
    assert reloaded.bkg.value == datastore["e361r"].model.bkg.value


def test_remove_dataset(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    e365_index = win.tree_model.index(1, 0)
    win.tree_view.setCurrentIndex(e365_index)
    win.on_remove_dataset_triggered()

    assert len(datastore) == 1
    assert "e365r" not in datastore
    assert win.tree_model.rowCount() == 1
    assert win.parameter_model.leaf_count() == 17
