import unittest
import pyplatypus.analysis.reflect as reflect
import pyplatypus.analysis._creflect as _creflect
import pyplatypus.analysis._reflect as _reflect
import pyplatypus.analysis.curvefitter as curvefitter

import numpy as np
from numpy.testing import assert_almost_equal, assert_equal
import os.path

path = os.path.dirname(os.path.abspath(__file__))

class TestReflect(unittest.TestCase):

    def setUp(self):
        self.coefs = np.zeros((12))
        self.coefs[0] = 1.
        self.coefs[1] = 1.
        self.coefs[4] = 2.07
        self.coefs[7] = 3
        self.coefs[8] = 100
        self.coefs[9] = 3.47
        self.coefs[11] = 2
        
        self.layer_format = reflect.convert_coefs_to_layer_format(self.coefs)

        theoretical = np.loadtxt(os.path.join(path, 'theoretical.txt'))
        qvals, rvals = np.hsplit(theoretical, 2)
        self.qvals = qvals.flatten()
        self.rvals = rvals.flatten()

    def test_abeles(self):
        #    test reflectivity calculation with values generated from Motofit
        calc = reflect.abeles(self.qvals, self.coefs)

        assert_almost_equal(calc, self.rvals)

    def test_format_conversion(self):
        coefs = reflect.convert_layer_format_to_coefs(self.layer_format)
        assert_equal(coefs, self.coefs)
        
    def test_c_abeles(self):
        #    test reflectivity calculation with values generated from Motofit
        calc = _creflect.abeles(self.qvals, self.layer_format)
        assert_almost_equal(calc, self.rvals)

    def test_py_abeles(self):
        # test reflectivity calculation with values generated from Motofit
        calc = _reflect.abeles(self.qvals, self.layer_format)
        assert_almost_equal(calc, self.rvals)

    def test_reflectivity_fitter(self):
        # test reflectivity calculation with values generated from Motofit
        params = curvefitter.params(self.coefs)
        
        fitter = reflect.ReflectivityFitter(params, self.qvals, self.rvals)
        model = fitter.model(params)

        assert_almost_equal(model, self.rvals)
        
    def test_smearedabeles(self):
        # test smeared reflectivity calculation with values generated from
        # Motofit (quadrature precsion order = 13)
        theoretical = np.loadtxt(os.path.join(path, 'smeared_theoretical.txt'))
        qvals, rvals, dqvals = np.hsplit(theoretical, 3)
        '''
        the order of the quadrature precision used to create these smeared
        values in Motofit was 13.
        Do the same here
        '''
        calc = reflect.abeles(qvals.flatten(), self.coefs,
                              **{'dqvals': dqvals.flatten(), 'quad_order': 13})

        assert_almost_equal(calc, rvals.flatten())

    def test_smeared_reflectivity_fitter(self):
        # test smeared reflectivity calculation with values generated from
        # Motofit (quadrature precsion order = 13)
        theoretical = np.loadtxt(os.path.join(path, 'smeared_theoretical.txt'))
        qvals, rvals, dqvals = np.hsplit(theoretical, 3)
        '''
        the order of the quadrature precision used to create these smeared
        values in Motofit was 13.
        Do the same here
        '''
        params = curvefitter.params(self.coefs)
        
        fitter = reflect.ReflectivityFitter(params, qvals.flatten(), 
                                            rvals.flatten(),
                                            kwds={'dqvals': dqvals.flatten(),
                                                  'quad_order': 13})
        model = fitter.model(params)

        assert_almost_equal(model, rvals.flatten())
        
    def test_sld_profile(self):
        # test SLD profile with SLD profile from Motofit.
        np.seterr(invalid='raise')
        profile = np.loadtxt(os.path.join(path, 'sld_theoretical_R.txt'))
        z, rho = np.split(profile, 2)
        myrho = reflect.sld_profile(self.coefs, z.flatten())
        assert_almost_equal(myrho, rho.flatten())


if __name__ == '__main__':
    unittest.main()
