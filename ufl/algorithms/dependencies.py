"""This module defines utilities for working with dependencies of subexpressions."""

__authors__ = "Martin Sandve Alnes"
__date__ = "2008-10-01 -- 2009-01-05"

from collections import defaultdict
from itertools import izip, chain

from ufl.common import some_key, split_dict, or_tuples, and_tuples, UFLTypeDict
from ufl.log import error, warning, debug
from ufl.assertions import ufl_assert
from ufl.permutation import compute_indices

# All classes:
from ufl.expr import Expr
from ufl.terminal import Terminal
from ufl.constantvalue import Zero, FloatValue, IntValue, Identity
from ufl.variable import Variable, Label
from ufl.basisfunction import BasisFunction
from ufl.function import Function, Constant
from ufl.differentiation import SpatialDerivative
from ufl.geometry import FacetNormal
from ufl.indexing import MultiIndex, Indexed, Index, FixedIndex
from ufl.tensors import ListTensor, ComponentTensor

# Lists of all Expr classes
from ufl.classes import ufl_classes, terminal_classes, nonterminal_classes

# Other algorithms:
from ufl.algorithms.analysis import extract_variables
from ufl.algorithms.transformations import Transformer


class DependencySet:
    def __init__(self, basisfunctions, runtime=False, coordinates=False):
        
        # depends on runtime arguments (i.e. should be inside tabulate_tensor, otherwise it can be precomputed)
        self.runtime = runtime
        
        # depends on spatial coordinates (i.e. should be inside quadrature loop or integral)
        self.coordinates = coordinates
        
        # depends on basis function i (i.e. should be inside a loop where this basis function is defined)
        self.basisfunctions = tuple(basisfunctions)
    
    def iter(self):
        return chain((self.runtime, self.coordinates), self.basisfunctions)
    
    def size(self):
        return len(list(self.iter()))
    
    def covers(self, other):
        "Return True if all dependencies of other are covered by this dependency set."
        for a, o in zip(self.iter(), other.iter()):
            if o and not a:
                return False
        return True
    
    def __hash__(self):
        return hash(tuple(self.iter()))
    
    def __cmp__(self, other):
        for (a,b) in izip(self.iter(), other.iter()):
            if a < b: return -1
            if a > 1: return +1
        return 0
    
    def __or__(self, other):
        basisfunctions = or_tuples(self.basisfunctions, other.basisfunctions)
        d = DependencySet(basisfunctions,
                          self.runtime     or other.runtime,
                          self.coordinates or other.coordinates)
        return d

    def __and__(self, other):
        basisfunctions = and_tuples(self.basisfunctions, other.basisfunctions)
        d = DependencySet(basisfunctions,
                          runtime = self.runtime and other.runtime,
                          coordinates = self.coordinates and other.coordinates)
        return d

    def __str__(self):
        s = "DependencySet:\n"
        s += "{\n"
        s += "  self.runtime        = %s\n" % self.runtime
        s += "  self.coordinates    = %s\n" % self.coordinates 
        s += "  self.basisfunctions = %s\n" % str(self.basisfunctions) 
        s += "}"
        return s


def _test_dependency_set():
    basisfunctions = (True, False)
    d1 = DependencySet(basisfunctions, runtime=True, coordinates=False)
    basisfunctions = (False, True)
    d2 = DependencySet(basisfunctions, runtime=True, coordinates=False)
    d3 = d1 | d2
    d4 = d1 & d2
    print d1
    print d2
    print d3
    print d4



class VariableInfo:
    def __init__(self, variable, deps):
        # Variable
        self.variable = variable
        # DependencySet
        self.deps = deps
        # VariableDerivativeVarSet -> VariableInfo
        self.diffcache = {}
    
    def __str__(self):
        s = "VariableInfo:\n"
        s += "{\n"
        s += "  self.variable = %s\n" % self.variable
        s += "  self.deps = %s\n" % self.deps
        s += "  self.diffcache = \n"
        s += "\n".join("    %s: %s" % (k,v) for (k,v) in self.diffcache.iteritems())
        s += "\n}"
        return s

class VariableDerivativeVarSet: # TODO: Use this?
    def __init__(self):
        self.fixed_spatial_directions = set() # Set of integer indices
        self.open_spatial_directions = set() # Set of Index objects that the stored expression uses for d/dx_i
        self.variables = set() # Set of variables we're differentiating w.r.t.

    def __hash__(self):
        return hash(tuple(d for d in self.fixed_spatial_directions) + \
                    tuple(d for d in self.open_spatial_directions) + \
                    tuple(d for d in self.variables))
    
    def __eq__(self, other):
        return self.fixed_spatial_directions == other.fixed_spatial_directions and \
               len(self.open_spatial_directions) == len(other.open_spatial_directions) and \
               self.variables == other.variables

    #def __contains__(self, other):
    #def __sub__(self, other):
    #def __add__(self, other):
    #def __cmp__(self, other):

