#!/usr/bin/env python
"""Smoke tests for validators and mods."""

import tempfile
from pathlib import Path

from core.compilers.compiler_type import CompilerType
from core.compilers.compiler_factory import get_compiler, set_compiler
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3
from core.mods.mod_factory import ModFactory
from core.repo.repo import Repo
from core.doxygen.symbol_table import SymbolTable


# =============================================================================
# Validator Smoke Tests
# =============================================================================

SCAFFOLD = "\nint main() { return f(); }"


class TestCase:
    """Test case for validators and refactorings.

    Contains source code before and after a transformation, along with the
    optimization level to use for compilation and validation.

    Can be used to test:
    - Validators: Check that validator correctly identifies equivalent code
    - Refactorings: Apply refactoring to source and verify result matches modified_source
    """
    def __init__(self, name: str, source: str, modified_source: str, o: int = 0):
        """paramters source and modified_source are source strings implementing int f()"""
        self.name = name
        self.source = source + SCAFFOLD
        self.modified_source = modified_source + SCAFFOLD
        self.optimization_level = o


VALIDATOR_SMOKE_TESTS = \
[
    # =============================================================================
    # Comments
    # =============================================================================
    TestCase("add_comments",         '                          int f() { return 17; }',
                                     '/* Hardcoded seventeen */ int f() { return 17;  }', o=0),

    # =============================================================================
    # Extract function (two steps)
    # =============================================================================
    TestCase("extract_function",     '                                          int f() { return 4*4 + 1; }',
                                     'inline int squared(int x) { return x*x; } int f() { return squared(4) + 1; }', o=3),
    TestCase("remove_inline",        'inline int squared(int x) { return x*x; } int f() { return squared(4) + 1; }',
                                     'int squared(int x) { return x*x; } int f() { return squared(4) + 1; }', o=0),

    # =============================================================================
    # USE: const
    # =============================================================================
    # const parameter
    TestCase("const_param",          'int len(      char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }',
                                    'int len(const char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }', o=0), # o=Any

    # const method
    TestCase("const_method",         'struct S { int x; int get()       { return x; } }; int f() { S s; s.x = 5; return s.get(); }',
                                    'struct S { int x; int get() const { return x; } }; int f() { S s; s.x = 5; return s.get(); }', o=0), # o=Any

    # =============================================================================
    # USE: override
    # =============================================================================
    TestCase("add_override",         'struct Base { virtual int get() { return 1; } }; struct Derived : Base { virtual int get()          { return 2; } }; int f() { Derived d; Base* b = &d; return b->get(); }',
                                    'struct Base { virtual int get() { return 1; } }; struct Derived : Base { virtual int get() override { return 2; } }; int f() { Derived d; Base* b = &d; return b->get(); }', o=0), # o=Any

    # =============================================================================
    # USE: explicit
    # =============================================================================
    TestCase("add_explicit",         'struct S {          S(int x) : v(x) {} int v; }; int f() { S s(5); return s.v; }',
                                    'struct S { explicit S(int x) : v(x) {} int v; }; int f() { S s(5); return s.v; }', o=0), # o=Any

    # =============================================================================
    # USE: =default
    # =============================================================================
    TestCase("use_default_ctor",     'struct S { int x;     S() { x = 0; }    }; int f() { S s; return s.x; }',
                                    'struct S { int x = 0; S() = default;    }; int f() { S s; return s.x; }', o=0), # o=Any

    # =============================================================================
    # USE: noexcept
    # =============================================================================
    TestCase("add_noexcept",         'int add(int a, int b)          { return a + b; } int f() { return add(2, 3); }',
                                    'int add(int a, int b) noexcept { return a + b; } int f() { return add(2, 3); }', o=0), # o=Any

    # =============================================================================
    # USE: [[nodiscard]]
    # =============================================================================
    TestCase("add_nodiscard",        '              int compute() { return 42; } int f() { return compute(); }',
                                    '[[nodiscard]] int compute() { return 42; } int f() { return compute(); }', o=0), # o=Any

    # =============================================================================
    # USE: [[maybe_unused]]
    # =============================================================================
    TestCase("add_maybe_unused",     'int f() {                  int x = 5; return 10; }',
                                    'int f() { [[maybe_unused]] int x = 5; return 10; }', o=0), # o=Any

    # =============================================================================
    # USE: final class
    # =============================================================================
    TestCase("add_final_class",      'struct Base { virtual int get() { return 1; } }; struct Derived       : Base { int get() override { return 2; } }; int f() { Derived d; return d.get(); }',
                                    'struct Base { virtual int get() { return 1; } }; struct Derived final : Base { int get() override { return 2; } }; int f() { Derived d; return d.get(); }', o=0), # o=Any

    # =============================================================================
    # USE: final method
    # =============================================================================
    TestCase("add_final_method",     'struct Base { virtual int get() { return 1; } }; struct Derived : Base { int get() override       { return 2; } }; int f() { Derived d; return d.get(); }',
                                    'struct Base { virtual int get() { return 1; } }; struct Derived : Base { int get() override final { return 2; } }; int f() { Derived d; return d.get(); }', o=0), # o=Any

    # =============================================================================
    # USE: auto type deduction
    # =============================================================================
    TestCase("use_auto",             'int f() { int  x = 42; return x; }',
                                    'int f() { auto x = 42; return x; }', o=0), # o=Any

    # =============================================================================
    # USE: trailing return type
    # =============================================================================
    TestCase("trailing_return_type", 'int  add(int a, int b)        { return a + b; } int f() { return add(1, 2); }',
                                    'auto add(int a, int b) -> int { return a + b; } int f() { return add(1, 2); }', o=0), # o=Any

    # =============================================================================
    # USE: enum class
    # =============================================================================
    TestCase("use_enum_class",       'enum Color { Red = 0, Green = 1 };       int f() { Color c = Red;        return (int)c; }',
                                    'enum class Color { Red = 0, Green = 1 }; int f() { Color c = Color::Red; return (int)c; }', o=0), # o=Any

    # =============================================================================
    # USE: constexpr variable
    # =============================================================================
    TestCase("use_constexpr_var",    'int f() { const     int x = 10; return x * 2; }',
                                    'int f() { constexpr int x = 10; return x * 2; }', o=0), # o=Any

    # =============================================================================
    # USE: constexpr function
    # =============================================================================
    TestCase("use_constexpr_func",   'inline    int square(int x) { return x * x; } int f() { return square(5); }',
                                    'constexpr int square(int x) { return x * x; } int f() { return square(5); }', o=3),

    # =============================================================================
    # USE: uniform initialization
    # =============================================================================
    TestCase("uniform_init",         'int f() { int x = 5;  return x; }',
                                    'int f() { int x{5};   return x; }', o=0), # o=Any

    # =============================================================================
    # USE: in-class member initializer
    # =============================================================================
    TestCase("in_class_init",        'struct S { int x;      S() : x(10) {} }; int f() { S s; return s.x; }',
                                    'struct S { int x = 10; S() {}         }; int f() { S s; return s.x; }', o=0), # o=Any

    # =============================================================================
    # USE: delegating constructor
    # =============================================================================
    TestCase("inline_ctor",          'struct S { int x;        S() { x = 0; }        S(int v) { x = v; } }; int f() { S s; return s.x; }',
                                    'struct S { int x; inline S() { x = 0; } inline S(int v) { x = v; } }; int f() { S s; return s.x; }', o=0),
    
    TestCase("delegating_ctor",      'struct S { int x; inline S() { x = 0; } inline S(int v) { x = v; } }; int f() { S s; return s.x; }',
                                    'struct S { int x; inline S() : S(0) {}  inline S(int v) { x = v; } }; int f() { S s; return s.x; }', o=3),

    # =============================================================================
    # REMOVE: dead code
    # =============================================================================
    TestCase("remove_dead_code",     'int f() { return 17; int x = 10; x++; }',
                                    'int f() { return 17; }', o=3),

    # ======================================================================<=======
    # REMOVE: commented-out code
    # =============================================================================
    TestCase("remove_comments",      'int f() { /* int old = 5; */ return 17; }',
                                    'int f() { return 17; }', o=0), # o=Any

    # =============================================================================
    # REMOVE: unused parameters
    # =============================================================================
    TestCase("remove_unused_param",  'inline int add(int a, int b, int unused) { return a + b; } int f() { return add(2, 3, 99); }',
                                    'inline int add(int a, int b            ) { return a + b; } int f() { return add(2, 3    ); }', o=3),

    # =============================================================================
    # REMOVE: unused variables
    # =============================================================================
    TestCase("remove_unused_var",    'int f() { int unused = 42; return 10; }',
                                    'int f() {                  return 10; }', o=3),

    # =============================================================================
    # REMOVE: unused variables
    # =============================================================================
    TestCase("remove_unused_var",    'int f() { int unused = 42; return 10; }',
                                    'int f() {                  return 10; }', o=3),

    # =============================================================================
    # REMOVE: void argument list
    # =============================================================================
    TestCase("remove_void_args",     'int f(void) { return 42; }',
                                    'int f()     { return 42; }', o=0), # o=Any

    # =============================================================================
    # REMOVE: redundant semicolons
    # =============================================================================
    TestCase("remove_extra_semicolon", 'int f() { return 42;; }',
                                      'int f() { return 42; }', o=0), # o=Any

    # =============================================================================
    # REMOVE: redundant this->
    # =============================================================================
    TestCase("remove_this_pointer",  'struct S { int x; int get() { return this->x; } }; int f() { S s; s.x = 5; return s.get(); }',
                                    'struct S { int x; int get() { return x;       } }; int f() { S s; s.x = 5; return s.get(); }', o=0), # o=Any

    # =============================================================================
    # REPLACE: NULL with nullptr
    # =============================================================================
    TestCase("null_to_nullptr",      '#define NULL 0\nint f() { int* p = NULL;    return p ? 1 : 0; }',
                                    '                int f() { int* p = nullptr; return p ? 1 : 0; }', o=0), # o=Any

    # =============================================================================
    # REPLACE: 0/1 bool with true/false
    # =============================================================================
    TestCase("bool_literals",        'int f() { bool b = 1;    return b ? 10 : 20; }',
                                    'int f() { bool b = true; return b ? 10 : 20; }', o=0), # o=Any

    # =============================================================================
    # REPLACE: static_cast
    # =============================================================================
    TestCase("use_static_cast",      'int f() { double d = 3.14; return (int)d; }',
                                    'int f() { double d = 3.14; return static_cast<int>(d); }', o=0), # o=Any

    # =============================================================================
    # REPLACE: typedef with using
    # =============================================================================
    TestCase("typedef_to_using",     'typedef int  MyInt; int f() { MyInt x = 5; return x; }',
                                    'using MyInt = int;  int f() { MyInt x = 5; return x; }', o=0), # o=Any

    # =============================================================================
    # REPLACE: header guards with #pragma once
    # =============================================================================
    TestCase("pragma_once",          '#ifndef HEADER_H\n#define HEADER_H\nint f() { return 42; }\n#endif',
                                    '#pragma once\nint f() { return 42; }', o=0), # o=Any

    # =============================================================================
    # REPLACE: throw() with noexcept
    # =============================================================================
    TestCase("throw_to_noexcept",    'int add(int a, int b) throw()   { return a + b; } int f() { return add(2, 3); }',
                                    'int add(int a, int b) noexcept  { return a + b; } int f() { return add(2, 3); }', o=0), # o=Any

    # =============================================================================
    # REFACTOR: declare variables where assigned
    # =============================================================================
    TestCase("declare_at_assign",    'int f() { int x; x = 10; return x; }',
                                    'int f() { int x = 10;    return x; }', o=0), # o=Any

    # =============================================================================
    # REFACTOR: extract named constant
    # =============================================================================
    TestCase("extract_constant",     'int f() { return 3 * 3 * 3.14159; }',
                                    'int f() { constexpr double PI = 3.14159; return 3 * 3 * PI; }', o=3),

    # =============================================================================
    # REFACTOR: reduce nesting (early return)
    # =============================================================================
    TestCase("early_return",         'int f() { int x = 5; if (x > 0) { return x * 2; } else { return 0; } }',
                                    'int f() { int x = 5; if (x <= 0) return 0; return x * 2; }', o=3),

    # =============================================================================
    # REFACTOR: modernize for loop (range-based)
    # =============================================================================
    TestCase("range_based_for",      'int f() { const int arr[5] = {1, 2, 3, 4, 5}; int sum = 0; for (const int* p = arr; p != arr + 5; ++p) { sum += *p; } return sum; }',
                                    'int f() { const int arr[5] = {1, 2, 3, 4, 5}; int sum = 0; for (const int& val : arr) { sum += val; } return sum; }', o=3),

    # =============================================================================
    # REFACTOR: replace pointer with reference (parameter)
    # =============================================================================
    TestCase("pointer_to_reference", 'int modify(int* p) { return *p + 1; } int f() { int x = 5; return modify(&x); }',
                                    'int modify(int& p) { return p + 1; }  int f() { int x = 5; return modify(x); }', o=0),

    # =============================================================================
    # OWNERSHIP/LIFETIME: add owner<T> and non_owner<T>:
    # All pointer members and parameters should be marked as owning the memory the point to
    # or not owning the memory. Only the pointers where it is not clear should be left as 
    # raw, unmarked pointers. This way, we can better reason about code during refactoring.
    # The owner/non_owner syntax will be removed at the end of refactoring.
    # The ValTests define owner/non_owner for simplicity, but this should be included from a header
    # =============================================================================
    TestCase("add_owner<T>",        '           int* get(int value) {            int* p = new int; *p = value; return p; } int f() {            int *p = get (17); int i = *p; delete p; return i; }',
                                   'namespace gsl { template <typename T> using owner = T*; }\n' +\
                                   'gsl::owner<int> get(int value) { gsl::owner<int> p = new int; *p = value; return p; } int f() { gsl::owner<int> p = get (17); int i = *p; delete p; return i; }', o=0),
    
    TestCase("add_non_owner<T>",    'int get(               int* p) { return *p; } int f() { int x = 42; return get(&x); }',
                                   'namespace gsl { template <typename T> using non_owner = T*; }\n' +\
                                   'int get(gsl::non_owner<int> p) { return *p; } int f() { int x = 42; return get(&x); }', o=0),

    # =============================================================================
    # REFACTOR: simplify boolean expressions
    # =============================================================================
    TestCase("simplify_bool_comparison", 'int f() { bool b = true; if (b == true) { return 10; } return 0; }',
                                         'int f() { bool b = true; if (b)        { return 10; } return 0; }', o=3),

    TestCase("simplify_double_negation",  'int f() { bool b = true; return !!b ? 5 : 0; }',
                                         'int f() { bool b = true; return b   ? 5 : 0; }', o=3),

    # =============================================================================
    # REPLACE: C-style casts with C++ casts (safer, more searchable)
    # =============================================================================
    TestCase("c_cast_to_static_cast",    'int f() { double d = 3.14; int x = (int)d; return x; }',
                                        'int f() { double d = 3.14; int x = static_cast<int>(d); return x; }', o=0),

    TestCase("c_cast_to_const_cast",     'int modify(int* p) { return *p + 1; } int f() { const int x = 5; return modify((int*)&x); }',
                                        'int modify(int* p) { return *p + 1; } int f() { const int x = 5; return modify(const_cast<int*>(&x)); }', o=0),

    # =============================================================================
    # REPLACE: #define constants with constexpr (type-safe, debuggable)
    # =============================================================================
    TestCase("define_to_constexpr",      '#define MAX_SIZE 100\nint f() { int arr[MAX_SIZE]; arr[0] = 5; return arr[0]; }',
                                        'constexpr int MAX_SIZE = 100; int f() { int arr[MAX_SIZE]; arr[0] = 5; return arr[0]; }', o=0),

    TestCase("define_func_to_constexpr", '#define SQUARE(x) ((x) * (x))\nint f() { return SQUARE(5); }',
                                        'constexpr int square(int x) { return x * x; } int f() { return square(5); }', o=3),

    # =============================================================================
    # USE: [[fallthrough]] attribute (documents intent, prevents warnings)
    # =============================================================================
    TestCase("add_fallthrough",          'int f() { int x = 2; switch(x) { case 1: x += 1; case 2: x += 2; break; default: x = 0; } return x; }',
                                        'int f() { int x = 2; switch(x) { case 1: x += 1; [[fallthrough]]; case 2: x += 2; break; default: x = 0; } return x; }', o=0),

    # =============================================================================
    # REPLACE: typedef with using (template-friendly, more readable)
    # =============================================================================
    TestCase("typedef_func_ptr_to_using", 'typedef int (*FuncPtr)(int); int apply(FuncPtr f, int x) { return f(x); } int double_it(int x) { return x * 2; } int f() { return apply(double_it, 5); }',
                                         'using FuncPtr = int (*)(int); int apply(FuncPtr f, int x) { return f(x); } int double_it(int x) { return x * 2; } int f() { return apply(double_it, 5); }', o=3),

    # =============================================================================
    # REPLACE: multiple returns with single return variable (NRVO-friendly)
    # =============================================================================
    TestCase("consolidate_returns",      'int f() { int x = 5; if (x > 0) { return x * 2; } else { return 0; } }',
                                        'int f() { int x = 5; int result; if (x > 0) { result = x * 2; } else { result = 0; } return result; }', o=3),

    # =============================================================================
    # REPLACE: size_t with more specific types for better overflow detection
    # =============================================================================
    TestCase("explicit_integer_width",   'int f() { unsigned int count = 100; return (int)count; }',
                                        '#include <cstdint>\nint f() { uint32_t count = 100; return (int)count; }', o=0),

    # =============================================================================
    # USE: =delete for uncopyable classes (clearer than private declarations)
    # =============================================================================
    TestCase("private_to_delete",        'struct S { private: S(const S&); S& operator=(const S&); public: int x; S() : x(0) {} int get() { return x; } }; int f() { S s; return s.get(); }',
                                        'struct S { S(const S&) = delete; S& operator=(const S&) = delete; int x; S() : x(0) {} int get() { return x; } }; int f() { S s; return s.get(); }', o=0),

    # =============================================================================
    # REPLACE: char* for string literals with const char* (const correctness)
    # =============================================================================
    TestCase("string_literal_const",     'int len(char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len((char*)"test"); }',
                                        'int len(const char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len("test"); }', o=0),

    # =============================================================================
    # USE: inline namespace for versioning (ABI compatibility)
    # =============================================================================
    TestCase("add_inline_namespace",     'namespace lib { struct S { int x; }; } int f() { lib::S s; s.x = 5; return s.x; }',
                                        'namespace lib { inline namespace v1 { struct S { int x; }; } } int f() { lib::S s; s.x = 5; return s.x; }', o=0),

    # =============================================================================
    # REPLACE: manual RAII with structured bindings for clarity
    # =============================================================================
    TestCase("extract_pair_values",      '#include <utility>\nstd::pair<int,int> get_pair() { return std::make_pair(3, 4); } int f() { std::pair<int,int> p = get_pair(); return p.first + p.second; }',
                                        '#include <utility>\nstd::pair<int,int> get_pair() { return std::make_pair(3, 4); } int f() { auto [x, y] = get_pair(); return x + y; }', o=3),

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
        "int f() { return 1; }",
    ),
    ModSmokeTest(
        "remove_inline_multiple",
        "remove_inline",
        "inline int f() { return 1; }\ninline int g() { return 2; }",
        "int f() { return 1; }\nint g() { return 2; }",
    ),
    # NOTE: ms_macro_replacement mod is currently stubbed out - test disabled
    # ModSmokeTest(
    #     "ms_macro_replacement_basic",
    #     "ms_macro_replacement",
    #     "__forceinline int f() { return 1; }",
    #     '#include "levelup_msvc_compat.h"\nLEVELUP_FORCEINLINE int f() { return 1; }',
    # ),
]


def run_validator_smoke_tests():
    for compiler_type in CompilerType:
        print(f"\n{'=' * 60}")
        print(f"Testing with compiler: {compiler_type.value}")
        print('=' * 60)

        # Set compiler type
        set_compiler(compiler_type.value)

        compiler = get_compiler()
        print(f"Initialized compiler: {compiler.get_name()}")

        validators = {
            0: ASMValidatorO0(),
            3: ASMValidatorO3(),
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

            # Create minimal repo and symbol table for testing
            # Note: Using temp_path as both repos_folder and repo location for simplicity
            repo = Repo(url="file:///test-repo", repos_folder=temp_path.parent)
            repo.repo_path = temp_path  # Override to use temp directory directly
            symbols = SymbolTable(repo)  # Empty symbol table is fine for simple tests

            # Create and run mod
            mod = ModFactory.from_id(test.mod_id)

            # Apply all refactorings from the mod
            for refactoring, params in mod.generate_refactorings(repo, symbols):
                # Apply the refactoring (modifies file in-place)
                refactoring.apply(params)

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
