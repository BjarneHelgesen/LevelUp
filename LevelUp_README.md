# LevelUp.h - Custom unique_ptr Implementation

## Overview

`LevelUp.h` is automatically force-included in all compiled C++ code in the LevelUp system. It provides `LevelUp::unique_ptr<T>`, which can be configured to use either:
- A custom, simple implementation (default)
- The standard library `std::unique_ptr` (via preprocessor define)

## Usage

All compiled code automatically has access to `LevelUp::unique_ptr<T>` without needing to include any headers:

```cpp
void example() {
    // Create a unique_ptr
    LevelUp::unique_ptr<int> ptr1(new int(42));

    // Use make_unique
    auto ptr2 = LevelUp::make_unique<int>(100);

    // Array specialization
    LevelUp::unique_ptr<int[]> arr(new int[10]);
    arr[0] = 1;
}
```

## Choosing the Implementation

### Default: Custom LevelUp Implementation

By default, `LevelUp::unique_ptr` uses a simple, correct implementation that provides all standard unique_ptr functionality:
- Single object and array specializations
- Move semantics (no copying)
- All standard operations: `get()`, `release()`, `reset()`, `operator*`, `operator->`, `operator bool`
- `make_unique` helper functions

This implementation is simpler and more straightforward than `std::unique_ptr` but may be less optimized.

### Using std::unique_ptr

To use the standard library implementation instead, define `LEVELUP_USE_STD_UNIQUE_PTR` when compiling:

**MSVC:**
```bash
# Add to compiler flags
/DLEVELUP_USE_STD_UNIQUE_PTR
```

**Clang:**
```bash
# Add to compiler flags
-DLEVELUP_USE_STD_UNIQUE_PTR
```

**In Python (compile_file):**
```python
compiler.compile_file(
    source_file,
    additional_flags="/DLEVELUP_USE_STD_UNIQUE_PTR",  # MSVC
    # or
    additional_flags="-DLEVELUP_USE_STD_UNIQUE_PTR",  # Clang
    optimization_level=0
)
```

When this define is set, `LevelUp::unique_ptr<T>` becomes an alias to `std::unique_ptr<T>`, providing access to all standard library optimizations and features.

## Implementation Details

The header uses conditional compilation:

```cpp
#ifdef LEVELUP_USE_STD_UNIQUE_PTR
    // Use std::unique_ptr implementation
    template<typename T>
    using unique_ptr = std::unique_ptr<T>;
#else
    // Use custom LevelUp implementation
    template<typename T>
    class unique_ptr { /* ... */ };
#endif
```

## Force-Include Configuration

The compilers are configured to automatically include `LevelUp.h` before any source code:

- **MSVC**: Uses `/FI` flag (core/compilers/msvc_compiler.py:31)
- **Clang**: Uses `-include` flag (core/compilers/clang_compiler.py:28-29)

This means no source file needs to explicitly `#include "LevelUp.h"` - it's always available.

## Use Cases

**When to use the custom implementation:**
- Default behavior - no additional flags needed
- Testing simple, readable code
- Understanding unique_ptr mechanics
- Maximum code clarity

**When to use std::unique_ptr:**
- Need standard library optimizations
- Compatibility with std library features (custom deleters, etc.)
- Production code requiring maximum performance
- Comparing assembly output between implementations
