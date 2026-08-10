"""
SelectAllDelegate: makes a text-editable cell start fully selected the
moment editing begins, so typing immediately replaces the whole value
rather than inserting/appending wherever the cursor happens to land.

Motivated by feedback that entering a precise, small value like
2.123e-5 into a parameter's Value box was hard -- the '.'/'-'/'e' in a
value already shown in scientific notation are exactly the kind of
characters that make double-click "select the word under the cursor"
behaviour inconsistent across platforms/styles, so half-selected or
unselected old text can end up merged with whatever gets typed next.
Explicitly selecting everything on entry removes that dependency on
platform-specific word-boundary behaviour entirely.

ParameterTreeDelegate: SelectAllDelegate, plus a rule drawn above each
dataset's own top-level row (except the first). Every group is
expanded by default (see main.py's _refresh_parameter_tree_view), so
with several datasets loaded, one dataset's last Component and the
next dataset's own row would otherwise run together with nothing to
show where one ends and the next begins.
"""

from qtpy import QtGui, QtWidgets


class SelectAllDelegate(QtWidgets.QStyledItemDelegate):
    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.selectAll()


class ParameterTreeDelegate(SelectAllDelegate):
    def paint(self, painter, option, index):
        if self.is_dataset_boundary(index):
            painter.save()
            pen = QtGui.QPen(
                option.palette.color(QtGui.QPalette.ColorRole.Mid)
            )
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(option.rect.topLeft(), option.rect.topRight())
            painter.restore()
        super().paint(painter, option, index)

    @staticmethod
    def is_dataset_boundary(index):
        # Top-level rows are exactly the per-dataset nodes (see
        # ParameterTableModel._populate_dataset) -- every one of them
        # except the first (nothing precedes that one to separate it
        # from) marks where a new dataset's parameters start.
        return not index.parent().isValid() and index.row() > 0
