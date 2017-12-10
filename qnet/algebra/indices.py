import re
from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict
import attr
import sympy
from sympy.core.cache import cacheit as sympy_cacheit

from ..printing import srepr, ascii

__all__ = [
    'IdxSym', 'IntIndex', 'FockIndex', 'StrLabel', 'IndexOverList',
    'IndexOverRange', 'IndexOverFockSpace', 'KroneckerDelta']

__private__ = [
    'yield_from_ranges', 'SymbolicLabelBase', 'IndexRangeBase', 'product']


# support routines


def KroneckerDelta(i, j):
    """Kronecker delta function.

    If ``i == j``, return 1. Otherwise,
    If ``i != j``, if `i` and `j` are Sympy or SymbolicLabelBase objects,
    return an instance of :class:`sympy.KroneckerDelta`, return 0 otherwise.

    Unlike in :class:`sympy.KroneckerDelta`, `i` and `j` will not be sympyfied
    """
    if i == j:
        return 1
    else:
        if isinstance(i, sympy.Basic) and isinstance(j, sympy.Basic):
            return sympy.KroneckerDelta(i, j)
        elif (
                isinstance(i, SymbolicLabelBase) and
                isinstance(j, SymbolicLabelBase)):
            return sympy.KroneckerDelta(i.expr, j.expr)

        else:
            return 0


def _immutable_attribs(cls):
    """Class decorator like ``attr.s(frozen=True)`` with improved __repr__"""
    cls = attr.s(cls, frozen=True)
    defaults = OrderedDict([(a.name, a.default) for a in cls.__attrs_attrs__])

    def repr_(self):
        real_cls = self.__class__
        class_name = real_cls.__name__
        args = []
        for name in defaults.keys():
            val = getattr(self, name)
            positional = defaults[name] == attr.NOTHING
            if val != defaults[name]:
                args.append(
                    srepr(val) if positional else "%s=%s" % (name, srepr(val)))
        return "{0}({1})".format(class_name, ", ".join(args))

    cls.__repr__ = repr_
    return cls


def _merge_dicts(*dicts):
    """Given any number of dicts, shallow copy and merge into a new dict."""
    result = {}
    for dictionary in dicts:
        result.update(dictionary)
    return result


def product(*generators, repeat=1):
    """Cartesian product akin to :func:`itertools.product`, but accepting
    generator functions.

    Unlike :func:`itertools.product` this function does not convert the input
    iterables into tuples. Thus, it can handle large or infinite inputs. As a
    drawback, however, it only works with "restartable" iterables (something
    that :func:`iter` can repeatably turn into an iterator, or a generator
    function (but not the generator iterator that is returned by that
    generator function)

    Args:
        generators: list of restartable iterators or generator functions
        repeat: number of times `generators` should be repeated

    Adapted from https://stackoverflow.com/q/12093364/
    """
    if len(generators) == 0:
        yield ()
    else:
        generators = generators * repeat
        it = generators[0]
        for item in it() if callable(it) else iter(it):
            for items in product(*generators[1:]):
                yield (item, ) + items


def yield_from_ranges(ranges):
    range_iters = []
    for index_range in ranges:
        assert callable(index_range.iter)
        # index_range.iter must be a generator (so that it's restartable),
        # *not* an iterator, which would be index_range.iter()
        range_iters.append(index_range.iter)
    for dicts in product(*range_iters):
        yield _merge_dicts(*dicts)


# IdxSym

