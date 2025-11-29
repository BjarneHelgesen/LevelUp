# Function Prototype Refactoring API

This package provides a comprehensive API for safely modifying C++ function prototypes with low risk of introducing errors. The API is designed to work with the Symbols classes from Doxygen XML parsing and handles edge cases like macros, inline comments, and type aliases.

## Overview

The API consists of:
- **Core refactoring**: `ChangeFunctionPrototypeRefactoring` - flexible, multi-purpose prototype modification
- **Specialized refactorings**: Focused, single-purpose refactorings with specific probability estimates
- **Utilities**: Parsing and modification helpers for prototype manipulation

## Entry Points

### 1. ChangeReturnTypeRefactoring
Changes the return type of a function.

**Probability of success**: 0.3 (medium - may break callers or change assembly)

**Usage**:
```python
from core.refactorings.function_prototype import ChangeReturnTypeRefactoring

refactoring = ChangeReturnTypeRefactoring(repo)
git_commit = refactoring.apply(function_symbol, "void")
```

### 2. RenameParameterRefactoring
Renames a function parameter (declaration only, not usage in implementation).

**Probability of success**: 0.85 (high - doesn't affect callers or assembly)

**Usage**:
```python
from core.refactorings.function_prototype import RenameParameterRefactoring

refactoring = RenameParameterRefactoring(repo)
git_commit = refactoring.apply(function_symbol, param_index=0, new_name="newName")
```

### 3. ChangeParameterTypeRefactoring
Changes the type of a specific parameter.

**Probability of success**: 0.25 (low - likely breaks callers)

**Usage**:
```python
from core.refactorings.function_prototype import ChangeParameterTypeRefactoring

refactoring = ChangeParameterTypeRefactoring(repo)
git_commit = refactoring.apply(function_symbol, param_index=1, new_type="const std::string&")
```

### 4. AddParameterRefactoring
Adds a new parameter to the function signature.

**Probability of success**: 0.2 (low - breaks callers unless default value provided)

**Usage**:
```python
from core.refactorings.function_prototype import AddParameterRefactoring

refactoring = AddParameterRefactoring(repo)
# Add at end
git_commit = refactoring.apply(function_symbol, "int", "newParam")
# Add at specific position
git_commit = refactoring.apply(function_symbol, "int", "newParam", position=1)
```

### 5. RemoveParameterRefactoring
Removes a parameter from the function signature.

**Probability of success**: 0.15 (very low - breaks callers)

**Usage**:
```python
from core.refactorings.function_prototype import RemoveParameterRefactoring

refactoring = RemoveParameterRefactoring(repo)
git_commit = refactoring.apply(function_symbol, param_index=2)
```

### 6. ChangeFunctionPrototypeRefactoring (Core API)
Flexible refactoring that can apply multiple changes at once using a PrototypeChangeSpec.

**Probability of success**: 0.5 (varies based on changes)

**Usage**:
```python
from core.refactorings.function_prototype import (
    ChangeFunctionPrototypeRefactoring,
    PrototypeChangeSpec
)

# Build change specification
spec = PrototypeChangeSpec()
spec.set_return_type("std::string")
spec.set_function_name("newFunctionName")
spec.change_parameter_type(0, "const char*")
spec.change_parameter_name(1, "newName")
spec.add_parameter("bool", "flag", position=-1)  # Add at end
spec.remove_parameter(2)

# Apply changes
refactoring = ChangeFunctionPrototypeRefactoring(repo)
git_commit = refactoring.apply(function_symbol, spec)
```

## Using in Mods

Mods generate refactorings using the generator pattern:

```python
from core.mods.base_mod import BaseMod
from core.refactorings.function_prototype import RenameParameterRefactoring
from core.doxygen.symbols.symbol_kind import SymbolKind

class ExampleMod(BaseMod):
    @staticmethod
    def get_id() -> str:
        return 'example_rename_params'

    @staticmethod
    def get_name() -> str:
        return 'Rename Function Parameters'

    def generate_refactorings(self, repo, symbols):
        refactoring = RenameParameterRefactoring(repo)

        # Find all functions
        all_symbols = symbols.get_all_symbols()

        for symbol in all_symbols:
            if symbol.kind == SymbolKind.FUNCTION:
                # Check if first parameter should be renamed
                if len(symbol.parameters) > 0:
                    param_type, param_name = symbol.parameters[0]

                    # Example: rename 'x' to 'value'
                    if param_name == 'x':
                        yield (refactoring, symbol, 0, 'value')
```

## How It Works

1. **Parse**: Uses `PrototypeParser` to find and parse function prototypes
   - Handles multi-line prototypes
   - Extracts return type, function name, parameters, qualifiers
   - Works with inline comments and macros

2. **Modify**: Uses `PrototypeModifier` to safely modify prototype text
   - Preserves formatting where possible
   - Handles edge cases (templates, pointers, references)
   - Regex-based replacement with careful boundary detection

3. **Validate**: Returns `GitCommit` if successful, `None` if unable to apply
   - Commits changes immediately (in-place modification)
   - Validators (ASM_O0/ASM_O3) check if changes are safe
   - Rollback occurs automatically if validation fails

## Safety Features

- **Precondition checks**: Validates file exists, line numbers are valid
- **Graceful failure**: Returns `None` instead of throwing exceptions
- **Boundary detection**: Uses `\b` regex to avoid partial matches
- **Comment preservation**: Strips comments during parsing, preserves in output
- **Template handling**: Tracks nesting depth when parsing parameter lists

## Probability Estimates

| Refactoring | Probability | Reason |
|-------------|-------------|---------|
| RenameParameter | 0.85 | High - only affects implementation, not callers |
| ChangeReturnType | 0.3 | Medium - may break callers or change assembly |
| ChangeParameterType | 0.25 | Low - likely breaks callers |
| AddParameter | 0.2 | Low - breaks callers unless default provided |
| RemoveParameter | 0.15 | Very low - definitely breaks callers |

Higher probabilities allow batching: when product of probabilities < 0.8, refactorings are batched and validated together.

## Limitations

- Only modifies function declaration, not call sites
- Does not update function implementation parameter usage
- Does not search for out-of-line definitions (separate from declaration)
- Template functions may require manual review
- Function pointers/references as parameters need careful handling

## Future Enhancements

Potential additions:
- Find and update all call sites when changing signatures
- Update parameter usage in function body when renaming
- Handle out-of-line definitions (search for matching signatures)
- Support for template parameter modifications
- Automatic default value generation for new parameters
