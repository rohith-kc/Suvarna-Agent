"""Tests for simulation/config.py's minimal stdlib .env loader."""

import importlib
import os

import simulation.config as config_module


def test_load_dotenv_does_not_override_real_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "already-set")
    monkeypatch.setattr(config_module, "_DOTENV_LOADED", True)  # pretend already loaded; no-op
    config_module._load_dotenv()
    assert os.environ["LLM_PROVIDER"] == "already-set"


def test_parsing_skips_comments_and_blank_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n\nFOO_TEST_KEY=bar\nBAZ_TEST_KEY = spaced \n", encoding="utf-8",
    )
    monkeypatch.delenv("FOO_TEST_KEY", raising=False)
    monkeypatch.delenv("BAZ_TEST_KEY", raising=False)
    monkeypatch.setattr(config_module, "_DOTENV_LOADED", False)

    original_dirname = config_module.os.path.dirname
    original_abspath = config_module.os.path.abspath

    def fake_abspath(p):
        if p == config_module.__file__:
            return str(tmp_path / "simulation" / "config.py")
        return original_abspath(p)

    def fake_dirname(p):
        if p == str(tmp_path / "simulation" / "config.py"):
            return str(tmp_path / "simulation")
        if p == str(tmp_path / "simulation"):
            return str(tmp_path)
        return original_dirname(p)

    monkeypatch.setattr(config_module.os.path, "abspath", fake_abspath)
    monkeypatch.setattr(config_module.os.path, "dirname", fake_dirname)

    config_module._load_dotenv()

    assert os.environ["FOO_TEST_KEY"] == "bar"
    assert os.environ["BAZ_TEST_KEY"] == "spaced"
