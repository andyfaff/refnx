import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.dirname(__file__))

from qtpy import QtCore

from refnx.reflect import SLD

from main import build_demo_datastore, MainWindow
from models import equivalent_parameter, same_model_shape


class _FakeMultiSelectDialog:
    """Stands in for DatasetMultiSelectDialog so tests can drive
    on_link_equivalent_triggered() without a real modal dialog."""

    def __init__(self, names):
        self._names = names

    def exec(self):
        return 1  # QDialog.DialogCode.Accepted

    def selected_names(self):
        return self._names


def _select_parameter(win, parameter):
    idx = win.parameter_model.index_for(parameter)
    win.table_view.selectionModel().select(
        idx,
        QtCore.QItemSelectionModel.SelectionFlag.Select
        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
    )


def test_equivalent_parameter_finds_matching_position():
    datastore = build_demo_datastore()
    do1 = datastore["e361r"]
    do2 = datastore["e365r"]

    thick1 = do1.model.structure[-2].thick
    thick2 = do2.model.structure[-2].thick
    assert equivalent_parameter(do1, thick1, do2) is thick2

    bkg1 = do1.model.bkg
    bkg2 = do2.model.bkg
    assert equivalent_parameter(do1, bkg1, do2) is bkg2


def test_equivalent_parameter_returns_none_for_unknown_parameter():
    datastore = build_demo_datastore()
    do1 = datastore["e361r"]
    do2 = datastore["e365r"]

    from refnx.analysis import Parameter

    stray = Parameter(1.0, name="not part of any model")
    assert equivalent_parameter(do1, stray, do2) is None


def test_same_model_shape():
    datastore = build_demo_datastore()
    do1 = datastore["e361r"]
    do2 = datastore["e365r"]
    assert same_model_shape([do1, do2])

    do2.model.structure.insert(1, SLD(1.23)(5, 1))
    assert not same_model_shape([do1, do2])


def test_link_equivalent_links_across_selected_datasets(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick1 = datastore["e361r"].model.structure[-2].thick
    _select_parameter(win, thick1)

    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: _FakeMultiSelectDialog(["e365r"]),
    )
    win.on_link_equivalent_triggered()

    thick2 = datastore["e365r"].model.structure[-2].thick
    assert thick2.constraint is thick1


def test_link_equivalent_remembers_previously_selected_datasets(
    qtbot, monkeypatch
):
    # a common workflow is linking several parameters, one at a time,
    # against the same set of datasets each time -- re-picking that set
    # from scratch every time the dialog opens would be tedious
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    seen_preselected = []

    def fake_dialog(names, title=None, preselected=(), parent=None):
        seen_preselected.append(list(preselected))
        return _FakeMultiSelectDialog(["e365r"])

    monkeypatch.setattr("main.DatasetMultiSelectDialog", fake_dialog)

    thick1 = datastore["e361r"].model.structure[-2].thick
    _select_parameter(win, thick1)
    win.on_link_equivalent_triggered()
    assert seen_preselected[0] == []  # nothing remembered on the first go

    sld1 = datastore["e361r"].model.structure[-2].sld.real
    _select_parameter(win, sld1)
    win.on_link_equivalent_triggered()
    assert seen_preselected[1] == ["e365r"]  # remembered from last time


def test_link_equivalent_clears_a_pre_existing_master_constraint(
    qtbot, monkeypatch
):
    # mirrors the production app's guard: if the selected (soon-to-be
    # master) parameter already has its own constraint, that has to be
    # cleared first or the new constraint would recurse
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick1 = datastore["e361r"].model.structure[-2].thick
    other = datastore["e361r"].model.structure[1].thick
    thick1.constraint = other
    _select_parameter(win, thick1)

    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: _FakeMultiSelectDialog(["e365r"]),
    )
    win.on_link_equivalent_triggered()

    assert thick1.constraint is None
    thick2 = datastore["e365r"].model.structure[-2].thick
    assert thick2.constraint is thick1