class IdxSym(sympy.Symbol):
    """A symbol that serves as the index in a symbolic indexed sum or
    product.

    Args:
        name (str): The label for the symbol. It must be a simple Latin or
            Greek letter, possibly with a subscript, e.g. ``'i'``, ``'mu'``,
            ``'gamma_A'``
        primed (int): Number of prime marks (') associated with the symbol

    Notes:

        The symbol can be used in arbitrary algebraic (sympy) expressions::

            >>> sympy.sqrt(IdxSym('n') + 1)
            sqrt(n + 1)

        By default, the symbol is assumed to represent an integer. If this is
        not the case, you can instantiate explicitly as a non-integer::

            >>> IdxSym('i').is_integer
            True
            >>> IdxSym('i', integer=False).is_integer
            False

        You may also declare the symbol as positive::

            >>> IdxSym('i').is_positive
            >>> IdxSym('i', positive=True).is_positive
            True

        The `primed` parameter is used to automatically create distinguishable
        indices in products of sums, or more generally if the same index occurs
        in an expression with potentially differnt values::

            >>> ascii(IdxSym('i', primed=2))
            "i''"
            >>> IdxSym('i') == IdxSym('i', primed=1)
            False

        It should not be used when creating indices "by hand"

    Raises:
        ValueError: if `name` is not a simple symbol label, or if primed < 0
        TypeError: if `name` is not a string
    """

    is_finite = True
    is_Symbol = True
    is_symbol = True
    is_Atom = True
    _diff_wrt = True

    _rx_name = re.compile('^[A-Za-z]+(_[A-Za-z0-9().,+-]+)?$')

    def __new_stage2__(cls, name, primed=0, **kwargs):
        # remove: start, stop, points
        if not cls._rx_name.match(name):
            raise ValueError(
                "name '%s' does not match pattern '%s'"
                % (name, cls._rx_name.pattern))
        primed = int(primed)
        if not primed >= 0:
            raise ValueError("`primed` must be an integer >= 0")
        if 'integer' not in kwargs:
            kwargs['integer'] = True
        obj = super().__xnew__(cls, name, **kwargs)
        obj.params = (primed, )
        obj._primed = primed
        return obj

    def __new__(cls, name, *, primed=0, **kwargs):
        obj = cls.__xnew_cached_(cls, name, primed, **kwargs)
        return obj

    __xnew__ = staticmethod(__new_stage2__)
    __xnew_cached_ = staticmethod(sympy_cacheit(__new_stage2__))

    def _hashable_content(self):
        return (sympy.Symbol._hashable_content(self), self.params)

    @property
    def primed(self):
        return self._primed


# Classes for symbolic labels


@_immutable_attribs
class SymbolicLabelBase(metaclass=ABCMeta):
    expr = attr.ib(validator=attr.validators.instance_of(sympy.Basic))

    @abstractmethod
    def evaluate(self, mapping):
        pass

    def _sympy_(self):
        # sympyfication allows the symbolic label to be used in other sympy
        # expressions (which happens in some algebraic rules)
        return self.expr


class IntIndex(SymbolicLabelBase):

    def evaluate(self, mapping):
        return int(self.expr.subs(mapping))


class FockIndex(IntIndex):
    pass


class StrLabel(SymbolicLabelBase):

    def evaluate(self, mapping):
        return ascii(self.expr.subs(mapping))


# Index Ranges


@_immutable_attribs
class IndexRangeBase(metaclass=ABCMeta):
    index_symbol = attr.ib(validator=attr.validators.instance_of(IdxSym))

    @abstractmethod
    def iter(self):
        # this should *not* be a property: for `product`, we need to pass a
        # generator function, i.e. IndexRangeBase.iter, not
        # IndexRangeBase.iter()
        raise NotImplementedError()

    @abstractmethod
    def __len__(self):
        raise NotImplementedError()

    @abstractmethod
    def __contains__(self, val):
        raise NotImplementedError()


@_immutable_attribs
class IndexOverList(IndexRangeBase):
    values = attr.ib(convert=tuple)

    def iter(self):
        for val in self.values:
            yield {self.index_symbol: val}

    def __len__(self):
        return len(self.values)

    def __contains__(self, val):
        return val in self.values


@_immutable_attribs
class IndexOverRange(IndexRangeBase):
    start_from = attr.ib(validator=attr.validators.instance_of(int))
    to = attr.ib(validator=attr.validators.instance_of(int))
    step = attr.ib(validator=attr.validators.instance_of(int), default=1)

    def iter(self):
        for ind in self.range:
            yield {self.index_symbol: ind}

    @property
    def range(self):
        return range(
            self.start_from,
            (self.to + 1) if self.step >= 0 else (self.to - 1),
            self.step)

    def __len__(self):
        return self.to - self.start_from + 1

    def __contains__(self, val):
        return val in self.range


@_immutable_attribs
class IndexOverFockSpace(IndexRangeBase):
    hs = attr.ib()
    # TODO: assert that hs is indeed a FockSpace

    def iter(self):
        if self.hs._dimension is None:
            i = 0
            while True:
                yield {self.index_symbol: i}
                i += 1
        else:
            for ind in range(self.hs.dimension):
                yield {self.index_symbol: ind}

    def __len__(self):
        return self.hs.dimension

    def __contains__(self, val):
        if self.hs._dimension is None:
            return val >= 0
        else:
            return 0 <= val < self.hs.dimension
