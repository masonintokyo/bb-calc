from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from bb_calc import calculate_realized_pnl, load_trades
from bb_calc.pnl_calculator import _cli


FIXTURE_PATH = Path(__file__).parent / "data" / "sample_trades.csv"


def test_load_trades_parses_expected_rows():
    trades = load_trades(FIXTURE_PATH)

    assert len(trades) == 9
    first = trades[0]
    assert first.uid == "382647166"
    assert first.trade_type == "SELL"
    assert first.realized_pnl == Decimal("217.92480262000000000000")


def test_calculate_realized_pnl_full_range():
    trades = load_trades(FIXTURE_PATH)

    total = calculate_realized_pnl(trades)

    assert total == Decimal("-7438.19642459000000000000")


def test_calculate_realized_pnl_within_period():
    trades = load_trades(FIXTURE_PATH)
    start = datetime(2025, 7, 18, 6, 0, 0)
    end = datetime(2025, 7, 18, 23, 59, 59)

    total = calculate_realized_pnl(trades, start=start, end=end)

    assert total == Decimal("4795.47585300000000000000")


def test_calculate_realized_pnl_invalid_range():
    trades = load_trades(FIXTURE_PATH)
    start = datetime(2025, 7, 19)
    end = datetime(2025, 7, 18)

    with pytest.raises(ValueError):
        calculate_realized_pnl(trades, start=start, end=end)


def test_cli_outputs_total(capsys):
    exit_code = _cli([str(FIXTURE_PATH), "--start", "2025-07-18", "--end", "2025-07-18 23:59:59"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "4795.47585300000000000000"
