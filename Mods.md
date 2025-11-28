# LevelUp Mods: Implementation Roadmap

This document catalogs all potential mods derived from validator smoke tests and provides implementation recommendations for each.

## Overview

Based on the 59 validator test cases in `smoketest.py`, we can create corresponding mods using three implementation approaches:

- **Python (Pattern-based)**: 15 mods - Simple regex/symbol-based transformations
- **Clang-Tidy**: 32 mods - AST-based transformations leveraging existing tooling
- **Local LLM**: 5 mods - Complex semantic transformations requiring contextual understanding
- **Already Implemented**: 3 mods - Currently available in the system

**Total**: 55 new mods to implement

## Implementation Status

### ✅ Already Implemented (3)

| Mod ID | Name | Test Case | Implementation |
|--------|------|-----------|----------------|
| `remove_inline` | Remove Inline Keywords | remove_inline | RemoveInlineMod |
| `add_override` | Add Override Keywords | add_override | AddFunctionQualifier(OVERRIDE) |
| `add_noexcept` | Add Noexcept Specifier | add_noexcept | AddFunctionQualifier(NOEXCEPT) |

---

## Phase 1: Python-Based Mods (15)

These mods use pattern matching, regex, or Doxygen symbols for straightforward transformations. They're fast to implement, deterministic, and work well with the existing architecture.

### Comments & Documentation

