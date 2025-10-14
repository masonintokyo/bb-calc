# BB Calc Trade Utilities

This repository contains utilities for working with BB Calc trade exports.  The
primary feature is a Python module that sums **Realized P&L** values from CSV
files and can optionally restrict the aggregation to a specific period.

## Features

- Parse trade CSV exports into structured `Trade` objects.
- Sum realized P&L across all trades or within an inclusive date range.
- Command line interface for quick calculations.
- Unit tests that exercise the parsing logic, aggregation behaviour, and CLI.

## Usage

### Command line

```bash
python -m bb_calc.pnl_calculator path/to/trades.csv --start 2025-07-01 --end "2025-07-31 23:59:59"
```

The command prints the total realized P&L for trades within the specified range.
When `--start` or `--end` are omitted the filter is unbounded on that side.  Log
verbosity can be adjusted by setting the `BB_CALC_LOG_LEVEL` environment
variable or with the `--log-level` flag.

### Python API

```python
from decimal import Decimal
from pathlib import Path
from datetime import datetime

from bb_calc import calculate_realized_pnl, load_trades

trades = load_trades(Path("trades.csv"))
total = calculate_realized_pnl(
    trades,
    start=datetime(2025, 7, 1),
    end=datetime(2025, 7, 31, 23, 59, 59),
)
```

## Development

### Running tests

```bash
pytest
```

### Project layout

- `bb_calc/`: library and CLI implementation.
- `tests/`: automated tests and sample fixtures.
- `docs/`: supplementary documentation.
