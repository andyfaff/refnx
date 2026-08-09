import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    assert win.parameter_model.rowCount() == 34


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


def test_boundary_hiding_follows_reorder(qtbot):
    # dragging a different Slab into the first position should hide
    # *its* thick/isld/rough and reveal the old first Slab's, since
    # "first" is a position, not a fixed identity
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    structure = datastore["e361r"].model.structure
    old_first = structure[0]
    polymer = structure[2]

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(2, 0, do_index)  # polymer
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, QtCore.Qt.DropAction.MoveAction, 0, 0, do_index
    )
    assert ok
    assert structure[0] is polymer

    shown = win.parameter_model._row_of
    assert polymer.thick not in shown
    assert old_first.thick in shown  # no longer first, no longer hidden


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

    rows = [
        r
        for r, (name, obj) in enumerate(win.parameter_model._rows)
        if name == "e361r"
        and getattr(obj, "attr_name", None) == "reverse_monolayer"
    ]
    assert len(rows) == 1
    row = rows[0]

    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index(row, value_col)

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

    property_row = next(
        r
        for r, (name, obj) in enumerate(win.parameter_model._rows)
        if name == "e361r"
        and getattr(obj, "attr_name", None) == "reverse_monolayer"
    )
    parameter_row = next(
        r
        for r, (name, obj) in enumerate(win.parameter_model._rows)
        if name == "e361r" and hasattr(obj, "vary")
    )

    # should not raise, and the property row is simply skipped
    win.parameter_model.link([property_row, parameter_row])
    win.parameter_model.auto_limits()


def test_tree_selection_highlights_without_hiding_other_rows(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    total_before = win.parameter_model.rowCount()

    # select the second dataset's third component (polymer)
    e365_index = win.tree_model.index(1, 0)
    polymer_index = win.tree_model.index(2, 0, e365_index)
    win.tree_view.setCurrentIndex(polymer_index)

    # nothing should have been hidden/filtered out of the table
    assert win.parameter_model.rowCount() == total_before

    # but the table's selection should now be exactly that component's
    # rows, and they should all belong to e365r
    selected_rows = sorted({i.row() for i in win.table_view.selectedIndexes()})
    assert len(selected_rows) == 5  # thick, sld, isld, rough, vfsolv
    for r in selected_rows:
        name, p = win.parameter_model._rows[r]
        assert name == "e365r"


def test_link_parameters_across_datasets(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick_e361 = datastore["e361r"].model.structure[-2].thick
    thick_e365 = datastore["e365r"].model.structure[-2].thick
    row_361 = win.parameter_model._row_of[thick_e361]
    row_365 = win.parameter_model._row_of[thick_e365]

    win.parameter_model.link([row_361, row_365])

    assert thick_e365.constraint is thick_e361

    # editing the master should propagate to the linked row's dataChanged,
    # even though it lives in a different dataset
    seen_rows = []
    win.parameter_model.dataChanged.connect(
        lambda tl, br, roles: seen_rows.append(tl.row())
    )
    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index(row_361, value_col)
    win.parameter_model.setData(idx, "260.0")

    assert thick_e361.value == 260.0
    assert (
        row_365 in seen_rows
    ), "linked row in the OTHER dataset wasn't notified"

    win.parameter_model.unlink([row_365])
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

    assert win.parameter_model.rowCount() == 34

    e365_index = win.tree_model.index(1, 0)
    win.tree_model.setData(
        e365_index,
        Qt.CheckState.Unchecked.value,
        Qt.ItemDataRole.CheckStateRole,
    )

    # e365r's rows should be gone, e361r's should still be there
    assert win.parameter_model.rowCount() == 17
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
    assert win.parameter_model.rowCount() == 34
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
    assert win.parameter_model.rowCount() == 17
