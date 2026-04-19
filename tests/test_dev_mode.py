"""Tester for systems/dev_mode.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from systems import dev_mode


@pytest.fixture
def temp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Rediriger PROJECT_ROOT til tmp_path og rydd PITCH_DEV-env."""
    monkeypatch.setattr(dev_mode, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("PITCH_DEV", raising=False)
    return tmp_path


def test_no_flag_no_env_false(temp_root: Path) -> None:
    assert dev_mode.is_dev_mode() is False


def test_devmode_file_enables(temp_root: Path) -> None:
    (temp_root / ".devmode").touch()
    assert dev_mode.is_dev_mode() is True


def test_env_pitch_dev_enables(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PITCH_DEV", "1")
    assert dev_mode.is_dev_mode() is True


def test_env_other_value_does_not_enable(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PITCH_DEV", "0")
    assert dev_mode.is_dev_mode() is False


def test_file_flag_takes_priority(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Både fil og env: begge gir True; dokumenterer prioritet er OR."""
    (temp_root / ".devmode").touch()
    monkeypatch.setenv("PITCH_DEV", "1")
    assert dev_mode.is_dev_mode() is True
