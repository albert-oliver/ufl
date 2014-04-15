"""FormData class easy for collecting of various data about a form."""

# Copyright (C) 2008-2014 Martin Sandve Alnes
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
# Modified by Anders Logg, 2008.
#
# First added:  2008-09-13
# Last changed: 2013-01-09

from ufl.common import lstr, tstr, estr
from ufl.assertions import ufl_assert

class FormData(object):
    """
    Class collecting various information extracted from a Form by
    calling preprocess.
    """

    def __init__(self):
        "Create empty form data for given form."

    def __str__(self):
        "Return formatted summary of form data"
        types = sorted(self.num_sub_domains.keys())
        subdomains = tuple(("Number of %s subdomains" % integral_type,
                            self.num_sub_domains[integral_type]) for integral_type in types)
        return tstr(
            (("Name",                               self.name),
             # Geometry
             ("Geometric dimension",                self.geometric_dimension),
             ) + subdomains + (
             # Arguments
             ("Rank",                               self.rank),
             ("Arguments",                          lstr(self.original_arguments)),
             ("Argument names",                     lstr(self.argument_names)),
             # Coefficients
             ("Number of coefficients",             self.num_coefficients),
             ("Coefficients",                       lstr(self.original_coefficients)),
             ("Coefficient names",                  lstr(self.coefficient_names)),
             # Elements
             ("Unique elements",                    estr(self.unique_elements)),
             ("Unique sub elements",                estr(self.unique_sub_elements)),
             ))

    def validate(self, object_names=None):
        "Validate that the form data was built from the same inputs."
        ufl_assert((object_names or {}) == self._input_object_names,
                   "Found non-matching object_names in form data validation.")

class ExprData(object):
    """
    Class collecting various information extracted from a Expr by
    calling preprocess.
    """

    def __init__(self):
        "Create empty expr data for given expr."

    def __str__(self):
        "Return formatted summary of expr data"
        return tstr((("Name",                               self.name),
                     ("Cell",                               self.cell),
                     ("Topological dimension",              self.topological_dimension),
                     ("Geometric dimension",                self.geometric_dimension),
                     ("Rank",                               self.rank),
                     ("Number of coefficients",             self.num_coefficients),
                     ("Arguments",                          lstr(self.arguments)),
                     ("Coefficients",                       lstr(self.coefficients)),
                     ("Argument names",                     lstr(self.argument_names)),
                     ("Coefficient names",                  lstr(self.coefficient_names)),
                     ("Unique elements",                    estr(self.unique_elements)),
                     ("Unique sub elements",                estr(self.unique_sub_elements)),
                     # FIXME DOMAINS what is "the domain(s)" for an expression?
                     ("Domains",                            self.domains),
                     ))
