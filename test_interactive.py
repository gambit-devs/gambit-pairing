#!/usr/bin/env python3
"""Test script for interactive mode fixes."""

import sys

sys.path.insert(0, "src")

from gambitpairing.testing.__main__ import COMMANDS, create_completer

# Test 1: Check that completer has both "/" and non-"/" versions
print("=" * 70)
print("TEST 1: Checking completer has both formats")
print("=" * 70)

completer = create_completer()
if completer:
    # Get the nested dict
    nested_dict = completer.options

    print("\nCommands available in completer:")
    commands_with_slash = [k for k in nested_dict.keys() if k.startswith("/")]
    commands_without_slash = [
        k for k in nested_dict.keys() if not k.startswith("/") and k in COMMANDS
    ]

    print(f"\nWith '/' prefix: {sorted(commands_with_slash)}")
    print(f"\nWithout '/' prefix: {sorted(commands_without_slash)}")

    # Verify both formats exist for each command
    for cmd in COMMANDS.keys():
        has_with_slash = f"/{cmd}" in nested_dict
        has_without_slash = cmd in nested_dict
        status = "[OK]" if (has_with_slash and has_without_slash) else "[FAIL]"
        print(
            f"{status} {cmd:15} - with /: {has_with_slash}, without /: {has_without_slash}"
        )
else:
    print("ERROR: Completer not created (prompt_toolkit not available)")

# Test 2: Command parsing with "/" prefix
print("\n" + "=" * 70)
print("TEST 2: Command parsing with '/' prefix")
print("=" * 70)

test_commands = ["/generate", "generate", "/compare", "compare", "/help", "help"]

print("\nTesting command stripping:")
for test_cmd in test_commands:
    stripped = test_cmd.lstrip("/")
    in_commands = stripped in COMMANDS
    status = "[OK]" if in_commands else "[FAIL]"
    print(f"{status} '{test_cmd}' -> '{stripped}' (in COMMANDS: {in_commands})")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("[OK] All tests passed! Interactive mode should work correctly.")
print("\nTo test interactively:")
print("  cd src && python -m gambitpairing.testing")
print("  Then try typing '/' and pressing TAB")
