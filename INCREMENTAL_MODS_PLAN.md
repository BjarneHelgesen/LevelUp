# Incremental Mods Implementation Plan

## Overview

Transform LevelUp to apply ALL mods incrementally: identify individual code changes, apply them one-by-one with validation, and accumulate only the validated changes into a single final commit.

**Key Constraint**: No backwards compatibility needed - all mods will be converted to incremental pattern.

**Performance Assumption**: Compilation will be optimized later (RAM disk, caching, etc.) - don't optimize now, focus on correctness.

---

## Architecture Changes

### 1. New Core Abstraction: `ChangeTarget`

**File**: `core/change_target.py`

```python
from pathlib import Path
from typing import Any, Dict, Optional

class ChangeTarget:
    """Represents a single atomic change within a file"""

    def __init__(
        self,
        file: Path,
        location: int,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file = file
        self.location = location  # line number or byte offset
        self.description = description  # "Add const to MyClass::getName()"
        self.metadata = metadata or {}  # mod-specific data

    def __repr__(self) -> str:
        return f"ChangeTarget(file={self.file.name}, location={self.location}, description={self.description})"
```

**Purpose**:
- Represents one atomic change (e.g., adding const to one method)
- Contains enough info to describe the change in logs and UI
- Metadata stores mod-specific data (method signature, regex match, etc.)

---

### 2. Updated `BaseMod` Interface

**File**: `core/mods/base_mod.py`

**Current**:
```python
@abstractmethod
def apply(self, source_file: Path) -> None:
    """Apply mod to source file in-place"""
```

**New**:
```python
@abstractmethod
def find_targets(self, source_file: Path) -> List[ChangeTarget]:
    """Find all individual changes this mod can make in the file"""
    pass

@abstractmethod
def apply_single(self, target: ChangeTarget) -> None:
    """Apply one specific change to the file"""
    pass
```

**Changes**:
- Remove `apply()` method entirely - no longer used
- Add `find_targets()` to identify all possible changes in a file
- Add `apply_single()` to apply exactly one change
- Each mod must implement both methods

**Example - RemoveInlineMod**:
```python
def find_targets(self, source_file: Path) -> List[ChangeTarget]:
    content = source_file.read_text(encoding='utf-8', errors='ignore')
    targets = []

    # Find each occurrence of 'inline' keyword
    for line_num, line in enumerate(content.splitlines(), 1):
        if 'inline' in line:
            targets.append(ChangeTarget(
                file=source_file,
                location=line_num,
                description=f"Remove 'inline' from line {line_num}",
                metadata={'line_number': line_num}
            ))

    return targets

def apply_single(self, target: ChangeTarget) -> None:
    # Read file
    lines = target.file.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)

    # Modify only the target line
    line_num = target.metadata['line_number']
    lines[line_num - 1] = lines[line_num - 1].replace('inline', '', 1)

    # Write back
    target.file.write_text(''.join(lines), encoding='utf-8')
```

---

### 3. New `ModProcessor.process_mod()` Implementation

**File**: `core/mod_processor.py`

**Complete replacement of current logic**:

