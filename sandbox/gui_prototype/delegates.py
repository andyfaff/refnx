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
"""

from qtpy import QtWidgets


class SelectAllDelegate(QtWidgets.QStyledItemDelegate):
    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.selectAll()
