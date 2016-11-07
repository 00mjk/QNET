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


from sympy import I
import pytest

from qnet.algebra.circuit_algebra import (
        SLH, CircuitSymbol, CPermutation, circuit_identity, map_signals,
        SeriesProduct, invert_permutation, Concatenation, P_sigma, cid,
        map_signals_circuit, FB, getABCD, connect, CIdentity)
from qnet.algebra.permutations import (
        permute, full_block_perm, block_perm_and_perms_within_blocks)
from qnet.algebra.operator_algebra import identity_matrix, sympyOne, Destroy


symbol_counter = 0


def get_symbol(cdim):
    global symbol_counter
    sym =  CircuitSymbol('test_%d' % symbol_counter, cdim)
    symbol_counter +=1
    return sym


def get_symbols(*cdim):
    return [get_symbol(n) for n in cdim]


#qnet.algebra.abstract_algebra.CHECK_OPERANDS = True
#qnet.algebra.abstract_algebra.PRINT_PRETTY = True


def test_permutation():
    n = 5
    assert CPermutation.create(()) == circuit_identity(0)
    invalid_permutation = (1,1)
    with pytest.raises(Exception):
        CPermutation.create((invalid_permutation,))
    p_id = tuple(range(n))
    assert CPermutation.create(p_id) == circuit_identity(n)
    assert map_signals({0:1,1:0}, 2) == (1,0)
    assert map_signals({0:5,1:0}, 6) == (5,0,1,2,3,4)
    assert map_signals({0:5,1:0, 3:2}, 6) == invert_permutation(map_signals({5:0,0:1, 2:3}, 6))


def test_series():
    A, B = get_symbol(1), get_symbol(1)
    assert A << B == SeriesProduct(A,B)
    assert A << B == SeriesProduct.create(A,B)
    assert SeriesProduct.create(CIdentity, CIdentity) == CIdentity
    # need at least two operands
    # self.assertRaises(Exception, SeriesProduct, ())
    # self.assertRaises(Exception, SeriesProduct.create, ())
    # self.assertRaises(Exception, SeriesProduct, (A,))
    assert SeriesProduct.create(A) == A


def test_series_filter_identities():
    for n in (1, 2, 3, 10):
        A, B = get_symbol(n), get_symbol(n)
        idn = circuit_identity(n)
        assert A << idn == A
        assert idn << A == A
        assert SeriesProduct.create(idn, idn, A, idn, idn, B, idn, idn) == A << B


def test_concatenation():
    n = 4
    A, B = get_symbol(n), get_symbol(n)
    id0 = circuit_identity(0)
    assert A+B == Concatenation(A,B)
    assert A+B == Concatenation.create(A,B)
    assert id0 + id0 + A + id0 + id0 + B + id0 + id0 == A + B
    #self.assertRaises(Exception, Concatenation, ())
    #self.assertRaises(Exception, Concatenation, (A,))

    assert (A+B).block_structure == (n,n)
    assert (A+B).get_blocks((n,n)) == (A,B)
    #test index_in_block()
    assert (A+B).index_in_block(0) == (0,0)
    assert (A+B).index_in_block(1) == (1,0)
    assert (A+B).index_in_block(2) == (2,0)
    assert (A+B).index_in_block(3) == (3,0)
    assert (A+B).index_in_block(4) == (0,1)
    assert (A+B).index_in_block(5) == (1,1)
    assert (A+B).index_in_block(7) == (3,1)

    res = Concatenation.create(CIdentity, CIdentity, CPermutation((1,0)))
    assert res == CPermutation((0, 1, 3, 2))


def test_distributive_law():
    A = CircuitSymbol('A', 2)
    B = CircuitSymbol('B', 1)
    C = CircuitSymbol('C', 1)
    D = CircuitSymbol('D', 1)
    E = CircuitSymbol('E', 1)
    assert (A+B) << (C+D+E) == Concatenation(A<<(C+D), B << E)
    assert (C+D+E) << (A+B) == Concatenation((C+D)<< A,  E<< B)
    assert (A+B) << (C+D+E) << (A+B) == Concatenation(A << (C+D)<< A,  B << E<< B)
    assert SeriesProduct.create((A+B), (C+D+E), (A+B)) == Concatenation(A << (C+D)<< A,  B << E<< B)
    test_perm = (0,1,3,2)
    qtp = CPermutation(test_perm)
    assert CPermutation((1,0)) << ( B + C) == SeriesProduct(Concatenation(C, B), CPermutation((1,0)))
    assert qtp << (A + B + C) == (A + C+ B) <<  qtp
    assert qtp << ( B + C + A) == B + C + (CPermutation((1,0)) << A)
    test_perm2 = (1,0,3,2)
    qtp2 = CPermutation(test_perm2)
    assert qtp2 << (A + B + C) == (CPermutation((1,0)) << A) + ((C+B) << CPermutation((1,0)))
    assert qtp << qtp2 == CPermutation(permute(test_perm, test_perm2))


