#!/usr/bin/env python
"""Test script to identify issues when switching to Clang compiler."""

import tempfile
from pathlib import Path

# Temporarily modify config to use Clang
import config
original_compiler = config.COMPILER_TYPE
config.COMPILER_TYPE = config.CompilerType.CLANG

try:
    from core.compilers.compiler_factory import get_compiler, reset_compiler
    from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3

    # Reset compiler to pick up new config
    reset_compiler()

    print("=" * 60)
    print("TESTING CLANG COMPILER")
    print("=" * 60)

    # Test 1: Can we create a Clang compiler instance?
    print("\n[Test 1] Creating Clang compiler instance...")
    try:
        compiler = get_compiler()
        print(f"✓ Compiler created: {compiler.get_name()}")
        print(f"  Compiler ID: {compiler.get_id()}")
        print(f"  Clang path: {compiler.clang_path}")
    except Exception as e:
        print(f"✗ Failed to create compiler: {e}")
        raise

    # Test 2: Can we compile a simple C++ file?
    print("\n[Test 2] Compiling simple C++ file...")
    test_code = """
int f() { return 17; }
int main() { return f(); }
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "test.cpp"
        source_file.write_text(test_code)

        try:
            compiled = compiler.compile_file(source_file, optimization_level=0)
            print(f"✓ Compilation successful")
            print(f"  ASM output length: {len(compiled.asm_output) if compiled.asm_output else 0} chars")
            if compiled.asm_output:
                print(f"  First 200 chars of ASM:\n{compiled.asm_output[:200]}")
        except Exception as e:
            print(f"✗ Compilation failed: {e}")
            raise

    # Test 3: Can the ASM validator parse Clang's assembly output?
    print("\n[Test 3] Testing ASM validator with Clang output...")
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

        try:
            original_compiled = compiler.compile_file(original_file, optimization_level=0)
            modified_compiled = compiler.compile_file(modified_file, optimization_level=0)

            print(f"✓ Both files compiled successfully")

            validator = ASMValidatorO0()
            result = validator.validate(original_compiled, modified_compiled)

            print(f"  Validation result: {'PASS' if result else 'FAIL'}")

            if not result:
                print("\n  === Original ASM ===")
                print(original_compiled.asm_output)
                print("\n  === Modified ASM ===")
                print(modified_compiled.asm_output)

        except Exception as e:
            print(f"✗ Validator test failed: {e}")
            import traceback
            traceback.print_exc()

    # Test 4: Check ASM format differences
    print("\n[Test 4] Analyzing Clang ASM format...")
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

        compiled = compiler.compile_file(source_file, optimization_level=0)

        print(f"  Full ASM output:")
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
        import re
        for pattern, name in msvc_patterns:
            matches = re.findall(pattern, compiled.asm_output)
            if matches:
                print(f"    ✓ Found {len(matches)} {name}: {matches[:3]}")
            else:
                print(f"    ✗ No {name} found")

finally:
    # Restore original compiler setting
    config.COMPILER_TYPE = original_compiler
    reset_compiler()
    print("\n" + "=" * 60)
    print("Test complete - compiler config restored")
    print("=" * 60)
