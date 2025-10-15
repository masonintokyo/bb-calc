# Usage Guide

This guide shows how to run the realized P&L calculator against CSV exports.

1. Export your trade history as a CSV file using the trading platform.
2. Run the CLI:

   ```bash
   python -m bb_calc.pnl_calculator exports/trades.csv
   ```

   The program prints a short report including the total of the **Realized P&L**
   column, the number of trades that were included and when those trades were
   filled.

3. To limit the aggregation to a period, provide `--start` and/or `--end`.

   ```bash
   python -m bb_calc.pnl_calculator exports/trades.csv --start 2025-07-01 --end 2025-07-31
   ```

   Dates are interpreted in UTC, matching the timestamps in the export.  The
   start and end timestamps are shown using the same ``YYYY-MM-DD HH:MM:SS``
   format for clarity.

## Calculation logic

The calculator loads each row in the CSV, normalizing numbers to ``Decimal``
for precision.  When ``--start``/``--end`` filters are provided the
``Filled/Settlement Time(UTC+0)`` column is compared against the inclusive
interval.  Only the trades that fall within the interval are counted.  The
total realized P&L is simply the arithmetic sum of the ``Realized P&L`` column
for the filtered trades.  The CLI surfaces this information together with the
number of trades considered and the earliest/latest fill timestamps so you can
quickly validate the aggregation.

## Logging

Set the `BB_CALC_LOG_LEVEL` environment variable (for example `INFO` or `DEBUG`)
to control verbosity.  The CLI also exposes a `--log-level` option for
one-off overrides.
