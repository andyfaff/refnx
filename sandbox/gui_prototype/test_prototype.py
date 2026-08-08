import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from importlib import resources

sys.path.insert(0, os.path.dirname(__file__))

import refnx.reflect.tests
from refnx.reflect import SLD, ReflectModel

import persistence
from main import build_demo_objective, MainWindow


def test_tree_selection_filters_table(qtbot):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    # whole structure to start with
    assert win.parameter_model.rowCount() == 20

    # select the second component (sio2) -- should narrow to just its
    # own parameters (thick, sld, isld, rough, vfsolv = 5)
    idx = win.structure_model.index(1, 0)
    win.tree_view.setCurrentIndex(idx)
    assert win.parameter_model.rowCount() == 5
    names = [
        win.parameter_model.data(win.parameter_model.index(r, 0))
        for r in range(5)
    ]
    print("selected component parameter names:", names)


def test_editing_updates_plot_and_dependents(qtbot):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    # link two parameters so we can prove dependency notification works
    model = objective.model
    thick_param = model.structure[-2].thick
    sld_param = model.structure[-2].sld.real
    sld_param.constraint = thick_param  # sld now depends on thick

    win.parameter_model.set_parameters(model.structure.parameters.flattened())

    row_of_thick = win.parameter_model._row_of[thick_param]
    row_of_sld = win.parameter_model._row_of[sld_param]

    seen_rows = []
    win.parameter_model.dataChanged.connect(
        lambda tl, br, roles: seen_rows.append(tl.row())
    )

    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index(row_of_thick, value_col)
    win.parameter_model.setData(idx, "250.0")

    assert thick_param.value == 250.0
    assert row_of_thick in seen_rows
    assert row_of_sld in seen_rows, "dependent row was not notified"
    print("dependency notification worked: rows touched =", seen_rows)

    sld_param.constraint = None  # undo for cleanliness


def test_fit_controller_runs_async(qtbot):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    before = objective.chisqr()

    progress_calls = []
    win.fit_controller.progress.connect(
        lambda chi2, it: progress_calls.append((chi2, it))
    )

    with qtbot.waitSignal(
        win.fit_controller.finished, timeout=30000
    ) as blocker:
        win.on_fit_clicked()
        # controller should be genuinely async: control returns to us
        # immediately, the fit hasn't necessarily finished yet.
        assert win.fit_button.text() == "Abort"

    exc = blocker.args[0]
    assert exc is None, f"fit raised: {exc!r}"

    after = objective.chisqr()
    print(f"chi2 before={before:.4g} after={after:.4g}")
    assert after <= before
    assert win.fit_button.text().startswith("Fit")


def test_load_differently_shaped_data(monkeypatch, qtbot):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    assert len(win.objective.data) == 99

    pth = resources.files(refnx.reflect.tests)
    other_data_path = str(pth / "smeared_theoretical.txt")

    # simulate the file dialog picking a differently-shaped dataset
    monkeypatch.setattr(
        "main.getopenfilename", lambda *a, **k: (other_data_path, True)
    )

    win.on_load_data_triggered()

    assert len(win.objective.data) != 99
    # this is the actual thing that would previously crash: update()
    # called again after a dataset of a different length was loaded
    win.plot_controller.update(win.objective)

    # model should be preserved (only the data changed)
    assert win.objective.model is objective.model
    assert win.structure_model.rowCount() == 4


def test_load_model(qtbot, tmp_path, monkeypatch):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    original_data = win.objective.data

    new_structure = SLD(2.07) | SLD(4.5)(20, 2) | SLD(6.36)(0, 3)
    new_model = ReflectModel(new_structure)
    mpath = tmp_path / "other_model.pkl"
    persistence.save_model(new_model, mpath)

    monkeypatch.setattr(
        "main.getopenfilename", lambda *a, **k: (str(mpath), True)
    )
    win.on_load_model_triggered()

    # unpickling always creates a new object, so compare by value, not
    # identity, for the loaded model
    assert win.objective.model.structure[1].sld.real.value == 4.5
    assert len(win.objective.model.structure) == 3

    # dataset should be preserved (only the model changed)
    assert win.objective.data is original_data
    assert win.structure_model.rowCount() == 3


def test_save_model_round_trips(qtbot, tmp_path, monkeypatch):
    objective = build_demo_objective()
    win = MainWindow(objective)
    qtbot.add_widget(win)

    mpath = tmp_path / "saved.pkl"
    monkeypatch.setattr(
        "main.getsavefilename", lambda *a, **k: (str(mpath), True)
    )
    win.on_save_model_triggered()

    reloaded = persistence.load_model(mpath)
    assert reloaded.bkg.value == win.objective.model.bkg.value
