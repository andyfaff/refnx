import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.dirname(__file__))

from qtpy import QtWidgets, QtTest
from qtpy.QtCore import Qt

from delegates import ParameterTreeDelegate, SelectAllDelegate
from main import build_demo_datastore, MainWindow


def test_select_all_delegate_selects_existing_text(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)
    bkg = datastore["e361r"].model.bkg  # displayed as "3e-06"
    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index_for(bkg, value_col)

    delegate = SelectAllDelegate(win.table_view)
    editor = QtWidgets.QLineEdit()
    qtbot.add_widget(editor)

    delegate.setEditorData(editor, idx)  # populates text, then selects it
    assert editor.text() == "3e-06"
    assert editor.selectedText() == "3e-06"


def test_typing_immediately_after_edit_replaces_a_small_value(qtbot):
    # end-to-end: open the real editor on a value already shown in
    # scientific notation, type a new small value without manually
    # selecting first, and confirm the old text doesn't leak through
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    bkg = datastore["e361r"].model.bkg
    assert bkg.value == 3e-6
    assert bkg.bounds.lb == 1e-6 and bkg.bounds.ub == 5e-6  # small window
    value_col = win.parameter_model.COLUMNS.index("value")
    idx = win.parameter_model.index_for(bkg, value_col)

    win.table_view.setCurrentIndex(idx)
    win.table_view.edit(idx)

    editor = win.table_view.findChild(QtWidgets.QLineEdit)
    assert editor is not None
    assert editor.selectedText() == "3e-06"

    QtTest.QTest.keyClicks(editor, "2.123e-6")  # still within bkg's bounds
    assert editor.text() == "2.123e-6"

    QtTest.QTest.keyClick(editor, Qt.Key.Key_Return)
    qtbot.wait(10)
    assert bkg.value == 2.123e-6


def test_lower_upper_bound_cells_use_a_line_edit_not_a_spinbox(qtbot):
    # the actual bug behind "hard to enter small values for the lower/
    # upper limits": ParameterTableModel.data() used to return a raw
    # Python float for the lb/ub columns, and Qt's default delegate
    # creates a QDoubleSpinBox (2 decimal places, no exponent support)
    # rather than a QLineEdit whenever the model data is a float rather
    # than a string -- so typing "2.123e-5" into a bound silently got
    # truncated to "2.12". Formatting lb/ub as strings, the same way
    # "value" already was, fixes it by keeping the editor a QLineEdit.
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    lb_col = win.parameter_model.COLUMNS.index("lb")
    idx = win.parameter_model.index_for(thick, lb_col)

    win.table_view.setCurrentIndex(idx)
    win.table_view.edit(idx)

    editor = win.table_view.findChild(QtWidgets.QLineEdit)
    assert editor is not None
    assert not win.table_view.findChildren(QtWidgets.QDoubleSpinBox)

    QtTest.QTest.keyClicks(editor, "2.123e-5")
    QtTest.QTest.keyClick(editor, Qt.Key.Key_Return)
    qtbot.wait(10)
    assert thick.bounds.lb == 2.123e-5


def test_lb_ub_data_is_a_formatted_string_not_a_raw_float(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    thick = datastore["e361r"].model.structure[-2].thick
    lb_col = win.parameter_model.COLUMNS.index("lb")
    ub_col = win.parameter_model.COLUMNS.index("ub")
    lb_idx = win.parameter_model.index_for(thick, lb_col)
    ub_idx = win.parameter_model.index_for(thick, ub_col)

    assert win.parameter_model.data(lb_idx) == "200"
    assert win.parameter_model.data(ub_idx) == "300"


def test_parameter_tree_uses_the_dataset_boundary_delegate(qtbot):
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    assert isinstance(win.table_view.itemDelegate(), ParameterTreeDelegate)


def test_dataset_boundary_detected_only_at_a_second_or_later_dataset(qtbot):
    # two datasets loaded (build_demo_datastore) -- their top-level rows
    # are index(0, 0) and index(1, 0) in ParameterTableModel, see
    # ParameterTableModel.set_datastore/_populate_dataset
    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    first_dataset_idx = win.parameter_model.index(0, 0)
    second_dataset_idx = win.parameter_model.index(1, 0)
    nested_idx = win.parameter_model.index(0, 0, first_dataset_idx)

    assert first_dataset_idx.isValid() and second_dataset_idx.isValid()
    assert nested_idx.isValid()

    is_boundary = ParameterTreeDelegate.is_dataset_boundary
    assert not is_boundary(first_dataset_idx)  # nothing precedes it
    assert is_boundary(second_dataset_idx)  # a new dataset starts here
    assert not is_boundary(nested_idx)  # not a top-level dataset row at all
