import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.dirname(__file__))

from qtpy.QtCore import Qt

from refnx.reflect import SLD, Stack
from refnx.reflect.spline import Spline

from main import build_demo_datastore, MainWindow


class _FakeAddDialog:
    """Stands in for AddComponentDialog so tests can drive
    on_add_component_triggered() without a real modal dialog."""

    def __init__(self, dataset, kind, position):
        self._dataset = dataset
        self._kind = kind
        self._position = position

    def exec(self):
        return 1  # QDialog.DialogCode.Accepted

    def dataset_name(self):
        return self._dataset

    def kind(self):
        return self._kind

    def position(self):
        return self._position


def test_add_component_via_dialog(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)
    rows_before = win.parameter_model.leaf_count()

    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "Slab", 2),
    )
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before + 1
    # a Slab contributes 5 parameters (thick, sld, isld, rough, vfsolv);
    # this also proves the table refreshed automatically via
    # tree_model.modelReset -> on_structure_changed, with no explicit
    # refresh call in the handler
    assert win.parameter_model.leaf_count() == rows_before + 5


def test_add_component_rejects_invalid_boundary(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)

    # a Spline at position 0 would become the new first Component
    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "Spline", 0),
    )
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before  # rejected, untouched


def test_remove_component_via_action(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    idx = win.tree_model.index(2, 0, win.tree_model.index(0, 0))  # polymer
    win.tree_view.setCurrentIndex(idx)
    win.on_remove_component_triggered()

    assert len(do.model.structure) == 3


def test_remove_component_refused_at_dataset_row(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)
    win.tree_view.setCurrentIndex(win.tree_model.index(0, 0))  # the dataset
    win.on_remove_component_triggered()

    assert len(do.model.structure) == n_before  # untouched


def test_remove_component_unlinks_cross_dataset_dependents(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do1 = datastore["e361r"]
    do2 = datastore["e365r"]
    master = do1.model.structure[2].thick
    dependent = do2.model.structure[2].thick
    dependent.constraint = master

    idx = win.tree_model.index(2, 0, win.tree_model.index(0, 0))
    win.tree_view.setCurrentIndex(idx)
    win.on_remove_component_triggered()

    assert dependent.constraint is None


def test_drag_drop_reorder_refreshes_table_and_plot(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    original = list(do.model.structure)
    rows_before = win.parameter_model.leaf_count()

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(2, 0, do_index)  # polymer

    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 0, 0, do_index
    )

    assert ok
    assert list(do.model.structure) == [
        original[2],
        original[0],
        original[1],
        original[3],
    ]
    # same number of parameters, just reordered -- but this proves
    # on_structure_changed fired and rebuilt the table without crashing
    assert win.parameter_model.leaf_count() == rows_before


def test_drag_drop_rejects_boundary_violation(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    spline = Spline(extent=20, vs=[3.0], dz=[0.5])
    win.tree_model.insert_component(do, 2, spline)
    original = list(do.model.structure)

    do_index = win.tree_model.index(0, 0)
    spline_index = win.tree_model.index(2, 0, do_index)
    mime = win.tree_model.mimeData([spline_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 0, 0, do_index
    )

    assert not ok
    assert list(do.model.structure) == original


def test_nested_stack_component_not_draggable(qtbot):
    datastore = build_demo_datastore()
    do = datastore["e361r"]
    stack = Stack([SLD(4.0)(5, 1)], name="stack")
    do.model.structure.insert(2, stack)

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do_index = win.tree_model.index(0, 0)
    stack_index = win.tree_model.index(2, 0, do_index)
    nested_index = win.tree_model.index(0, 0, stack_index)

    mime = win.tree_model.mimeData([nested_index])
    assert mime is None
