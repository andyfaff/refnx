import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.dirname(__file__))

from refnx.reflect import LipidLeaflet
from refnx.reflect._app._lipid_leaflet import Lipid

from dialogs import LipidLeafletDialog
from main import build_demo_datastore, MainWindow


def test_lipid_leaflet_dialog_lists_known_lipids(qtbot):
    dialog = LipidLeafletDialog()
    qtbot.add_widget(dialog)

    names = [
        dialog.lipid_combo.itemText(i)
        for i in range(dialog.lipid_combo.count())
    ]
    assert names[0] == ""  # nothing selected yet
    assert "h-DMPC" in names
    assert len(names) == 23  # 22 lipids + the blank placeholder


def test_lipid_leaflet_dialog_ok_disabled_until_a_lipid_is_chosen(qtbot):
    dialog = LipidLeafletDialog()
    qtbot.add_widget(dialog)

    assert not dialog._ok_button.isEnabled()

    dialog.lipid_combo.setCurrentText("h-DMPC")
    assert dialog._ok_button.isEnabled()

    dialog.lipid_combo.setCurrentText("")
    assert not dialog._ok_button.isEnabled()


def test_lipid_leaflet_dialog_populates_conditions_and_chemical_name(qtbot):
    dialog = LipidLeafletDialog()
    qtbot.add_widget(dialog)

    dialog.lipid_combo.setCurrentText("h-DMPC")

    conditions = [
        dialog.condition_combo.itemText(i)
        for i in range(dialog.condition_combo.count())
    ]
    assert conditions == ["fluid30C", "gel10C"]
    assert "dimyristoyl" in dialog.chemical_name_label.text()


def test_lipid_leaflet_dialog_component_matches_the_chosen_lipid(qtbot):
    dialog = LipidLeafletDialog()
    qtbot.add_widget(dialog)

    dialog.lipid_combo.setCurrentText("h-DMPC")
    dialog.condition_combo.setCurrentText("fluid30C")
    dialog.apm_spin.setValue(60.0)

    leaflet = dialog.component()
    assert isinstance(leaflet, LipidLeaflet)
    assert leaflet.name == "h-DMPC"

    lipid = Lipid(
        name="h-DMPC",
        head_formula="C10H18O8NP",
        tail_formula="C26H54",
        conditions={"fluid30C": [319, 782]},
    )
    expected_b_heads, expected_b_tails = lipid.neutron_scattering_lengths(
        "fluid30C"
    )

    assert leaflet.vm_heads.value == 319
    assert leaflet.vm_tails.value == 782
    assert leaflet.thickness_heads.value == 319 / 60.0
    assert leaflet.thickness_tails.value == 782 / 60.0
    assert leaflet.b_heads_real.value == expected_b_heads.real
    assert leaflet.b_tails_real.value == expected_b_tails.real


def test_add_lipid_leaflet_via_dialog_shows_the_lipid_picker(
    qtbot, monkeypatch
):
    from test_structure_editing import _FakeAddDialog

    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)

    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "LipidLeaflet", 2),
    )

    seeded = LipidLeaflet(
        50, 6e-4, 319, 319 / 50, -3e-4, 782, 782 / 50, 3, 3, name="h-DMPC"
    )

    class _FakeLipidDialog:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return 1

        def component(self):
            return seeded

    monkeypatch.setattr("main.LipidLeafletDialog", _FakeLipidDialog)
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before + 1
    assert do.model.structure[2] is seeded


def test_add_lipid_leaflet_cancelled_picker_aborts_the_whole_add(
    qtbot, monkeypatch
):
    from test_structure_editing import _FakeAddDialog

    datastore = build_demo_datastore()
    win = MainWindow(datastore)
    qtbot.add_widget(win)

    do = datastore["e361r"]
    n_before = len(do.model.structure)

    monkeypatch.setattr(
        "main.AddComponentDialog",
        lambda *a, **k: _FakeAddDialog("e361r", "LipidLeaflet", 2),
    )

    class _FakeLipidDialog:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return 0  # QDialog.DialogCode.Rejected

    monkeypatch.setattr("main.LipidLeafletDialog", _FakeLipidDialog)
    win.on_add_component_triggered()

    assert len(do.model.structure) == n_before  # nothing added
