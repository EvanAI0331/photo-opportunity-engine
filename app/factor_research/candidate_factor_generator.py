from __future__ import annotations

from .factor_registry import default_factors, save_factors


def generate_initial_candidates() -> list[dict]:
    factors = default_factors()
    save_factors(factors)
    return factors
