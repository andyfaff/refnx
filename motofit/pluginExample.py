from __future__ import division
import numpy as np
import scipy as sp
import scipy.linalg
import scipy.integrate as spi
import math
from refnx.analysis import CurveFitter


class line(CurveFitter):
    '''
        fitfunction for a straightline
        y = p[0] + p[1] * x
    '''
    def __init__(self, xdata, ydata, parameters, edata=None, fcn_args=(),
                 fcn_kws=None):

        super(line, self).__init__(None,
                                   xdata,
                                   ydata,
                                   parameters,
                                   edata=edata,
                                   fcn_args=fcn_args,
                                   fcn_kws=fcn_kws)

    def model(self, parameters, *args):
        values = [param.value for param in parameters.values()]

        return values[0] + self.xdata * values[1]

class gauss1D(CurveFitter):
    '''
        fitfunction for a Gaussian
        y = p[0] + p[1] * exp(-0.5 * ((x - p[2])/p[3])**2)
    '''

    def __init__(self, xdata, ydata, parameters, edata=None, fcn_args=(),
                 fcn_kws=None):

        super(gauss1D, self).__init__(None,
                                      xdata,
                                      ydata,
                                      parameters,
                                      edata=edata,
                                      fcn_args=fcn_args,
                                      fcn_kws=fcn_kws)

    def model(self, parameters, *args):
        return parameters[0] + parameters[1] * \
            np.exp(-0.5 * np.power((self.xdata - parameters[2])/parameters[3], 2))