#This file is part of QNET.
#
#    QNET is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#    QNET is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with QNET.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2012-2013, Nikolas Tezak
#
###########################################################################

from sympy import symbols
import numpy as np
from numpy import sqrt
import qutip

import pytest

from qnet.algebra.operator_algebra import (
    Create, Destroy, LocalSigma, LocalProjector, OperatorSymbol,
    ScalarTimesOperator)
from qnet.convert.to_qutip import _time_dependent_to_qutip, convert_to_qutip
from qnet.algebra.hilbert_space_algebra import LocalSpace

_hs_counter = 0


def hs_name():
    global _hs_counter
    _hs_counter += 1
    return 'QT%d' % _hs_counter


def test_create_destoy():
    H = LocalSpace(hs_name(), dimension=5)
    ad = Create(hs=H)
    a = Create(hs=H).adjoint()
    aq = convert_to_qutip(a)
    for k in range(H.dimension - 1):
        assert abs(aq[k, k+1] - sqrt(k + 1)) < 1e-10
    assert convert_to_qutip(ad) == qutip.dag(convert_to_qutip(a))


def test_N():
    H = LocalSpace(hs_name(), dimension=5)
    ad = Create(hs=H)
    a = Create(hs=H).adjoint()
    aq = qutip.dag(convert_to_qutip(a))
    assert aq == qutip.create(5)
    n = ad * a
    nq = convert_to_qutip(n)
    for k in range(H.dimension):
        assert abs(nq[k,k] - k) < 1e-10


def test_sigma():
    H = LocalSpace(hs_name(), basis=("e","g","h"))
    sigma = LocalSigma('g', 'e', hs=H)
    sq = convert_to_qutip(sigma)
    assert sq[1, 0] == 1
    assert (sq**2).norm() == 0


def test_Pi():
    H = LocalSpace(hs_name(), basis=("e", "g", "h"))
    Pi_h = LocalProjector('h', hs=H)
    assert convert_to_qutip(Pi_h).tr() == 1
    assert convert_to_qutip(Pi_h)**2 == convert_to_qutip(Pi_h)


def test_tensor_product():
    H = LocalSpace(hs_name(), dimension=5)
    a = Create(hs=H).adjoint()
    H2 = LocalSpace(hs_name(), basis=("e", "g", "h"))
    sigma = LocalSigma('g', 'e', hs=H2)
    assert convert_to_qutip(sigma * a) == \
                        qutip.tensor(convert_to_qutip(a),
                                    convert_to_qutip(sigma))


def test_local_sum():
    H = LocalSpace(hs_name(), dimension=5)
    ad = Create(hs=H)
    a = Create(hs=H).adjoint()
    assert convert_to_qutip(a + ad) == \
                        convert_to_qutip(a) + convert_to_qutip(ad)


def test_nonlocal_sum():
    H = LocalSpace(hs_name(), dimension=5)
    a = Create(hs=H).adjoint()
    H2 = LocalSpace(hs_name(), basis=("e", "g", "h"))
    sigma = LocalSigma('g', 'e', hs=H2)
    assert convert_to_qutip(a + sigma)**2 == \
                        convert_to_qutip((a + sigma)*(a + sigma))


def test_scalar_coeffs():
    H = LocalSpace(hs_name(), dimension=5)
    a = Create(hs=H).adjoint()
    assert 2 * convert_to_qutip(a) == convert_to_qutip(2 * a)


