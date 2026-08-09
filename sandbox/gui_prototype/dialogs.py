"""
AddComponentDialog: picks a dataset, a container (the top level of its
Structure, or a Stack found somewhere within it), a Component type, and
a position within that container.

Deliberately doesn't have per-type parameter entry fields (a full
LipidLeaflet needs nine required numbers, Spline needs knot arrays,
etc. -- replicating the production app's dedicated LipidLeafletDialog /
SplineDialog is a separate, larger piece of work). Instead this hands
back a Component built with reasonable placeholder values from
`default_component()`, which then shows up in ParameterTableModel like
any other Component's parameters -- because that model is generic (it
just flattens whatever `.parameters` a Component exposes), editing the
placeholder values afterward needs no bespoke UI at all.
"""

from qtpy import QtWidgets

from refnx.reflect import SLD, LipidLeaflet, Stack
from refnx.reflect.spline import Spline


COMPONENT_KINDS = ("Slab", "LipidLeaflet", "Spline", "Stack")


def default_component(kind):
    if kind == "Slab":
        return SLD(3.47)(15, 3)
    if kind == "LipidLeaflet":
        return LipidLeaflet(
            apm=50,
            b_heads=6.01e-4,
            vm_heads=319,
            thickness_heads=9,
            b_tails=-2.92e-4,
            vm_tails=782,
            thickness_tails=14,
            rough_head_tail=3,
            rough_preceding_mono=3,
            name="lipid",
        )
    if kind == "Spline":
        return Spline(extent=30, vs=[3.0, 3.0], dz=[0.33, 0.33], name="spline")
    if kind == "Stack":
        return Stack([SLD(3.47)(15, 3)], repeats=2, name="stack")
    raise ValueError(f"Unknown component kind: {kind!r}")


def _iter_stacks(component, path=()):
    """Yields (stack, path) for every Stack found within `component` --
    itself, if it is one, then recursing into its children (a Stack can
    nest another Stack). `path` is the sequence of indices needed to
    reach it from the top of the Structure -- e.g. (2,) for a top-level
    Stack at position 2, or (1, 0) for one nested at position 0 inside
    a Stack at top-level position 1 -- since a Stack's own `.name` is
    just a label a user typed in (or left blank), not a unique
    identifier: two Stacks can easily share a name, or have none at
    all, so the container list needs something else to tell them apart
    by. Ordinary Components can't hold anything, so they're never
    yielded here."""
    if isinstance(component, Stack):
        yield component, path
        for i, child in enumerate(component):
            yield from _iter_stacks(child, path + (i,))


def _containers(data_object):
    """(label, container) pairs for every place a new Component could
    go in `data_object`'s Structure: the top level itself (`None`),
    plus every Stack found anywhere within it, each labelled with its
    structural position so multiple Stacks stay distinguishable even
    if they share a name -- a Stack is the only kind of Component that
    can hold other Components."""
    containers = [("Top level", None)]
    for i, top_level in enumerate(data_object.model.structure):
        for stack, path in _iter_stacks(top_level, (i,)):
            label = getattr(stack, "name", None) or "Stack"
            position = " → ".join(str(p) for p in path)
            containers.append(
                (f"{label} (Stack at position {position})", stack)
            )
    return containers


class AddComponentDialog(QtWidgets.QDialog):
    def __init__(
        self,
        datastore,
        default_dataset=None,
        default_position=0,
        default_container=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Component")
        self._datastore = datastore

        self.dataset_combo = QtWidgets.QComboBox()
        self.dataset_combo.addItems(datastore.names)
        if default_dataset in datastore.names:
            self.dataset_combo.setCurrentText(default_dataset)
        self.dataset_combo.currentTextChanged.connect(self._update_containers)

        self.container_combo = QtWidgets.QComboBox()
        self.container_combo.currentIndexChanged.connect(
            self._update_position_range
        )

        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItems(COMPONENT_KINDS)

        self.position_spin = QtWidgets.QSpinBox()

        self._update_containers(self.dataset_combo.currentText())
        if default_container is not None:
            self._select_container(default_container)
        self.position_spin.setValue(
            min(
                max(default_position, self.position_spin.minimum()),
                self.position_spin.maximum(),
            )
        )

        form = QtWidgets.QFormLayout()
        form.addRow("Dataset:", self.dataset_combo)
        form.addRow("Add into:", self.container_combo)
        form.addRow("Component type:", self.kind_combo)
        form.addRow("Insert at position:", self.position_spin)

        hint = QtWidgets.QLabel(
            "At the top level, the first and last Component are pinned "
            "-- a new Component can only go somewhere in between. Inside "
            "a Stack there's no such restriction: position 0 = before "
            "everything in it, the last position = after everything."
        )
        hint.setWordWrap(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _update_containers(self, dataset_name):
        if dataset_name not in self._datastore:
            return
        self.container_combo.clear()
        for label, container in _containers(self._datastore[dataset_name]):
            self.container_combo.addItem(label, container)

    def _select_container(self, container):
        for i in range(self.container_combo.count()):
            if self.container_combo.itemData(i) is container:
                self.container_combo.setCurrentIndex(i)
                return

    def _update_position_range(self, *_args):
        if self.container_combo.currentIndex() == -1:
            return
        dataset_name = self.dataset_combo.currentText()
        if dataset_name not in self._datastore:
            return
        container = self.container_combo.currentData()
        if container is None:
            # position 0 or len(target) would insert as a *new* first/
            # last Component of the top-level Structure -- pinned, so
            # not offered here at all (see models.insert_component)
            target = self._datastore[dataset_name].model.structure
            lo, hi = 1, max(1, len(target) - 1)
        else:
            lo, hi = 0, len(container)
        self.position_spin.setRange(lo, hi)

    def dataset_name(self):
        return self.dataset_combo.currentText()

    def container(self):
        return self.container_combo.currentData()

    def kind(self):
        return self.kind_combo.currentText()

    def position(self):
        return self.position_spin.value()


class DatasetMultiSelectDialog(QtWidgets.QDialog):
    """Pick any number of datasets by name -- used by "Link Equivalent
    Parameters" to choose which other datasets to link across, mirroring
    the production app's DataObjectSelectorDialog (a checkable list),
    just without that dialog's dedicated widget class.

    `preselected` pre-selects the given names on open -- callers use
    this to remember whichever datasets were picked last time, so
    repeated linking (a common workflow: link one parameter, then the
    next, against the same set of datasets each time) doesn't need
    re-picking them every time the dialog appears."""

    def __init__(
        self, names, title="Select datasets", preselected=(), parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.MultiSelection
        )
        self.list_widget.addItems(names)
        preselected = set(preselected)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() in preselected:
                item.setSelected(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addWidget(buttons)

    def selected_names(self):
        return [item.text() for item in self.list_widget.selectedItems()]
