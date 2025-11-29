# Refactorings Package

Atomic code transformations that modify files and create validated git commits.

## Purpose

Refactorings are low-level, atomic transformations (e.g., "remove inline keyword from function X") that:
1. Modify source file(s) in-place
2. Create a git commit
3. Specify which validator to use for regression detection
4. Return `GitCommit` on success or `None` if cannot apply

## Key Components

**RefactoringBase (refactoring_base.py)**
- Abstract base class defining refactoring interface
- Required methods:
  - `get_probability_of_success() -> float`: Return 0.0-1.0 confidence (e.g., 0.9 for safe changes)
  - `apply(*args) -> Optional[GitCommit]`: Implement the transformation
- Each refactoring receives `repo` in `__init__` for file/git operations

**RemoveFunctionQualifier (remove_function_qualifier.py)**
- Removes qualifiers (e.g., `inline`, `static`) from function definitions
- Validates qualifier exists before removal
- Uses ASM O0 validation by default

**AddFunctionQualifier (add_function_qualifier.py)**
- Adds qualifiers (e.g., `override`) to function definitions
- Validates qualifier doesn't already exist
- Uses ASM O0 validation by default

**QualifierType (qualifier_type.py)**
- Enum for function qualifiers: `INLINE`, `STATIC`, `OVERRIDE`, etc.
- Used by qualifier refactorings for type safety

**GitCommit (../repo/git_commit.py)**
- Represents single atomic git commit created by refactorings
- Fields:
  - `validator_type`: String ID of validator to use (e.g., ValidatorId.ASM_O0)
  - `affected_symbols`: List of symbols modified
  - `probability_of_success`: Float 0.0-1.0
- Methods:
  - `rollback()`: Reverts commit if validation fails

## Adding a New Refactoring

1. Create class in this folder inheriting from `RefactoringBase`
2. Implement required methods:
   - `get_probability_of_success() -> float`: Return confidence level
   - `apply(*args) -> Optional[GitCommit]`: Implement transformation
3. In `apply()` method:
   - Validate preconditions (return `None` if cannot apply)
   - Modify file(s) in-place using `repo` methods
   - Create and return `GitCommit` with validator_type and affected_symbols
4. Choose validator based on change safety:
   - `ValidatorId.ASM_O0`: Most changes (lenient, catches semantic changes)
   - `ValidatorId.ASM_O3`: Stricter validation (catches optimization-affecting changes)

## Example Refactoring Implementation

```python
from core.refactorings.refactoring_base import RefactoringBase
from core.repo.git_commit import GitCommit
from core.validators.validator_id import ValidatorId

class RemoveFunctionQualifier(RefactoringBase):
    def __init__(self, repo):
        self.repo = repo

    def get_probability_of_success(self) -> float:
        return 0.9  # High confidence

    def apply(self, symbol, qualifier: str) -> Optional[GitCommit]:
        # Validate preconditions
        if qualifier not in symbol.prototype:
            return None  # Cannot apply

        # Read file
        file_path = self.repo.git_path / symbol.file_path
        content = file_path.read_text()

        # Modify content (simplified)
        new_content = content.replace(f"{qualifier} ", "")
        file_path.write_text(new_content)

        # Create commit
        self.repo.commit(f"Remove {qualifier} from {symbol.name}")

        # Return GitCommit for validation
        return GitCommit(
            validator_type=ValidatorId.ASM_O0,
            affected_symbols=[symbol],
            probability_of_success=self.get_probability_of_success()
        )
```

## Validation Flow

1. Refactoring modifies file and creates commit
2. Returns `GitCommit` specifying which validator to use
3. ModProcessor compiles original and modified versions
4. Validator compares outputs (e.g., assembly comparison)
5. If valid: keep commit; if invalid: call `commit.rollback()` to revert

## Testing

Run tests: `pytest core/refactorings/tests/`

Tests verify:
- Precondition validation
- File modification correctness
- GitCommit creation with proper validator
- Rollback functionality
- Edge cases and error handling