class CodeStructure:
    def __init__(self):
        # A place to look up if a variable has been added to the stacks already
        self.variableinfo = {}   # variable count -> VariableInfo
        # One stack of variables for each dependency configuration
        self.stacks = defaultdict(list) # DependencySet -> [VariableInfo]
    
#===============================================================================
#    def __str__(self):
#        deps = DependencySet(TODO)
#        s = ""
#        s += "Variables independent of spatial coordinates:\n"
#        keys = [k for k in self.stacks.keys() if not k.coordinates]
#        for deps in keys:
#            if k.facet:
#                stack = self.stacks[k]
#                s += str(stack)
#        for deps in keys:
#            if not k.facet:
#                stack = self.stacks[k]
#                s += str(stack)
#        
#        s += "Variables dependent of spatial coordinates:\n"
#        for k in dependent:
#            s += k
#        
#        return s
# 
#    def split_stacks(self): # TODO: Remove this or change the concept. Doesn't belong here.
#        
#        # Start with all variable stacks
#        stacks = self.stacks
#        
#        # Split into precomputable and not
#        def criteria(k):
#            return not (k.spatial or any(k.coefficients) or k.facet)
#        precompute_stacks, runtime_stacks = split_dict(stacks, criteria)
#        
#        # Split into outside or inside quadrature loop
#        def criteria(k):
#            return k.spatial
#        quad_precompute_stacks, precompute_stacks = split_dict(precompute_stacks, criteria)
#        quad_runtime_stacks, runtime_stacks = split_dict(runtime_stacks, criteria)
#        
#        # Example! TODO: Make below code a function and apply to each stack group separately. 
#        stacks = quad_runtime_stacks
#        
#        # Split by basis function dependencies
#        
#        # TODO: Does this give us the order we want?
#        # Want to iterate faster over test function, i.e. (0,0), (1,0), (0,1), (1,1) 
#        keys = set(stacks.iterkeys())
#        perms = [p for p in compute_permutations(rank, 2) if p in keys] # TODO: NOT RIGHT!
#        for perm in perms:
#            def criteria(k):
#                return k.basisfunctions == perm
#            dep_stacks, stacks = split_dict(stacks, criteria)
#            
#            # TODO: For all permutations of basis function indices
#            # TODO: Input elementreps
#            sizes = [elementreps[i].local_dimension for i in range(self.rank) if perms[i]]
#            basis_function_perms = compute_indices(sizes)
#            for basis_function_perm in basis_function_perms:
#                context.update_basisfunction_permutation(basis_function_perm) # TODO: Map tuple to whole range of basisfunctions.
#                for stack in dep_stacks.itervalues():
#                    for (k,v) in stack.iteritems():
#                        s = context.variable_to_symbol(k)
#                        e = ufl_to_swiginac(v, context)
#                        context.add_token(s, e)
#===============================================================================

class DependencySplitter(Transformer):
    def __init__(self, formdata, basisfunction_deps, function_deps):
        Transformer.__init__(self)
        self.formdata = formdata
        self.basisfunction_deps = basisfunction_deps
        self.function_deps = function_deps
        self.variables = []
        self.codestructure = CodeStructure()
    
    def make_empty_deps(self):
        return DependencySet((False,)*len(self.basisfunction_deps))
    
    def terminal(self, x):
        return x, self.make_empty_deps()
    
    def basis_function(self, x):
        ufl_assert(x in self.formdata.basisfunction_renumbering,
                   "Can't find basis function %s in renumbering dict!" % repr(x))
        i = self.formdata.basisfunction_renumbering[x]
        d = self.basisfunction_deps[i]
        return x, d
    
    def function(self, x):
        print 
        print self.formdata.coefficient_renumbering
        print
        ufl_assert(x in self.formdata.coefficient_renumbering,
                   "Can't find function %s in renumbering dict!" % repr(x))
        i = self.formdata.coefficient_renumbering[x]
        d = self.function_deps[i]
        return x, d
    
    def facet_normal(self, x):
        deps = self.make_empty_deps()
        deps.runtime = True
        #deps.coordinates = True # TODO: Enable for higher order geometries.
        return x, deps
    
    def variable(self, x):
        vinfo = self.codestructure.variableinfo.get(x.label()._count, None)
        ufl_assert(vinfo is not None, "Haven't handled variable in time: %s" % repr(x))
        return vinfo.variable, vinfo.deps
    
    def spatial_derivative(self, x, f, ii):
        # BasisFunction won't normally depend on the mapping,
        # but the spatial derivatives will always do...
        # FIXME: Don't just reuse deps from f[1], the form compiler needs
        # to consider whether df/dx depends on coordinates or not!
        # I.e. for gradients of a linear basis function.
        
        deps = self.make_empty_deps()
        deps.runtime = True
        #deps.coordinates = True # TODO: Enable for higher order mappings.
        
        # Combine dependencies
        d = f[1] | deps
        
        # Reuse expression if possible
        if f[0] is x.operands()[0]:
            return x, d
        
        # Construct new expression
        return type(x)(f[0], ii[0]), d
    
    def expr(self, x, *ops):
        ufl_assert(ops, "Non-terminal with no ops should never occur.")
        # Combine dependencies
        d = ops[0][1]
        for o in ops[1:]:
            d |= o[1]
        
        # Make variables of all ops with differing dependencies
        if any(o[1] != d for o in ops):
            oldops = ops
            ops = []
            _skiptypes = (MultiIndex, Zero, FloatValue, IntValue)
            for o in oldops:
                if isinstance(o[0], _skiptypes):
                    ops.append(o)
                else:
                    vinfo = self.register_expression(o[0], o[1])
                    ops.append((vinfo.variable, vinfo.deps))
        
        # Reuse expression if possible
        ops = [o[0] for o in ops]
        if all((a is b) for (a, b) in zip(ops, x.operands())):
            return x, d
        # Construct new expression
        return type(x)(*ops), d

    def register_expression(self, e, deps, count=None):
        """Register expression as a variable with dependency
        data, reusing variable count if necessary.
        If the expression is already a variable, reuse it."""
        if count is None:
            if isinstance(e, Variable):
                v = e
            else:
                v = Variable(e)
        else:
            v = Variable(e, label=Label(count))
        count = v.label()._count
        vinfo = self.codestructure.variableinfo.get(count, None)
        if vinfo is None:
            vinfo = VariableInfo(v, deps)
            self.codestructure.variableinfo[count] = vinfo
            self.codestructure.stacks[deps].append(vinfo)
        else:
            debug("When does this happen? Need an algorithm revision to trust this fully.") # FIXME
        return vinfo
    
    def handle(self, v):
        ufl_assert(isinstance(v, Variable), "Expecting Variable.")
        vinfo = self.codestructure.variableinfo.get(v.label()._count, None)
        if vinfo is None:
            # split v._expression 
            e, deps = self.visit(v._expression)
            # Register expression e as the expression of variable v
            vinfo = self.register_expression(e, deps, count=v.label()._count)
        return vinfo

