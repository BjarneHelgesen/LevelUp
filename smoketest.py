#!/usr/bin/env python
"""Smoke tests for validators and mods."""

import argparse
import tempfile
from pathlib import Path

import git

from core.compilers.compiler_type import CompilerType
from core.compilers.compiler_factory import get_compiler, set_compiler
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3
from core.validators.validator_id import ValidatorId
from core.mods.mod_factory import ModFactory
from core.repo.repo import Repo
from core.doxygen.symbol_table import SymbolTable
from core.doxygen.symbol import Symbol, SymbolKind
from core.refactorings.remove_function_qualifier import RemoveFunctionQualifier
from core.refactorings.add_function_qualifier import AddFunctionQualifier
from core.refactorings.qualifier_type import QualifierType


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
# Validator Smoke Tests
# =============================================================================

SCAFFOLD = "\nint main() { return f(); }"


class TestCase:
    """Test case for validators.

    Contains source code before and after a transformation, along with the
    optimization level to use for compilation and validation.
    """
    def __init__(
        self,
        name: str,
        source: str,
        modified_source: str,
        o: int = 0,
        additional_flags: str = None,
        compiler_flags: str = None
    ):
        """
        Args:
            name: Test case name
            source: Source implementing int f() before transformation
            modified_source: Source after transformation
            o: Optimization level for validation
            additional_flags: Compiler flags for original source (e.g., preprocessor defines)
            modified_additional_flags: Compiler flags for modified source (defaults to additional_flags)
        """
        self.name = name
        self.source = source + SCAFFOLD
        self.modified_source = modified_source + SCAFFOLD
        self.optimization_level = o
        self.additional_flags = additional_flags
        self.modified_additional_flags = compiler_flags if compiler_flags is not None else additional_flags


