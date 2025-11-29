# Parsers Package

C++ code analysis using Doxygen XML output to extract symbol information for refactoring.

## Purpose

Parses C++ codebases to extract symbol metadata (functions, classes, enums, etc.) that mods use to identify refactoring opportunities. Uses Doxygen XML output for accurate symbol information.

## Key Components

**DoxygenRunner (doxygen_runner.py)**
- Runs Doxygen to generate XML output for a repository
- Auto-generates Doxyfile with XML output enabled
- Disables macro expansion for accurate source location
- Output stored in `workspace/doxygen/{repo_name}/xml/`
- Creates `.doxygen_stale` marker when repo changes detected

**DoxygenParser (doxygen_parser.py)**
- Parses Doxygen XML files to extract symbol information
- Handles:
  - Functions (free functions, methods, constructors)
  - Classes and structs
  - Enums and enum values
  - Namespaces
  - Typedefs and using declarations
- Returns `Symbol` objects with metadata

**Symbol (symbol.py)**
- Data class holding symbol metadata
- Key fields:
  - `name`: Symbol name (e.g., "myFunction")
  - `qualified_name`: Fully qualified name (e.g., "MyNamespace::MyClass::myFunction")
  - `file_path`: Relative path to source file
  - `line_start`, `line_end`: Source location
  - `prototype`: Function signature or declaration
  - `qualifiers`: List of qualifiers (e.g., ["inline", "static"])
  - `kind`: Symbol type (function, class, enum, etc.)
  - `dependencies`: Other symbols this symbol depends on

**SymbolTable (symbol_table.py)**
- Manages all symbols for a repository
- Incremental invalidation: marks files dirty after modification
- Methods:
  - `get_all_symbols()`: Returns all symbols
  - `get_symbols_in_file(file_path)`: Returns symbols in specific file
  - `get_symbol_by_name(name)`: Finds symbol by name
  - `invalidate_file(file_path)`: Marks file dirty (symbols need refresh)
  - `invalidate_all()`: Marks all symbols dirty (full refresh needed)
- Lazy loading: only parses Doxygen XML when symbols are requested
- Stale detection: regenerates Doxygen if `.doxygen_stale` marker exists

## Workflow

1. **Initial Setup**: When repo added, `DoxygenRunner.run()` generates XML
2. **Symbol Loading**: `SymbolTable` parses XML lazily when mods request symbols
3. **Refactoring**: Mods query `SymbolTable` to find refactoring targets
4. **Invalidation**: After file modifications, `SymbolTable.invalidate_file()` marks symbols dirty
5. **Regeneration**: If `.doxygen_stale` marker exists, Doxygen re-runs before next mod

## Usage in Mods

```python
def generate_refactorings(self, repo, symbols):
    # Query SymbolTable for specific symbols
    for symbol in symbols.get_all_symbols():
        if symbol.kind == "function" and "inline" in symbol.qualifiers:
            # Generate refactoring for this symbol
            yield (RemoveFunctionQualifier(repo), symbol, "inline")
```

## Extending Symbol Extraction

To extract additional symbol metadata:
1. Identify Doxygen XML element in `workspace/doxygen/{repo}/xml/`
2. Add parsing logic to `DoxygenParser._parse_*()` methods
3. Add field to `Symbol` class
4. Update tests to verify new field extraction

## Testing

Run tests: `pytest core/parsers/tests/`

Tests verify:
- Doxygen execution and XML generation
- XML parsing for various symbol types
- SymbolTable querying and filtering
- Incremental invalidation
- Stale detection and regeneration
