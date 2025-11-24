"""Test configuration ensuring root and src packages importable and logging set."""

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
EXAMPLES = ROOT / "examples"

for p in (ROOT, SRC, EXAMPLES):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
