"""Tests for the cross-platform development setup script."""

import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_dev.py"


def _load_setup_dev():
    spec = importlib.util.spec_from_file_location("setup_dev", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup_dev = _load_setup_dev()

PLATFORMS = ["linux", "win32", "darwin"]


def write_venv(venv_dir, platform, system_site="false", python=True):
    python_path = setup_dev.venv_python_path(venv_dir, platform)
    python_path.parent.mkdir(parents=True)
    if python:
        python_path.write_text("")
    (venv_dir / "pyvenv.cfg").write_text(
        f"home = /usr/bin\ninclude-system-site-packages = {system_site}\n"
        "version = 3.12.1\n"
    )


def probe_returning(version, base="/usr/bin/python3.12"):
    return lambda command: (base, version)


# Argument handling


def test_parse_args_defaults():
    args = setup_dev.parse_args([])
    assert args.python is None
    assert not (args.recreate or args.build_bbp or args.require_breeze)


def test_parse_args_all_flags():
    args = setup_dev.parse_args(
        ["--python", "/opt/py", "--recreate", "--build-bbp", "--require-breeze"]
    )
    assert args.python == "/opt/py"
    assert args.recreate and args.build_bbp and args.require_breeze


@pytest.mark.parametrize(
    "argv", [["--python"], ["--python", ""], ["--bogus"], ["--skip-system-deps"]]
)
def test_parse_args_rejects_bad_input(argv):
    with pytest.raises(SystemExit) as excinfo:
        setup_dev.parse_args(argv)
    assert excinfo.value.code != 0


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_exits_cleanly(flag, capsys):
    with pytest.raises(SystemExit) as excinfo:
        setup_dev.parse_args([flag])
    assert excinfo.value.code == 0
    assert "--require-breeze" in capsys.readouterr().out


# Platform paths


@pytest.mark.parametrize(
    "platform, python_rel, launcher_rel",
    [
        ("linux", ("bin", "python"), ("bin", "gambit-pairing")),
        ("darwin", ("bin", "python"), ("bin", "gambit-pairing")),
        ("win32", ("Scripts", "python.exe"), ("Scripts", "gambit-pairing.exe")),
    ],
)
def test_venv_paths(platform, python_rel, launcher_rel):
    venv = Path("proj") / ".venv"
    assert setup_dev.venv_python_path(venv, platform) == venv.joinpath(*python_rel)
    assert setup_dev.launcher_path(venv, platform) == venv.joinpath(*launcher_rel)


def test_python_candidates_windows():
    assert setup_dev.python_candidates("win32") == [["py", "-3"], ["python"]]


def test_python_candidates_linux_prefers_system():
    fake_glob = lambda pattern: ["/usr/bin/python3.14", "/usr/bin/python3.12"]
    assert setup_dev.python_candidates("linux", fake_glob) == [
        ["/usr/bin/python3"],
        ["/usr/bin/python3.12"],
        ["/usr/bin/python3.14"],
        ["python3"],
        ["python"],
    ]


def test_python_candidates_darwin_prefers_path():
    candidates = setup_dev.python_candidates("darwin", lambda pattern: [])
    assert candidates == [["python3"], ["python"], ["/usr/bin/python3"]]


# Finding Python


@pytest.mark.parametrize(
    "version, ok",
    [("3.10.0", True), ("3.14.8", True), ("4.0.0", True), ("3.9.18", False)],
)
def test_version_is_compatible(version, ok):
    assert setup_dev.version_is_compatible(version) is ok


def test_probe_python_skips_missing_command(monkeypatch):
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: None)
    run = lambda *a, **k: pytest.fail("should not run")
    assert setup_dev.probe_python(["python3"], run=run) is None


@pytest.mark.parametrize(
    "result",
    [
        # Windows Store stub: exists on PATH but fails without output.
        SimpleNamespace(returncode=9009, stdout=""),
        SimpleNamespace(returncode=0, stdout="garbage\n"),
    ],
)
def test_probe_python_rejects_unusable(monkeypatch, result):
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: name)
    assert setup_dev.probe_python(["python"], run=lambda *a, **k: result) is None


