#!/usr/bin/env python

__authors__ = "Martin Sandve Alnes"
__date__ = "2008-08-22 -- 2008-08-22"

import unittest

from ufl import *
from ufl.algorithms import * 
from ufl.algorithms.swiginac_eval import *

# disable log output
import logging
logging.basicConfig(level=logging.CRITICAL)


class Context:
    "Context class for obtaining terminal expressions."
    def __init__(self, x, basisfunctions, functions, variables):
        self._x = x
        self._basisfunctions = basisfunctions
        self._functions = functions
        self._variables = variables
    
    def x(self, i):
        return self._x[i]
    
    def basisfunction(self, i):
        return self._basisfunctions[i]
    
    def function(self, i):
        return self._functions[i]
    
    def variable(self, i):
        return self._variables.get(i, None)
    
    def facet_normal(self):
        return NotImplemented

_0 = swiginac.numeric(0.0)
_1 = swiginac.numeric(1.0)

class SwiginacTestCase(unittest.TestCase):
    
    def setUp(self):
        self.x = [swiginac.symbol(name) for name in ("x", "y", "z")]
        x, y, z = self.x
        basisfunctions = [1.0-x-y, x, y]
        functions      = [x*y]
        variables      = {}
        self.context = Context(x, basisfunctions, functions, variables)
    
    def test_number(self):
        f = Number(1.23)
        g = evaluate_as_swiginac(f, self.context)
        self.assertTrue((g-1.23) == 0)

    def test_basisfunction(self):
        x, y, z = self.x
        element = FiniteElement("CG", "triangle", 1)
        v = TestFunction(element)
        u = TrialFunction(element)
        a = 1.23*v*dx
        a = renumber_arguments(a)
        f = a.cell_integrals()[0]._integrand
        g = evaluate_as_swiginac(f, self.context)
        self.assertTrue((g-1.23*self.context._basisfunctions[0]) == 0)

    def test_mass(self):
        x, y, z = self.x
        element = FiniteElement("CG", "triangle", 1)
        v = TestFunction(element)
        u = TrialFunction(element)
        w = Function(element)
        a = (1.23 + w)*u*v*dx
        a = renumber_arguments(a)
        f1 = a.cell_integrals()[0]._integrand
        f2 = flatten(f1)
        g1 = evaluate_as_swiginac(f1, self.context)
        g2 = evaluate_as_swiginac(f2, self.context)
        # Get expressions for arguments:
        v = self.context._basisfunctions[0]
        u = self.context._basisfunctions[1]
        w = self.context._functions[0]
        self.assertTrue((g1 - (1.23 + w)*u*v) == 0)
        self.assertTrue((g2 - (1.23 + w)*u*v) == 0)

    def _test_something(self):
        element = FiniteElement("CG", "triangle", 1)
        
        v = TestFunction(element)
        u = TrialFunction(element)
        w = Function(element, "w")
        
        f = (w**2/2)*dx
        L = w*v*dx
        a = u*v*dx
        F  = Derivative(f, w)
        J1 = Derivative(L, w)
        J2 = Derivative(F, w)
    

if __name__ == "__main__":
    unittest.main()