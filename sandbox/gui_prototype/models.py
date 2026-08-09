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

from refnx.reflect import Slab, Stack

from datastore import DataObject


class StructureEditError(Exception):
    """Raised when an add/remove/move would leave a top-level Structure
    without a Slab as its first and/or last Component."""


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

    # -- structural editing: add / remove / reorder Components --
    #
    # All three go through the same shape: build the list the mutation
    # *would* produce, validate it, and only then touch the real
    # refnx Structure/Stack. That keeps the "first and last must be a
    # Slab" rule (which only applies to a top-level Structure -- Stacks
    # have no such requirement) enforced in one place instead of
    # separately in insert/remove/move.

    def _check_boundary(self, is_top_level, resulting_components):
        if not is_top_level:
            return
        if not resulting_components:
            raise StructureEditError("A structure can't be left empty.")
        if not isinstance(resulting_components[0], Slab):
            raise StructureEditError(
                "The first Component in a Structure must be a Slab."
            )
        if not isinstance(resulting_components[-1], Slab):
            raise StructureEditError(
                "The last Component in a Structure must be a Slab."
            )

    def insert_component(self, data_object, position, component):
        """Insert `component` into `data_object.model.structure` at
        `position`. Raises StructureEditError, and leaves the structure
        untouched, if that would put a non-Slab first or last."""
        structure = data_object.model.structure
        prospective = list(structure)
        prospective.insert(position, component)
        self._check_boundary(True, prospective)

        structure.insert(position, component)
        self.set_datastore(self._datastore)  # rebuilds the tree from scratch

    def remove_component(self, index):
        """Remove the Component at `index` (top-level, or nested in a
        Stack). Returns the removed Component so the caller can unlink
        any parameters elsewhere that depended on it. Raises
        StructureEditError, and leaves the structure untouched, if
        removing a top-level Component would put a non-Slab first or
        last (or leave it empty)."""
        node = index.internalPointer()
        component = node.obj
        if isinstance(component, DataObject):
            raise StructureEditError("Select a Component, not a dataset.")

        parent_list, is_top_level = self._owning_list(node)
        position = parent_list.index(component)

        prospective = list(parent_list)
        del prospective[position]
        self._check_boundary(is_top_level, prospective)

        del parent_list[position]
        self.set_datastore(self._datastore)
        return component

    def move_component(self, index, new_position):
        """Move the top-level Component at `index` to `new_position`
        within the same Structure. Nested (Stack) Components can't be
        dragged -- see flags(). Raises StructureEditError, and leaves
        the structure untouched, on a boundary violation."""
        node = index.internalPointer()
        component = node.obj
        parent_list, is_top_level = self._owning_list(node)
        if not is_top_level:
            raise StructureEditError(
                "Only top-level Components can be reordered."
            )

        old_position = parent_list.index(component)
        prospective = list(parent_list)
        prospective.pop(old_position)
        if new_position > old_position:
            new_position -= 1
        prospective.insert(new_position, component)
        self._check_boundary(True, prospective)

        del parent_list[old_position]
        parent_list.insert(new_position, component)
        self.set_datastore(self._datastore)

    def _owning_list(self, node):
        """Returns (list, is_top_level) for the list that directly
        contains `node`'s Component -- the parent DataObject's
        Structure, or an enclosing Stack."""
        parent_obj = node.parent.obj
        if isinstance(parent_obj, DataObject):
            return parent_obj.model.structure, True
        return parent_obj, False  # parent_obj is a Stack

    # -- drag and drop (top-level Components only, reorder in place) --
    #
    # Doesn't serialise row-index paths into the dragged MIME data --
    # that's brittle if the tree changes shape between drag-start and
    # drop (see the review of refnx.reflect._app.treeview_gui_model's
    # dropMimeData, which does exactly that). Since the drag and the
    # drop happen within the same running model instance, it's simpler
    # and more robust to just remember the live Component object being
    # dragged as a plain attribute.

    _MIME_TYPE = "application/x-refnx-component"

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [self._MIME_TYPE]

    def mimeData(self, indexes):
        if not indexes:
            return None
        node = indexes[0].internalPointer()
        _, is_top_level = self._owning_list(node)
        if not is_top_level:
            return None
        self._drag_component = node.obj
        mime = QtCore.QMimeData()
        mime.setData(self._MIME_TYPE, b"1")  # placeholder; real payload
        return mime  # is the attribute above, read back in dropMimeData

    def dropMimeData(self, data, action, row, column, parent):
        component = getattr(self, "_drag_component", None)
        self._drag_component = None
        if component is None or not data.hasFormat(self._MIME_TYPE):
            return False

        # dropping "onto" a row with row == -1 means "as a child of
        # parent" -- not supported, only reordering among siblings is.
        if row == -1:
            return False

        # a component's siblings are the other children of its owning
        # DataObject, so a valid drop target is a DataObject's own
        # index (Qt passes that as `parent` when you drop between two
        # of its children in the tree view).
        if not parent.isValid():
            return False
        target_do = parent.internalPointer().obj
        if not isinstance(target_do, DataObject):
            return False

        source_index = None
        for i, child in enumerate(parent.internalPointer().children):
            if child.obj is component:
                source_index = self.index(i, 0, parent)
                break
        if source_index is None:
            # dropped onto a different dataset than the one the
            # component came from -- not supported
            return False

        try:
            self.move_component(source_index, row)
        except StructureEditError:
            return False
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        node = index.internalPointer()
        obj = node.obj
        if isinstance(obj, DataObject):
            base |= (
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDropEnabled
            )
        else:
            _, is_top_level = self._owning_list(node)
            if is_top_level:
                base |= (
                    Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
        return base


class ParameterTableModel(QtCore.QAbstractTableModel):
    """
    One row per Parameter, across every DataObject in the datastore
    that's currently checked for fitting (DataObject.in_fit). Editing a
    value/bound writes straight to the Parameter and emits dataChanged
    both for the edited cell *and* for every other row whose parameter
    depends on it -- including rows belonging to a different dataset,
    since dependency checking only ever looks at Parameter identity,
    never which dataset a row came from.

    Unchecking a dataset in the tree hides its parameters here (see
    main.py's connection from DataStoreTreeModel.dataChanged to
    set_datastore). A constraint made while a dataset was checked still
    holds after it's unchecked and its rows disappear -- constraints
    live on the Parameter objects themselves, not in this model -- so
    linking across a not-currently-fitted dataset just means checking
    it, linking, then unchecking again afterwards if you still don't
    want it included in the fit.
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
                if not data_object.in_fit:
                    continue
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

    def auto_limits(self):
        """
        Set bounds to [0, 2*value] on every currently-varying parameter
        (or [2*value, 0] if value is negative -- same shape, just
        reflected around zero). Mirrors the production app's
        on_auto_limits_button_clicked exactly, including not
        special-casing value == 0 (which produces a zero-width [0, 0]
        bound -- a known quirk of the original heuristic, not something
        introduced here).

        Applies to every varying parameter currently in the table, i.e.
        every checked dataset's varying parameters -- not just a
        selection -- same scope as the production app's button, which
        acts on "currently fitting" datasets rather than whatever's
        selected in the tree.

        Returns how many parameters were touched, so the caller can
        report something more useful than silence if it's zero.
        """
        lb_col = self.COLUMNS.index("lb")
        ub_col = self.COLUMNS.index("ub")
        touched = 0
        for row, (_, p) in enumerate(self._rows):
            if not p.vary:
                continue
            val = p.value
            if val < 0:
                p.bounds.lb = 2 * val
                p.bounds.ub = 0
            else:
                p.bounds.lb = 0
                p.bounds.ub = 2 * val
            touched += 1
            idx_lo = self.index(row, lb_col)
            idx_hi = self.index(row, ub_col)
            self.dataChanged.emit(idx_lo, idx_hi)
        return touched


def unlink_dependents(datastore, removed_parameters):
    """
    When a Component is removed, its own Parameters go with it, but
    other Parameters -- possibly in a different dataset, possibly in a
    dataset that's currently unchecked and so not shown in
    ParameterTableModel at all -- might be constrained to depend on one
    of them. Left alone, those constraints would reference Parameter
    objects that no longer belong to any Structure. This clears them.

    Deliberately a free function taking `datastore` directly rather than
    a method on ParameterTableModel: that model only knows about
    currently-checked datasets (see its docstring), but a constraint can
    exist on an unchecked dataset's parameter too, so this needs to see
    everything, filtered or not.

    Returns the list of Parameters that had a constraint cleared, so the
    caller can report what happened.
    """
    removed = set(removed_parameters)
    unlinked = []
    for data_object in datastore:
        for p in data_object.model.parameters.flattened():
            if p not in removed and removed.intersection(p.dependencies()):
                p.constraint = None
                unlinked.append(p)
    return unlinked