def test_probe_python_handles_timeout(monkeypatch):
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: name)

    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("python", 60)

    assert setup_dev.probe_python(["python"], run=run) is None


def test_probe_python_parses_output(monkeypatch):
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: name)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="/usr/bin/python3.12\n3.12.1\n")

    assert setup_dev.probe_python(["py", "-3"], run=run) == (
        "/usr/bin/python3.12",
        "3.12.1",
    )
    assert calls[0][:3] == ["py", "-3", "-c"]
    assert "_base_executable" in calls[0][3]


def test_find_python_uses_requested_only():
    seen = []

    def probe(command):
        seen.append(command)
        return ("/opt/py/bin/python3.12", "3.12.1")

    assert setup_dev.find_python("/opt/py/bin/python3", "linux", probe) == (
        "/opt/py/bin/python3.12",
        None,
    )
    assert seen == [["/opt/py/bin/python3"]]


@pytest.mark.parametrize("platform", PLATFORMS)
def test_find_python_records_older_version(monkeypatch, platform):
    monkeypatch.setattr(
        setup_dev, "python_candidates", lambda p: [["old"], ["broken"], ["new"]]
    )
    results = {
        "old": ("/usr/bin/python3.8", "3.8.10"),
        "broken": None,
        "new": ("/usr/bin/python3.12", "3.12.1"),
    }
    python_bin, old = setup_dev.find_python(None, platform, lambda c: results[c[0]])
    assert (python_bin, old) == ("/usr/bin/python3.12", "3.8.10")


def test_find_python_only_old_found(monkeypatch):
    monkeypatch.setattr(setup_dev, "python_candidates", lambda p: [["old"]])
    with pytest.raises(setup_dev.SetupError, match="3.9.1 is older"):
        setup_dev.find_python(None, "linux", lambda c: ("/x", "3.9.1"))


def test_find_python_requested_unusable():
    with pytest.raises(setup_dev.SetupError, match="Cannot run the requested"):
        setup_dev.find_python("/nope", "linux", lambda c: None)


def test_find_python_none_found(monkeypatch):
    monkeypatch.setattr(setup_dev, "python_candidates", lambda p: [["python3"]])
    with pytest.raises(setup_dev.SetupError, match="3.10 or newer is required"):
        setup_dev.find_python(None, "win32", lambda c: None)


# Privileges


@pytest.mark.parametrize("variable", ["SUDO_USER", "DOAS_USER"])
@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_check_privileges_refuses_sudo(platform, variable):
    with pytest.raises(setup_dev.SetupError, match="without sudo/doas"):
        setup_dev.check_privileges(platform, {variable: "me"}, lambda: 0)


def test_check_privileges_allows_plain_root_and_users():
    setup_dev.check_privileges("linux", {}, lambda: 0)
    setup_dev.check_privileges("linux", {"SUDO_USER": "me"}, lambda: 1000)


def test_check_privileges_skipped_on_windows():
    setup_dev.check_privileges("win32", {"SUDO_USER": "me"}, lambda: pytest.fail())


# Venv compatibility


@pytest.mark.parametrize("platform", PLATFORMS)
def test_usable_venv_passes(tmp_path, platform):
    venv = tmp_path / ".venv"
    write_venv(venv, platform)
    setup_dev.check_existing_venv(venv, platform, False, probe_returning("3.12.1"))


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.parametrize(
    "case",
    ["system_site", "missing_python", "missing_cfg", "old_python", "probe_fails"],
)
def test_unusable_venv_needs_recreate(tmp_path, platform, case):
    venv = tmp_path / ".venv"
    write_venv(
        venv,
        platform,
        system_site="true" if case == "system_site" else "false",
        python=case != "missing_python",
    )
    if case == "missing_cfg":
        (venv / "pyvenv.cfg").unlink()
    probe = {
        "old_python": probe_returning("3.9.1"),
        "probe_fails": lambda command: None,
    }.get(case, probe_returning("3.12.1"))
    with pytest.raises(setup_dev.SetupError, match="--recreate"):
        setup_dev.check_existing_venv(venv, platform, False, probe)
    # --recreate skips the compatibility check.
    setup_dev.check_existing_venv(venv, platform, True, probe)