def test_permutation():
    test_perm = (0,1,2,5,6,3,4)
    qtp = CPermutation.create(test_perm)
    assert qtp.series_inverse() == CPermutation.create(invert_permutation(test_perm))
    assert qtp.block_structure == (1,1,1,4)
    id1 = circuit_identity(1)
    assert qtp.get_blocks() == (id1, id1, id1, CPermutation.create((2,3,0,1)))

    assert CPermutation((1,0,3,2)).get_blocks() == (CPermutation((1,0)), CPermutation((1,0)))
    nt = len(test_perm)
    assert qtp << qtp.series_inverse() == circuit_identity(nt)
    assert permute(list(invert_permutation(test_perm)), test_perm) == list(range(nt))


def test_factorize_permutation():
    assert full_block_perm((0,1,2), (1,1,1)) == (0,1,2)
    assert full_block_perm((0,2,1), (1,1,1)) == (0,2,1)
    assert full_block_perm((0,2,1), (1,1,2)) == (0,3,1,2)
    assert full_block_perm((0,2,1), (1,2,3)) == (0,4,5,1,2,3)
    assert full_block_perm((1,2,0), (1,2,3)) == (3,4,5,0,1,2)
    assert full_block_perm((3,1,2,0), (1,2,3,4)) == (9, 4, 5, 6, 7, 8, 0, 1, 2, 3 )
    assert block_perm_and_perms_within_blocks((9, 4, 5, 6, 7, 8, 0, 1, 2, 3 ), (1,2,3,4)) == \
                                                                    ((3,1,2,0), [(0,),(0,1),(0,1,2),(0,1,2,3)])

    A1,A2,A3,A4 = get_symbols(1,2,3,4)

    new_lhs, permuted_rhs, new_rhs = P_sigma(9, 4, 5, 6, 7, 8, 0, 1, 2, 3 )._factorize_for_rhs(A1+A2+A3+A4)
    assert new_lhs == cid(10)
    assert permuted_rhs == (A4+A2+A3+A1)
    assert new_rhs == P_sigma(9, 4, 5, 6, 7, 8, 0, 1, 2, 3 )

    p = P_sigma(0,1,4,2,3,5)
    expr = A2 + A3 + A1
    new_lhs, permuted_rhs, new_rhs = p._factorize_for_rhs(expr)
    assert new_lhs == cid(6)
    assert permuted_rhs == A2 + (P_sigma(2,0,1) << A3) + A1
    assert new_rhs == cid(6)

    p = P_sigma(0, 3, 1, 2)

    p_r = P_sigma(2, 0, 1)
    assert p == cid(1) + p_r
    A = get_symbol(2)

    new_lhs, permuted_rhs, new_rhs = p._factorize_for_rhs(cid(1) + A+ cid(1))

    assert new_lhs == P_sigma(0,1,3,2)
    assert permuted_rhs == (cid(1) + (P_sigma(1,0) << A)  + cid(1))
    assert new_rhs == cid(4)

    new_lhs, permuted_rhs, new_rhs = p._factorize_for_rhs(cid(2) + A)

    assert new_lhs == cid(4)
    assert permuted_rhs == (cid(1) + A  + cid(1))
    assert new_rhs == p

    assert p.series_inverse() << (cid(2) + A) == cid(1) + SeriesProduct(P_sigma(0,2,1), Concatenation(SeriesProduct(P_sigma(1,0), A), cid(1)),P_sigma(2,0,1))

    assert p.series_inverse() << (cid(2) + A) << p == cid(1) + (p_r.series_inverse() << (cid(1) + A) << p_r)

    new_lhs, permuted_rhs, new_rhs = P_sigma(4,2,1,3,0)._factorize_for_rhs((A4 + cid(1)))
    assert new_lhs == cid(5)
    assert permuted_rhs == (cid(1) + (P_sigma(3,1,0,2) << A4))
    assert new_rhs == map_signals_circuit({4:0}, 5)

    ## special test case that helped find the major permutation block structure factorization bug
    p = P_sigma(3, 4, 5, 0, 1, 6, 2)
    q = cid(3) + CircuitSymbol('NAND1', 4)

    new_lhs, permuted_rhs, new_rhs = p._factorize_for_rhs(q)
    assert new_lhs == P_sigma(0,1,2,6,3,4,5)
    assert permuted_rhs == (P_sigma(0,1,3,2) << CircuitSymbol('NAND1', 4)) + cid(3)
    assert new_rhs == P_sigma(4,5,6, 0,1,2,3)


