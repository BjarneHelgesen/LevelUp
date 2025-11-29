#!/usr/bin/env python
"""Minimal wrapper that executes core/smoketest.py"""

import sys
from pathlib import Path

# Add core to Python path
core_path = Path(__file__).parent / "core"
sys.path.insert(0, str(core_path))

# Import and run the main smoketest module
if __name__ == "__main__":
    from smoketest import run_smoke_tests, get_default_compiler
    from core.compilers.compiler_type import CompilerType
    import argparse

    parser = argparse.ArgumentParser(description="Run LevelUp smoke tests")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run tests with all compilers (default: only default compiler)"
    )
    args = parser.parse_args()

    if args.all:
        compilers = list(CompilerType)
        print(f"Running smoke tests with ALL compilers: {[c.value for c in compilers]}")
    else:
        compilers = [get_default_compiler()]
        print(f"Running smoke tests with default compiler: {compilers[0].value}")
        print("(Use --all to test with all compilers)")

    run_smoke_tests(compilers)
