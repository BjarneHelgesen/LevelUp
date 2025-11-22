#!/usr/bin/env python
"""Smoke tests for validators and mods."""

import argparse
import tempfile
from pathlib import Path

from core.compilers.compiler import MSVCCompiler
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3
from core.mods.mod_factory import ModFactory


# =============================================================================
# Validator Smoke Tests
# =============================================================================

SCAFFOLD = "\nint caller() { return f(); }"


class ValidatorSmokeTest:
    def __init__(self, name: str, source: str, modified_source: str, optimization_level: int = 0):
        """source and modified_source are source strings implementing int f()"""
        self.name = name
        self.source = source + SCAFFOLD
        self.modified_source = modified_source + SCAFFOLD
        self.optimization_level = optimization_level


VALIDATOR_SMOKE_TESTS = [
    ValidatorSmokeTest(
        "remove_inline_simple_o0",
        "inline int f() { return 17; }",
        "int f() { return 17; }",
        optimization_level=0),
    ValidatorSmokeTest(
        "remove_inline_simple_o3",
        "inline int f() { return 17; }",
        "int f() { return 17; }",
        optimization_level=3),
]


# =============================================================================
# Mod Smoke Tests
# =============================================================================

class ModSmokeTest:
    def __init__(self, name: str, mod_id: str, source: str, expected: str):
        """source is input C++ code, expected is output after mod runs"""
        self.name = name
        self.mod_id = mod_id
        self.source = source
        self.expected = expected


MOD_SMOKE_TESTS = [
    ModSmokeTest(
        "remove_inline_single",
        "remove_inline",
        "inline int f() { return 1; }",
        " int f() { return 1; }",
    ),
    ModSmokeTest(
        "remove_inline_multiple",
        "remove_inline",
        "inline int f() { return 1; }\ninline int g() { return 2; }",
        " int f() { return 1; }\n int g() { return 2; }",
    ),
]


def run_smoke_tests(verbose: bool = False):
    print("Initializing MSVC compiler...")
    compiler = MSVCCompiler()

    # Create validators for each optimization level
    validators = {
        0: ASMValidatorO0(compiler),
        3: ASMValidatorO3(compiler),
    }

    passed = 0
    failed = 0

    for test in SMOKE_TESTS:
        print(f"\nRunning: {test.name}")

        validator = validators[test.optimization_level]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write source files
            original_file = temp_path / "original.cpp"
            modified_file = temp_path / "modified.cpp"

            original_file.write_text(test.source)
            modified_file.write_text(test.modified_source)

            # Compile both with the test's optimization level
            original_compiled = compiler.compile_file(
                original_file, optimization_level=test.optimization_level
            )
            modified_compiled = compiler.compile_file(
                modified_file, optimization_level=test.optimization_level
            )

            # Validate
            result = validator.validate(original_compiled, modified_compiled)

            if result:
                print(f"  PASS")
                passed += 1
            else:
                print(f"  FAIL - validator returned False (expected True)")
                if verbose:
                    print(f"  Original ASM:\n{original_compiled.asm_output}")
                    print(f"  Modified ASM:\n{modified_compiled.asm_output}")
                failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run validator smoke tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show ASM output on failure")
    args = parser.parse_args()

    success = run_smoke_tests(verbose=args.verbose)
    exit(0 if success else 1)
