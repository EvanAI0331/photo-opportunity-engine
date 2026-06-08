#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.factor_research.factor_reporter import build_factor_report


if __name__ == "__main__":
    print(json.dumps(build_factor_report(), ensure_ascii=False, indent=2))