SMOKE_TESTS = \
[
    # =============================================================================
    # Comments
    # =============================================================================
    TestCase("document_function",    '                           int f() { return 17; }',
                                     '/* Returns seventeen */ \n int f() { return 17;  }', o=0),  

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
    TestCase("const_param",         'int len(      char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }',
                                    'int len(const char *buf) { int i = 0; for (const char* p = buf; *p; p++, i++) {} return i;} int f() { return len("asdf"); }', o=0),

    # const method
    TestCase("const_method",        'struct S { int x; int get()       { return x; } }; int f() { S s; s.x = 5; return s.get(); }',
                                    'struct S { int x; int get() const { return x; } }; int f() { S s; s.x = 5; return s.get(); }', o=0),

    # =============================================================================
    # USE: override
    # =============================================================================
    TestCase("add_override",         '''struct Base {
    virtual int get();
};
struct Derived : Base {
    virtual int get();
};
int Base::get() { return 1; }
int Derived::get() { return 2; }
int f() {
    Derived d;
    Base* b = &d;
    return b->get();
}''',
                                    '''struct Base {
    virtual int get();
};
struct Derived : Base {
    virtual int get() override;
};
int Base::get() { return 1; }
int Derived::get() { return 2; }
int f() {
    Derived d;
    Base* b = &d;
    return b->get();
}''', o=0),

    # =============================================================================
    # USE: explicit
    # =============================================================================
    TestCase("add_explicit",        'struct S {          S(int x) : v(x) {} int v; }; int f() { S s(5); return s.v; }',
                                    'struct S { explicit S(int x) : v(x) {} int v; }; int f() { S s(5); return s.v; }', o=0),

    # =============================================================================
    # USE: =default
    # =============================================================================
    TestCase("use_default_ctor",    'struct S { int x;     S() { x = 0; }    }; int f() { S s; return s.x; }',
                                    'struct S { int x = 0; S() = default;    }; int f() { S s; return s.x; }', o=0),

    # =============================================================================
    # USE: noexcept
    # =============================================================================
    TestCase("add_noexcept",        'int add(int a, int b)          { return a + b; } int f() { return add(2, 3); }',
                                    'int add(int a, int b) noexcept { return a + b; } int f() { return add(2, 3); }', o=0),

    # =============================================================================
    # USE: final class
    # =============================================================================
    TestCase("add_final_class",     'struct Base { virtual int get() { return 1; } }; struct Derived       : Base { int get() override { return 2; } }; int f() { Derived d; return d.get(); }',
                                    'struct Base { virtual int get() { return 1; } }; struct Derived final : Base { int get() override { return 2; } }; int f() { Derived d; return d.get(); }', o=0),

    # =============================================================================
    # USE: final method
    # =============================================================================
    TestCase("add_final_method",    'struct Base { virtual int get() { return 1; } }; struct Derived : Base { int get() override       { return 2; } }; int f() { Derived d; return d.get(); }',
                                    'struct Base { virtual int get() { return 1; } }; struct Derived : Base { int get() override final { return 2; } }; int f() { Derived d; return d.get(); }', o=0),

    # =============================================================================
    # USE: auto type deduction
    # =============================================================================
    TestCase("use_auto",            'int f() { int  x = 42; return x; }',
                                    'int f() { auto x = 42; return x; }', o=0),

    # =============================================================================
    # USE: trailing return type
    # =============================================================================
    TestCase("trailing_return_type", 'int  add(int a, int b)        { return a + b; } int f() { return add(1, 2); }',
                                     'auto add(int a, int b) -> int { return a + b; } int f() { return add(1, 2); }', o=0),

    # =============================================================================
    # USE: enum class
    # =============================================================================
    TestCase("use_enum_class",      'enum Color { Red = 0, Green = 1 };       int f() { Color c = Red;        return (int)c; }',
                                    'enum class Color { Red = 0, Green = 1 }; int f() { Color c = Color::Red; return (int)c; }', o=0),

    # =============================================================================
    # USE: constexpr variable
    # =============================================================================
    TestCase("use_constexpr_var",   'int f() { const     int x = 10; return x * 2; }',
                                    'int f() { constexpr int x = 10; return x * 2; }', o=0),

    # =============================================================================
    # USE: constexpr function
    # =============================================================================
    TestCase("use_constexpr_func",  'inline    int square(int x) { return x * x; } int f() { return square(5); }',
                                    'constexpr int square(int x) { return x * x; } int f() { return square(5); }', o=3),

    # =============================================================================
    # USE: uniform initialization
    # =============================================================================
    TestCase("uniform_init",        'int f() { int x = 5;  return x; }',
                                    'int f() { int x{5};   return x; }', o=0),

    # =============================================================================
    # USE: in-class member initializer
    # =============================================================================
    TestCase("in_class_init",       'struct S { int x;      S() : x(10) {} }; int f() { S s; return s.x; }',
                                    'struct S { int x = 10; S() {}         }; int f() { S s; return s.x; }', o=0),

    # =============================================================================
    # USE: delegating constructor
    # =============================================================================
    TestCase("inline_ctor",         'struct S { int x;        S() { x = 0; }        S(int v) { x = v; } }; int f() { S s; return s.x; }',
                                    'struct S { int x; inline S() { x = 0; } inline S(int v) { x = v; } }; int f() { S s; return s.x; }', o=0), 

    TestCase("delegating_ctor",     'struct S { int x; inline S() { x = 0; } inline S(int v) { x = v; } }; int f() { S s; return s.x; }',
                                    'struct S { int x; inline S() : S(0) {}  inline S(int v) { x = v; } }; int f() { S s; return s.x; }', o=3),

    # =============================================================================
    # REMOVE: dead code
    # =============================================================================
    TestCase("remove_dead_code",    'int f() { return 17; int x = 10; x++; }',
                                    'int f() { return 17; }', o=3),

    # ======================================================================<=======
    # REMOVE: commented-out code
    # =============================================================================
    TestCase("remove_comments",     'int f() { /* int old = 5; */ return 17; }',
                                    'int f() { return 17; }', o=0),  # Validator-only test

    # =============================================================================
    # REMOVE: unused parameters
    # =============================================================================
    TestCase("remove_unused_param", 'inline int add(int a, int b, int unused) { return a + b; } int f() { return add(2, 3, 99); }',
                                    'inline int add(int a, int b            ) { return a + b; } int f() { return add(2, 3    ); }', o=3),

    # =============================================================================
    # REMOVE: unused variables
    # =============================================================================
    TestCase("remove_unused_var",   'int f() { int unused = 42; return 10; }',
                                    'int f() {                  return 10; }', o=3),

    # =============================================================================
    # REMOVE: unused variables
    # =============================================================================
    TestCase("remove_unused_var",   'int f() { int unused = 42; return 10; }',
                                    'int f() {                  return 10; }', o=3),

    # =============================================================================
    # REMOVE: void argument list
    # =============================================================================
    TestCase("remove_void_args",    'int f(void) { return 42; }',
                                    'int f()     { return 42; }', o=0),

    # =============================================================================
    # REMOVE: redundant semicolons
    # =============================================================================
    TestCase("remove_extra_semicolon", 'int f() { return 42;; }',
                                       'int f() { return 42; }', o=0),

    # =============================================================================
    # REMOVE: redundant this->
    # =============================================================================
    TestCase("remove_this_pointer", 'struct S { int x; int get() { return this->x; } }; int f() { S s; s.x = 5; return s.get(); }',
                                    'struct S { int x; int get() { return x;       } }; int f() { S s; s.x = 5; return s.get(); }', o=0),

    # =============================================================================
    # REPLACE: NULL with nullptr
    # =============================================================================
    TestCase("null_to_nullptr",     '#define NULL 0\nint f() { int* p = NULL;    return p ? 1 : 0; }',
                                    '                int f() { int* p = nullptr; return p ? 1 : 0; }', o=0),

    # =============================================================================
    # REPLACE: 0/1 bool with true/false
    # =============================================================================
    TestCase("bool_literals",       'int f() { bool b = 1;    return b ? 10 : 20; }',
                                    'int f() { bool b = true; return b ? 10 : 20; }', o=0),

    # =============================================================================
    # REPLACE: static_cast
    # =============================================================================
    TestCase("use_static_cast",     'int f() { double d = 3.14; return (int)d; }',
                                    'int f() { double d = 3.14; return static_cast<int>(d); }', o=0),

    # =============================================================================
    # REPLACE: typedef with using
    # =============================================================================
    TestCase("typedef_to_using",    'typedef int  MyInt; int f() { MyInt x = 5; return x; }',
                                    'using MyInt = int;  int f() { MyInt x = 5; return x; }', o=0),

    # =============================================================================
    # REPLACE: header guards with #pragma once
    # =============================================================================
    TestCase("pragma_once",         '#ifndef HEADER_H\n#define HEADER_H\nint f() { return 42; }\n#endif',
                                    '#pragma once\nint f() { return 42; }', o=0),

    # =============================================================================
    # REPLACE: throw() with noexcept
    # =============================================================================
    TestCase("throw_to_noexcept",   'int add(int a, int b) throw()   { return a + b; } int f() { return add(2, 3); }',
                                    'int add(int a, int b) noexcept  { return a + b; } int f() { return add(2, 3); }', o=0),

    # =============================================================================
    # REFACTOR: declare variables where assigned
    # =============================================================================
    TestCase("declare_at_assign",   'int f() { int x; x = 10; return x; }',
                                    'int f() { int x = 10;    return x; }', o=0),

    # =============================================================================
    # REFACTOR: extract named constant
    # =============================================================================
    TestCase("extract_constant",    'int f() { return 3 * 3 * 3.14159; }',
                                    'int f() { constexpr double PI = 3.14159; return 3 * 3 * PI; }', o=3),

    # =============================================================================
    # REFACTOR: reduce nesting (early return)
    # =============================================================================
    TestCase("early_return",        'int f() { int x; if (x > 0) { return x * 2; } else { return 0; } }',
                                    'int f() { int x; if (x > 0) { return x * 2; } return 0; }', o=3),

    # =============================================================================
    # REFACTOR: modernize for loop (range-based)
    # =============================================================================
    TestCase("range_based_for",     'int f() { const int arr[5] = {1, 2, 3, 4, 5}; int sum = 0; for (const int* p = arr; p != arr + 5; ++p) { sum += *p; } return sum; }',
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
    TestCase("add_owner<T>",       '           int* get(int value) {            int* p = new int; *p = value; return p; } int f() {            int *p = get (17); int i = *p; delete p; return i; }',
                                   'namespace gsl { template <typename T> using owner = T*; }\n' +\
                                 'gsl::owner<int> get(int value) { gsl::owner<int> p = new int; *p = value; return p; } int f() { gsl::owner<int> p = get (17); int i = *p; delete p; return i; }', o=0),

    TestCase("add_non_owner<T>",   'int get(               int* p) { return *p; } int f() { int x = 42; return get(&x); }',
                                   'namespace gsl { template <typename T> using non_owner = T*; }\n' +\
                                   'int get(gsl::non_owner<int> p) { return *p; } int f() { int x = 42; return get(&x); }', o=0),

    # =============================================================================
    # OWNERSHIP/LIFETIME: use unique_ptr instead of malloc and free:
    # =============================================================================
    TestCase("unique_ptr_simple",  'int f() noexcept { int* p = new int; *p = 17; int x = *p; delete p; return x; }',
                                   'int f() noexcept { LevelUp::unique_ptr<int> p = LevelUp::make_unique<int>(); *p = 17; return *p; }', o=3),

    # =============================================================================
    # OWNERSHIP/LIFETIME: use unique_ptr instead traditional RAII:
    # =============================================================================
    TestCase("unique_ptr_RAII",    'class f { public: f() : p(new int)                         {*p = 17;} ~f() {delete p;} operator int() {return *p;} private: int* p; };',
                                   'class f { public: f() : p(LevelUp::make_unique<int>()) {*p = 17;}                  operator int() {return *p;} private: LevelUp::unique_ptr<int> p; };', o=3),

    # =============================================================================
    # OWNERSHIP/LIFETIME: verify LevelUp::unique_ptr with std impl == std::unique_ptr
    # This test validates that LevelUp::unique_ptr (when using LEVELUP_USE_STD_UNIQUE_PTR)
    # produces identical assembly to std::unique_ptr, proving behavioral equivalence
    # =============================================================================
    TestCase("unique_ptr_levelup_std_equiv",
             '#include <memory>\nint f() noexcept {     std::unique_ptr<int> p =     std::make_unique<int>(); *p = 17; return *p; }',
             '                   int f() noexcept { LevelUp::unique_ptr<int> p = LevelUp::make_unique<int>(); *p = 17; return *p; }',
             o=3,
             compiler_flags='/DLEVELUP_USE_STD_UNIQUE_PTR'),

    # =============================================================================
    # REFACTOR: simplify boolean expressions
    # =============================================================================
    TestCase("simplify_bool_comparison", 'int f() { bool b = true; if (b == true) { return 10; } return 0; }',
                                         'int f() { bool b = true; if (b)         { return 10; } return 0; }', o=3),

    TestCase("simplify_double_negation", 'int f() { bool b = true; return !!b ? 5 : 0; }',
                                         'int f() { bool b = true; return b   ? 5 : 0; }', o=3),

    # =============================================================================
    # REPLACE: C-style casts with C++ casts (safer, more searchable)
    # =============================================================================
    TestCase("c_cast_to_static_cast",   'int f() { double d = 3.14; int x = (int)d; return x; }',
                                        'int f() { double d = 3.14; int x = static_cast<int>(d); return x; }', o=0),

    TestCase("c_cast_to_const_cast",    'int modify(int* p) { return *p + 1; } int f() { const int x = 5; return modify((int*)&x); }',
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
    TestCase("add_fallthrough",         'int f() { int x = 2; switch(x) { case 1: x += 1; case 2: x += 2; break; default: x = 0; } return x; }',
                                        'int f() { int x = 2; switch(x) { case 1: x += 1; [[fallthrough]]; case 2: x += 2; break; default: x = 0; } return x; }', o=0),

    # =============================================================================
    # REPLACE: typedef with using (template-friendly, more readable)
    # =============================================================================
    TestCase("typedef_func_ptr_to_using", 'typedef int (*FuncPtr)(int); int apply(FuncPtr f, int x) { return f(x); } int double_it(int x) { return x * 2; } int f() { return apply(double_it, 5); }',
                                          'using FuncPtr = int (*)(int); int apply(FuncPtr f, int x) { return f(x); } int double_it(int x) { return x * 2; } int f() { return apply(double_it, 5); }', o=3),

    # =============================================================================
    # REPLACE: multiple returns with single return variable (NRVO-friendly)
    # =============================================================================
    TestCase("consolidate_returns",     'int f() { int x = 5; if (x > 0) { return x * 2; } else { return 0; } }',
                                        'int f() { int x = 5; int result; if (x > 0) { result = x * 2; } else { result = 0; } return result; }', o=3),

    # =============================================================================
    # REPLACE: size_t with more specific types for better overflow detection
    # =============================================================================
    TestCase("explicit_integer_width",  'int f() { unsigned int count = 100; return (int)count; }',
                                        '#include <cstdint>\nint f() { uint32_t count = 100; return (int)count; }', o=0),

    # =============================================================================
    # USE: =delete for uncopyable classes (clearer than private declarations)
    # =============================================================================
    TestCase("private_to_delete",       'struct S { private: S(const S&); S& operator=(const S&); public:  int x; S() : x(0) {} int get() { return x; } }; int f() { S s; return s.get(); }',
                                        'struct S { S(const S&) = delete; S& operator=(const S&) = delete; int x; S() : x(0) {} int get() { return x; } }; int f() { S s; return s.get(); }', o=0),

    # =============================================================================
    # REPLACE: char* for string literals with const char* (const correctness)
    # =============================================================================
    TestCase("string_literal_const",    'int len(char* s)       { int i = 0; while(s[i]) i++; return i; } int f() { return len((char*)"test"); }',
                                        'int len(const char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len("test"); }', o=0),

    # =============================================================================
    # USE: inline namespace for versioning (ABI compatibility)
    # =============================================================================
    TestCase("add_inline_namespace",    'namespace lib                       { struct S { int x; }; }   int f() { lib::S s; s.x = 5; return s.x; }',
                                        'namespace lib { inline namespace v1 { struct S { int x; }; } } int f() { lib::S s; s.x = 5; return s.x; }', o=0),

    # =============================================================================
    # REPLACE: char* -> std::string_view (progressive validated modernization)
    # Demonstrates step-by-step transformation of the same function with ASM validation
    # Note: Steps 2+ could be broken down further in production for incremental validation
    # =============================================================================

    # CHAIN 1: Simple string length function - char* to const char* to string_view
    # Step 1: char* -> const char* (const correctness, O0 validation)
    TestCase("sv_chain1_step1_add_const",
             'int len(char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len((char*)"hello"); }',
             'int len(const char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len("hello"); }', o=0),

    # Step 2: const char* -> string_view::size() (modern C++, O3 validation)
    TestCase("sv_chain1_step2_string_view",
             '#include <string_view>\ninline int len(const char* s) { int i = 0; while(s[i]) i++; return i; } int f() { return len("hello"); }',
             '#include <string_view>\ninline int len(std::string_view s) { return static_cast<int>(s.size()); } int f() { return len("hello"); }', o=3),

    # CHAIN 2: Character access - pointer dereference to string_view indexing
    # Step 1: char* -> const char* (const correctness, O0 validation)
    TestCase("sv_chain2_step1_add_const",
             'int first_char(char* str) { return *str; } int f() { return first_char((char*)"abc"); }',
             'int first_char(const char* str) { return *str; } int f() { return first_char("abc"); }', o=0),

    # Step 2: const char* -> string_view[0] (modern C++, O3 validation)
    TestCase("sv_chain2_step2_string_view",
             '#include <string_view>\ninline int first_char(const char* str) { return *str; } int f() { return first_char("abc"); }',
             '#include <string_view>\ninline int first_char(std::string_view str) { return str[0]; } int f() { return first_char("abc"); }', o=3),

    # CHAIN 3: Empty string check - null terminator to string_view::empty()
    # Step 1: char* -> const char* (const correctness, O0 validation)
    TestCase("sv_chain3_step1_add_const",
             'int is_empty(char* s) { return s[0] == 0; } int f() { return is_empty((char*)""); }',
             'int is_empty(const char* s) { return s[0] == 0; } int f() { return is_empty(""); }', o=0),

    # Step 2: const char* -> string_view::empty() (modern C++, O3 validation)
    TestCase("sv_chain3_step2_string_view",
             '#include <string_view>\ninline int is_empty(const char* s) { return s[0] == 0; } int f() { return is_empty(""); }',
             '#include <string_view>\ninline int is_empty(std::string_view s) { return s.empty(); } int f() { return is_empty(""); }', o=3),

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
]


def run_validator_smoke_tests(compilers):
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

        validators = {
            0: ASMValidatorO0(),
            3: ASMValidatorO3(),
        }

        for test in SMOKE_TESTS:
            print(f"\nRunning: {test.name}")

            validator = validators[test.optimization_level]

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                original_file = temp_path / "original.cpp"
                modified_file = temp_path / "modified.cpp"

                original_file.write_text(test.source)
                modified_file.write_text(test.modified_source)

                # Convert flags for current compiler (MSVC uses /D, Clang uses -D)
                def convert_flags(flags):
                    if flags is None:
                        return None
                    if compiler_type == CompilerType.CLANG:
                        return flags.replace('/D', '-D')
                    return flags

                original_compiled = compiler.compile_file(
                    original_file,
                    additional_flags=convert_flags(test.additional_flags),
                    optimization_level=test.optimization_level
                )
                modified_compiled = compiler.compile_file(
                    modified_file,
                    additional_flags=convert_flags(test.modified_additional_flags),
                    optimization_level=test.optimization_level
                )

                result = validator.validate(original_compiled, modified_compiled)

                if result:
                    print(f"  PASS")
                    total_passed += 1
                else:
                    print(f"  FAIL - validator returned False (expected True)")
                    print(f"  Original ASM:\n{original_compiled.asm_output}")
                    print(f"  Modified ASM:\n{modified_compiled.asm_output}")
                    total_failed += 1

    return total_passed, total_failed



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