```python
def process_mod(self, mod_request: ModRequest) -> Result:
    mod_id = mod_request.id
    logger.info(f"Processing mod {mod_id} incrementally: {mod_request.description}")

    try:
        # 1. Initialize repository
        repo = Repo(
            url=mod_request.repo_url,
            repos_folder=self.repos_path,
            git_path=self.git_path
        )
        repo.ensure_cloned()
        repo.prepare_work_branch()

        # 2. Create temporary experiment branch
        temp_branch = f"levelup-temp-{mod_id[:8]}"
        repo.create_branch(temp_branch)
        repo.checkout_branch(temp_branch)

        # 3. Find all C/C++ files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo.repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        # 4. Collect all change targets from all files
        all_targets = []
        for source_file in source_files:
            targets = mod_request.mod_instance.find_targets(source_file)
            all_targets.extend(targets)

        logger.info(f"Found {len(all_targets)} potential changes across {len(source_files)} files")

        # 5. Process each change incrementally
        accepted_targets = []
        rejected_targets = []

        for idx, target in enumerate(all_targets, 1):
            logger.debug(f"Processing change {idx}/{len(all_targets)}: {target.description}")

            # 5a. Compile original
            original = self.compiler.compile_file(target.file)
            if not original.asm_output:
                logger.warning(f"Failed to compile original {target.file.name}, skipping change")
                rejected_targets.append(target)
                continue

            # 5b. Apply single change
            mod_request.mod_instance.apply_single(target)

            # 5c. Compile modified
            modified = self.compiler.compile_file(target.file)
            if not modified.asm_output:
                logger.warning(f"Failed to compile after change, rejecting: {target.description}")
                rejected_targets.append(target)
                repo.reset_hard('HEAD')  # Revert this change
                continue

            # 5d. Validate
            is_valid = self.asm_validator.validate(original, modified)

            if is_valid:
                # 5e. Keep change: make temporary commit
                repo.commit(f"LevelUp-temp: {target.description}")
                accepted_targets.append(target)
                logger.debug(f"Accepted: {target.description}")
            else:
                # 5f. Reject change: revert file
                repo.reset_hard('HEAD')
                rejected_targets.append(target)
                logger.debug(f"Rejected: {target.description}")

        # 6. Merge accepted changes into work branch
        if accepted_targets:
            logger.info(f"Merging {len(accepted_targets)} accepted changes into work branch")
            repo.checkout_branch(repo.work_branch)
            repo.merge_squash(temp_branch)

            # Create final commit message
            mod_name = mod_request.mod_instance.get_name()
            commit_msg = f"LevelUp: Applied {mod_name} - {len(accepted_targets)} changes"
            repo.commit(commit_msg)
            repo.push()

            # Clean up temp branch
            repo.delete_branch(temp_branch)

            status = ResultStatus.SUCCESS if not rejected_targets else ResultStatus.PARTIAL
            return Result(
                status=status,
                message=mod_name,
                accepted_changes=accepted_targets,
                rejected_changes=rejected_targets
            )
        else:
            # No changes accepted
            logger.warning(f"No changes accepted for mod {mod_id}")
            repo.checkout_branch(repo.work_branch)
            repo.delete_branch(temp_branch)

            return Result(
                status=ResultStatus.FAILED,
                message="No changes passed validation",
                rejected_changes=rejected_targets
            )

    except Exception as e:
        logger.exception(f"Error processing mod {mod_id}: {e}")
        try:
            repo.checkout_branch(repo.work_branch)
            repo.delete_branch(temp_branch, force=True)
        except:
            pass  # Best effort cleanup
        return Result(
            status=ResultStatus.ERROR,
            message=str(e)
        )
```

**Key differences from current**:
- No more bulk apply → bulk validate → all-or-nothing commit
- Each change gets individual validation before being kept
- Temporary branch holds incremental commits during processing
- Squash merge at end produces single clean commit on work branch
- Tracks accepted vs rejected changes separately

---

### 4. Updated `Result` Class

**File**: `core/result.py`

**Add new fields**:
```python
class Result:
    def __init__(
        self,
        status: ResultStatus,
        message: str,
        timestamp: Optional[str] = None,
        validation_results: Optional[List['ValidationResult']] = None,
        accepted_changes: Optional[List['ChangeTarget']] = None,  # NEW
        rejected_changes: Optional[List['ChangeTarget']] = None   # NEW
    ):
        # ... existing init code ...
        self.accepted_changes = accepted_changes
        self.rejected_changes = rejected_changes

    def to_dict(self) -> Dict[str, Any]:
        result_dict = {
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp
        }

        if self.validation_results is not None:
            result_dict['validation_results'] = [vr.to_dict() for vr in self.validation_results]

        # NEW: Serialize change targets
        if self.accepted_changes is not None:
            result_dict['accepted_changes'] = [
                {'file': str(t.file), 'location': t.location, 'description': t.description}
                for t in self.accepted_changes
            ]

        if self.rejected_changes is not None:
            result_dict['rejected_changes'] = [
                {'file': str(t.file), 'location': t.location, 'description': t.description}
                for t in self.rejected_changes
            ]

        return result_dict
```

**Purpose**:
- Track which specific changes were accepted/rejected
- Provide detailed feedback to user in UI
- Keep `validation_results` for backwards compatibility during transition

---

### 5. Extended `Repo` Class

**File**: `core/repo/repo.py`

**Add new methods**:
```python
def create_branch(self, branch_name: str) -> None:
    """Create a new branch without checking it out"""
    self._run_git(['branch', branch_name])

def merge_squash(self, branch: str) -> None:
    """Merge branch with --squash (all commits become one)"""
    self._run_git(['merge', '--squash', branch])

def delete_branch(self, branch: str, force: bool = False) -> None:
    """Delete a branch"""
    flag = '-D' if force else '-d'
    self._run_git(['branch', flag, branch])
```

**Purpose**:
- Support temporary branch workflow
- Enable squash merging for clean final commits
- Allow branch cleanup after processing

---

### 6. Migration Path for Existing Mods

**All mods must be converted** (no backwards compatibility):

#### RemoveInlineMod
**Current**: Replaces all 'inline' in file at once
**New**: Find each 'inline' occurrence → apply individually

#### AddOverrideMod
**Current**: Adds 'override' to all virtual methods at once
**New**: Find each virtual method → add 'override' individually

#### ReplaceMSSpecificMod
**Current**: Replaces all MS-specific syntax patterns at once
**New**: Find each pattern occurrence → replace individually

**Implementation strategy**:
1. Start with RemoveInlineMod (simplest)
2. Convert AddOverrideMod
3. Convert ReplaceMSSpecificMod
4. Test each conversion thoroughly

