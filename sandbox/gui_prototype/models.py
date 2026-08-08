"""
Prototype: a two-model replacement for refnx's monolithic
treeview_gui_model.TreeModel.

StructureTreeModel   -- pure navigation: Structure -> Component rows
                        (recursing into Stacks). No parameter data lives
                        in this model at all.
ParameterTableModel  -- flat, one row per Parameter. Populated by calling
                        `.parameters.flattened()` on whatever is currently
                        selected in the structure tree.

The point of the split: today's app has one Node subclass per component
type (SlabNode, LipidLeafletNode, ParNode, PropertyNode, ...), each with
its own hand-written data()/setData()/flags(), and dependency-aware
updates (unlink_dependent_parameters, notify_dependents, link_action)
are reimplemented in three separate places. Splitting navigation from
editing means there's exactly one generic node type in the tree, and
exactly one place (ParameterTableModel._rows_depending_on) that knows
how to propagate a change to linked parameters.
"""

from qtpy import QtCore
from qtpy.QtCore import Qt

from refnx.reflect import Stack


class _StructureNode:
    """Wraps a single Component. One class for every component type --
    there's nothing to override per-type because this model doesn't
    expose parameters, only navigation."""

    __slots__ = ("obj", "parent", "row", "children")

    def __init__(self, obj, parent, row):
        self.obj = obj
        self.parent = parent
        self.row = row
        self.children = []


class StructureTreeModel(QtCore.QAbstractItemModel):
    """
    Top-level rows are the Structure's components, in order. A Stack's
    members appear as its children, recursively -- same node class, no
    special-casing required (contrast with today's SlabNode/StackNode
    split, and the hardcoded fronting/backing row numbers in
    TreeFilter.filterAcceptsRow).
    """

    def __init__(self, structure=None, parent=None):
        super().__init__(parent)
        self._root = _StructureNode(None, None, 0)
        self.set_structure(structure)

    def set_structure(self, structure):
        self.beginResetModel()
        self._structure = structure
        self._root = _StructureNode(None, None, 0)
        if structure is not None:
            self._populate(self._root, structure)
        self.endResetModel()

    def _populate(self, parent_node, components):
        for i, c in enumerate(components):
            child = _StructureNode(c, parent_node, i)
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
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        obj = index.internalPointer().obj
        return getattr(obj, "name", None) or type(obj).__name__

    def component_for_index(self, index):
        """None means "nothing selected" -- caller should fall back to
        the whole structure's flattened parameters."""
        if not index.isValid():
            return None
        return index.internalPointer().obj


class ParameterTableModel(QtCore.QAbstractTableModel):
    """
    One row per Parameter, whatever the current selection handed us.
    Editing a value/bound writes straight to the Parameter and emits
    dataChanged both for the edited cell *and* for every other row whose
    parameter depends on it -- this is the one place in the whole
    prototype that needs to know about constraint dependencies.
    """

    COLUMNS = ("name", "value", "vary", "lb", "ub", "constraint")
    HEADERS = ("Name", "Value", "Vary", "Lower", "Upper", "Constraint")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parameters = []
        self._row_of = {}

    def set_parameters(self, parameters):
        self.beginResetModel()
        self._parameters = list(parameters)
        self._row_of = {p: i for i, p in enumerate(self._parameters)}
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._parameters)

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

        constrained = self._parameters[index.row()].constraint is not None
        if col in ("value", "lb", "ub") and not constrained:
            return base | Qt.ItemFlag.ItemIsEditable

        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        p = self._parameters[index.row()]
        col = self.COLUMNS[index.column()]

        if role == Qt.ItemDataRole.CheckStateRole and col == "vary":
            return Qt.CheckState.Checked if p.vary else Qt.CheckState.Unchecked

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
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

        p = self._parameters[index.row()]
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
            self._row_of[p]
            for p in self._parameters
            if p is not parameter and parameter in p.dependencies()
        ]

    def parameter_at(self, row):
        return self._parameters[row]
