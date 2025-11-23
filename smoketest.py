#!/usr/bin/env python
"""Smoke tests for validators and mods."""

import tempfile
from pathlib import Path

from core.compilers.compiler import MSVCCompiler
from core.validators.asm_validator import ASMValidator
from core.mods.mod_factory import ModFactory


# =============================================================================
# Validator Smoke Tests
# =============================================================================

SCAFFOLD = "\nint main() { return f(); }"


class ValidatorSmokeTest:
    def __init__(self, name: str, source: str, modified_source: str, o: int = 0):
        """paramters source and modified_source are source strings implementing int f()"""
        self.name = name
        self.source = source + SCAFFOLD
        self.modified_source = modified_source + SCAFFOLD
        self.optimization_level = o


ValTest = ValidatorSmokeTest #shorthand for the list 
VALIDATOR_SMOKE_TESTS = \
[   
    # Add comments
    ValTest("add_comments",         'int f() { return 17; }', 
                                    '/* Hardcoded seventeen */ int f() { return 17;  }', o=3), 

    # Extract function (two steps)
    ValTest("extract_function",     'int f() { return 4*4 + 1; }', 
                                    'inline int squared(int x) { return x*x; } int f() { return squared(4) + 1; }', o=3),
    ValTest("remove_inline",        'inline int squared(int x) { return x*x; } int f() { return squared(4) + 1; }', 
                                    'int squared(int x) { return x*x; } int f() { return squared(4) + 1; }', o=0),

    # Const parameter (one step)
    ValTest("add_const param",       'int len(      char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }', 
                                    'int len(const char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }', o=0), #o=Any
    
    # Dead code
    ValTest("remove_dead_code",     'int f() { return 17; int x = 10; x++; }', 
                                    'int f() { return 17; }', o=3), 




]


# =============================================================================
# Mod Smoke Tests
# =============================================================================

class ModSmokeTest:
    def __init__(self, name: str, mod_id: str, source: str, expected: str):
        """source is input C++ code, expected is output C++ code after mod runs"""
        self.name = name
        self.mod_id = mod_id
        self.source = source
        self.expected = expected


def print_header(title: str):
    print("\n" + "=" * 40)
    print(title)
    print("=" * 40)


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


def run_validator_smoke_tests():
    print("Initializing MSVC compiler...")
    compiler = MSVCCompiler()

    validators = {
        0: ASMValidator(compiler, optimization_level=0),
        3: ASMValidator(compiler, optimization_level=3),
    }

    for test in VALIDATOR_SMOKE_TESTS:
        print(f"\nRunning: {test.name}")

        validator = validators[test.optimization_level]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            original_file = temp_path / "original.cpp"
            modified_file = temp_path / "modified.cpp"

            original_file.write_text(test.source)
            modified_file.write_text(test.modified_source)

            original_compiled = compiler.compile_file(
                original_file, optimization_level=test.optimization_level
            )
            modified_compiled = compiler.compile_file(
                modified_file, optimization_level=test.optimization_level
            )

            result = validator.validate(original_compiled, modified_compiled)

            if result:
                print(f"  PASS")
            else:
                print(f"  FAIL - validator returned False (expected True)")
                print(f"  Original ASM:\n{original_compiled.asm_output}")
                print(f"  Modified ASM:\n{modified_compiled.asm_output}")


def run_mod_smoke_tests():
    for test in MOD_SMOKE_TESTS:
        print(f"\nRunning: {test.name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write source file
            source_file = temp_path / "test.cpp"
            source_file.write_text(test.source)

            # Create and run mod
            mod = ModFactory.from_id(test.mod_id)

            # Consume all changes from the generator
            for _ in mod.generate_changes(temp_path):
                pass

            # Read result and compare
            result = source_file.read_text()

            if result == test.expected:
                print(f"  PASS")
            else:
                print(f"  FAIL - output does not match expected")
                print(f"  Expected:\n{repr(test.expected)}")
                print(f"  Got:\n{repr(result)}")


def run_smoke_tests():
    print_header("VALIDATOR SMOKE TESTS")
    run_validator_smoke_tests()

    print_header("MOD SMOKE TESTS")
    run_mod_smoke_tests()


if __name__ == "__main__":
    run_smoke_tests()
