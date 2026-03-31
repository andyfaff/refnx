import numpy as np

from refnx.analysis import Parameter, Parameters
from refnx._lib._cutil import c_flatten
from refnx._lib.util import flatten

from .common import Benchmark


def create(items, params, rng):
    for i in range(items):
        if rng.uniform() < 0.2:
            f = Parameters()
            _p = create(items - i, f, rng)
            params.append(_p)
        else:
            _p = Parameter(1)
            params.append(_p)
    return params


class Flatten(Benchmark):
    def setup(self):
        rng = np.random.default_rng(1892908)
        p = Parameters()
        self.p = create(20, p, rng)

    def time_cflatten(self):
        list(c_flatten(self.p))

    def time_flatten(self):
        list(flatten(self.p))
