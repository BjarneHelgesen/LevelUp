# Mods Package

Code modernization transformations that generate validated refactorings for legacy C++ codebases.

## Purpose

Mods are high-level transformations (e.g., "remove all inline keywords") that generate multiple refactorings. Each mod analyzes the codebase using SymbolTable and yields refactorings to apply.

## Key Components

**BaseMod (base_mod.py)**
- Abstract base class defining mod interface
- Required methods:
  - `get_id()`: Stable string identifier (IMPORTANT: Never change once set)
  - `get_name()`: Human-readable name for UI
  - `generate_refactorings(repo, symbols) -> Iterator[Tuple[BaseRefactoring, ...]]`: Yields (refactoring_instance, *args) tuples

**ModFactory (mod_factory.py)**
- Enum-based registry using `ModType` enum
- `from_id(mod_id: str)`: Creates mod instance from ID
- `get_available_mods()`: Returns list with id and name for each mod

## Built-in Mods

**RemoveInlineMod (remove_inline_mod.py)**
- Removes `inline` keywords from function definitions
- Uses SymbolTable to find inline functions
- Generates `RemoveFunctionQualifier` refactorings

**AddOverrideMod (add_override_mod.py)**
- Adds `override` keywords to virtual function overrides
- Uses SymbolTable to find virtual functions that override base class methods
- Generates `AddFunctionQualifier` refactorings

**ReplaceMSSpecificMod (replace_ms_specific_mod.py)**
- Replaces MS-specific syntax with standards-compliant alternatives
- Examples: `__int64` → `long long`, `__declspec(dllexport)` → portable macros

**MSMacroReplacementMod (ms_macro_replacement.py)**
- Replaces Microsoft-specific macros with standard equivalents
- Pattern-based replacement using regex

## Adding a New Mod

1. Create class in this folder inheriting from `BaseMod`
2. Implement required methods:
   - `get_id()`: Stable string identifier (IMPORTANT: Never change once set)
   - `get_name()`: Human-readable name for UI
   - `generate_refactorings(repo, symbols)`: Generator that yields tuples
3. Each yielded tuple structure:
   ```python
   # Yield (refactoring_instance, *args)
   # The args are passed to refactoring.apply(*args)
   yield (RemoveFunctionQualifier(repo), symbol, "inline")
   ```
4. Import and use:
   - `repo`: Repo object for file operations and git commands
   - `symbols`: SymbolTable for finding functions, classes, etc.
   - Refactoring classes from `core.refactorings`
5. Add to `ModType` enum in `mod_factory.py`
6. ID automatically available in UI via `/api/available/mods`

## Example Mod Implementation

```python
from core.mods.base_mod import BaseMod
from core.refactorings.remove_function_qualifier import RemoveFunctionQualifier

class RemoveInlineMod(BaseMod):
    @staticmethod
    def get_id() -> str:
        return "remove_inline"

    @staticmethod
    def get_name() -> str:
        return "Remove Inline Keywords"

    def generate_refactorings(self, repo, symbols):
        # Find all inline functions
        for symbol in symbols.get_all_symbols():
            if "inline" in symbol.qualifiers:
                # Yield refactoring instance and its arguments
                yield (RemoveFunctionQualifier(repo), symbol, "inline")
```

## Testing

Run tests: `pytest core/mods/tests/`

Tests verify:
- Mod registration and factory creation
- Refactoring generation logic
- Symbol filtering and selection
- Integration with SymbolTable
