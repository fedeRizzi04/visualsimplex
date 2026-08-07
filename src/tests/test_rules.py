from fractions import Fraction

import pytest

from visualsimplex import VarKind, Variable
from visualsimplex.rules import LeavingCandidate, minimum_ratio_rule


def leaving_candidate(symbol, *, pivot, rhs):
    variable = Variable(VarKind.SLACK, symbol)
    return LeavingCandidate(variable, Fraction(pivot), Fraction(rhs))


def test_minimum_ratio_rule_selects_the_smallest_rhs_over_pivot_ratio():
    first = leaving_candidate("s1", pivot=2, rhs=8)
    second = leaving_candidate("s2", pivot=1, rhs=3)

    assert minimum_ratio_rule((first, second)) == second


def test_minimum_ratio_rule_breaks_ties_by_candidate_order():
    earlier = leaving_candidate("s1", pivot=2, rhs=4)
    later = leaving_candidate("s2", pivot=1, rhs=2)

    assert minimum_ratio_rule((earlier, later)) == earlier


def test_minimum_ratio_rule_rejects_an_empty_candidate_sequence():
    with pytest.raises(ValueError, match="no eligible leaving candidates"):
        minimum_ratio_rule(())
