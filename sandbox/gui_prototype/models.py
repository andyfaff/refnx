"""
DataStoreTreeModel   -- pure navigation: DataObject -> Component rows
                        (recursing into Stacks), one row per loaded
                        dataset at the top level, checkable to control
                        whether it's included in the next fit.
ParameterTableModel  -- a second, separate tree: Dataset -> [Model
                        parameters, one group per top-level Component
                        (recursing into Stacks)] -> individual
                        Parameter/ComponentProperty rows, expandable
                        per group. Still shows *every* checked
                        dataset's parameters at once, not just
                        whichever one is selected in the navigation
                        tree -- that's the point: you can only
                        multi-select parameters to link them if
                        they're all visible in the same view,
                        including across datasets. Grouping by
                        Component only changes how the rows are
                        organised, not which ones exist.

Splitting navigation from editing still means there's exactly one
generic node type per tree, and exactly one place
(ParameterTableModel._notify_dependents) that knows how to propagate a
change to linked parameters -- linking across datasets falls out of
that for free, since it only ever looks at Parameter identity and
`.dependencies()`, never which dataset or group a parameter came from.
"""

from qtpy import QtCore
from qtpy.QtCore import Qt

from refnx.analysis import Objective, Parameter, Transform
from refnx.reflect import LipidLeaflet, Slab, Stack
from refnx.reflect.spline import Spline

from datastore import DataObject


def _boundary_slab_hidden_parameters(structure):
    """
    Which Parameters shouldn't be shown for the top-level fronting/
    backing Slabs of a Structure: thickness and iSLD don't mean
    anything for a semi-infinite medium, and neither does roughness for
    the very first one (there's nothing above it to roughen against).
    Roughness for the *last* Slab is kept -- that's the backing medium's
    interface with whatever's above it, which is physically meaningful.
    volfrac solvent is hidden for both ends too -- fronting/backing
    media are pure phases, not a solvated mixture.

    Only applies to a Slab that's actually a top-level Structure member
    (position 0 or -1); a Slab nested inside a Stack has no such
    "boundary" meaning, so nothing is hidden for it.
    """
    hidden = set()
    if not len(structure):
        return hidden

    first = structure[0]
    if isinstance(first, Slab):
        hidden.add(first.thick)
        hidden.add(first.sld.imag)
        hidden.add(first.rough)
        hidden.add(first.vfsolv)

    if len(structure) > 1:
        last = structure[-1]
        if isinstance(last, Slab):
            hidden.add(last.thick)
            hidden.add(last.sld.imag)
            hidden.add(last.vfsolv)

    return hidden


# Attributes worth exposing in the GUI that aren't Parameters at all --
# a plain bool/str/whatever set directly on the Component -- so they'd
# otherwise be invisible no matter how the parameter table filters or
# displays actual Parameters. Small and explicit rather than
# auto-discovered: introspecting a Component for "any attribute that
# looks interesting" would as easily surface internal implementation
# details as something a user would want to edit. Mirrors the
# production app's PropertyNode usage in LipidLeafletNode/SplineNode.
COMPONENT_PROPERTIES = {
    LipidLeaflet: ("reverse_monolayer",),
    Spline: ("zgrad",),
}


class ComponentProperty:
    """
    A non-Parameter attribute of a Component -- e.g.
    LipidLeaflet.reverse_monolayer -- wrapped so it can sit in
    ParameterTableModel._rows alongside ordinary Parameters. Only bool
    attributes are supported for editing right now (both of the
    properties in COMPONENT_PROPERTIES are bools); anything else is
    shown read-only as text rather than silently failing to edit.
    """

    __slots__ = ("component", "attr_name")

    def __init__(self, component, attr_name):
        self.component = component
        self.attr_name = attr_name

    @property
    def value(self):
        return getattr(self.component, self.attr_name)

    @value.setter
    def value(self, new_value):
        setattr(self.component, self.attr_name, new_value)

    def __eq__(self, other):
        return (
            isinstance(other, ComponentProperty)
            and self.component is other.component
            and self.attr_name == other.attr_name
        )

    def __hash__(self):
        return hash((id(self.component), self.attr_name))


def _component_label(obj):
    """Display text for a DataObject or Component row -- its own name
    if it has one (most Components default to '' until named), falling
    back to the Python class name (e.g. "Slab", "LipidLeaflet")."""
    return getattr(obj, "name", None) or type(obj).__name__


