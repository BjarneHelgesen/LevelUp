# Validators Package

Regression detection through assembly comparison and other validation strategies.

## Purpose

Ensures code transformations produce functionally identical output by comparing assembly, AST, or running tests. Primary validation method is assembly comparison at different optimization levels.

## Key Components

**BaseValidator (base_validator.py)**
- Abstract base class defining validator interface
- Required methods:
  - `get_id()`: Stable string identifier
  - `get_name()`: Human-readable name
  - `get_optimization_level()`: Which compiler optimization level to use (0-3)
  - `validate(original: CompiledFile, modified: CompiledFile) -> bool`: Compare outputs

**ASMValidator (asm_validator.py)**
- Assembly comparison validator (primary regression detection)
- `ASMValidatorO0`: Compares at O0 (no optimization) - ID: `asm_o0`
- `ASMValidatorO3`: Compares at O3 (full optimization) - ID: `asm_o3`
- Both inherit from `BaseASMValidator` with shared comparison logic
- Takes compiler instance in `__init__` to support different compilers
- Validation logic:
  - `_extract_functions()`: Parses PROC/ENDP blocks from assembly
  - `_normalize_body()`: Canonicalizes identifiers (mangled names, labels, data refs)
  - `_function_bodies_match()`: Compares normalized function bodies
- Handles COMDAT functions (inline functions that linker can discard)
- Conservative: rejects if function bodies don't match exactly

**ValidatorFactory (validator_factory.py)**
- Enum-based registry using `ValidatorType` enum
- `from_id(validator_id: str, compiler=None)`: Creates instance from ID
- Takes optional compiler; if None, uses configured compiler from `get_compiler()`
- `get_available_validators()`: Returns list with id and name for each validator

**ValidatorId (validator_id.py)**
- Constants for validator IDs: `ASM_O0`, `ASM_O3`
- Used by refactorings to specify which validator to use when creating GitCommit
- Prefer these constants over raw strings for type safety

## Adding a New Validator

1. Create class in this folder inheriting from `BaseValidator`
2. Implement required methods:
   - `get_id()`: Stable string identifier (IMPORTANT: Never change once set)
   - `get_name()`: Human-readable name for UI
   - `get_optimization_level()`: Return 0-3 for compiler optimization level
   - `validate(original: CompiledFile, modified: CompiledFile) -> bool`: Compare and return True if identical
3. Add to `ValidatorType` enum in `validator_factory.py`
4. Add constant to `validator_id.py` if needed
5. ID automatically available in UI via `/api/available/validators`

## Usage by Refactorings

Refactorings specify which validator to use when creating `GitCommit`:

```python
from core.validators.validator_id import ValidatorId

# In refactoring's apply() method:
commit = GitCommit(
    validator_type=ValidatorId.ASM_O0,  # or ASM_O3 for stricter validation
    affected_symbols=[symbol],
    probability_of_success=0.9
)
```

## Testing

Run tests: `pytest core/validators/tests/`

Tests verify:
- Assembly parsing and normalization
- Function extraction from PROC/ENDP blocks
- Validation accuracy (accepts identical, rejects different)
- Cross-compiler compatibility