def test_link_equivalent_refuses_on_mismatched_shape(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    datastore["e365r"].model.structure.insert(1, SLD(1.23)(5, 1))
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick1 = datastore["e361r"].model.structure[-2].thick
    original_constraint = thick1.constraint
    _select_parameter(win, thick1)

    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: _FakeMultiSelectDialog(["e365r"]),
    )
    win.on_link_equivalent_triggered()

    assert thick1.constraint is original_constraint
    thick2_equivalent_slot = datastore["e365r"].model.structure[-2].thick
    assert thick2_equivalent_slot.constraint is None


def test_link_equivalent_does_nothing_with_no_selection(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    called = []
    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: called.append(1) or _FakeMultiSelectDialog(["e365r"]),
    )
    win.on_link_equivalent_triggered()

    # refused before even opening the dataset picker
    assert not called


def test_link_equivalent_does_nothing_with_only_one_dataset_loaded(
    qtbot, monkeypatch
):
    datastore = build_demo_datastore()
    datastore.remove("e365r")
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick1 = datastore["e361r"].model.structure[-2].thick
    _select_parameter(win, thick1)

    called = []
    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: called.append(1) or _FakeMultiSelectDialog([]),
    )
    win.on_link_equivalent_triggered()

    assert not called
    assert thick1.constraint is None


def test_link_equivalent_ignores_component_property_rows(qtbot, monkeypatch):
    from dialogs import default_component

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    leaflet = default_component("LipidLeaflet")
    do.model.structure.insert(2, leaflet)
    datastore["e365r"].model.structure.insert(
        2, default_component("LipidLeaflet")
    )

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    property_index = next(
        win.parameter_model.index_for(obj)
        for name, obj in win.parameter_model._rows
        if name == "e361r"
        and getattr(obj, "attr_name", None) == "reverse_monolayer"
    )
    win.table_view.selectionModel().select(
        property_index,
        QtCore.QItemSelectionModel.SelectionFlag.Select
        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
    )

    monkeypatch.setattr(
        "main.DatasetMultiSelectDialog",
        lambda *a, **k: _FakeMultiSelectDialog(["e365r"]),
    )
    # should not raise -- the property row is simply skipped, and since
    # nothing else was selected there's nothing to link
    win.on_link_equivalent_triggered()


def test_parameters_menu_has_link_actions_with_shortcuts(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    actions = {a.text(): a for a in win.menuBar().actions()}
    assert "&Parameters" in actions

    parameters_menu = actions["&Parameters"].menu()
    by_text = {a.text(): a for a in parameters_menu.actions()}
    assert (
        by_text["Link Selected Parameters"].shortcut().toString() == "Ctrl+1"
    )
    assert (
        by_text["Unlink Selected Parameters"].shortcut().toString() == "Ctrl+2"
    )
    assert (
        by_text["Link Equivalent Parameters..."].shortcut().toString()
        == "Ctrl+3"
    )


def test_link_selected_and_unlink_selected_still_work_without_buttons(qtbot):
    # the standalone Link/Unlink Selected buttons were removed in favour
    # of menu actions + Ctrl+1/Ctrl+2 -- the underlying handlers are
    # unchanged, so drive them directly the same way a menu trigger would
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    assert not hasattr(win, "link_button")
    assert not hasattr(win, "unlink_button")

    thick_e361 = datastore["e361r"].model.structure[-2].thick
    thick_e365 = datastore["e365r"].model.structure[-2].thick
    _select_parameter(win, thick_e361)
    win.table_view.selectionModel().select(
        win.parameter_model.index_for(thick_e365),
        QtCore.QItemSelectionModel.SelectionFlag.Select
        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
    )

    win.on_link_clicked()
    assert thick_e365.constraint is thick_e361

    win.on_unlink_clicked()
    assert thick_e365.constraint is None
