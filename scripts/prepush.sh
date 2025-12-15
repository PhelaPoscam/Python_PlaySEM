#!/usr/bin/env bash
# Pre-push checks for Python_PlaySEM (POSIX shell)
# Usage: bash scripts/prepush.sh [--fix]

set -euo pipefail

FIX=0
if [[ "${1:-}" == "--fix" ]]; then
  FIX=1
fi

PY=./.venv/Scripts/python.exe
if [[ ! -x "$PY" ]]; then
  # Try Unix venv path as fallback
  PY=./.venv/bin/python
fi

if [[ ! -x "$PY" ]]; then
  echo "Python venv not found. Please activate venv first." >&2
  exit 1
fi

# 1) Black formatting
if ! $PY -m pip show black >/dev/null 2>&1; then
  $PY -m pip install -q black
fi

if [[ $FIX -eq 1 ]]; then
  $PY -m black playsem tests
else
  if ! $PY -m black --check playsem tests; then
    echo "Black failed. Re-run with --fix to auto-format: bash scripts/prepush.sh --fix" >&2
    exit 1
  fi
fi

# 2) Quick tests
$PY -m pytest -q

echo "All pre-push checks passed."
exit 0
