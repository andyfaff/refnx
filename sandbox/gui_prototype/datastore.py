"""
DataObject / DataStore: the missing piece from the first version of this
prototype. That version deliberately worked with a single Objective, on
the assumption that "one dataset at a time" was a reasonable
simplification. It wasn't -- co-refining multiple datasets, and linking
parameters *across* them, is a core Motofit workflow, and it changes the
shape of the whole GUI: you need every dataset's parameters visible at
once (so you can multi-select across datasets to link them), not just
whichever one happens to be selected in a tree.

A DataObject is just a name + dataset + model. A DataStore is an ordered
collection of them. Deliberately much simpler than
refnx.reflect._app.dataobject.DataObject / datastore.DataStore, which
also track graph properties (colours, visibility styling) and
uncertainties -- not needed to demonstrate the architecture point.
"""

from dataclasses import dataclass

from refnx.reflect import ReflectModel
from refnx.dataset import ReflectDataset


@dataclass
class DataObject:
    name: str
    dataset: ReflectDataset
    model: ReflectModel
    in_fit: bool = True


class DataStore:
    def __init__(self):
        self._objects: dict[str, DataObject] = {}

    def __iter__(self):
        return iter(self._objects.values())

    def __len__(self):
        return len(self._objects)

    def __getitem__(self, name):
        return self._objects[name]

    def __contains__(self, name):
        return name in self._objects

    @property
    def names(self):
        return list(self._objects.keys())

    def add(self, data_object: DataObject):
        name = data_object.name
        # de-duplicate rather than silently overwrite
        if name in self._objects:
            i = 1
            while f"{name}_{i}" in self._objects:
                i += 1
            name = f"{name}_{i}"
            data_object.name = name
        self._objects[name] = data_object
        return data_object

    def remove(self, name):
        del self._objects[name]

    def fitted_objects(self):
        return [do for do in self._objects.values() if do.in_fit]
