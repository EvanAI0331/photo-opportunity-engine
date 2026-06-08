from __future__ import annotations

from .factor_backtester import backtest_factors
from .factor_registry import load_factors


def build_factor_report() -> dict:
    results = backtest_factors(load_factors())
    return {
        "status": "completed",
        "factor_count": len(results),
        "factors": results,
    }
