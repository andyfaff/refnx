from __future__ import division

try:
    from inspect import getfullargspec as _getargspec
except ImportError:
    # on 2.7
    from inspect import getargspec as _getargspec


def fitfunc(f):
    """
    A decorator that can be used to say if something is a fitfunc.
    """
    f.fitfuncwraps = True
    return f


class Model(object):
    def __init__(self, parameters, fitfunc=None, fcn_args=(), fcn_kwds=None):
        self._parameters = parameters

        self._fitfunc = None
        self._fitfunc_has_xerr = False
        self.fitfunc = fitfunc

        self.fcn_args = fcn_args
        self.fcn_kwds = {}
        if fcn_kwds is not None:
            self.fcn_kwds = fcn_kwds

    def __call__(self, x, p=None, x_err=None):
        return self.model(x, p=p, x_err=x_err)

    def model(self, x, p=None, x_err=None):
        # self.fitfunc or this method has to understand the structure of
        # self.params.
        if self.fitfunc is not None:
            kwds = {}
            kwds.update(self.fcn_kwds)

            if self._fitfunc_has_xerr:
                # fitfunc has resolution
                kwds['x_err'] = x_err

            _params = self._parameters
            if p is not None:
                _params = p

            return self.fitfunc(x, _params,
                                *self.fcn_args,
                                **kwds)
        else:
            raise RuntimeError("Overide Model.model() or provide a fitfunc to"
                               " the constructor")

    def lnprob(self):
        # the model can add additional terms to it's log-probability. However,
        # it should _not_ include lnprob from any of the parameters. That is
        # calculated by objective.lnprior.
        return 0

    @property
    def fitfunc(self):
        return self._fitfunc

    @fitfunc.setter
    def fitfunc(self, fitfunc):
        self._fitfunc = fitfunc
        self._fitfunc_has_xerr = False
        if 'x_err' in _getargspec(fitfunc).args:
            self._fitfunc_has_xerr = True

    @property
    def parameters(self):
        # override this if model adds more parameters than just
        # self._parameters
        return self._parameters