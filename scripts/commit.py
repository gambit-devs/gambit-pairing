#!/usr/bin/env python3
"""Git commit helper with optional auto‑format retry.

Primary behavior (no feature creep):
 1. (Optional) stage all changes (``--all``).
 2. Attempt ``git commit`` (message from ``-m``, interactive editor, or auto‑generated timestamp).
 3. On failure (non‑zero) and if *not* ``--no-format``:
             a. Run ``format_project.py`` if present.
             b. Re‑stage updated tracked files (``git add -u`` + any new files).
             c. Retry commit once.
 4. Exit codes: 0 success, 1 commit failed, 127 missing dependency (git / python tools).

Purpose: provide a **single consistent command** new contributors can use
instead of remembering to run formatters manually.

This script intentionally avoids adding push / test / lint orchestration so it
stays predictable and fast. Pre‑commit hooks still run normally.

Typical usage (PowerShell):
    python commit.py -m "Add pairing logic"
    python commit.py --all -m "WIP: adjust dialogs"
    python commit.py --amend --no-edit
    python commit.py --dry-run --all -m "Preview"
    python commit.py --all          # Opens editor for commit message
    python commit.py --auto-timestamp  # Uses timestamp instead of editor

When *not* providing ``-m``, an interactive editor opens for commit message composition
by default. Use ``--auto-timestamp`` to generate automatic timestamp messages instead.

Failure handling:
 - If formatting cannot fix the issue (e.g. merge conflicts, failed tests in
     a hook, unresolved files) the second attempt also fails and the script exits 1.
 - If there is nothing staged it exits cleanly after reporting *Nothing to commit*.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Sequence, Tuple

SCRIPT_DIR = Path(__file__).parent.resolve()

# --- Exit codes ---
EXIT_OK = 0
EXIT_COMMIT_FAILED = 1
EXIT_DEP_MISSING = 127


def run(cmd: Sequence[str], desc: str, check: bool = False) -> Tuple[int, str, str]:
    """Run a command and echo output.

    Returns: (returncode, stdout, stderr).
    Never raises unless ``check=True`` (mirrors subprocess.run) in which case
    caller already expects an exception; we capture and return values anyway.
    """
    if desc:  # Only print if description is provided
        printable = " ".join(cmd)
        print(f"→ {desc}: {printable}")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=check)
    except FileNotFoundError:
        msg = f"Command not found: {cmd[0]}"
        print(f"!! {msg}")
        return EXIT_DEP_MISSING, "", msg
    except subprocess.CalledProcessError as e:
        # Occurs only if check=True; still surface its captured output.
        if e.stdout:
            print(e.stdout.rstrip())
        if e.stderr:
            print(e.stderr.rstrip())
        return e.returncode, e.stdout or "", e.stderr or ""

    if desc and proc.stdout.strip():  # Only print output if we showed the command
        print(proc.stdout.rstrip())
    if desc and proc.stderr.strip():  # some tools (git) send hints to stderr
        print(proc.stderr.rstrip())
    return proc.returncode, proc.stdout, proc.stderr


def detect_repo_root(start: Path) -> Path:
    """Find the repository root (.git directory) by ascending from start.

    Returns the *first* ancestor containing ``.git``; if none is found within
    10 levels, ``start`` is returned (script will still attempt to run, but git
    commands will fail gracefully).
    """
    cur = start
    for _ in range(10):  # arbitrary but sufficient depth limit
        if (cur / ".git").exists():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return start


def staged_files() -> List[str]:
    """Return a list of currently staged file paths (empty on error)."""
    rc, out, _ = run(
        ["git", "diff", "--cached", "--name-only"], "Checking staged files"
    )
    if rc != 0:
        return []
    return [line for line in out.splitlines() if line.strip()]


def working_changes() -> bool:
    """Return True if there are *any* unstaged or uncommitted changes."""
    rc, out, _ = run(["git", "status", "--porcelain"], "Checking working tree status")
    return rc == 0 and bool(out.strip())


def get_editor() -> str:
    """Get the preferred editor in a cross-platform way.

    Priority order:
    1. GIT_EDITOR environment variable
    2. EDITOR environment variable
    3. VISUAL environment variable
    4. Platform-specific defaults
    """
    # Check git-specific editor first
    git_editor = os.environ.get("GIT_EDITOR")
    if git_editor:
        return git_editor

    # Check standard editor environment variables
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if editor:
        return editor

    # Platform-specific defaults
    system = platform.system().lower()
    if system == "windows":
        # Try notepad as fallback on Windows
        if shutil.which("notepad"):
            return "notepad"
    elif system in ("linux", "darwin"):  # Linux or macOS
        # Try common editors in order of preference
        for ed in ["nano", "vim", "vi", "emacs"]:
            if shutil.which(ed):
                return ed

    # Last resort fallback
    return "vi" if system != "windows" else "notepad"


def get_commit_message_interactive(template: str = "") -> str | None:
    """Open an editor for the user to compose a commit message.

    Returns the commit message or None if user cancelled/error occurred.
    """
    editor = get_editor()

    # Create temporary file with template
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_file = f.name
        f.write(template)
        if template and not template.endswith("\n"):
            f.write("\n")
        f.write("\n# Please enter the commit message for your changes.\n")
        f.write('# Lines starting with "#" will be ignored, and an empty message\n')
        f.write("# aborts the commit.\n")

        # Add some helpful context
        staged = staged_files()
        if staged:
            f.write("#\n# Changes to be committed:\n")
            for file in staged[:10]:  # Limit to first 10 files
                f.write(f"#\tmodified:   {file}\n")
            if len(staged) > 10:
                f.write(f"#\t... and {len(staged) - 10} more files\n")

    try:
        # Open editor - need to handle different editor types
        if platform.system().lower() == "windows" and "notepad" in editor.lower():
            # Notepad on Windows
            subprocess.run([editor, temp_file], check=True)
        else:
            # Unix-style editors (need to inherit stdin/stdout/stderr)
            subprocess.run(
                [editor, temp_file],
                check=True,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

        # Read the result
        with open(temp_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Process the content - remove comments and empty lines
        lines = []
        for line in content.splitlines():
            line = line.rstrip()
            if line and not line.startswith("#"):
                lines.append(line)

        message = "\n".join(lines).strip()
        return message if message else None

    except (subprocess.CalledProcessError, FileNotFoundError, KeyboardInterrupt):
        print("Editor failed or was cancelled.")
        return None
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def try_commit(args: argparse.Namespace, first_attempt: bool) -> int:
    """Attempt a git commit; return git's exit code.

    Provides user feedback on 'nothing to commit' vs generic failure.
    """
    attempt = "first" if first_attempt else "second"
    cmd = ["git", "commit"]

    if args.amend:
        cmd.append("--amend")
        if args.no_edit:
            cmd.append("--no-edit")

    # Only add message if we have one and we're not using --no-edit
    if args.message and not args.no_edit:
        cmd.extend(["-m", args.message])
    elif not args.amend and not args.message:
        # Let git handle the interactive editor
        pass

    rc, _, stderr = run(cmd, f"Attempting {attempt} commit")
    stderr_lower = stderr.lower()
    if rc != 0:
        if "nothing to commit" in stderr_lower:
            print_nothing_to_commit_help()
        elif "aborting commit due to empty commit message" in stderr_lower:
            print("Commit aborted: empty commit message.")
        else:
            print(f"Commit failed (exit {rc}).")
    return rc


def print_nothing_to_commit_help() -> None:
    """Provide helpful guidance when there's nothing staged to commit."""
    print()
    print("Nothing staged for commit.")
    print()

    # Check what state the working directory is in
    has_unstaged = False
    has_untracked = False

    # Check for unstaged changes (suppress command echo for cleaner output)
    rc, out, _ = run(["git", "diff", "--name-only"], "", check=False)
    if rc == 0 and out.strip():
        has_unstaged = True
        unstaged_files = [f.strip() for f in out.splitlines() if f.strip()]

    # Check for untracked files (suppress command echo for cleaner output)
    rc, out, _ = run(
        ["git", "ls-files", "--others", "--exclude-standard"], "", check=False
    )
    if rc == 0 and out.strip():
        has_untracked = True
        untracked_files = [f.strip() for f in out.splitlines() if f.strip()]

    if has_unstaged or has_untracked:
        print("You have changes that aren't staged for commit:")
        print()

        if has_unstaged:
            print("  📝 Modified files:")
            for file in unstaged_files[:5]:  # Show first 5 files
                print(f"      {file}")
            if len(unstaged_files) > 5:
                print(f"      ... and {len(unstaged_files) - 5} more files")
            print()

        if has_untracked:
            print("  ➕ Untracked files:")
            for file in untracked_files[:5]:  # Show first 5 files
                print(f"      {file}")
            if len(untracked_files) > 5:
                print(f"      ... and {len(untracked_files) - 5} more files")
            print()

        print("💡 To stage and commit these changes:")
        if has_unstaged and has_untracked:
            print("   python commit.py --all         # Stage all changes and commit")
        elif has_unstaged:
            print("   python commit.py --all         # Stage modified files and commit")
            print("   git add <file>                 # Stage specific files")
        else:  # only untracked
            print("   git add <file>                 # Add specific new files")
            print("   python commit.py --all         # Add all files and commit")

        print()
        print("   Or stage files step by step:")
        print("   git add <file>                 # Stage what you want")
        print("   python commit.py               # Then commit")

    else:
        print("✅ Your working tree is clean - all changes have been committed.")
        print()
        print("💡 Next steps:")
        print("   python commit.py --amend       # Modify the last commit")
        print("   git log --oneline              # View recent commits")
        print("   # Make changes to files, then use 'python commit.py --all'")


