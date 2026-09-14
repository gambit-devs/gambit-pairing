"""Run with python -I to smoke-test the installed wheel, outside source imports."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

from gambitpairing.__main__ import run_app

sys.argv = [sys.argv[0], "--smoke-test"]
raise SystemExit(run_app())