def test_symbol():
    expN = OperatorSymbol("expN", hs=1)
    hs1 = LocalSpace("sym1", dimension=10)
    hs2 = LocalSpace("sym2", dimension=5)
    N = Create(hs=hs1)*Destroy(hs=hs1)

    M = Create(hs=hs2)*Destroy(hs=hs2)

    converter1 = {
        expN: convert_to_qutip(N).expm()
    }
    expNq = convert_to_qutip(expN, mapping=converter1)

    assert np.linalg.norm(expNq.data.toarray()
        - (convert_to_qutip(N).expm().data.toarray())) < 1e-8

    expNMq = convert_to_qutip(expN*M,  mapping=converter1)

    assert np.linalg.norm(expNMq.data.toarray()
        - (qutip.tensor(convert_to_qutip(N).expm(),
                        convert_to_qutip(M)).data.toarray())) < 1e-8

    converter2 = {
        expN: lambda expr: convert_to_qutip(N).expm()
    }
    expNq = convert_to_qutip(expN, mapping=converter2)

    assert np.linalg.norm(expNq.data.toarray()
        - (convert_to_qutip(N).expm().data.toarray())) < 1e-8

    expNMq = convert_to_qutip(expN*M,  mapping=converter1)

    assert np.linalg.norm(expNMq.data.toarray()
        - (qutip.tensor(convert_to_qutip(N).expm(),
                        convert_to_qutip(M)).data.toarray())) < 1e-8


def test_time_dependent_to_qutip():
    """Test conversion of a time-dependent Hamiltonian"""
    Hil = LocalSpace(hs_name(), dimension=5)
    ad = Create(hs=Hil)
    a = Create(hs=Hil).adjoint()

    w, g, t = symbols('w, g, t', real=True)

    H = ad*a + (a + ad)
    assert _time_dependent_to_qutip(H) == convert_to_qutip(H)

    H = g * t * a
    res = _time_dependent_to_qutip(H, time_symbol=t)
    assert res[0] == convert_to_qutip(a)
    assert res[1](1, {}) == g
    assert res[1](1, {g: 2}) == 2

    H =  ad*a + g * t * (a + ad)
    res = _time_dependent_to_qutip(H, time_symbol=t)
    assert len(res) == 3
    assert res[0] == convert_to_qutip(ad*a)
    assert res[1][0] == convert_to_qutip(ad)
    assert res[1][1](1, {}) == g
    assert res[2][0] == convert_to_qutip(a)
    assert res[2][1](1, {}) == g

    res = _time_dependent_to_qutip(H, time_symbol=t, convert_as='str')
    terms = [term for H, term in res[1:]]
    assert terms == ['g*t', 'g*t']

    H =  (ad*a + t * (a + ad))**2
    res = _time_dependent_to_qutip(H, time_symbol=t, convert_as='str')
    assert len(res) == 9
    terms = sorted([term for H, term in res[1:]])
    expected = sorted([str(op.coeff) for op in H.expand().operands
                       if isinstance(op, ScalarTimesOperator)])
    assert terms == expected


def test_trivial_space_conversion():
    """Test that the conversion of objects in TrivialSpace gives useful error
    messages and that the conversion works successfully if the full Hilbert
    space is given explicitly

    This tests the resolution of issue #48
    """
    from qnet.convert.to_qutip import convert_to_qutip, SLH_to_qutip
    from qnet.algebra.operator_algebra import ZeroOperator
    from qnet.algebra.hilbert_space_algebra import LocalSpace
    from qnet.circuit_components import mach_zehnder_cc
    from qnet.algebra.abstract_algebra import AlgebraError

    with pytest.raises(AlgebraError) as excinfo:
        O = convert_to_qutip(ZeroOperator)
    assert "Cannot convert object in TrivialSpace" in str(excinfo.value)

    O = convert_to_qutip(ZeroOperator, full_space=LocalSpace(0, dimension=10))
    assert np.linalg.norm((O.data.todense() - np.zeros((10, 10)))) == 0.0

    mz = mach_zehnder_cc.MachZehnder('Zender', alpha=1, phi=0)
    slh = mz.toSLH()

    with pytest.raises(AlgebraError) as excinfo:
        H, Ls = SLH_to_qutip(slh)
    assert "Cannot convert SLH object in TrivialSpace" in str(excinfo.value)

    H, Ls = SLH_to_qutip(slh, full_space=LocalSpace(0, dimension=10))
    assert np.linalg.norm((H.data.todense() - np.zeros((10, 10)))) == 0.0
    assert len(Ls) == 0
