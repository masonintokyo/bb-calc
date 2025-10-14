from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on the import path when tests run in isolation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
