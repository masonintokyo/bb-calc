# Usage Guide

This guide shows how to run the realized P&L calculator against CSV exports.

1. Export your trade history as a CSV file using the trading platform.
2. Run the CLI:

   ```bash
   python -m bb_calc.pnl_calculator exports/trades.csv
   ```

   The program prints the sum of the **Realized P&L** column.

3. To limit the aggregation to a period, provide `--start` and/or `--end`.

   ```bash
   python -m bb_calc.pnl_calculator exports/trades.csv --start 2025-07-01 --end 2025-07-31
   ```

   Dates are interpreted in UTC, matching the timestamps in the export.

## Logging

Set the `BB_CALC_LOG_LEVEL` environment variable (for example `INFO` or `DEBUG`)
to control verbosity.  The CLI also exposes a `--log-level` option for
one-off overrides.
