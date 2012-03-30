"""This module defines the Expr class, the superclass 
for all expression tree node types in UFL.

NB! A note about other operators not implemented here:

More operators (special functions) on Exprs are defined in exproperators.py,
as well as the transpose "A.T" and spatial derivative "a.dx(i)".
This is to avoid circular dependencies between Expr and its subclasses.
"""

# Copyright (C) 2008-2011 Martin Sandve Alnes
#
# This file is part of UFL.
#
# UFL is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# UFL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with UFL. If not, see <http://www.gnu.org/licenses/>.
#
# Modified by Anders Logg, 2008
#
# First added:  2008-03-14
# Last changed: 2012-03-20

#--- The base object for all UFL expression tree nodes ---

from collections import defaultdict
from ufl.log import warning, error
_class_usage_statistics = defaultdict(int)
_class_del_statistics = defaultdict(int)

def print_expr_statistics():
    for k in sorted(_class_usage_statistics.keys()):
        born = _class_usage_statistics[k]
        live = born - _class_del_statistics.get(k, 0)
        print "%40s:  %10d  /  %10d" % (k.__name__, live, born)

class Expr(object):
    "Base class for all UFL objects."
    # Freeze member variables for objects of this class
    __slots__ = ()
    
    def __init__(self):
        # Comment out this line to disable class construction
        # statistics (used in some unit tests)
        _class_usage_statistics[self.__class__._uflclass] += 1

    def __del__(self):
        # Comment out this line to disable class construction
        # statistics (used for manual memory profiling)
        _class_del_statistics[self.__class__._uflclass] += 1

    #=== Abstract functions that must be implemented by subclasses ===
    
    #--- Functions for reconstructing expression ---
    
    # All subclasses must implement reconstruct
    def reconstruct(self, *operands):
        "Return a new object of the same type with new operands."
        raise NotImplementedError(self.__class__.reconstruct)
    
    #--- Functions for expression tree traversal ---
    
    # All subclasses must implement operands
    def operands(self):
        "Return a sequence with all subtree nodes in expression tree."
        raise NotImplementedError(self.__class__.operands)
    
    #--- Functions for general properties of expression ---
    
    # All subclasses must implement shape
    def shape(self):
        "Return the tensor shape of the expression."
        raise NotImplementedError(self.__class__.shape)
    
    # Subclasses can implement rank if it is known directly (TODO: Is this used anywhere? Usually want to compare shapes anyway.)
    def rank(self):
        "Return the tensor rank of the expression."
        return len(self.shape())

    # All subclasses must implement cell if it is known
    def cell(self):
        "Return the cell this expression is defined on."
        c = None
        for o in self.operands():
            d = o.cell()
            if d is not None:
                c = d # Best we have so far
                if not d.is_undefined():
                    # Use the first fully defined cell found
                    break
        return c

    def geometric_dimension(self):
        "Return the geometric dimension this expression lives in."
        # This function was introduced to clarify and
        # eventually reduce direct dependencies on cells.
        cell = self.cell()
        if cell is None or cell.is_undefined():
            error("Cannot infer geometric dimension for this expression.")
        else:
            return cell.geometric_dimension()

    def is_cellwise_constant(self):
        "Return whether this expression is spatially constant over each cell."
        raise NotImplementedError(self.__class__.is_cellwise_constant)

    #--- Functions for float evaluation ---

    def evaluate(self, x, mapping, component, index_values):
        """Evaluate expression at given coordinate with given values for terminals."""
        raise NotImplementedError(self.__class__.evaluate)

    #--- Functions for index handling ---

    # All subclasses that can have indices must implement free_indices
    def free_indices(self):
        "Return a tuple with the free indices (unassigned) of the expression."
        raise NotImplementedError(self.__class__.free_indices)
    
    # All subclasses must implement index_dimensions
    def index_dimensions(self):
        """Return a dict with the free or repeated indices in the expression
        as keys and the dimensions of those indices as values."""
        raise NotImplementedError(self.__class__.index_dimensions)
    
    #--- Special functions for string representations ---
    
    # All subclasses must implement signature_data
    def signature_data(self):
        "Return data that uniquely identifies this object."
        raise NotImplementedError(self.__class__.signature_data)

    # All subclasses must implement __repr__
    def __repr__(self):
        "Return string representation this object can be reconstructed from."
        raise NotImplementedError(self.__class__.__repr__)

    # All subclasses must implement __str__
    def __str__(self):
        "Return pretty print string representation of this object."
        raise NotImplementedError(self.__class__.__str__)
    
    #--- Special functions used for processing expressions ---
    
    def __hash__(self):
        "Compute a hash code for this expression. Used by sets and dicts."
        raise NotImplementedError(self.__class__.__hash__)

    def __eq__(self, other):
        """Checks whether the two expressions are represented the
        exact same way. This does not check if the expressions are
        mathematically equal or equivalent! Used by sets and dicts."""
        raise NotImplementedError(self.__class__.__eq__)

    def __nonzero__(self):
        "By default, all Expr are nonzero."
        return True 

    def __len__(self):
        "Length of expression. Used for iteration over vector expressions."
        s = self.shape()
        if len(s) == 1:
            return s[0]
        raise NotImplementedError("Cannot take length of non-vector expression.")
    
    def __iter__(self):
        "Iteration over vector expressions."
        for i in range(len(self)):
            yield self[i]
 
    def __floordiv__(self, other):
        "UFL does not support integer division."
        raise NotImplementedError(self.__class__.__floordiv__)

    #def __getnewargs__(self): # TODO: Test pickle and copy with this. Must implement differently for Terminal objects though.
    #    "Used for pickle and copy operations."
    #    return self.operands()