def test_symlinked_venv_refused(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    link = tmp_path / ".venv"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(setup_dev.SetupError, match="symlink"):
        setup_dev.check_existing_venv(link, "linux", True)


def test_unwritable_venv_refused(tmp_path, monkeypatch):
    venv = tmp_path / ".venv"
    venv.mkdir()
    monkeypatch.setattr(setup_dev.os, "access", lambda path, mode: False)
    with pytest.raises(setup_dev.SetupError, match="not writable"):
        setup_dev.check_existing_venv(venv, "linux", True)


def test_missing_venv_is_fine(tmp_path):
    setup_dev.check_existing_venv(tmp_path / ".venv", "win32", False)


def test_venv_base_mismatch(tmp_path):
    python = tmp_path / "python"
    with pytest.raises(setup_dev.SetupError, match="different Python"):
        setup_dev.check_venv_base(python, "/usr/bin/python3.12", lambda c: None)
    with pytest.raises(setup_dev.SetupError, match="different Python"):
        setup_dev.check_venv_base(
            python, "/usr/bin/python3.12", probe_returning("3.13.0", "/usr/bin/x")
        )
    setup_dev.check_venv_base(python, "/usr/bin/python3.12", probe_returning("3.12"))


# pip bootstrap


def fake_runs(monkeypatch, outcomes):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        for key, code in outcomes.items():
            if command[1:3] == ["-m", key]:
                if kwargs.get("check") and code:
                    raise subprocess.CalledProcessError(code, command)
                return SimpleNamespace(returncode=code)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(setup_dev.subprocess, "run", run)
    return calls


def test_ensure_pip_already_present(monkeypatch):
    calls = fake_runs(monkeypatch, {})
    setup_dev.ensure_pip(Path("py"), Path(".venv"))
    assert calls == [["py", "-m", "pip", "--version"]]


def test_ensure_pip_uses_ensurepip(monkeypatch):
    calls = fake_runs(monkeypatch, {"pip": 1})
    setup_dev.ensure_pip(Path("py"), Path(".venv"))
    assert calls[-1] == ["py", "-m", "ensurepip", "--upgrade"]


def test_ensure_pip_falls_back_to_uv(monkeypatch):
    calls = fake_runs(monkeypatch, {"pip": 1, "ensurepip": 1})
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: "/bin/uv")
    setup_dev.ensure_pip(Path("py"), Path(".venv"))
    assert calls[-1] == ["/bin/uv", "pip", "install", "--python", "py", "pip"]


def test_ensure_pip_gives_up(monkeypatch):
    fake_runs(monkeypatch, {"pip": 1, "ensurepip": 1})
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: None)
    with pytest.raises(setup_dev.SetupError, match="ensurepip"):
        setup_dev.ensure_pip(Path("py"), Path(".venv"))


# BBP, Qt environment and notes


def test_bbp_engine_staged(tmp_path):
    staged = tmp_path / "src" / "gambitpairing" / "resources" / "bin"
    staged.mkdir(parents=True)
    (staged / "README.txt").write_text("")
    assert not setup_dev.bbp_engine_available(tmp_path, lambda name: None)
    (staged / "bbpPairings.exe").write_text("")
    assert setup_dev.bbp_engine_available(tmp_path, lambda name: None)


@pytest.mark.parametrize("name", ["bbpPairings", "bbpPairings.exe"])
def test_bbp_engine_on_path(tmp_path, name):
    which = lambda candidate: "/bin/x" if candidate == name else None
    assert setup_dev.bbp_engine_available(tmp_path, which)


