"""Tests for the README version banner tool."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

pytest.importorskip("pyfiglet")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


banner = _load("update_readme_version")


def sample_readme(version: str = "1.0") -> str:
    """Return a README-like text whose banner is drawn by the tool itself."""
    lines = ["# Title", "", "```", *banner.compose(version), "```", "", "Some text."]
    return "\r\n".join(lines) + "\r\n"


def test_the_bars_frame_every_version():
    rows = banner.compose("0.8")
    assert len(rows) == 5
    assert rows[2].startswith(" _____ _____ _____")
    assert rows[3].startswith("|_____|_____|_____|")
    assert "_____ _____ _____" in rows[2][34:]


def test_a_three_part_version_draws_major_and_minor(capsys):
    assert banner.main(["0.8.0", "--dry-run"]) == 0
    assert capsys.readouterr().out.splitlines() == banner.compose("0.8")


def test_the_banner_is_found_inside_surrounding_text():
    lines = ["intro", "", "```", *banner.compose("1.0"), "```"]
    assert banner.find_banner(lines) == 3


def test_update_changes_only_the_banner_and_keeps_crlf():
    text = sample_readme("1.0")
    updated, changed = banner.update_readme(text, "0.8")
    assert changed
    assert "\r\n" in updated and "\n" not in updated.replace("\r\n", "")
    before = text.replace("\r\n", "\n").split("\n")
    after = updated.replace("\r\n", "\n").split("\n")
    assert len(before) == len(after)
    differing = [index for index, (a, b) in enumerate(zip(before, after)) if a != b]
    assert differing and all(3 <= index <= 7 for index in differing)
    assert after[3:8] == banner.compose("0.8")
    assert after[-2] == "Some text."


def test_a_second_update_changes_nothing():
    updated, _ = banner.update_readme(sample_readme("1.0"), "0.8")
    again, changed = banner.update_readme(updated, "0.8")
    assert not changed
    assert again == updated


def test_a_version_that_runs_into_the_bar_is_refused():
    with pytest.raises(banner.BannerError, match="too wide"):
        banner.compose("0.10")


def test_a_readme_without_a_banner_is_refused():
    with pytest.raises(banner.BannerError, match="not found"):
        banner.update_readme("# Title\r\n\r\nNo art here.\r\n", "0.8")


def test_an_invalid_version_is_refused(tmp_path, capsys):
    readme = tmp_path / "README.md"
    readme.write_text(sample_readme("1.0"), encoding="utf-8", newline="")
    assert banner.main(["banana", "--readme", str(readme)]) == 1
    assert "Expected a version" in capsys.readouterr().out


def test_main_writes_the_readme(tmp_path, capsys):
    readme = tmp_path / "README.md"
    readme.write_text(sample_readme("1.0"), encoding="utf-8", newline="")
    assert banner.main(["0.8", "--readme", str(readme)]) == 0
    with open(readme, encoding="utf-8", newline="") as handle:
        text = handle.read()
    assert "\r\n" in text
    assert banner.compose("0.8")[2] in text
    assert "now shows 0.8" in capsys.readouterr().out
