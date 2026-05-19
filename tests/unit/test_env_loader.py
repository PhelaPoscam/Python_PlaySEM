"""Unit tests for the custom .env file loader."""

import os
from tools.test_server.env_loader import load_env


def test_load_env_non_existent() -> None:
    # Calling it on a non-existent file should do nothing and not raise
    load_env("this_file_does_not_exist_xyz.env")


def test_load_env_valid(tmp_path) -> None:
    env_file = tmp_path / "test.env"
    env_content = """
    # This is a comment
    TEST_VAR_1 = hello
    TEST_VAR_2="world"
    TEST_VAR_3 = 'quoted'
    INVALID_LINE
    # Another comment
    TEST_VAR_1 = ignored_because_already_set
    """
    env_file.write_text(env_content, encoding="utf-8")

    # Ensure keys are not in os.environ first
    for key in ["TEST_VAR_1", "TEST_VAR_2", "TEST_VAR_3"]:
        os.environ.pop(key, None)

    # Load env
    load_env(env_file)

    assert os.environ.get("TEST_VAR_1") == "hello"
    assert os.environ.get("TEST_VAR_2") == "world"
    assert os.environ.get("TEST_VAR_3") == "quoted"

    # Cleanup
    for key in ["TEST_VAR_1", "TEST_VAR_2", "TEST_VAR_3"]:
        os.environ.pop(key, None)


def test_load_env_does_not_override_existing(tmp_path) -> None:
    env_file = tmp_path / "test.env"
    env_content = "EXISTING_VAR=new_val\n"
    env_file.write_text(env_content, encoding="utf-8")

    os.environ["EXISTING_VAR"] = "original_val"

    try:
        load_env(env_file)
        assert os.environ.get("EXISTING_VAR") == "original_val"
    finally:
        os.environ.pop("EXISTING_VAR", None)
