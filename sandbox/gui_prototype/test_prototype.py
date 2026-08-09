import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from importlib import resources

sys.path.insert(0, os.path.dirname(__file__))

from qtpy.QtCore import Qt

import refnx.reflect.tests
from refnx.reflect import SLD, ReflectModel
from refnx.analysis import Objective

import persistence
from main import build_demo_datastore, MainWindow


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
    assert win.parameter_model.rowCount() == 48  # 24 params x 2 datasets


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

    assert win.parameter_model.rowCount() == 48

    e365_index = win.tree_model.index(1, 0)
    win.tree_model.setData(
        e365_index,
        Qt.CheckState.Unchecked.value,
        Qt.ItemDataRole.CheckStateRole,
    )

    # e365r's rows should be gone, e361r's should still be there
    assert win.parameter_model.rowCount() == 24
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
    assert win.parameter_model.rowCount() == 48
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
    assert win.parameter_model.rowCount() == 24