@pytest.mark.parametrize("required, expected", [(True, "1"), (False, "0")])
def test_qt_check_env(required, expected):
    env = setup_dev.qt_check_env(required, {"PATH": "/bin"})
    assert env == {
        "PATH": "/bin",
        "QT_QPA_PLATFORM": "offscreen",
        "GAMBIT_NATIVE_STYLE_REQUIRED": expected,
    }


def test_notes_text():
    assert setup_dev.old_python_note("3.8.10", "/usr/bin/python3.12") == (
        "Python 3.8.10 was also found; this environment uses /usr/bin/python3.12."
    )
    assert setup_dev.format_notes([]) == ""
    assert setup_dev.format_notes(["a", "b"]) == "\nNote: a\n\nNote: b\n"
    assert "python scripts/build_bbp.py" in setup_dev.BBP_NOTE
    assert "Breeze" in setup_dev.BREEZE_NOTE


# End-to-end flow with subprocesses mocked


@pytest.mark.parametrize("platform", PLATFORMS)
def test_run_setup_flow(tmp_path, monkeypatch, capsys, platform):
    project = tmp_path / "proj"
    venv = project / ".venv"
    write_venv(venv, platform)
    monkeypatch.setattr(setup_dev, "PROJECT_DIR", project)
    monkeypatch.setattr(setup_dev, "SCRIPTS_DIR", project / "scripts")
    monkeypatch.setattr(setup_dev, "check_privileges", lambda p: None)
    monkeypatch.setattr(
        setup_dev, "find_python", lambda r, p: ("/usr/bin/python3.12", "3.8.10")
    )
    monkeypatch.setattr(setup_dev.shutil, "which", lambda name: None)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs.get("env")))
        # Breeze probe fails, everything else succeeds.
        failed = "-c" in command and "configure_native_style" in command[-1]
        return SimpleNamespace(returncode=1 if failed else 0)

    monkeypatch.setattr(setup_dev.subprocess, "run", run)
    # Venv checks have their own tests; keep the flow test on the orchestration.
    monkeypatch.setattr(setup_dev, "check_existing_venv", lambda *a: None)
    monkeypatch.setattr(setup_dev, "check_venv_base", lambda *a: None)
    monkeypatch.setattr(setup_dev.os, "chdir", lambda path: None)
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")
    monkeypatch.delenv("PYTHONHOME", raising=False)
    monkeypatch.delenv("PYTHONPATH", raising=False)

    setup_dev.run_setup(setup_dev.parse_args([]), platform)

    venv_python = str(setup_dev.venv_python_path(venv, platform))
    commands = [command for command, _ in calls]
    assert [venv_python, str(project / "scripts" / "install_editable_pip.py")] in (
        commands
    )
    qt = [venv_python, "-m", "gambitpairing", "--verify-native-style"]
    qt_env = calls[commands.index(qt)][1]
    assert qt_env["QT_QPA_PLATFORM"] == "offscreen"
    assert qt_env["GAMBIT_NATIVE_STYLE_REQUIRED"] == "0"
    breeze_probed = any("configure_native_style" in c[-1] for c in commands)
    assert breeze_probed is (platform == "linux")

    out = capsys.readouterr().out
    assert "Development environment is ready." in out
    assert str(setup_dev.launcher_path(venv, platform)) in out
    assert setup_dev.BBP_NOTE in out
    assert (setup_dev.BREEZE_NOTE in out) is (platform == "linux")
    assert out.rstrip().endswith(
        "Note: Python 3.8.10 was also found; this environment uses "
        "/usr/bin/python3.12."
    )


def test_main_reports_setup_error(monkeypatch, capsys):
    def fail(args):
        raise setup_dev.SetupError("boom")

    monkeypatch.setattr(setup_dev, "run_setup", fail)
    assert setup_dev.main([]) == 1
    assert capsys.readouterr().err.strip() == "boom"
