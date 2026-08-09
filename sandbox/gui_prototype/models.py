"""
DataStoreTreeModel   -- pure navigation: DataObject -> Component rows
                        (recursing into Stacks), one row per loaded
                        dataset at the top level, checkable to control
                        whether it's included in the next fit.
ParameterTableModel  -- flat, one row per Parameter, across *every*
                        loaded dataset at once (not just whichever one
                        is selected in the tree). That's the point: you
                        can only multi-select parameters to link them if
                        they're all visible in the same view, including
                        across datasets.

Splitting navigation from editing still means there's exactly one
generic node type in the tree, and exactly one place
(ParameterTableModel._rows_depending_on) that knows how to propagate a
change to linked parameters -- linking across datasets falls out of
that for free, since it only ever looks at Parameter identity and
`.dependencies()`, never which dataset a parameter came from.
"""

from qtpy import QtCore
from qtpy.QtCore import Qt

from refnx.reflect import Stack

from datastore import DataObject


class _TreeNode:
    """Wraps either a DataObject (top-level) or a Component (nested,
    recursively for Stacks). One class for all of them -- there's
    nothing to override per-type because this model doesn't expose
    parameters, only navigation."""

    __slots__ = ("obj", "parent", "row", "children")

    def __init__(self, obj, parent, row):
        self.obj = obj
        self.parent = parent
        self.row = row
        self.children = []


class DataStoreTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, datastore=None, parent=None):
        super().__init__(parent)
        self._root = _TreeNode(None, None, 0)
        self.set_datastore(datastore)

    def set_datastore(self, datastore):
        self.beginResetModel()
        self._datastore = datastore
        self._root = _TreeNode(None, None, 0)
        if datastore is not None:
            for i, data_object in enumerate(datastore):
                do_node = _TreeNode(data_object, self._root, i)
                self._root.children.append(do_node)
                self._populate(do_node, data_object.model.structure)
        self.endResetModel()

    def _populate(self, parent_node, components):
        for i, c in enumerate(components):
            child = _TreeNode(c, parent_node, i)
            parent_node.children.append(child)
            if isinstance(c, Stack):
                self._populate(child, c)

    # -- QAbstractItemModel plumbing --

    def index(self, row, column, parent=QtCore.QModelIndex()):
        parent_node = (
            parent.internalPointer() if parent.isValid() else self._root
        )
        if parent_node is None or row >= len(parent_node.children):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, parent_node.children[row])

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        node = index.internalPointer()
        if node.parent is None or node.parent is self._root:
            return QtCore.QModelIndex()
        return self.createIndex(node.parent.row, 0, node.parent)

    def rowCount(self, parent=QtCore.QModelIndex()):
        node = parent.internalPointer() if parent.isValid() else self._root
        return len(node.children) if node is not None else 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        obj = index.internalPointer().obj

        if role == Qt.ItemDataRole.DisplayRole:
            return getattr(obj, "name", None) or type(obj).__name__

        if role == Qt.ItemDataRole.CheckStateRole and isinstance(
            obj, DataObject
        ):
            return (
                Qt.CheckState.Checked
                if obj.in_fit
                else Qt.CheckState.Unchecked
            )

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        obj = index.internalPointer().obj

        if role == Qt.ItemDataRole.CheckStateRole and isinstance(
            obj, DataObject
        ):
            obj.in_fit = value == Qt.CheckState.Checked.value
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        obj = index.internalPointer().obj
        if isinstance(obj, DataObject):
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def object_for_index(self, index):
        """Returns the DataObject or Component this row represents, or
        None if nothing (or an invalid index) is selected."""
        if not index.isValid():
            return None
        return index.internalPointer().obj

    def data_object_for_index(self, index):
        """Walks up from any row (a DataObject row, or one of its nested
        Component rows) to find the owning DataObject."""
        if not index.isValid():
            return None
        node = index.internalPointer()
        while node is not None and not isinstance(node.obj, DataObject):
            node = node.parent
        return node.obj if node is not None else None


