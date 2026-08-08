import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.dirname(__file__))

from qtpy import QtCore

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