def run_formatter_if_available() -> None:
    """Execute ``format_project.py`` if present; ignore failures."""
    fmt_script = SCRIPT_DIR / "format_project.py"
    if not fmt_script.exists():
        print("No format_project.py found; skipping formatting step.")
        return
    rc, _, _ = run([sys.executable, str(fmt_script)], "Formatting project")
    if rc != 0:
        print("Formatting script returned non-zero; proceeding regardless.")


def build_auto_message() -> str:
    """Return a deterministic but human-friendly auto commit message."""
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Auto commit: {ts}"


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Commit helper: optional mass stage, auto message, and one formatting retry on failure."
    )
    p.add_argument(
        "-m", "--message", help="Commit message (if omitted, opens editor by default)."
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Stage all changes (tracked + untracked) before committing.",
    )
    p.add_argument("--amend", action="store_true", help="Amend previous commit.")
    p.add_argument(
        "--no-edit",
        action="store_true",
        help="With --amend, keep previous commit message (skip -m).",
    )
    p.add_argument(
        "--no-format",
        action="store_true",
        help="Do NOT run format_project.py + retry if the first commit fails.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show actions without executing commit / formatting.",
    )
    p.add_argument(
        "--auto-timestamp",
        action="store_true",
        help="Generate auto timestamp message instead of opening editor.",
    )
    p.add_argument(
        "--no-auto-timestamp",
        action="store_true",
        help="(Deprecated) Interactive editor is now the default.",
    )
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    # Ensure git binary is available early.
    if shutil.which("git") is None:
        print("git not found on PATH.")
        return EXIT_DEP_MISSING

    # Normalize to repository root (improves consistency for relative scripts).
    repo_root = detect_repo_root(SCRIPT_DIR)
    os.chdir(repo_root)
    print(f"Repository root: {repo_root}")

    # Optionally mass-stage changes.
    if args.all:
        if args.dry_run:
            print("[DRY RUN] Would: git add -A")
        else:
            run(["git", "add", "-A"], "Staging all changes")

    # Check what's staged early and provide guidance if nothing
    staged_before = staged_files()
    print(f"Staged files: {staged_before or '[none]'}")

    # If nothing is staged, provide helpful guidance and exit early
    if not staged_before and not args.dry_run:
        print_nothing_to_commit_help()
        return EXIT_OK

    # Handle commit message logic after we know there's something to commit
    if not args.message and not (args.amend and args.no_edit):
        if not args.auto_timestamp:
            # Interactive editor is now the default
            print("Opening editor for commit message...")
            if not args.dry_run:
                args.message = get_commit_message_interactive()
                if args.message is None:
                    print("Commit cancelled: no message provided.")
                    return EXIT_COMMIT_FAILED
                print(f"Commit message: {args.message}")
            else:
                print("[DRY RUN] Would open editor for commit message")
        else:
            # Generate auto message when explicitly requested
            args.message = build_auto_message()
            print(f"Auto message: {args.message}")

    if args.dry_run:
        print("[DRY RUN] Stopping before commit attempt.")
        return EXIT_OK

    rc = try_commit(args, first_attempt=True)
    if rc != 0 and not args.no_format:
        print("First commit failed; running formatters then retrying once...")
        run_formatter_if_available()
        # Restage modified tracked files + newly created (if any).
        run(["git", "add", "-u"], "Restaging modified tracked files")
        run(["git", "add", "."], "Staging any new files")
        rc = try_commit(args, first_attempt=False)
    elif rc != 0 and args.no_format:
        print("Commit failed and formatting retry disabled (--no-format).")

    if rc == 0:
        hash_rc, out, _ = run(
            ["git", "rev-parse", "HEAD"], "Retrieving new commit hash"
        )
        if hash_rc == 0:
            print(f"Commit hash: {out.strip()}")
        print("Done.")
        return EXIT_OK

    print("Commit failed after retry." if not args.no_format else "Commit failed.")
    return EXIT_COMMIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
