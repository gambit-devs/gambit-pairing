"""Common utilities for subprocess command execution.

This module provides reusable functions for running external commands
with consistent error handling and logging.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


class CommandResult:
    """Result of a command execution.

    Attributes:
        returncode: Exit code of the command
        stdout: Standard output as string
        stderr: Standard error as string
        success: Whether the command succeeded (returncode == 0)
    """

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0

    def __bool__(self) -> bool:
        """Allow using result in boolean context: if result: ..."""
        return self.success

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else f"FAILED({self.returncode})"
        return f"CommandResult({status})"


def run_command(
    cmd: Union[List[str], str],
    description: str = "",
    check: bool = False,
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    text: bool = True,
    verbose: bool = True,
) -> CommandResult:
    """Run a command with consistent error handling.

    Args:
        cmd: Command and arguments as list or string
        description: Human-readable description for logging
        check: If True, raise exception on non-zero exit code
        cwd: Working directory for command execution
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text
        verbose: Whether to print execution info

    Returns:
        CommandResult with exit code and output

    Raises:
        FileNotFoundError: If command executable not found
        subprocess.CalledProcessError: If check=True and command fails

    Example:
        >>> result = run_command(["git", "status"], "Check git status")
        >>> if result:
        ...     print("Success!")
        >>> print(result.stdout)
    """
    if verbose and description:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        logger.info(f"{description}: {cmd_str}")
        print(f"→ {description}: {cmd_str}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            check=check,
            cwd=cwd,
        )

        result = CommandResult(
            returncode=proc.returncode,
            stdout=proc.stdout if capture_output else "",
            stderr=proc.stderr if capture_output else "",
        )

        # Log output if verbose
        if verbose:
            if result.stdout and result.stdout.strip():
                print(result.stdout.rstrip())
            if result.stderr and result.stderr.strip():
                print(result.stderr.rstrip(), file=sys.stderr)

        return result

    except FileNotFoundError as e:
        msg = (
            f"Command not found: {cmd[0] if isinstance(cmd, list) else cmd.split()[0]}"
        )
        logger.error(msg)
        if verbose:
            print(f"!! {msg}", file=sys.stderr)
        raise

    except subprocess.CalledProcessError as e:
        # This only occurs if check=True
        result = CommandResult(
            returncode=e.returncode,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
        )

        if verbose:
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip(), file=sys.stderr)

        raise


def run_command_silent(
    cmd: Union[List[str], str],
    cwd: Optional[Path] = None,
) -> CommandResult:
    """Run a command silently without any output.

    Convenience wrapper for run_command with verbose=False.

    Args:
        cmd: Command and arguments
        cwd: Working directory

    Returns:
        CommandResult with exit code and output
    """
    return run_command(cmd, description="", check=False, cwd=cwd, verbose=False)


def check_command_exists(command: str) -> bool:
    """Check if a command is available on the system.

    Args:
        command: Name of the command to check

    Returns:
        True if command is found, False otherwise

    Example:
        >>> if check_command_exists("git"):
        ...     print("Git is installed")
    """
    import shutil

    return shutil.which(command) is not None


def run_python_module(
    module: str,
    args: Optional[List[str]] = None,
    description: str = "",
    check: bool = False,
) -> CommandResult:
    """Run a Python module using the current interpreter.

    Args:
        module: Module name (e.g., "pip", "pytest")
        args: Additional arguments for the module
        description: Human-readable description
        check: If True, raise exception on failure

    Returns:
        CommandResult with exit code and output

    Example:
        >>> result = run_python_module("pip", ["install", "requests"], "Install requests")
    """
    cmd = [sys.executable, "-m", module]
    if args:
        cmd.extend(args)

    return run_command(
        cmd,
        description=description or f"Running Python module: {module}",
        check=check,
    )


def run_with_retry(
    cmd: Union[List[str], str],
    description: str = "",
    max_attempts: int = 3,
    delay: float = 1.0,
) -> CommandResult:
    """Run a command with automatic retry on failure.

    Args:
        cmd: Command and arguments
        description: Human-readable description
        max_attempts: Maximum number of attempts
        delay: Delay in seconds between attempts

    Returns:
        CommandResult from successful attempt

    Raises:
        subprocess.CalledProcessError: If all attempts fail
    """
    import time

    last_result = None
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Attempt {attempt}/{max_attempts}: {description}")

        try:
            result = run_command(cmd, description, check=True, verbose=(attempt == 1))
            return result
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            last_result = getattr(e, "result", None)
            if attempt < max_attempts:
                logger.warning(f"Attempt {attempt} failed, retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed")
                raise

    # Should never reach here, but satisfy type checker
    return last_result or CommandResult(1, "", "All attempts failed")
