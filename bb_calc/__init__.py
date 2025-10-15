"""Utilities for working with BB Calc trade data.

The public API is intentionally re-exported lazily to avoid importing the
``pnl_calculator`` module during package initialization.  This prevents the
RuntimeWarning raised by ``python -m bb_calc.pnl_calculator`` when the module
is already present in :mod:`sys.modules`.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = ["Trade", "load_trades", "calculate_realized_pnl", "summarize_realized_pnl"]


if TYPE_CHECKING:  # pragma: no cover - used only for static analysis
    from .pnl_calculator import Trade, calculate_realized_pnl, load_trades, summarize_realized_pnl


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module(".pnl_calculator", __name__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
