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

    def __init__(self, dataset, kind, position, container=None):
        self._dataset = dataset
        self._kind = kind
        self._position = position
        self._container = container

    def exec(self):
        return 1  # QDialog.DialogCode.Accepted

    def dataset_name(self):
        return self._dataset

    def kind(self):
        return self._kind

    def position(self):
        return self._position

    def container(self):
        return self._container


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

    # position 0 would make this the new first Component -- rejected
    # unconditionally now, not just because a Spline isn't a Slab
    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "Spline", 0),
    )
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before  # rejected, untouched


def test_add_component_rejects_new_last_position_too(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)

    # position == len(structure) would append as the new last Component
    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "Slab", n_before),
    )
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before  # rejected, untouched


def test_add_component_into_a_stack(qtbot, monkeypatch):
    datastore = build_demo_datastore()
    do = datastore["e361r"]
    stack = Stack([SLD(4.0)(5, 1)], name="stack")
    do.model.structure.insert(1, stack)  # a legal, middle position

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    n_before = len(stack)
    rows_before = win.parameter_model.leaf_count()

    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog(
            "e361r", "Slab", n_before, container=stack
        ),
    )
    win.on_add_component_triggered()

    # the Stack grew, the top-level Structure didn't
    assert len(stack) == n_before + 1
    assert len(do.model.structure) == 5  # unchanged top-level count
    assert win.parameter_model.leaf_count() == rows_before + 5


def test_add_component_at_start_or_end_of_a_stack_is_allowed(
    qtbot, monkeypatch
):
    # unlike the top level, a Stack has no first/last restriction --
    # position 0 (or the very end) is fine
    datastore = build_demo_datastore()
    do = datastore["e361r"]
    inner = SLD(4.0)(5, 1)
    stack = Stack([inner], name="stack")
    do.model.structure.insert(1, stack)

    win = MainWindow(datastore)
    qtbot.add_widget(win)

    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "Slab", 0, container=stack),
    )
    win.on_add_component_triggered()

    assert len(stack) == 2
    assert stack[0] is not inner  # the new Slab was inserted before it


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


def test_first_component_cannot_be_removed(qtbot):
    # the fronting Slab can never be removed, no matter what would end
    # up taking its place -- unlike the old "just needs to still be a
    # Slab" rule, this is unconditional
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)
    idx = win.tree_model.index(0, 0, win.tree_model.index(0, 0))
    win.tree_view.setCurrentIndex(idx)
    win.on_remove_component_triggered()

    assert len(do.model.structure) == n_before  # refused, untouched


def test_last_component_cannot_be_removed(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)
    do_index = win.tree_model.index(0, 0)
    last_row = win.tree_model.rowCount(do_index) - 1
    idx = win.tree_model.index(last_row, 0, do_index)
    win.tree_view.setCurrentIndex(idx)
    win.on_remove_component_triggered()

    assert len(do.model.structure) == n_before  # refused, untouched


def test_first_slab_cannot_be_dragged_away(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    original = list(do.model.structure)

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(0, 0, do_index)  # the front Slab
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 2, 0, do_index
    )

    assert not ok
    assert list(do.model.structure) == original


def test_component_cannot_be_dragged_into_first_position(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    original = list(do.model.structure)

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(2, 0, do_index)  # polymer
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 0, 0, do_index
    )

    assert not ok
    assert list(do.model.structure) == original


def test_component_cannot_be_dragged_into_last_position(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    original = list(do.model.structure)

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(1, 0, do_index)  # sio2
    append_row = win.tree_model.rowCount(do_index)  # "after everything"
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, append_row, 0, do_index
    )

    assert not ok
    assert list(do.model.structure) == original


def test_drag_drop_reorder_refreshes_table_and_plot(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    original = list(do.model.structure)
    rows_before = win.parameter_model.leaf_count()

    do_index = win.tree_model.index(0, 0)
    source_index = win.tree_model.index(2, 0, do_index)  # polymer

    # a legal *interior* move: polymer (position 2) in front of sio2
    # (position 1) -- neither end is the first/last position, so this
    # one's allowed (see test_boundary_* below for the ones that aren't)
    mime = win.tree_model.mimeData([source_index])
    ok = win.tree_model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 1, 0, do_index
    )

    assert ok
    assert list(do.model.structure) == [
        original[0],
        original[2],
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


def test_add_component_dialog_lists_stacks_as_containers(qtbot):
    from dialogs import AddComponentDialog

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    stack = Stack([SLD(4.0)(5, 1)], name="stack")
    do.model.structure.insert(1, stack)

    dialog = AddComponentDialog(datastore, default_dataset="e361r")
    qtbot.add_widget(dialog)

    labels = [
        dialog.container_combo.itemText(i)
        for i in range(dialog.container_combo.count())
    ]
    assert labels == ["Top level", "stack (inside Stack)"]
    assert dialog.container_combo.itemData(0) is None
    assert dialog.container_combo.itemData(1) is stack


def test_add_component_dialog_position_range_excludes_top_level_boundary(
    qtbot,
):
    from dialogs import AddComponentDialog

    datastore = build_demo_datastore()  # e361r has 4 top-level Slabs
    dialog = AddComponentDialog(datastore, default_dataset="e361r")
    qtbot.add_widget(dialog)

    # position 0 and 4 would create a new first/last Component -- not
    # offered at all for the top level
    assert dialog.position_spin.minimum() == 1
    assert dialog.position_spin.maximum() == 3


def test_add_component_dialog_position_range_allows_stack_boundary(qtbot):
    from dialogs import AddComponentDialog

    datastore = build_demo_datastore()
    do = datastore["e361r"]
    stack = Stack([SLD(4.0)(5, 1)], name="stack")
    do.model.structure.insert(1, stack)

    dialog = AddComponentDialog(
        datastore, default_dataset="e361r", default_container=stack
    )
    qtbot.add_widget(dialog)

    # a Stack has no first/last restriction -- the full range is offered
    assert dialog.position_spin.minimum() == 0
    assert dialog.position_spin.maximum() == len(stack)
