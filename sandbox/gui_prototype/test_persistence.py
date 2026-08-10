"""
Unit tests for persistence.py: the restricted unpickler guarding
load_model/load_experiment against arbitrary code execution, the
save_experiment/load_experiment round trip, and window-state
save/restore via QSettings.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pickle
from importlib import resources

import pytest
from qtpy import QtWidgets
from qtpy.QtCore import QSettings

import refnx.analysis
from refnx.dataset import ReflectDataset
from refnx.reflect import SLD, ReflectModel

import persistence
from datastore import DataObject, DataStore


def _demo_datastore():
    pth = resources.files(refnx.analysis)
    dataset = ReflectDataset(pth / "tests" / "e361r.txt")
    structure = SLD(2.07)(0, 0) | SLD(3.47)(15, 3) | SLD(6.36)(0, 3)
    model = ReflectModel(structure)
    model.bkg.setp(vary=True, bounds=(1e-6, 5e-6))
    datastore = DataStore()
    datastore.add(DataObject("e361r", dataset, model))
    return datastore


class _ShellOut:
    """A pickle payload that runs an arbitrary command on unpickling --
    the standard demonstration that unpickling an untrusted file is
    equivalent to running arbitrary code, not just loading data. Never
    actually unpickled with plain pickle.load in this test; only used
    to confirm persistence's restricted loader refuses it."""

    def __reduce__(self):
        return (os.system, ("echo pwned",))


def test_restricted_unpickler_blocks_a_malicious_experiment(tmp_path):
    path = tmp_path / "malicious.mtft"
    with open(path, "wb") as f:
        pickle.dump({"datastore": _ShellOut(), "transform_form": "lin"}, f)

    with pytest.raises(pickle.UnpicklingError):
        persistence.load_experiment(path)


def test_restricted_unpickler_blocks_a_malicious_model(tmp_path):
    path = tmp_path / "malicious.pkl"
    with open(path, "wb") as f:
        pickle.dump(_ShellOut(), f)

    with pytest.raises(pickle.UnpicklingError):
        persistence.load_model(path)


def test_restricted_unpickler_allows_legitimate_refnx_objects(tmp_path):
    datastore = _demo_datastore()
    path = tmp_path / "experiment.mtft"
    persistence.save_experiment(datastore, "YX4", path)

    reloaded, transform_form = persistence.load_experiment(path)
    assert transform_form == "YX4"
    assert reloaded["e361r"].model.bkg.bounds.lb == 1e-6


def test_save_and_load_experiment_round_trip_preserves_links(tmp_path):
    datastore = _demo_datastore()
    other = _demo_datastore()["e361r"]
    other.name = "e365r"
    datastore.add(other)
    datastore["e365r"].model.bkg.constraint = datastore["e361r"].model.bkg
    datastore["e365r"].in_fit = False

    path = tmp_path / "experiment.mtft"
    persistence.save_experiment(datastore, "lin", path)
    reloaded, _ = persistence.load_experiment(path)

    assert reloaded["e365r"].in_fit is False
    assert reloaded["e361r"].in_fit is True
    assert (
        reloaded["e365r"].model.bkg.constraint is reloaded["e361r"].model.bkg
    )


def test_load_experiment_rejects_a_non_experiment_pickle(tmp_path):
    path = tmp_path / "not_an_experiment.pkl"
    with open(path, "wb") as f:
        pickle.dump({"just": "a dict"}, f)

    with pytest.raises(ValueError):
        persistence.load_experiment(path)


def test_window_state_round_trips(qtbot, tmp_path, monkeypatch):
    # redirected at a throwaway .ini file rather than whatever the
    # developer's real, OS-level Qt settings store happens to hold
    settings_path = str(tmp_path / "settings.ini")
    monkeypatch.setattr(
        persistence,
        "QSettings",
        lambda *a: QSettings(settings_path, QSettings.Format.IniFormat),
    )

    saved = QtWidgets.QMainWindow()
    qtbot.add_widget(saved)
    saved.resize(654, 321)
    persistence.save_window_state(saved)

    restored = QtWidgets.QMainWindow()
    qtbot.add_widget(restored)
    restored.resize(200, 200)
    persistence.restore_window_state(restored)

    assert restored.size().width() == 654
    assert restored.size().height() == 321
