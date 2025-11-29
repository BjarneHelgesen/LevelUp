#!/usr/bin/env python
"""Smoke tests for mods and chained refactorings."""

import argparse
import sys
import tempfile
from pathlib import Path

import git

# Add parent directory to path to support running from core/ directory
_file_path = Path(__file__).resolve()
_core_path = _file_path.parent
_project_root = _core_path.parent
sys.path.insert(0, str(_project_root))

from core.compilers.compiler_type import CompilerType
from core.compilers.compiler_factory import get_compiler, set_compiler
from core.validators.validator_id import ValidatorId
from core.mods.mod_factory import ModFactory
from core.repo.repo import Repo
from core.parsers.symbol_table import SymbolTable
from core.parsers.symbol import Symbol, SymbolKind
from core.refactorings.remove_function_qualifier import RemoveFunctionQualifier
from core.refactorings.add_function_qualifier import AddFunctionQualifier
from core.refactorings.qualifier_type import QualifierType

# Import validator smoke tests from validators package
from core.validators.smoketest import run_validator_smoke_tests


def create_mock_symbol(name: str, qualified_name: str, file_path: Path, line_number: int,
                       prototype: str = "", kind: str = SymbolKind.FUNCTION) -> Symbol:
    """Create a mock Symbol object for testing."""
    symbol = Symbol(kind=kind)
    symbol.name = name
    symbol.qualified_name = qualified_name
    symbol.file_path = str(file_path)
    symbol.line_start = line_number
    symbol.line_end = line_number
    symbol.prototype = prototype
    return symbol


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
        "int f() { return 1; }",
    ),
    ModSmokeTest(
        "remove_inline_multiple",
        "remove_inline",
        "inline int f() { return 1; }\ninline int g() { return 2; }",
        "int f() { return 1; }\nint g() { return 2; }",
    ),
]