---

## Implementation Order

### Phase 1: Core Infrastructure
1. Create `core/change_target.py` with ChangeTarget class
2. Update `core/result.py` with new fields (accepted/rejected changes)
3. Add new methods to `core/repo/repo.py` (create_branch, merge_squash, delete_branch)

### Phase 2: BaseMod Interface Change
4. Update `core/mods/base_mod.py`:
   - Remove `apply()` method
   - Add `find_targets()` abstract method
   - Add `apply_single()` abstract method

### Phase 3: ModProcessor Rewrite
5. Replace `core/mod_processor.py` process_mod() with incremental implementation
6. Remove ModHandler usage (each mod applies its own changes)

### Phase 4: Mod Conversions
7. Convert RemoveInlineMod to incremental pattern
8. Test RemoveInlineMod thoroughly with ExampleCPP repo
9. Convert AddOverrideMod to incremental pattern
10. Convert ReplaceMSSpecificMod to incremental pattern

### Phase 5: Cleanup
11. Update all tests to work with new pattern
12. Update documentation (CLAUDE.md files)
13. Update UI to display accepted/rejected changes

---

## Testing Strategy

**For each converted mod**:
1. Run against ExampleCPP test repository
2. Verify:
   - All valid changes are accepted
   - Invalid changes are rejected
   - Final commit contains only accepted changes
   - Work branch is clean after processing
   - No temp branches left behind
3. Check logs for clear per-change feedback

**Integration tests**:
- Test mods that find 0 changes (no-op case)
- Test mods where all changes fail validation
- Test mods with mix of accepted/rejected changes
- Test error handling (repo cleanup on exceptions)

---

## Git Branch Strategy

**Workflow for each mod run**:
```
main (or master)
  ↓
levelup-work (persistent work branch)
  ↓ create temp branch
levelup-temp-{mod_id} (temporary experiment branch)
  ↓ make incremental commits
  [commit 1: change A accepted]
  [commit 2: change B accepted]
  [commit 3: change C accepted]
  ↓ squash merge back to levelup-work
levelup-work
  [single commit: "LevelUp: Applied mod X - 3 changes"]
  ↓ push to remote
remote/levelup-work
```

**Cleanup**:
- Delete `levelup-temp-{mod_id}` after successful merge
- Force delete on error (best effort)

---

## UI Changes (Future)

**Mod status display enhancements**:
- Show "Processing change 15/47..." during execution
- Display accepted/rejected change counts in completed mods
- Expandable details showing specific changes:
  ```
  ✓ Remove 'inline' from MyClass::foo() at line 42
  ✓ Remove 'inline' from MyClass::bar() at line 87
  ✗ Remove 'inline' from Helper::baz() at line 123 (validation failed)
  ```

---

## Performance Considerations

**Current reality**: Compilation is slow (will be optimized later)

**Implications for now**:
- Don't try to optimize compilation in this phase
- Accept that processing 100 changes = 100 compile cycles
- Focus on correctness and clean architecture
- Keep door open for future optimizations:
  - RAM disk for repos/temp files
  - Cached compilation units (incremental compilation)
  - Parallel validation of independent changes
  - Batch validation of changes in different files

**Design decisions supporting future optimization**:
- ChangeTarget is independent (can be validated in parallel)
- Each change operates on single file (enables file-level parallelism)
- Compilation is abstracted in Compiler class (can swap implementation)

---

## Success Criteria

1. All mods use incremental pattern (find_targets + apply_single)
2. Each change is validated independently before being kept
3. Final commit contains only validated changes (clean history)
4. Detailed feedback on accepted/rejected changes
5. No temporary branches left behind after processing
6. All existing tests pass (after updating for new pattern)
7. RemoveInlineMod, AddOverrideMod, ReplaceMSSpecificMod all work incrementally

---

## Risk Mitigation

**Risk**: Partial processing leaves repository in bad state
**Mitigation**: All work happens on temp branch; checkout work branch + delete temp branch on any error

**Risk**: Change N depends on change N-1 being applied first
**Mitigation**: Each change validated against original baseline (not accumulated changes) - no dependencies

**Risk**: Too many commits on temp branch (Git performance)
**Mitigation**: Squash merge produces single commit; temp branch deleted after

**Risk**: Incremental approach misses cross-file dependencies
**Mitigation**: ASM validation catches this (if change breaks compilation or changes ASM, it's rejected)

---

## Notes for Implementation

- Import ChangeTarget in mod files: `from core.change_target import ChangeTarget`
- Import type for Result: `from typing import List` and `Optional[List[ChangeTarget]]`
- Temp branch naming: Use first 8 chars of mod_id for uniqueness
- Logging: DEBUG level for each change, INFO for summary counts
- Error handling: Always cleanup temp branch (use try/finally)
- Validation: Use ASM validator by default (SourceDiffValidator removed from plan)