def test_feedback():
    A, B, C, D, A1, A2 = get_symbols(3, 2, 1, 1, 1, 1)
    circuit_identity(1)

    #self.assertRaises(Exception, Feedback, ())
    #self.assertRaises(Exception, Feedback, (C,))
    #self.assertRaises(Exception, Feedback, (C + D,))
    #self.assertRaises(Exception, Feedback, (C << D,))
    #self.assertRaises(Exception, Feedback, (circuit_identity(n),))
    #self.assertRaises(Exception, Feedback.create, (circuit_identity(0)))
    #self.assertEquals(Feedback.create(circuit_identity(n)), circuit_identity(n-1))
    assert FB(A+B) == A + FB(B)
    smq = map_signals_circuit({2:1}, 3) # == 'cid(1) + X'
    assert smq == smq.series_inverse()
    # import metapost as mp
    # mp.display_circuit(Feedback.apply_with_rules(smq.series_inverse() << (B + C) << smq))
    # mp.display_circuit(B.feedback() + C)

    assert ( smq << (B + C)).feedback(out_index = 2, in_index = 1) == B.feedback() + C

    assert ( smq << (B + C) << smq).feedback() == B.feedback() + C

    assert (B + C).feedback(1,1) == B.feedback() + C

    #check that feedback is resolved into series when possible
    assert B.feedback(1,0).substitute({B:(C+D)}) == C << D
    assert (A << (B + cid(1))).feedback() == A.feedback() << B
    assert (A << (B + cid(1)) << (cid(1) + P_sigma(1,0))).feedback(2,1) == A.feedback() << B
    assert (A << (cid(1) + P_sigma(1,0)) << (B + cid(1)) << (cid(1) + P_sigma(1,0))).feedback(1,1) == A.feedback(1,1) << B
    assert (B << (cid(1)  + C)).feedback(0,1).substitute({B: (A1 + A2)}) == A2 << C << A1
    assert ((cid(1)  + C)<< P_sigma(1,0) << B).feedback(1,1).substitute({B: (A1 + A2)}) == A2 << C << A1
    assert ((cid(1)  + C)<< P_sigma(1,0) << B << (cid(1) + D)).feedback(1,1).substitute({B: (A1 + A2)}) == A2 << D<< C << A1


def test_ABCD():
    a = Destroy(1)
    H = 2 * a.dag() * a
    slh1 = SLH(identity_matrix(1), [a], H)
    slh = slh1.coherent_input(3)
    A, B, C, D, a, c = getABCD(slh, doubled_up=True)
    assert A[0, 0] == -sympyOne / 2 - 2 * I
    assert A[1, 1] == -sympyOne / 2 + 2 * I
    assert B[0, 0] == -1
    assert C[0, 0] == 1
    assert D[0, 0] == 1


def connect_data():
    A = CircuitSymbol('A', 1)
    B = CircuitSymbol('B', 1)
    C = CircuitSymbol('C', 2)
    return [
        ([A, B],                 # components
         [((0, 0), (1, 0))],     # connection
         B << A                  # expected
        ),
        ([A, B, C],              # components
         [((0, 0), (2, 0)),      # connection 1
          ((1, 0), (2, 1))],     # connection 2
         (C << A + B)            # expected
        ),
        ([A, C],                 # components
         [((0, 0), (1, 0))],     # connections
         C << (A + cid(1))       # expected
        ),
    ]


@pytest.mark.parametrize('components, connections, expected', connect_data())
def test_connect(components, connections, expected):
    res = connect(components, connections, force_SLH=False)
    assert res == expected