def split_by_dependencies(expression, formdata, basisfunction_deps, function_deps):
    """Split an expression into stacks of variables based
    on the dependencies of its subexpressions.
    
    @type expression: Expr
    @param expression: The expression to parse.
    @type basisfunction_deps: list(DependencySet)
    @param basisfunction_deps:
        A list of DependencySet objects, one for each
        BasisFunction in the Form the expression originates from.
    @type function_deps: list(DependencySet)
    @param function_deps:
        A list of DependencySet objects, one for each
        Function in the Form the expression originates from.
    @return (e, deps, codestructure):
        variableinfo: data structure with info about the final
                      variable representing input expression
        codestructure: data structure containing stacks of variables
        
    If the *_deps arguments are unknown, a safe way to invoke this function is::
    
        (variableinfo, codestructure) = split_by_dependencies(expression, formdata, [(True,True)]*rank, [(True,True)]*num_coefficients)
    """
    ufl_assert(isinstance(expression, Expr), "Expecting Expr.")
    
    # Exctract a list of all variables in expression 
    variables = extract_variables(expression)
    if isinstance(expression, Variable):
        ufl_assert(expression is variables[-1],
                   "Expecting the last result from extract_variables to be the input variable...")
    else:
        # Wrap root node in Variable for consistency below
        expression = Variable(expression)
        variables.append(expression)
    
    # Split each variable
    ds = DependencySplitter(formdata, basisfunction_deps, function_deps)
    for v in variables:
        print "Handling variable ", repr(v)
        vinfo = ds.handle(v)
        print "Done handling variable ", v
        print "Got vinfo:"
        print vinfo
    
    # How can I be sure we won't mess up the expressions of v and vinfo.variable, before and after splitting?
    # The answer is to never use v in the form compiler after this point,
    # and let v._count identify the variable in the code structure.
    
    return (vinfo, ds.codestructure)



def _test_split_by_dependencies():
    pass
#===============================================================================
#    def unit_tuple(i, n, true=True, false=False):
#        return tuple(true if i == j else false for j in xrange(n))
#    
#    a = ...
#    
#    from ufl.algorithms.formdata import FormData
#    formdata = FormData(a)
#    
#    basisfunction_deps = []
#    for i in range(formdata.rank):
#        bfs = unit_tuple(i, formdata.rank, True, False)
#        d = DependencySet(bfs, coordinates=True) # Disable coordinates depending on element
#        basisfunction_deps.append(d)
#    
#    function_deps = []
#    bfs = (False,)*formdata.rank
#    for i in range(num_coefficients):
#        d = DependencySet(bfs, runtime=True, coordinates=True) # Disable coordinates depending on element
#        function_deps.append(d)
#    
#    e, d, c = split_by_dependencies(integrand, formdata, basisfunction_deps, function_deps)
#    print e
#    print d
#    print c
#===============================================================================

if __name__ == "__main__":
    _test_dependency_set()
