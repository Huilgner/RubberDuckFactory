"""fitness_math: Wilson lower bound e janela deslizante."""
from fitness_math import (
    EVOLUTION_WINDOW,
    fitness_score,
    rolling_success_rate,
    wilson_lower_bound,
)


def test_wilson_no_evidence_is_zero():
    assert wilson_lower_bound(0, 0) == 0.0


def test_wilson_prefers_evidence_over_luck():
    # 100% com n=2 deve perder de 95% com n=200
    assert wilson_lower_bound(2, 2) < wilson_lower_bound(190, 200)
    assert fitness_score(2, 2) < fitness_score(190, 200)


def test_wilson_bounds_and_monotonicity():
    assert 0.0 <= wilson_lower_bound(5, 10) <= 0.5
    assert wilson_lower_bound(10, 10) < 1.0
    # mais sucessos com mesmo n => score maior
    assert wilson_lower_bound(9, 10) > wilson_lower_bound(5, 10)


def test_wilson_clamps_invalid_input():
    assert wilson_lower_bound(15, 10) == wilson_lower_bound(10, 10)
    assert wilson_lower_bound(-3, 10) == wilson_lower_bound(0, 10)


def test_rolling_requires_min_samples():
    assert rolling_success_rate([1, 1, 1]) is None
    assert rolling_success_rate([1, 1, 1, 1, 0]) == 80.0


def test_rolling_window_discards_old_results():
    # 5 falhas antigas fora da janela de EVOLUTION_WINDOW acertos recentes
    history = [0] * 5 + [1] * EVOLUTION_WINDOW
    assert rolling_success_rate(history) == 100.0
