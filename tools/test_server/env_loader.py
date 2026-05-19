"""Dependency-free .env file loader for the PlaySEM Test Server."""

import os
from pathlib import Path
from typing import Union


def load_env(env_path: Union[Path, str, None] = None) -> None:
    """Loads environment variables from a `.env` file if it exists."""
    if env_path is None:
        # Project root is 2 levels up from tools/test_server/env_loader.py
        project_root = Path(__file__).resolve().parents[2]
        env_path = project_root / ".env"
    else:
        env_path = Path(env_path)

    if not env_path.exists():
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Split at the first '='
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()

                # Strip optional quotes around value
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]

                # Set variable if not already present in the environment
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"[ENV] Warning: Failed to read .env file at {env_path}: {e}")