class ParameterTableModel(QtCore.QAbstractTableModel):
    """
    One row per Parameter, across every DataObject in the datastore.
    Editing a value/bound writes straight to the Parameter and emits
    dataChanged both for the edited cell *and* for every other row whose
    parameter depends on it -- including rows belonging to a different
    dataset, since dependency checking only ever looks at Parameter
    identity, never which dataset a row came from.
    """

    COLUMNS = ("dataset", "name", "value", "vary", "lb", "ub", "constraint")
    HEADERS = (
        "Dataset",
        "Name",
        "Value",
        "Vary",
        "Lower",
        "Upper",
        "Constraint",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []  # list of (data_object_name, Parameter)
        self._row_of = {}  # Parameter -> row

    def set_datastore(self, datastore):
        self.beginResetModel()
        self._rows = []
        if datastore is not None:
            for data_object in datastore:
                for p in data_object.model.parameters.flattened():
                    self._rows.append((data_object.name, p))
        self._row_of = {p: i for i, (_, p) in enumerate(self._rows)}
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.COLUMNS)

    def headerData(
        self, section, orientation, role=Qt.ItemDataRole.DisplayRole
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.HEADERS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        col = self.COLUMNS[index.column()]
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        if col == "vary":
            return base | Qt.ItemFlag.ItemIsUserCheckable

        _, p = self._rows[index.row()]
        if col in ("value", "lb", "ub") and p.constraint is None:
            return base | Qt.ItemFlag.ItemIsEditable

        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        dataset_name, p = self._rows[index.row()]
        col = self.COLUMNS[index.column()]

        if role == Qt.ItemDataRole.CheckStateRole and col == "vary":
            return Qt.CheckState.Checked if p.vary else Qt.CheckState.Unchecked

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == "dataset":
                return dataset_name
            if col == "name":
                return p.name
            if col == "value":
                return f"{p.value:.6g}"
            if col == "lb":
                return p.bounds.lb
            if col == "ub":
                return p.bounds.ub
            if col == "constraint":
                return repr(p.constraint) if p.constraint is not None else ""

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        _, p = self._rows[index.row()]
        col = self.COLUMNS[index.column()]

        if role == Qt.ItemDataRole.CheckStateRole and col == "vary":
            p.vary = value == Qt.CheckState.Checked.value
            self.dataChanged.emit(index, index, [role])
            return True

        if role == Qt.ItemDataRole.EditRole and col in ("value", "lb", "ub"):
            try:
                fvalue = float(value)
            except (TypeError, ValueError):
                return False

            if col == "value":
                p.value = fvalue
            elif col == "lb":
                p.bounds.lb = fvalue
            elif col == "ub":
                p.bounds.ub = fvalue

            self.dataChanged.emit(index, index, [role])
            if col == "value":
                self._notify_dependents(p)
            return True

        return False

    def _notify_dependents(self, parameter):
        value_col = self.COLUMNS.index("value")
        for row in self._rows_depending_on(parameter):
            idx = self.index(row, value_col)
            self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.EditRole])

    def _rows_depending_on(self, parameter):
        return [
            row
            for row, (_, p) in enumerate(self._rows)
            if p is not parameter and parameter in p.dependencies()
        ]

    def parameter_at(self, row):
        return self._rows[row][1]

    def link(self, rows):
        """Constrain every parameter in `rows` to the first one."""
        if len(rows) < 2:
            return
        master = self.parameter_at(rows[0])
        constraint_col = self.COLUMNS.index("constraint")
        for row in rows[1:]:
            self.parameter_at(row).constraint = master
            idx_lo = self.index(row, self.COLUMNS.index("value"))
            idx_hi = self.index(row, constraint_col)
            self.dataChanged.emit(idx_lo, idx_hi)

    def unlink(self, rows):
        constraint_col = self.COLUMNS.index("constraint")
        for row in rows:
            self.parameter_at(row).constraint = None
            idx_lo = self.index(row, self.COLUMNS.index("value"))
            idx_hi = self.index(row, constraint_col)
            self.dataChanged.emit(idx_lo, idx_hi)
