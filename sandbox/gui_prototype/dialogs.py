"""
AddComponentDialog: picks a dataset, a Component type, and a position.

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


class AddComponentDialog(QtWidgets.QDialog):
    def __init__(
        self,
        datastore,
        default_dataset=None,
        default_position=0,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Add Component")
        self._datastore = datastore

        self.dataset_combo = QtWidgets.QComboBox()
        self.dataset_combo.addItems(datastore.names)
        if default_dataset in datastore.names:
            self.dataset_combo.setCurrentText(default_dataset)
        self.dataset_combo.currentTextChanged.connect(
            self._update_position_range
        )

        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItems(COMPONENT_KINDS)

        self.position_spin = QtWidgets.QSpinBox()
        self._update_position_range(self.dataset_combo.currentText())
        self.position_spin.setValue(
            min(default_position, self.position_spin.maximum())
        )

        form = QtWidgets.QFormLayout()
        form.addRow("Dataset:", self.dataset_combo)
        form.addRow("Component type:", self.kind_combo)
        form.addRow("Insert at position:", self.position_spin)

        hint = QtWidgets.QLabel(
            "Position 0 = before everything; the last position = after "
            "everything. Only a Slab can go first or last."
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

    def _update_position_range(self, dataset_name):
        if dataset_name not in self._datastore:
            return
        n = len(self._datastore[dataset_name].model.structure)
        self.position_spin.setRange(0, n)

    def dataset_name(self):
        return self.dataset_combo.currentText()

    def kind(self):
        return self.kind_combo.currentText()

    def position(self):
        return self.position_spin.value()
