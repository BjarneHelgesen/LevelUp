#!/usr/bin/env python
"""Test script to identify issues when switching to Clang compiler."""

import tempfile
import re
import pytest
from pathlib import Path

import config
from core.compilers.compiler_factory import get_compiler, reset_compiler
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3


@pytest.fixture
def clang_compiler():
    original_compiler = config.COMPILER_TYPE
    config.COMPILER_TYPE = config.CompilerType.CLANG
    reset_compiler()

    yield get_compiler()

    config.COMPILER_TYPE = original_compiler
    reset_compiler()


def test_create_clang_compiler(clang_compiler):
    print(f"\n✓ Compiler created: {clang_compiler.get_name()}")
    print(f"  Compiler ID: {clang_compiler.get_id()}")
    print(f"  Clang path: {clang_compiler.clang_path}")

    assert clang_compiler.get_id() == "clang"


def test_compile_simple_cpp_file(clang_compiler):
    test_code = """
int f() { return 17; }
int main() { return f(); }
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "test.cpp"
        source_file.write_text(test_code)

        compiled = clang_compiler.compile_file(source_file, optimization_level=0)

        print(f"\n✓ Compilation successful")
        print(f"  ASM output length: {len(compiled.asm_output) if compiled.asm_output else 0} chars")
        if compiled.asm_output:
            print(f"  First 200 chars of ASM:\n{compiled.asm_output[:200]}")

        assert compiled.asm_output is not None
        assert len(compiled.asm_output) > 0


def test_asm_validator_with_clang(clang_compiler):
    test_original = """
inline int squared(int x) { return x*x; }
int f() { return squared(4) + 1; }
int main() { return f(); }
"""

    test_modified = """
int squared(int x) { return x*x; }
int f() { return squared(4) + 1; }
int main() { return f(); }
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original_file = temp_path / "original.cpp"
        modified_file = temp_path / "modified.cpp"

        original_file.write_text(test_original)
        modified_file.write_text(test_modified)

        original_compiled = clang_compiler.compile_file(original_file, optimization_level=0)
        modified_compiled = clang_compiler.compile_file(modified_file, optimization_level=0)

        print(f"\n✓ Both files compiled successfully")

        validator = ASMValidatorO0()
        result = validator.validate(original_compiled, modified_compiled)

        print(f"  Validation result: {'PASS' if result else 'FAIL'}")

        if not result:
            print("\n  === Original ASM ===")
            print(original_compiled.asm_output)
            print("\n  === Modified ASM ===")
            print(modified_compiled.asm_output)

        assert result, "Validator should accept semantically identical code"


def test_clang_asm_format(clang_compiler):
    simple_code = """
int add(int a, int b) {
    return a + b;
}
int main() { return add(2, 3); }
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "test.cpp"
        source_file.write_text(simple_code)

        compiled = clang_compiler.compile_file(source_file, optimization_level=0)

        print(f"\n  Full ASM output:")
        print("  " + "=" * 58)
        for i, line in enumerate(compiled.asm_output.split('\n')[:50], 1):
            print(f"  {i:3d}: {line}")
        print("  " + "=" * 58)

        # Check for MSVC-specific patterns that might not exist in Clang ASM
        msvc_patterns = [
            (r'PROC', 'PROC markers'),
            (r'ENDP', 'ENDP markers'),
            (r'; COMDAT', 'COMDAT markers'),
            (r'\?\w+@@', 'MSVC name mangling'),
            (r'\$LN\d+', 'MSVC local labels'),
            (r'\$SG\d+', 'MSVC string/data labels'),
        ]

        print("\n  Pattern analysis:")
        for pattern, name in msvc_patterns:
            matches = re.findall(pattern, compiled.asm_output)
            if matches:
                print(f"    ✓ Found {len(matches)} {name}: {matches[:3]}")
            else:
                print(f"    ✗ No {name} found")

        assert compiled.asm_output is not None