#### 1. **document_function**
- **Test**: `document_function`
- **Transformation**: Add documentation comment before function
- **Pattern**: `int f()` → `/* Returns seventeen */ int f()`
- **Complexity**: Low
- **Implementation**: Insert comment line before function declaration
- **Validation**: O0 (comments don't affect assembly)

### Qualifiers & Specifiers

#### 2. **add_explicit**
- **Test**: `add_explicit`
- **Transformation**: Add `explicit` to single-argument constructors
- **Pattern**: `S(int x)` → `explicit S(int x)`
- **Complexity**: Low
- **Implementation**: Use Doxygen symbols to find single-arg constructors, insert keyword
- **Validation**: O0
- **Notes**: Prevents implicit conversions

#### 3. **add_final_class**
- **Test**: `add_final_class`
- **Transformation**: Add `final` to class declarations
- **Pattern**: `struct Derived : Base` → `struct Derived final : Base`
- **Complexity**: Low
- **Implementation**: Use symbols to identify leaf classes (no derived classes)
- **Validation**: O0

#### 4. **add_final_method**
- **Test**: `add_final_method`
- **Transformation**: Add `final` to virtual methods
- **Pattern**: `int get() override` → `int get() override final`
- **Complexity**: Low
- **Implementation**: Find virtual methods with override, append `final`
- **Validation**: O0

### Cleanup & Simplification

#### 5. **remove_void_args**
- **Test**: `remove_void_args`
- **Transformation**: Remove `(void)` parameter list
- **Pattern**: `int f(void)` → `int f()`
- **Complexity**: Very Low
- **Implementation**: Regex `\(\s*void\s*\)` → `()`
- **Validation**: O0
- **Notes**: Modern C++ doesn't need explicit void

#### 6. **remove_extra_semicolon**
- **Test**: `remove_extra_semicolon`
- **Transformation**: Remove redundant semicolons
- **Pattern**: `return 42;;` → `return 42;`
- **Complexity**: Very Low
- **Implementation**: Regex `;;+` → `;`
- **Validation**: O0

#### 7. **remove_this_pointer**
- **Test**: `remove_this_pointer`
- **Transformation**: Remove redundant `this->`
- **Pattern**: `return this->x;` → `return x;`
- **Complexity**: Low
- **Implementation**: Context-aware regex in member functions
- **Validation**: O0
- **Notes**: Only when unambiguous (no parameter shadowing)

### Type Modernization

#### 8. **null_to_nullptr**
- **Test**: `null_to_nullptr`
- **Transformation**: Replace `NULL` with `nullptr`
- **Pattern**: `int* p = NULL;` → `int* p = nullptr;`
- **Complexity**: Low
- **Implementation**: Regex `\bNULL\b` → `nullptr` (with macro handling)
- **Validation**: O0
- **Notes**: Type-safe null pointer constant

#### 9. **bool_literals**
- **Test**: `bool_literals`
- **Transformation**: Replace 0/1 with true/false for bool types
- **Pattern**: `bool b = 1;` → `bool b = true;`
- **Complexity**: Low
- **Implementation**: Type-aware replacement (only for bool variables)
- **Validation**: O0

#### 10. **typedef_to_using**
- **Test**: `typedef_to_using`
- **Transformation**: Convert `typedef` to `using` alias
- **Pattern**: `typedef int MyInt;` → `using MyInt = int;`
- **Complexity**: Low
- **Implementation**: Regex `typedef\s+(.+)\s+(\w+);` → `using $2 = $1;`
- **Validation**: O0
- **Notes**: More readable, template-friendly syntax

### Preprocessor Modernization

#### 11. **pragma_once**
- **Test**: `pragma_once`
- **Transformation**: Replace header guards with `#pragma once`
- **Pattern**: `#ifndef X / #define X / #endif` → `#pragma once`
- **Complexity**: Medium
- **Implementation**: Detect include guard pattern, replace entire structure
- **Validation**: O0
- **Notes**: Simpler, faster compilation (compiler-dependent but widely supported)

#### 12. **throw_to_noexcept**
- **Test**: `throw_to_noexcept`
- **Transformation**: Replace deprecated `throw()` with `noexcept`
- **Pattern**: `int f() throw()` → `int f() noexcept`
- **Complexity**: Low
- **Implementation**: Regex `throw\(\s*\)` → `noexcept`
- **Validation**: O0
- **Notes**: `throw()` deprecated in C++11, removed in C++17

### Control Flow Attributes

#### 13. **add_fallthrough**
- **Test**: `add_fallthrough`
- **Transformation**: Add `[[fallthrough]]` attribute to intentional case fallthrough
- **Pattern**: `case 1: x += 1; case 2:` → `case 1: x += 1; [[fallthrough]]; case 2:`
- **Complexity**: Medium
- **Implementation**: Detect case without break before next case, insert attribute
- **Validation**: O0
- **Notes**: Documents intent, prevents compiler warnings

### Namespace Features

#### 14. **add_inline_namespace**
- **Test**: `add_inline_namespace`
- **Transformation**: Add inline namespace for versioning
- **Pattern**: `namespace lib {` → `namespace lib { inline namespace v1 {`
- **Complexity**: Medium
- **Implementation**: Insert inline namespace, manage closing braces
- **Validation**: O0
- **Notes**: ABI versioning without breaking existing code

### Modern Class Features

#### 15. **private_to_delete**
- **Test**: `private_to_delete`
- **Transformation**: Convert private copy operations to `= delete`
- **Pattern**: `private: S(const S&);` → `S(const S&) = delete;`
- **Complexity**: Medium
- **Implementation**: Find private copy ctor/assignment, move to public as deleted
- **Validation**: O0
- **Notes**: Clearer intent than private declaration

---

## Phase 2: Clang-Tidy Integration (32)

These mods leverage clang-tidy's AST-based analysis for complex transformations. Implementation strategy: create `ClangTidyMod` wrapper that executes clang-tidy checks and converts fixes to LevelUp refactorings.

### const Correctness

#### 16. **const_param**
- **Test**: `const_param`
- **Transformation**: Add `const` to pointer/reference parameters
- **Clang-Tidy Check**: `readability-non-const-parameter`
- **Pattern**: `int len(char* buf)` → `int len(const char* buf)`
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Prevents accidental modification

#### 17. **const_method**
- **Test**: `const_method`
- **Transformation**: Add `const` to non-mutating member functions
- **Clang-Tidy Check**: `readability-make-member-function-const`
- **Pattern**: `int get() { return x; }` → `int get() const { return x; }`
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Enables const object usage

#### 18. **string_literal_const**
- **Test**: `string_literal_const`
- **Transformation**: Add `const` to string literal parameters
- **Clang-Tidy Check**: Similar to `const_param`
- **Pattern**: `int len(char* s)` → `int len(const char* s)`
- **Complexity**: Low
- **Validation**: O0

#### 19. **string_view_add_const**
- **Test**: `string_view_add_const`
- **Transformation**: Add const to char* (step 1 of string_view chain)
- **Clang-Tidy Check**: Same as `const_param`
- **Pattern**: `char* s` → `const char* s`
- **Complexity**: Low
- **Validation**: O0
- **Notes**: Prerequisite for string_view conversion

### Default Operations

#### 20. **use_default_ctor**
- **Test**: `use_default_ctor`
- **Transformation**: Use `= default` for trivial constructors
- **Clang-Tidy Check**: `modernize-use-equals-default`
- **Pattern**: `S() { x = 0; }` → `S() = default;` (with member initializer)
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Compiler-generated is more efficient

### Auto Type Deduction

#### 21. **use_auto**
- **Test**: `use_auto`
- **Transformation**: Use `auto` for obvious types
- **Clang-Tidy Check**: `modernize-use-auto`
- **Pattern**: `int x = 42;` → `auto x = 42;`
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Reduces redundancy, improves maintainability

#### 22. **trailing_return_type**
- **Test**: `trailing_return_type`
- **Transformation**: Convert to trailing return type syntax
- **Clang-Tidy Check**: `modernize-use-trailing-return-type`
- **Pattern**: `int add(int a, int b)` → `auto add(int a, int b) -> int`
- **Complexity**: Low
- **Validation**: O0
- **Notes**: Useful for template return types

### Enum Modernization

#### 23. **use_enum_class**
- **Test**: `use_enum_class`
- **Transformation**: Convert `enum` to `enum class`
- **Clang-Tidy Check**: Custom or future check
- **Pattern**: `enum Color { Red }; Color c = Red;` → `enum class Color { Red }; Color c = Color::Red;`
- **Complexity**: High (requires updating all usage sites)
- **Validation**: O0
- **Notes**: Type-safe enums, prevents name pollution

### constexpr Promotion

#### 24. **use_constexpr_var**
- **Test**: `use_constexpr_var`
- **Transformation**: Replace `const` with `constexpr` for compile-time constants
- **Clang-Tidy Check**: Custom check (analyze if value is compile-time)
- **Pattern**: `const int x = 10;` → `constexpr int x = 10;`
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Enables compile-time evaluation

#### 25. **use_constexpr_func**
- **Test**: `use_constexpr_func`
- **Transformation**: Mark functions `constexpr`
- **Clang-Tidy Check**: Custom check (analyze function body)
- **Pattern**: `inline int square(int x) { return x * x; }` → `constexpr int square(int x) { return x * x; }`
- **Complexity**: High
- **Validation**: O3 (optimization differences)

#### 26. **define_to_constexpr**
- **Test**: `define_to_constexpr`
- **Transformation**: Replace `#define` constants with `constexpr`
- **Clang-Tidy Check**: `modernize-macro-to-enum` / custom
- **Pattern**: `#define MAX_SIZE 100` → `constexpr int MAX_SIZE = 100;`
- **Complexity**: Medium
- **Validation**: O0
- **Notes**: Type-safe, debuggable, scoped

#### 27. **define_func_to_constexpr**
- **Test**: `define_func_to_constexpr`
- **Transformation**: Replace function macros with `constexpr` functions
- **Clang-Tidy Check**: Custom check
- **Pattern**: `#define SQUARE(x) ((x) * (x))` → `constexpr int square(int x) { return x * x; }`
- **Complexity**: High (macro expansion analysis)
- **Validation**: O3

### Initialization

#### 28. **uniform_init**
- **Test**: `uniform_init`
- **Transformation**: Use brace initialization
- **Clang-Tidy Check**: Custom (reverse of `modernize-use-brace-init`)
- **Pattern**: `int x = 5;` → `int x{5};`
- **Complexity**: Low
- **Validation**: O0
- **Notes**: Prevents narrowing conversions

#### 29. **in_class_init**
- **Test**: `in_class_init`
- **Transformation**: Use in-class member initializers
- **Clang-Tidy Check**: `modernize-use-default-member-init`
- **Pattern**: `struct S { int x; S() : x(10) {} }` → `struct S { int x = 10; S() {} }`
- **Complexity**: Medium
- **Validation**: O0

#### 30. **delegating_ctor**
- **Test**: `delegating_ctor`
- **Transformation**: Use delegating constructors
- **Clang-Tidy Check**: Custom check
- **Pattern**: `S() { x = 0; } S(int v) { x = v; }` → `S() : S(0) {} S(int v) { x = v; }`
- **Complexity**: High (analyze constructor bodies)
- **Validation**: O3

### Code Removal

#### 31. **remove_dead_code**
- **Test**: `remove_dead_code`
- **Transformation**: Remove unreachable code
- **Clang-Tidy Check**: `misc-unreachable-code` + custom fix
- **Pattern**: `return 17; int x = 10;` → `return 17;`
- **Complexity**: Medium (control flow analysis)
- **Validation**: O3

#### 32. **remove_comments**
- **Test**: `remove_comments`
- **Transformation**: Remove commented-out code
- **Clang-Tidy Check**: Custom check
- **Pattern**: `/* int old = 5; */ return 17;` → `return 17;`
- **Complexity**: Low
- **Validation**: O0
- **Notes**: Distinguish from documentation comments

#### 33. **remove_unused_param**
- **Test**: `remove_unused_param`
- **Transformation**: Remove unused function parameters
- **Clang-Tidy Check**: `misc-unused-parameters` with fix
- **Pattern**: `int add(int a, int b, int unused)` → `int add(int a, int b)`
- **Complexity**: Medium (update all call sites)
- **Validation**: O3

#### 34. **remove_unused_var**
- **Test**: `remove_unused_var`
- **Transformation**: Remove unused local variables
- **Clang-Tidy Check**: `clang-analyzer-deadcode.DeadStores` + fix
- **Pattern**: `int unused = 42; return 10;` → `return 10;`
- **Complexity**: Low
- **Validation**: O3

### Cast Modernization

#### 35. **use_static_cast**
- **Test**: `use_static_cast`
- **Transformation**: Replace C-style cast with `static_cast`
- **Clang-Tidy Check**: `modernize-use-static-cast`
- **Pattern**: `(int)d` → `static_cast<int>(d)`
- **Complexity**: Low
- **Validation**: O0
- **Notes**: More searchable, explicit intent

#### 36. **c_cast_to_static_cast**
- **Test**: `c_cast_to_static_cast`
- **Transformation**: Same as above
- **Clang-Tidy Check**: Same check
- **Complexity**: Low
- **Validation**: O0

#### 37. **c_cast_to_const_cast**
- **Test**: `c_cast_to_const_cast`
- **Transformation**: Replace C-cast with `const_cast`
- **Clang-Tidy Check**: Part of cast modernization
- **Pattern**: `(int*)&x` → `const_cast<int*>(&x)`
- **Complexity**: Medium (type analysis)
- **Validation**: O0

### Type Aliases

#### 38. **typedef_func_ptr_to_using**
- **Test**: `typedef_func_ptr_to_using`
- **Transformation**: Convert typedef function pointer to using
- **Clang-Tidy Check**: `modernize-use-using`
- **Pattern**: `typedef int (*FuncPtr)(int);` → `using FuncPtr = int (*)(int);`
- **Complexity**: Low
- **Validation**: O3

#### 39. **explicit_integer_width**
- **Test**: `explicit_integer_width`
- **Transformation**: Use fixed-width integer types
- **Clang-Tidy Check**: Custom check
- **Pattern**: `unsigned int count` → `uint32_t count`
- **Complexity**: Medium (platform assumptions)
- **Validation**: O0

### Loop Modernization

#### 40. **range_based_for**
- **Test**: `range_based_for`
- **Transformation**: Modernize pointer loops to range-based for
- **Clang-Tidy Check**: `modernize-loop-convert`
- **Pattern**: `for (const int* p = arr; p != arr + 5; ++p)` → `for (const int& val : arr)`
- **Complexity**: High (pattern recognition)
- **Validation**: O3

### Smart Pointers

#### 41. **unique_ptr_simple**
- **Test**: `unique_ptr_simple`
- **Transformation**: Convert new/delete to `unique_ptr`
- **Clang-Tidy Check**: `modernize-make-unique`
- **Pattern**: `int* p = new int; delete p;` → `auto p = std::make_unique<int>();`
- **Complexity**: Medium
- **Validation**: O3

### Boolean Simplification

#### 42. **simplify_bool_comparison**
- **Test**: `simplify_bool_comparison`
- **Transformation**: Simplify boolean expressions
- **Clang-Tidy Check**: `readability-simplify-boolean-expr`
- **Pattern**: `if (b == true)` → `if (b)`
- **Complexity**: Low
- **Validation**: O3

#### 43. **simplify_double_negation**
- **Test**: `simplify_double_negation`
- **Transformation**: Remove double negation
- **Clang-Tidy Check**: Part of boolean simplification
- **Pattern**: `!!b` → `b`
- **Complexity**: Low
- **Validation**: O3

### Declaration Optimization

#### 44. **declare_at_assign**
- **Test**: `declare_at_assign`
- **Transformation**: Move declaration to first assignment
- **Clang-Tidy Check**: Custom (reverse of `readability-isolate-declaration`)
- **Pattern**: `int x; x = 10;` → `int x = 10;`
- **Complexity**: Medium (control flow)
- **Validation**: O0

### String Modernization

#### 45. **sv_chain1_step3_string_view**
- **Test**: `sv_chain1_step3_string_view`
- **Transformation**: Convert `const char*` to `std::string_view`
- **Clang-Tidy Check**: Custom check
- **Pattern**: `int len(const char* s) { while(s[i]) i++; }` → `int len(std::string_view s) { return s.size(); }`
- **Complexity**: High (function body rewrite)
- **Validation**: O3
- **Notes**: Requires prior steps (add const, add inline)

### Span Conversion

#### 46. **span_chain1_step2_to_span**
- **Test**: `span_chain1_step2_to_span`
- **Transformation**: Convert buffer+length to `std::span`
- **Clang-Tidy Check**: Custom check for buffer+length pattern
- **Pattern**: `checksum(const char* buf, int len)` → `checksum(std::span<const char> buf)`
- **Complexity**: Very High (multi-parameter pattern, call site updates)
- **Validation**: O3

### Extract Function

#### 47. **extract_function**
- **Test**: `extract_function`
- **Transformation**: Extract code to separate function
- **Clang-Tidy Check**: Not typically automated (IDE refactoring)
- **Pattern**: `int f() { return 4*4 + 1; }` → `inline int squared(int x) { return x*x; } int f() { return squared(4) + 1; }`
- **Complexity**: Very High
- **Validation**: O3
- **Notes**: Better suited for LLM or manual refactoring

---

## Phase 3: Local LLM Mods (5)

These mods require semantic understanding, naming decisions, or complex ownership analysis. A local LLM (ollama + codellama/deepseek) can generate transformations that are then validated by ASM comparison.

### Semantic Refactorings

#### 48. **extract_constant**
- **Test**: `extract_constant`
- **Transformation**: Extract magic number to named constant
- **Why LLM**: Requires semantic naming (3.14159 → PI)
- **Pattern**: `return 3 * 3 * 3.14159;` → `constexpr double PI = 3.14159; return 3 * 3 * PI;`
- **Complexity**: High (naming, scope decision)
- **Validation**: O3
- **LLM Prompt**: "Extract the magic number to a well-named constexpr constant"

#### 49. **pointer_to_reference**
- **Test**: `pointer_to_reference`
- **Transformation**: Convert pointer parameters to references
- **Why LLM**: Requires nullability analysis
- **Pattern**: `int modify(int* p) { return *p + 1; }` → `int modify(int& p) { return p + 1; }`
- **Complexity**: High (lifetime/nullability analysis)
- **Validation**: O0
- **LLM Prompt**: "Analyze if this pointer parameter can never be null. If so, convert to reference."
- **Notes**: Dangerous if pointer can be null; LLM must analyze all call sites

### Ownership Annotations

#### 50. **add_owner**
- **Test**: `add_owner<T>`
- **Transformation**: Annotate owning pointers with `gsl::owner<T>`
- **Why LLM**: Ownership inference requires whole-program analysis
- **Pattern**: `int* get()` → `gsl::owner<int*> get()`
- **Complexity**: Very High (interprocedural analysis)
- **Validation**: O0
- **LLM Prompt**: "Analyze if this pointer owns the memory it points to (allocated in function, caller must delete)"

#### 51. **add_non_owner**
- **Test**: `add_non_owner<T>`
- **Transformation**: Annotate non-owning pointers with `gsl::non_owner<T>`
- **Why LLM**: Ownership inference
- **Pattern**: `int get(int* p)` → `int get(gsl::non_owner<int*> p)`
- **Complexity**: Very High
- **Validation**: O0
- **LLM Prompt**: "Analyze if this pointer borrows memory without owning it"

### Smart Pointer Refactoring

#### 52. **unique_ptr_RAII**
- **Test**: `unique_ptr_RAII`
- **Transformation**: Convert RAII class to use `unique_ptr`
- **Why LLM**: Class-level refactoring, pattern recognition
- **Pattern**: Class with `T* member`, ctor with `new`, dtor with `delete` → `unique_ptr<T> member`
- **Complexity**: Very High (multi-member class transformation)
- **Validation**: O3
- **LLM Prompt**: "This class uses manual RAII. Convert to unique_ptr: remove dtor, update ctor, change member type"

### Style Refactorings (Debatable Value)

#### 53. **consolidate_returns** (Optional)
- **Test**: `consolidate_returns`
- **Transformation**: Use single return variable
- **Why LLM**: Control flow restructuring, style preference
- **Pattern**: `if (x > 0) { return x * 2; } else { return 0; }` → `int result; if (x > 0) { result = x * 2; } else { result = 0; } return result;`
- **Complexity**: Medium
- **Validation**: O3
- **Notes**: Modern compilers optimize both patterns equally; debatable benefit

#### 54. **early_return** (Optional)
- **Test**: `early_return`
- **Transformation**: Refactor if-else to early return
- **Why LLM**: Style preference, control flow inversion
- **Pattern**: `if (x > 0) { return x * 2; } else { return 0; }` → `if (x > 0) { return x * 2; } return 0;`
- **Complexity**: Medium
- **Validation**: O3
- **Notes**: Reduces nesting but changes control flow structure

---

## Implementation Strategy

### Phase 1: Python Mods (2-3 weeks)
**Goal**: Implement 15 simple pattern-based mods

1. Start with simplest: `remove_extra_semicolon`, `remove_void_args`, `null_to_nullptr`
2. Progress to symbol-aware: `add_explicit`, `add_final_class`, `add_final_method`
3. Finish with complex patterns: `pragma_once`, `add_fallthrough`, `private_to_delete`

**Deliverable**: 15 new mods, battle-tested with existing validator infrastructure

### Phase 2: Clang-Tidy Integration (1-2 months)
**Goal**: Wrap clang-tidy checks as LevelUp mods

**Architecture**:
```python
class ClangTidyMod(BaseMod):
    def __init__(self, check_name: str, fix_name: str = None):
        self.check_name = check_name  # e.g., "modernize-use-auto"
        self.fix_name = fix_name or check_name

    def generate_refactorings(self, repo, symbols):
        # 1. Generate compile_commands.json for repo
        # 2. Run: clang-tidy -checks=<check> -fix -export-fixes=fixes.yaml
        # 3. Parse YAML fixes
        # 4. Convert each fix to RefactoringBase instance
        # 5. Yield refactorings
        # 6. Each refactoring creates GitCommit with ASM validation
```

**Implementation Steps**:
1. Create `ClangTidyMod` base class
2. Implement compilation database generation
3. Create YAML fix parser
4. Build fix-to-refactoring converter
5. Add individual mods by instantiating with check names
6. Test with existing clang-tidy checks first (const_method, use_auto)
7. Create custom checks for LevelUp-specific patterns

**Deliverable**: 32 mods leveraging clang-tidy ecosystem

### Phase 3: Local LLM Experimental (Ongoing)
**Goal**: Prototype LLM-based mod generation

**Architecture**:
```python
class LLMMod(BaseMod):
    def __init__(self, prompt_template: str, model: str = "codellama"):
        self.prompt_template = prompt_template
        self.model = model

    def generate_refactorings(self, repo, symbols):
        # 1. For each function/class in symbols:
        # 2. Extract code context (function body, call sites)
        # 3. Format prompt: prompt_template.format(context=context)
        # 4. Query local LLM (ollama API)
        # 5. Parse LLM response as code transformation
        # 6. Create RefactoringBase with transformation
        # 7. Yield refactoring
        # 8. ASM validation catches hallucinations/errors
```

**Implementation Steps**:
1. Set up ollama with codellama/deepseek-coder
2. Create LLM query infrastructure
3. Design prompt templates for each mod type
4. Implement response parsing (expect code snippets)
5. Start with `extract_constant` (bounded, testable)
6. Measure accuracy: % of LLM suggestions that pass ASM validation
7. Iterate on prompts based on validation failures
8. Expand to ownership analysis mods

**Deliverable**: 5 LLM-powered mods with measured accuracy metrics

---

## Success Metrics

### Validation Pass Rate
- **Python Mods**: Target 95%+ (deterministic transformations)
- **Clang-Tidy Mods**: Target 90%+ (proven tooling)
- **LLM Mods**: Target 60-80% (experimental, non-deterministic)

### Coverage
- **Total Smoke Tests**: 59
- **After Phase 1**: 18 covered (3 existing + 15 new)
- **After Phase 2**: 50 covered (+32 clang-tidy)
- **After Phase 3**: 55 covered (+5 LLM)
- **Remaining**: 4 tests (complex IDE-style refactorings)

### Performance
- **Python Mods**: <1 second per refactoring
- **Clang-Tidy Mods**: 1-5 seconds per refactoring (AST parsing)
- **LLM Mods**: 5-30 seconds per refactoring (LLM query latency)

---

## Future Considerations

### Chained Transformations
Some smoke tests demonstrate multi-step chains:
- **String View Chain**: `char*` → `const char*` → `inline` → `std::string_view`
- **Span Chain**: `(buffer, length)` → `inline` → `std::span`

**Strategy**: Implement as separate mods that can be run sequentially. Each step is independently validated.

### User-Defined Mods
Allow users to:
1. Provide custom clang-tidy checks (`.clang-tidy` config)
2. Write Python mod scripts (drop in `mods/custom/`)
3. Define LLM prompt templates for domain-specific refactorings

### Mod Composition
Build higher-level mods from primitives:
```python
class ModernizeStringsMod(CompositeMod):
    def __init__(self):
        self.mods = [
            AddConstToStringParamsMod(),
            StringViewMod(),
        ]
```

### Machine Learning Insights
After accumulating validation data:
- Analyze which refactorings have highest success rates
- Identify code patterns that commonly fail validation
- Train models to predict refactoring applicability

---

## Appendix: Quick Reference Table

| # | Mod Name | Test Case | Approach | Complexity | O-Level |
|---|----------|-----------|----------|------------|---------|
| 1 | document_function | document_function | Python | Low | O0 |
| 2 | add_explicit | add_explicit | Python | Low | O0 |
| 3 | add_final_class | add_final_class | Python | Low | O0 |
| 4 | add_final_method | add_final_method | Python | Low | O0 |
| 5 | remove_void_args | remove_void_args | Python | Very Low | O0 |
| 6 | remove_extra_semicolon | remove_extra_semicolon | Python | Very Low | O0 |
| 7 | remove_this_pointer | remove_this_pointer | Python | Low | O0 |
| 8 | null_to_nullptr | null_to_nullptr | Python | Low | O0 |
| 9 | bool_literals | bool_literals | Python | Low | O0 |
| 10 | typedef_to_using | typedef_to_using | Python | Low | O0 |
| 11 | pragma_once | pragma_once | Python | Medium | O0 |
| 12 | throw_to_noexcept | throw_to_noexcept | Python | Low | O0 |
| 13 | add_fallthrough | add_fallthrough | Python | Medium | O0 |
| 14 | add_inline_namespace | add_inline_namespace | Python | Medium | O0 |
| 15 | private_to_delete | private_to_delete | Python | Medium | O0 |
| 16 | const_param | const_param | Clang-Tidy | Medium | O0 |
| 17 | const_method | const_method | Clang-Tidy | Medium | O0 |
| 18 | string_literal_const | string_literal_const | Clang-Tidy | Low | O0 |
| 19 | string_view_add_const | string_view_add_const | Clang-Tidy | Low | O0 |
| 20 | use_default_ctor | use_default_ctor | Clang-Tidy | Medium | O0 |
| 21 | use_auto | use_auto | Clang-Tidy | Medium | O0 |
| 22 | trailing_return_type | trailing_return_type | Clang-Tidy | Low | O0 |
| 23 | use_enum_class | use_enum_class | Clang-Tidy | High | O0 |
| 24 | use_constexpr_var | use_constexpr_var | Clang-Tidy | Medium | O0 |
| 25 | use_constexpr_func | use_constexpr_func | Clang-Tidy | High | O3 |
| 26 | define_to_constexpr | define_to_constexpr | Clang-Tidy | Medium | O0 |
| 27 | define_func_to_constexpr | define_func_to_constexpr | Clang-Tidy | High | O3 |
| 28 | uniform_init | uniform_init | Clang-Tidy | Low | O0 |
| 29 | in_class_init | in_class_init | Clang-Tidy | Medium | O0 |
| 30 | delegating_ctor | delegating_ctor | Clang-Tidy | High | O3 |
| 31 | remove_dead_code | remove_dead_code | Clang-Tidy | Medium | O3 |
| 32 | remove_comments | remove_comments | Clang-Tidy | Low | O0 |
| 33 | remove_unused_param | remove_unused_param | Clang-Tidy | Medium | O3 |
| 34 | remove_unused_var | remove_unused_var | Clang-Tidy | Low | O3 |
| 35 | use_static_cast | use_static_cast | Clang-Tidy | Low | O0 |
| 36 | c_cast_to_static_cast | c_cast_to_static_cast | Clang-Tidy | Low | O0 |
| 37 | c_cast_to_const_cast | c_cast_to_const_cast | Clang-Tidy | Medium | O0 |
| 38 | typedef_func_ptr_to_using | typedef_func_ptr_to_using | Clang-Tidy | Low | O3 |
| 39 | explicit_integer_width | explicit_integer_width | Clang-Tidy | Medium | O0 |
| 40 | range_based_for | range_based_for | Clang-Tidy | High | O3 |
| 41 | unique_ptr_simple | unique_ptr_simple | Clang-Tidy | Medium | O3 |
| 42 | simplify_bool_comparison | simplify_bool_comparison | Clang-Tidy | Low | O3 |
| 43 | simplify_double_negation | simplify_double_negation | Clang-Tidy | Low | O3 |
| 44 | declare_at_assign | declare_at_assign | Clang-Tidy | Medium | O0 |
| 45 | sv_chain1_step3_string_view | sv_chain1_step3_string_view | Clang-Tidy | High | O3 |
| 46 | span_chain1_step2_to_span | span_chain1_step2_to_span | Clang-Tidy | Very High | O3 |
| 47 | extract_function | extract_function | LLM/Manual | Very High | O3 |
| 48 | extract_constant | extract_constant | LLM | High | O3 |
| 49 | pointer_to_reference | pointer_to_reference | LLM | High | O0 |
| 50 | add_owner | add_owner | LLM | Very High | O0 |
| 51 | add_non_owner | add_non_owner | LLM | Very High | O0 |
| 52 | unique_ptr_RAII | unique_ptr_RAII | LLM | Very High | O3 |

**Note**: Some test cases like `early_return`, `consolidate_returns` are style preferences with debatable value and are excluded from the priority list.

---

## Conclusion

The 59 validator smoke tests provide a comprehensive roadmap for LevelUp's mod development. By categorizing mods into Python (15), Clang-Tidy (32), and LLM (5) approaches, we can strategically build out modernization capabilities:

1. **Python mods** provide quick wins with deterministic transformations
2. **Clang-Tidy integration** leverages battle-tested AST analysis for complex patterns
3. **Local LLM mods** enable experimental semantic transformations with validation safety net

The ASM comparison validation architecture is the key enabler—it allows us to safely experiment with all three approaches, knowing that incorrect transformations will be automatically rejected.

**Recommended Priority**: Phase 1 (Python) → Phase 2 (Clang-Tidy) → Phase 3 (LLM)
