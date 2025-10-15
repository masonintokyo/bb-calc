"""Tools for aggregating realized P&L from trade CSV exports.

The module exposes a :class:`Trade` data class, helpers to load trades from a CSV
file and a function to aggregate realized P&L optionally constrained to a time
range.  A small CLI is also provided for ad-hoc usage.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

_LOGGER = logging.getLogger(__name__)

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)


@dataclass(frozen=True)
class Trade:
    """Normalized representation of a single trade entry."""

    uid: str
    contract: str
    trade_type: str
    quantity: Decimal
    entry_price: Decimal
    realized_pnl: Decimal
    filled_price: Decimal
    exit_type: str
    filled_time: datetime
    created_time: datetime


@dataclass(frozen=True)
class PnLSummary:
    """Aggregated view of realized P&L over a period."""

    total: Decimal
    trade_count: int
    start: Optional[datetime]
    end: Optional[datetime]
    earliest_fill: Optional[datetime]
    latest_fill: Optional[datetime]


def configure_logging(log_level: Optional[str] = None) -> None:
    """Configure module wide logging.

    Parameters
    ----------
    log_level:
        Optional textual level (e.g. ``"INFO"``). When omitted an environment
        variable ``BB_CALC_LOG_LEVEL`` is used.  ``logging.basicConfig`` is only
        invoked when no handlers are already configured to avoid clobbering
        application level logging.
    """

    if logging.getLogger().handlers:
        return

    level_name = (log_level or os.getenv("BB_CALC_LOG_LEVEL", "WARNING")).upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _parse_decimal(value: str, column: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Invalid decimal value '{value}' in column '{column}'") from exc


def _parse_datetime(value: str, column: str) -> datetime:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format '{value}' in column '{column}'")


def _normalize_trade(row: dict) -> Trade:
    return Trade(
        uid=row["Uid"],
        contract=row["Contracts"],
        trade_type=row["Trade Type"],
        quantity=_parse_decimal(row["Qty"], "Qty"),
        entry_price=_parse_decimal(row["Entry Price"], "Entry Price"),
        realized_pnl=_parse_decimal(row["Realized P&L"], "Realized P&L"),
        filled_price=_parse_decimal(row["Filled Price"], "Filled Price"),
        exit_type=row["Exit Type"],
        filled_time=_parse_datetime(row["Filled/Settlement Time(UTC+0)"], "Filled/Settlement Time(UTC+0)"),
        created_time=_parse_datetime(row["Create Time"], "Create Time"),
    )


def load_trades(csv_path: Path, encoding: str = "utf-8") -> List[Trade]:
    """Load trades from a CSV file.

    Parameters
    ----------
    csv_path:
        Path to the CSV file exported from the trading platform.
    encoding:
        Character encoding of the file. Defaults to UTF-8.

    Returns
    -------
    list[Trade]
        A list of :class:`Trade` instances in the order they appear in the file.

    Notes
    -----
    Some exports prepend metadata lines (e.g. ``"UID: 382647166"``) before the
    actual header row.  These lines are automatically skipped when searching for
    the header so the function can ingest such files without manual editing.
    """

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    _LOGGER.debug("Loading trades from %s", csv_path)

    with csv_path.open("r", encoding=encoding, newline="") as handle:
        lines = list(handle)

    header_index = _find_header_index(lines)
    reader = csv.DictReader(lines[header_index:])

    if reader.fieldnames is None:  # pragma: no cover - csv module invariants
        raise ValueError("CSV file is missing a header row")

    reader.fieldnames = [_clean_header_cell(name) for name in reader.fieldnames]

    missing_columns = {key for key in _required_columns() if key not in reader.fieldnames}
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing_columns))}")

    return [_normalize_trade(row) for row in reader]


def _clean_header_cell(value: str) -> str:
    """Normalize header cell names for consistent column matching."""

    return value.strip().lstrip("\ufeff")


def _find_header_index(lines: List[str]) -> int:
    """Locate the CSV header row within the provided file contents."""

    required = _required_columns()

    for index, raw_line in enumerate(lines):
        try:
            row = next(csv.reader([raw_line]))
        except csv.Error:  # pragma: no cover - defensive branch
            continue

        cleaned_cells = {_clean_header_cell(cell) for cell in row if cell}
        if required.issubset(cleaned_cells):
            return index

    raise ValueError(
        "Unable to locate header row containing required columns in CSV file"
    )


def _required_columns() -> set[str]:
    return {
        "Uid",
        "Contracts",
        "Trade Type",
        "Qty",
        "Entry Price",
        "Realized P&L",
        "Filled Price",
        "Exit Type",
        "Filled/Settlement Time(UTC+0)",
        "Create Time",
    }


def _filter_trades(
    trades: Iterable[Trade], start: Optional[datetime], end: Optional[datetime]
) -> Iterator[Trade]:
    for trade in trades:
        if start and trade.filled_time < start:
            continue
        if end and trade.filled_time > end:
            continue
        yield trade


def calculate_realized_pnl(
    trades: Iterable[Trade], start: Optional[datetime] = None, end: Optional[datetime] = None
) -> Decimal:
    """Aggregate realized P&L for the provided trades.

    The *start* and *end* boundaries are inclusive.  When both are provided the
    function validates that *start* is not after *end*.
    """

    summary = summarize_realized_pnl(trades, start=start, end=end)
    _LOGGER.debug(
        "Calculated realized P&L",
        extra={
            "total": str(summary.total),
            "start": summary.start,
            "end": summary.end,
            "trade_count": summary.trade_count,
        },
    )
    return summary.total


def summarize_realized_pnl(
    trades: Iterable[Trade], start: Optional[datetime] = None, end: Optional[datetime] = None
) -> PnLSummary:
    """Compute aggregated statistics for realized P&L within an optional period."""

    if start and end and start > end:
        raise ValueError("start datetime must be earlier than or equal to end datetime")

    total = Decimal("0")
    trade_count = 0
    earliest: Optional[datetime] = None
    latest: Optional[datetime] = None

    for trade in _filter_trades(trades, start, end):
        total += trade.realized_pnl
        trade_count += 1
        if earliest is None or trade.filled_time < earliest:
            earliest = trade.filled_time
        if latest is None or trade.filled_time > latest:
            latest = trade.filled_time

    return PnLSummary(
        total=total,
        trade_count=trade_count,
        start=start,
        end=end,
        earliest_fill=earliest,
        latest_fill=latest,
    )


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize realized P&L from a trade CSV export")
    parser.add_argument("csv", type=Path, help="Path to the CSV file")
    parser.add_argument(
        "--start",
        dest="start",
        type=str,
        default=None,
        help="Inclusive start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
    )
    parser.add_argument(
        "--end",
        dest="end",
        type=str,
        default=None,
        help="Inclusive end datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        default=None,
        help="Override logging level (e.g. INFO, DEBUG)",
    )

    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    start_dt = _parse_datetime(args.start, "--start") if args.start else None
    end_dt = _parse_datetime(args.end, "--end") if args.end else None

    trades = load_trades(args.csv)
    summary = summarize_realized_pnl(trades, start=start_dt, end=end_dt)
    print(_format_summary(summary))
    return 0


def _format_summary(summary: PnLSummary) -> str:
    lines = ["Realized P&L Summary", "===================="]

    def _line(label: str, value: str) -> str:
        return f"{label:<20}: {value}"

    lines.append(_line("Total realized P&L", str(summary.total)))
    lines.append(_line("Trades considered", str(summary.trade_count)))
    lines.append(_line("Filter start (UTC)", _format_datetime(summary.start)))
    lines.append(_line("Filter end (UTC)", _format_datetime(summary.end)))
    lines.append(_line("First fill (UTC)", _format_datetime(summary.earliest_fill)))
    lines.append(_line("Last fill (UTC)", _format_datetime(summary.latest_fill)))

    return "\n".join(lines)


def _format_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return "not specified"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    raise SystemExit(_cli())


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