def _component_properties(component):
    for cls, attrs in COMPONENT_PROPERTIES.items():
        if isinstance(component, cls):
            return [ComponentProperty(component, a) for a in attrs]
    return []


def _own_parameters(component):
    """A Component's own Parameters, not counting anything nested
    inside it -- a Stack's own Parameter is just `repeats`, since its
    children's parameters get grouped separately wherever this is used
    (ParameterTableModel's tree, and the structural addressing below),
    rather than being flattened in alongside it."""
    if isinstance(component, Stack):
        return [component.repeats]
    return component.parameters.flattened()


class StructureEditError(Exception):
    """Raised when an insert/remove/move would touch the first or last
    Component of a top-level Structure -- those positions are pinned,
    see DataStoreTreeModel's structural-editing methods below."""


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
        self.transform = Transform(None)
        self.set_datastore(datastore)

    def set_transform(self, transform):
        """Sets the Transform used for the chi2 column, and refreshes
        it immediately -- chi2 isn't cached, so nothing else needs to
        change for the new value to show up."""
        self.transform = transform
        self.refresh_chi2()

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

    COLUMNS = ("name", "chi2")
    HEADERS = ("Dataset", "χ²")

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

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        obj = index.internalPointer().obj
        col = self.COLUMNS[index.column()]

        if col == "chi2":
            if role == Qt.ItemDataRole.DisplayRole and isinstance(
                obj, DataObject
            ):
                objective = Objective(
                    obj.model, obj.dataset, transform=self.transform
                )
                return f"{objective.chisqr():.4g}"
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return _component_label(obj)

        if role == Qt.ItemDataRole.CheckStateRole and isinstance(
            obj, DataObject
        ):
            return (
                Qt.CheckState.Checked
                if obj.in_fit
                else Qt.CheckState.Unchecked
            )

        return None

    def refresh_chi2(self):
        """Emits dataChanged for every DataObject row's chi-squared
        column, so an already-visible tree picks up the latest
        parameter values -- chi2 isn't cached anywhere, data() computes
        it fresh every time this is called (after an edit, a fit, a
        structural change, ...). Only needed for views that have
        already rendered; a first paint always queries data() fresh."""
        n = len(self._root.children)
        if not n:
            return
        col = self.COLUMNS.index("chi2")
        top_left = self.index(0, col)
        bottom_right = self.index(n - 1, col)
        self.dataChanged.emit(top_left, bottom_right)

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

        if role == Qt.ItemDataRole.EditRole and not isinstance(
            obj, DataObject
        ):
            # renames a Component -- a DataObject's own name is a fixed
            # identity (it's the DataStore's key), so only Components
            # are editable here. The new name shows up in the
            # parameter tree too (see ParameterTableModel._group_label
            # / _component_label), since both just read `.name` off
            # the same live Component object -- no separate rename
            # propagation needed.
            obj.name = str(value)
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
    # The top-level fronting/backing Slabs are pinned: neither one can
    # ever be removed, dragged elsewhere, displaced by something else
    # being dragged into position 0 or -1, or displaced by a *new*
    # Component being inserted there either -- insert, remove, and move
    # all refuse to touch position 0 or -1 of a top-level Structure,
    # unconditionally, regardless of whether the result would still
    # technically have a Slab there. A Stack has no such rule; its
    # contents can be freely inserted/removed/reordered anywhere.

    def insert_component(
        self, data_object, position, component, container=None
    ):
        """Insert `component` at `position` into `data_object.model.
        structure`, or into `container` (a Stack found somewhere within
        it) if given -- a Stack is a list in its own right, so this is
        how a Component ever gets added *inside* one. Raises
        StructureEditError, and leaves the structure untouched, if this
        would insert a *new* Component as the first or last Component
        of a top-level Structure -- a Stack has no such rule."""
        is_top_level = container is None
        target = data_object.model.structure if is_top_level else container

        if is_top_level and (position == 0 or position == len(target)):
            raise StructureEditError(
                "A Component can't be inserted as the first or last "
                "Component of a Structure."
            )

        target.insert(position, component)
        self.set_datastore(self._datastore)  # rebuilds the tree from scratch

    def remove_component(self, index):
        """Remove the Component at `index` (top-level, or nested in a
        Stack). Returns the removed Component so the caller can unlink
        any parameters elsewhere that depended on it. Raises
        StructureEditError, and leaves the structure untouched, if this
        is the top-level fronting or backing Slab -- those can never be
        removed, no matter what would end up taking their place."""
        node = index.internalPointer()
        component = node.obj
        if isinstance(component, DataObject):
            raise StructureEditError("Select a Component, not a dataset.")

        parent_list, is_top_level = self._owning_list(node)
        position = parent_list.index(component)

        if is_top_level:
            if position == 0:
                raise StructureEditError(
                    "The first Component in a Structure can't be removed."
                )
            if position == len(parent_list) - 1:
                raise StructureEditError(
                    "The last Component in a Structure can't be removed."
                )

        del parent_list[position]
        self.set_datastore(self._datastore)
        return component

    def move_component(self, index, new_position):
        """Move the top-level Component at `index` to `new_position`
        within the same Structure. Nested (Stack) Components can't be
        dragged -- see flags(). Raises StructureEditError, and leaves
        the structure untouched, if the Component being dragged is the
        fronting/backing Slab, or if the destination is position 0 or
        -1 -- neither the boundary Slabs themselves, nor what occupies
        their position, can ever change via a drag."""
        node = index.internalPointer()
        component = node.obj
        parent_list, is_top_level = self._owning_list(node)
        if not is_top_level:
            raise StructureEditError(
                "Only top-level Components can be reordered."
            )

        old_position = parent_list.index(component)
        last_position = len(parent_list) - 1
        if old_position == 0 or old_position == last_position:
            raise StructureEditError(
                "The first and last Component in a Structure can't be "
                "moved."
            )

        # new_position is expressed in "before removing the dragged
        # Component" coordinates (Qt's drop-row convention); once it's
        # popped out, everything after its old slot shifts down by one.
        destination = new_position
        if destination > old_position:
            destination -= 1
        if destination == 0 or destination == last_position:
            raise StructureEditError(
                "A Component can't be moved into the first or last "
                "position."
            )

        del parent_list[old_position]
        parent_list.insert(destination, component)
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
            base |= Qt.ItemFlag.ItemIsEditable
            _, is_top_level = self._owning_list(node)
            if is_top_level:
                base |= (
                    Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
        return base


class _ModelParametersGroup:
    """Sentinel standing in for a DataObject's own scale/bkg/dq/
    q_offset parameters, which don't belong to any Component -- gives
    them a group row of their own in ParameterTableModel, the same way
    the production app's ReflectModelNode wraps them in a
    ParametersNode."""

    __slots__ = ("data_object",)

    def __init__(self, data_object):
        self.data_object = data_object


class _ParamNode:
    """One row in ParameterTableModel's tree: a dataset, a group (a
    DataObject's _ModelParametersGroup, or a Component -- possibly
    nested, for a Stack's children), or a leaf (Parameter or
    ComponentProperty). `dataset_name` is carried on every node so a
    leaf's owning dataset can be read without walking up the tree."""

    __slots__ = ("obj", "dataset_name", "parent", "row", "children")

    def __init__(self, obj, dataset_name, parent, row):
        self.obj = obj
        self.dataset_name = dataset_name
        self.parent = parent
        self.row = row
        self.children = []


class ParameterTableModel(QtCore.QAbstractItemModel):
    """
    Tree of every Parameter (and ComponentProperty) across every
    DataObject in the datastore that's currently checked for fitting
    (DataObject.in_fit): Dataset -> [Model parameters, one group per
    top-level Component, recursing into Stacks] -> individual rows.
    Grouping by Component only changes how rows are organised -- every
    checked dataset's parameters are still all present at once, not
    just whichever one is selected in the navigation tree, so
    multi-selecting rows to link them still works across groups and
    across datasets exactly as it did in the old flat table.

    Editing a value/bound writes straight to the Parameter and emits
    dataChanged both for the edited cell *and* for every other row
    whose parameter depends on it -- including rows belonging to a
    different dataset or a different Component group, since dependency
    checking only ever looks at Parameter identity, never which
    dataset or group a row came from.

    Unchecking a dataset in the tree hides its parameters here (see
    main.py's connection from DataStoreTreeModel.dataChanged to
    set_datastore). A constraint made while a dataset was checked still
    holds after it's unchecked and its rows disappear -- constraints
    live on the Parameter objects themselves, not in this model -- so
    linking across a not-currently-fitted dataset just means checking
    it, linking, then unchecking again afterwards if you still don't
    want it included in the fit.
    """

    COLUMNS = ("name", "value", "stderr", "vary", "lb", "ub", "constraint")
    HEADERS = ("Name", "Value", "σ", "Vary", "Lower", "Upper", "Constraint")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = _ParamNode(None, None, None, 0)
        self._rows = (
            []
        )  # list of (dataset_name, Parameter | ComponentProperty)
        self._leaf_node_of = {}  # Parameter | ComponentProperty -> _ParamNode
        self._row_of = (
            {}
        )  # Parameter -> QModelIndex (ComponentProperty isn't linkable)

    def set_datastore(self, datastore):
        self.beginResetModel()
        self._datastore = datastore
        self._root = _ParamNode(None, None, None, 0)
        self._rows = []
        self._leaf_node_of = {}
        if datastore is not None:
            for data_object in datastore:
                if not data_object.in_fit:
                    continue
                do_node = _ParamNode(
                    data_object,
                    data_object.name,
                    self._root,
                    len(self._root.children),
                )
                self._root.children.append(do_node)
                self._populate_dataset(do_node, data_object)
        self._row_of = {
            obj: self.createIndex(node.row, 0, node)
            for obj, node in self._leaf_node_of.items()
            if isinstance(obj, Parameter)
        }
        self.endResetModel()

    def _populate_dataset(self, do_node, data_object):
        name = data_object.name
        model = data_object.model

        group_node = _ParamNode(
            _ModelParametersGroup(data_object),
            name,
            do_node,
            len(do_node.children),
        )
        do_node.children.append(group_node)
        for p in (model.scale, model.bkg, model.dq, model.q_offset):
            self._add_leaf(group_node, p, name)

        hidden = _boundary_slab_hidden_parameters(model.structure)
        for component in model.structure:
            self._populate_component(do_node, component, name, hidden)

    def _populate_component(
        self, parent_node, component, dataset_name, hidden
    ):
        comp_node = _ParamNode(
            component, dataset_name, parent_node, len(parent_node.children)
        )
        parent_node.children.append(comp_node)

        for p in _own_parameters(component):
            if p in hidden:
                continue
            self._add_leaf(comp_node, p, dataset_name)

        for prop in _component_properties(component):
            self._add_leaf(comp_node, prop, dataset_name)

        if isinstance(component, Stack):
            for child in component:
                self._populate_component(
                    comp_node, child, dataset_name, hidden
                )

    def _add_leaf(self, parent_node, obj, dataset_name):
        node = _ParamNode(
            obj, dataset_name, parent_node, len(parent_node.children)
        )
        parent_node.children.append(node)
        self._leaf_node_of[obj] = node
        self._rows.append((dataset_name, obj))

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
        return len(self.COLUMNS)

    def leaf_count(self):
        """Total number of Parameter/ComponentProperty leaf rows across
        the whole tree -- the tree-model analogue of the old flat
        table's rowCount(), for callers that just want "how many
        editable rows are there" without caring about grouping."""
        return len(self._rows)

    def index_for(self, obj, column=0):
        """QModelIndex for a specific Parameter or ComponentProperty
        leaf, in the given column -- e.g. to build a selection or drive
        setData() directly without walking the tree by hand. Returns an
        invalid index if `obj` isn't currently shown (not present, or
        its dataset is unchecked)."""
        node = self._leaf_node_of.get(obj)
        if node is None:
            return QtCore.QModelIndex()
        return self.createIndex(node.row, column, node)

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
        obj = index.internalPointer().obj

        if isinstance(obj, ComponentProperty):
            if col == "value" and isinstance(obj.value, bool):
                return base | Qt.ItemFlag.ItemIsUserCheckable
            return base

        if isinstance(obj, Parameter):
            if col == "vary":
                return base | Qt.ItemFlag.ItemIsUserCheckable
            if col == "value" and obj.constraint is None:
                return base | Qt.ItemFlag.ItemIsEditable
            # bounds are meaningless (and hidden, see _parameter_data)
            # for a parameter that isn't currently varying -- nothing
            # to fit against them, so nothing to edit either
            if col in ("lb", "ub") and obj.constraint is None and obj.vary:
                return base | Qt.ItemFlag.ItemIsEditable
            return base

        return base  # group / dataset row -- name only, nothing editable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        obj = index.internalPointer().obj
        col = self.COLUMNS[index.column()]

        if isinstance(obj, ComponentProperty):
            return self._property_data(obj, col, role)
        if isinstance(obj, Parameter):
            return self._parameter_data(obj, col, role)

        if role == Qt.ItemDataRole.DisplayRole and col == "name":
            return self._group_label(obj)
        return None

    def _group_label(self, obj):
        if isinstance(obj, _ModelParametersGroup):
            return "Model"
        return _component_label(obj)  # DataObject or Component

    def _parameter_data(self, p, col, role):
        if role == Qt.ItemDataRole.CheckStateRole and col == "vary":
            return Qt.CheckState.Checked if p.vary else Qt.CheckState.Unchecked

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == "name":
                return p.name
            if col == "value":
                return f"{p.value:.6g}"
            if col == "stderr":
                return f"{p.stderr:.3g}" if p.stderr is not None else ""
            if col == "lb":
                return f"{p.bounds.lb:.6g}" if p.vary else ""
            if col == "ub":
                return f"{p.bounds.ub:.6g}" if p.vary else ""
            if col == "constraint":
                return repr(p.constraint) if p.constraint is not None else ""

        return None

    def _property_data(self, prop, col, role):
        if role == Qt.ItemDataRole.CheckStateRole:
            if col == "value" and isinstance(prop.value, bool):
                return (
                    Qt.CheckState.Checked
                    if prop.value
                    else Qt.CheckState.Unchecked
                )
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == "name":
                return prop.attr_name
            if col == "value" and not isinstance(prop.value, bool):
                return str(prop.value)

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        node = index.internalPointer()
        obj = node.obj
        col = self.COLUMNS[index.column()]

        if isinstance(obj, ComponentProperty):
            if (
                role == Qt.ItemDataRole.CheckStateRole
                and col == "value"
                and isinstance(obj.value, bool)
            ):
                obj.value = value == Qt.CheckState.Checked.value
                self.dataChanged.emit(index, index, [role])
                return True
            return False

        if isinstance(obj, Parameter):
            p = obj
            if role == Qt.ItemDataRole.CheckStateRole and col == "vary":
                p.vary = value == Qt.CheckState.Checked.value
                self.dataChanged.emit(index, index, [role])
                # lb/ub are hidden (and non-editable) unless the
                # parameter varies -- that visibility just flipped, so
                # those cells need to be told to re-query data()/
                # flags(), not just the checkbox's own cell
                node = index.internalPointer()
                lb_idx = self.createIndex(
                    node.row, self.COLUMNS.index("lb"), node
                )
                ub_idx = self.createIndex(
                    node.row, self.COLUMNS.index("ub"), node
                )
                self.dataChanged.emit(lb_idx, ub_idx)
                return True

            if role == Qt.ItemDataRole.EditRole and col in (
                "value",
                "lb",
                "ub",
            ):
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
                    self._clear_dataset_stderr(node.dataset_name)
                return True

        return False

    def _clear_dataset_stderr(self, dataset_name):
        """A value just changed by hand -- every previously-computed
        uncertainty for that dataset is stale now, not just the edited
        parameter's own (correlated parameters shift too), so clear
        all of them. Mirrors the production app's
        clear_data_object_uncertainties. Only fires on a "value" edit;
        toggling Vary or nudging a bound doesn't itself invalidate a
        fit that's already been run."""
        if self._datastore is None or dataset_name not in self._datastore:
            return
        stderr_col = self.COLUMNS.index("stderr")
        model = self._datastore[dataset_name].model
        for p in model.parameters.flattened():
            if p.stderr is None:
                continue
            p.stderr = None
            node = self._leaf_node_of.get(p)
            if node is None:
                continue
            idx = self.createIndex(node.row, stderr_col, node)
            self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.EditRole])

    def _notify_dependents(self, parameter):
        value_col = self.COLUMNS.index("value")
        for p, idx in self._row_of.items():
            if p is parameter or parameter not in p.dependencies():
                continue
            node = idx.internalPointer()
            value_idx = self.createIndex(node.row, value_col, node)
            self.dataChanged.emit(
                value_idx, value_idx, [Qt.ItemDataRole.EditRole]
            )

    def parameter_at(self, index):
        return index.internalPointer().obj

    def link(self, indexes):
        """Constrain every (real Parameter) index in `indexes` to the
        first one. ComponentProperty/group rows in the selection are
        silently skipped -- refnx constraints only apply to
        Parameters."""
        indexes = [
            i for i in indexes if isinstance(self.parameter_at(i), Parameter)
        ]
        if len(indexes) < 2:
            return
        master = self.parameter_at(indexes[0])
        value_col = self.COLUMNS.index("value")
        constraint_col = self.COLUMNS.index("constraint")
        for idx in indexes[1:]:
            self.parameter_at(idx).constraint = master
            node = idx.internalPointer()
            idx_lo = self.createIndex(node.row, value_col, node)
            idx_hi = self.createIndex(node.row, constraint_col, node)
            self.dataChanged.emit(idx_lo, idx_hi)

    def unlink(self, indexes):
        value_col = self.COLUMNS.index("value")
        constraint_col = self.COLUMNS.index("constraint")
        for idx in indexes:
            obj = self.parameter_at(idx)
            if not isinstance(obj, Parameter):
                continue
            obj.constraint = None
            node = idx.internalPointer()
            idx_lo = self.createIndex(node.row, value_col, node)
            idx_hi = self.createIndex(node.row, constraint_col, node)
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
        selected in the tree. ComponentProperty rows have no such thing
        as "varying" and are skipped.

        Returns how many parameters were touched, so the caller can
        report something more useful than silence if it's zero.
        """
        lb_col = self.COLUMNS.index("lb")
        ub_col = self.COLUMNS.index("ub")
        touched = 0
        for p, idx in self._row_of.items():
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
            node = idx.internalPointer()
            idx_lo = self.createIndex(node.row, lb_col, node)
            idx_hi = self.createIndex(node.row, ub_col, node)
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


def same_model_shape(data_objects):
    """Whether every DataObject's model has the same number of
    top-level Components and the same total parameter count -- the
    "same model" precondition equivalent_parameter() assumes, checked
    up front so linking fails with one clear message instead of
    silently linking the wrong thing. Mirrors the production app's
    link_equivalent_action / is_same_structure check."""
    data_objects = list(data_objects)
    ncomponents = {len(do.model.structure) for do in data_objects}
    nparams = {
        len(list(do.model.parameters.flattened())) for do in data_objects
    }
    return len(ncomponents) <= 1 and len(nparams) <= 1


def _dataset_parameter_addresses(data_object):
    """Maps every Parameter/ComponentProperty in `data_object.model` to
    an address describing its position *structurally* -- which
    top-level Component (recursing into Stacks) and which of that
    Component's own parameters/properties -- rather than by row number,
    so equivalent_parameter() can look the same address up on a
    different dataset assumed to have the same model shape.
    """
    model = data_object.model
    addresses = {}
    for i, p in enumerate((model.scale, model.bkg, model.dq, model.q_offset)):
        addresses[p] = ("model", i)

    def walk(component, path):
        for i, p in enumerate(_own_parameters(component)):
            addresses[p] = ("component", path, "parameter", i)
        for i, prop in enumerate(_component_properties(component)):
            addresses[prop] = ("component", path, "property", i)
        if isinstance(component, Stack):
            for i, child in enumerate(component):
                walk(child, path + (i,))

    for i, component in enumerate(model.structure):
        walk(component, (i,))

    return addresses


def _component_at_path(data_object, path):
    component = data_object.model.structure[path[0]]
    for i in path[1:]:
        component = component[i]
    return component


def equivalent_parameter(source_data_object, parameter, target_data_object):
    """The Parameter/ComponentProperty in `target_data_object.model`
    occupying the same structural position as `parameter` does in
    `source_data_object.model` -- assumes the two models have the same
    shape (see same_model_shape()). Returns None if `parameter` isn't
    found in the source, or if the target has nothing at that address
    (a real shape mismatch that same_model_shape's cheap count check
    didn't catch)."""
    address = _dataset_parameter_addresses(source_data_object).get(parameter)
    if address is None:
        return None

    if address[0] == "model":
        _, i = address
        model = target_data_object.model
        return (model.scale, model.bkg, model.dq, model.q_offset)[i]

    _, path, kind, i = address
    try:
        component = _component_at_path(target_data_object, path)
    except (IndexError, TypeError):
        return None

    candidates = (
        _own_parameters(component)
        if kind == "parameter"
        else _component_properties(component)
    )
    if i >= len(candidates):
        return None
    return candidates[i]