def run_mod_smoke_tests():
    total_passed = 0
    total_failed = 0

    for test in MOD_SMOKE_TESTS:
        print(f"\nRunning: {test.name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write source file
            source_file = temp_path / "test.cpp"
            source_file.write_text(test.source)

            # Create minimal repo and symbol table for testing
            # Note: Using temp_path as both repos_folder and repo location for simplicity
            repo = Repo(url="file:///test-repo", repos_folder=temp_path.parent)
            repo.repo_path = temp_path  # Override to use temp directory directly
            symbols = SymbolTable(repo)  # Empty symbol table is fine for simple tests

            # Create and run mod
            mod = ModFactory.from_id(test.mod_id)

            # Apply all refactorings from the mod
            for refactoring, *args in mod.generate_refactorings(repo, symbols):
                # Apply the refactoring (modifies file in-place)
                refactoring.apply(*args)

            # Read result and compare
            result = source_file.read_text()

            if result == test.expected:
                print(f"  PASS")
                total_passed += 1
            else:
                print(f"  FAIL - output does not match expected")
                print(f"  Expected:\n{repr(test.expected)}")
                print(f"  Got:\n{repr(result)}")
                total_failed += 1

    return total_passed, total_failed


def run_chained_refactoring_tests(compilers):
    """Run chained refactoring tests showing progressive modernization."""
    print("\n" + "=" * 80)
    print("CHAINED REFACTORING TESTS")
    print("=" * 80)

    import subprocess
    import gc
    import platform

    total_passed = 0
    total_failed = 0

    for compiler_type in compilers:
        print(f"\n{'=' * 60}")
        print(f"Testing with compiler: {compiler_type.value}")
        print('=' * 60)

        # Set compiler type
        set_compiler(compiler_type.value)
        compiler = get_compiler()
        print(f"Initialized compiler: {compiler.get_name()}")

        # On Windows, manually manage temp directory to avoid file handle issues
        temp_dir_obj = tempfile.TemporaryDirectory()
        temp_dir = temp_dir_obj.name
        try:
            temp_path = Path(temp_dir)
            source_file = temp_path / "modernize_me.cpp"

            # Create C++ file with various modernization opportunities
            # This file will be progressively modernized through chained refactorings
            initial_source = """// Legacy C++ code needing modernization

inline int squared(int x) {
    return x * x;
}

inline int cubed(int x) {
    return x * x * x;
}

inline int add(int a, int b) {
    return a + b;
}

int compute() {
    return 42;
}

struct Point {
    int x;
    int y;
    Point(int x_val, int y_val) : x(x_val), y(y_val) {}
    int getX() { return x; }
    int getY() { return y; }
};

struct Base {
    virtual int compute(int x);
    virtual int process(int y);
    virtual int calculate();
};

struct Derived : Base {
    virtual int compute(int x);
    virtual int process(int y);
    virtual int calculate();
};

int Base::compute(int x) {
    return squared(x);
}

int Base::process(int y) {
    return y + 1;
}

int Base::calculate() {
    return 10;
}

int Derived::compute(int x) {
    return cubed(x);
}

int Derived::process(int y) {
    return y * 2;
}

int Derived::calculate() {
    return 20;
}

int main() {
    Point p(3, 4);
    Derived d;
    Base* b = &d;
    return b->compute(5) + b->process(3) + p.getX() + add(1, 2) + compute();
}
"""

            source_file.write_text(initial_source)

            # Initialize git repository using GitPython (faster than subprocess)
            test_repo = git.Repo.init(temp_path)
            test_repo.index.add('*')
            # Configure git user for commit
            with test_repo.config_writer() as config:
                config.set_value('user', 'name', 'LevelUp Test')
                config.set_value('user', 'email', 'test@levelup.com')
            test_repo.index.commit('Initial legacy code')
            test_repo.close()  # Close to release file handles
            del test_repo  # Delete reference to help GC

            # Create repo
            repo = Repo(url="file:///test-chained-refactoring", repos_folder=temp_path.parent)
            repo.repo_path = temp_path

            # Run Doxygen to extract symbols
            print("\nGenerating Doxygen symbols...")
            symbols = SymbolTable(repo)
            try:
                repo.generate_doxygen()
                symbols.load_from_doxygen()
                print(f"  Doxygen generated {len(symbols.get_all_symbols())} symbols")
            except Exception as e:
                print(f"  WARNING: Doxygen failed ({e}), using mock symbols")

            # Ensure any GitPython handles are released before temp cleanup
            import gc
            gc.collect()  # Force garbage collection to release any lingering handles

            # Define chain of refactorings that build on each other progressively
            # Each refactoring is tested with O0 validation, building cumulative modernization
            # Tests mimic validator smoke tests but chain together on a single file
            refactoring_chain = [
                # Test 1: Remove inline qualifiers (mimics remove_inline validator test)
                {
                    'name': 'Remove inline from squared()',
                    'refactoring_class': RemoveFunctionQualifier,
                    'symbol_lookup': 'squared',
                    'qualifier': QualifierType.INLINE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Remove inline from cubed()',
                    'refactoring_class': RemoveFunctionQualifier,
                    'symbol_lookup': 'cubed',
                    'qualifier': QualifierType.INLINE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Remove inline from add()',
                    'refactoring_class': RemoveFunctionQualifier,
                    'symbol_lookup': 'add',
                    'qualifier': QualifierType.INLINE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                # Test 2: Add override qualifiers (mimics add_override validator test)
                {
                    'name': 'Add override to Derived::compute()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Derived::compute',
                    'qualifier': QualifierType.OVERRIDE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Add override to Derived::process()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Derived::process',
                    'qualifier': QualifierType.OVERRIDE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Add override to Derived::calculate()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Derived::calculate',
                    'qualifier': QualifierType.OVERRIDE,
                    'validator_id': ValidatorId.ASM_O0,
                },
                # Test 3: Add final to methods (mimics add_final_method validator test)
                {
                    'name': 'Add final to Derived::calculate()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Derived::calculate',
                    'qualifier': QualifierType.FINAL,
                    'validator_id': ValidatorId.ASM_O0,
                },
                # Test 4: Add const qualifiers to methods (mimics const_method validator test)
                {
                    'name': 'Add const to Point::getX()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Point::getX',
                    'qualifier': QualifierType.CONST,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Add const to Point::getY()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'Point::getY',
                    'qualifier': QualifierType.CONST,
                    'validator_id': ValidatorId.ASM_O0,
                },
                # Test 5: Add noexcept to free functions (mimics add_noexcept validator test)
                {
                    'name': 'Add noexcept to squared()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'squared',
                    'qualifier': QualifierType.NOEXCEPT,
                    'validator_id': ValidatorId.ASM_O0,
                },
                {
                    'name': 'Add noexcept to cubed()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'cubed',
                    'qualifier': QualifierType.NOEXCEPT,
                    'validator_id': ValidatorId.ASM_O0,
                },
                # Test 6: Add [[nodiscard]] attribute (mimics add_nodiscard validator test)
                {
                    'name': 'Add [[nodiscard]] to compute()',
                    'refactoring_class': AddFunctionQualifier,
                    'symbol_lookup': 'compute',
                    'qualifier': QualifierType.NODISCARD,
                    'validator_id': ValidatorId.ASM_O0,
                },
            ]

            print("\n" + "-" * 60)
            print("Progressive Modernization Chain")
            print("-" * 60)

            for step_num, step in enumerate(refactoring_chain, start=1):
                print(f"\nStep {step_num}: {step['name']}")

                # Store content before refactoring
                content_before = source_file.read_text()

                # Find symbol (from Doxygen or create mock)
                symbol_name = step['symbol_lookup']
                symbol = symbols.get_symbol(symbol_name)

                if symbol is None:
                    # Create mock symbol if Doxygen didn't find it
                    print(f"  Creating mock symbol for '{symbol_name}'")
                    # Parse file to find the symbol
                    lines = content_before.split('\n')
                    function_name = symbol_name.split('::')[-1]
                    class_name = symbol_name.split('::')[0] if '::' in symbol_name else None

                    # Look for function declaration/definition
                    # For qualified names (Class::method), find the class context first
                    in_target_class = False
                    class_depth = 0

                    for line_num, line in enumerate(lines, start=1):
                        stripped = line.strip()

                        # Track class context for qualified names
                        if class_name:
                            if f'struct {class_name}' in stripped or f'class {class_name}' in stripped:
                                in_target_class = True
                                class_depth = 0
                            if in_target_class:
                                class_depth += stripped.count('{') - stripped.count('}')
                                if class_depth < 0:
                                    in_target_class = False

                        # Check if this line contains the function name
                        if function_name in line:
                            # For qualified names, check if we're in the right class or it's a definition
                            if class_name:
                                # Either in the class declaration or it's an out-of-line definition
                                is_definition = f'{class_name}::{function_name}' in stripped
                                if not (in_target_class or is_definition):
                                    continue

                            # Check if it looks like a function declaration or definition
                            if (('(' in stripped and function_name in stripped) or
                                ('virtual' in stripped and function_name in stripped) or
                                (f'{function_name}(' in stripped)):
                                symbol = create_mock_symbol(
                                    name=function_name,
                                    qualified_name=symbol_name,
                                    file_path=source_file,
                                    line_number=line_num,
                                    prototype=stripped
                                )
                                break

                if symbol is None:
                    print(f"  FAIL - Could not find symbol '{symbol_name}'")
                    total_failed += 1
                    continue

                # Get validator and optimization level
                from core.validators.validator_factory import ValidatorFactory
                validator = ValidatorFactory.from_id(step['validator_id'])
                optimization_level = validator.get_optimization_level()

                # Compile original
                try:
                    original_compiled = compiler.compile_file(
                        source_file, optimization_level=optimization_level
                    )
                except Exception as e:
                    print(f"  FAIL - Original compilation failed: {e}")
                    total_failed += 1
                    continue

                # Apply refactoring
                refactoring = step['refactoring_class'](repo)
                git_commit = refactoring.apply(symbol, step['qualifier'])

                if git_commit is None:
                    print(f"  FAIL - Refactoring returned None (not applicable)")
                    total_failed += 1
                    continue

                # Check that file was modified
                content_after = source_file.read_text()
                if content_before == content_after:
                    print(f"  FAIL - No changes made to file (refactoring must make changes)")
                    total_failed += 1
                    continue

                print(f"  File modified: {len(content_after)} bytes (was {len(content_before)} bytes)")

                # Compile modified
                try:
                    modified_compiled = compiler.compile_file(
                        source_file, optimization_level=optimization_level
                    )
                except Exception as e:
                    print(f"  FAIL - Modified compilation failed: {e}")
                    # Rollback for next test
                    source_file.write_text(content_before)
                    total_failed += 1
                    continue

                # Validate
                is_valid = validator.validate(original_compiled, modified_compiled)

                if is_valid:
                    print(f"  PASS - Validation successful")
                    total_passed += 1
                    # Keep the change (commit already created by refactoring)
                else:
                    print(f"  FAIL - Validation failed")
                    total_failed += 1
                    # Rollback
                    source_file.write_text(content_before)

            # Print final modernized code
            print("\n" + "-" * 60)
            print("Final modernized code:")
            print("-" * 60)
            print(source_file.read_text())
        finally:
            # Cleanup with retry on Windows
            gc.collect()  # Release any lingering handles
            if platform.system() == 'Windows':
                import time
                # Give Windows time to release file handles
                time.sleep(0.5)
            try:
                temp_dir_obj.cleanup()
            except PermissionError:
                # On Windows, if cleanup fails, warn but don't crash
                print(f"\n  WARNING: Could not clean up temp directory: {temp_dir}")
                pass

    return total_passed, total_failed


def get_default_compiler():
    """Get the default compiler """
    return CompilerType.CLANG


def run_smoke_tests(compilers):
    print_header("VALIDATOR SMOKE TESTS")
    validator_passed, validator_failed = run_validator_smoke_tests(compilers)

    print_header("MOD SMOKE TESTS")
    mod_passed, mod_failed = run_mod_smoke_tests()

    print_header("CHAINED REFACTORING TESTS")
    chain_passed, chain_failed = run_chained_refactoring_tests(compilers)

    # Print final summary
    total_passed = validator_passed + mod_passed + chain_passed
    total_failed = validator_failed + mod_failed + chain_failed
    total_tests = total_passed + total_failed

    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Validator tests:           {validator_passed:3d} passed, {validator_failed:3d} failed")
    print(f"Mod tests:                 {mod_passed:3d} passed, {mod_failed:3d} failed")
    print(f"Chained refactoring tests: {chain_passed:3d} passed, {chain_failed:3d} failed")
    print("-" * 60)
    print(f"TOTAL:                     {total_passed:3d} passed, {total_failed:3d} failed ({total_tests} total)")
    print("=" * 60)

    if total_failed == 0:
        print("\nAll tests PASSED!")
    else:
        print(f"\n{total_failed} test(s) FAILED")


if __name__ == "__main__":
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
