# Pre-Push Rules

Follow these before pushing to any branch:

- Black: `black --check playsem tests` (or auto-fix with `black playsem tests`)
- Tests: `pytest -q` (ensure 0 failures, known skips OK)
- Lint (optional but recommended): `flake8 playsem tests`
- Type check (optional): `mypy playsem`
- Update requirements if you installed new dev tools: `requirements-dev.txt`

Shortcuts:
- Windows PowerShell: `./scripts/prepush.ps1` (use `-Fix` to auto-format)
- Bash: `bash scripts/prepush.sh` (use `--fix` to auto-format)

CI notes:
- CI enforces Black check. If it fails, run the scripts above locally and re-push.
