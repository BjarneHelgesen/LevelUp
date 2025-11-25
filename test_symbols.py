"""
Test script to verify Symbol parsing from Doxygen XML.
"""

from pathlib import Path
from core.doxygen import DoxygenRunner, DoxygenParser, Symbol, SymbolKind

# Test with ExampleCPP repository
repo_path = Path("workspace/repos/ExampleCPP")

if not repo_path.exists():
    print(f"Repository not found at {repo_path}")
    exit(1)

print(f"Testing Doxygen Symbol parsing with {repo_path}")
print("=" * 80)

# Run Doxygen to generate XML
print("\n1. Running Doxygen to generate XML...")
runner = DoxygenRunner()
if not runner.is_available():
    print("ERROR: Doxygen not found on system")
    exit(1)

try:
    xml_unexpanded, xml_expanded = runner.run(repo_path)
    print(f"   ✓ XML generated at {xml_unexpanded}")
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# Parse the XML
print("\n2. Parsing Doxygen XML...")
parser = DoxygenParser(xml_unexpanded, xml_expanded)
try:
    parser.parse()
    print(f"   ✓ XML parsed successfully")
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Get statistics
functions = parser.get_all_functions()
symbols = parser.get_all_symbols()

print("\n3. Statistics:")
print(f"   Functions: {len(functions)}")
print(f"   Symbols: {len(symbols)}")

# Show symbols by kind
print("\n4. Symbols by kind:")
for kind in [SymbolKind.CLASS, SymbolKind.STRUCT, SymbolKind.ENUM]:
    kind_symbols = parser.get_symbols_by_kind(kind)
    print(f"   {kind}: {len(kind_symbols)}")
    for symbol in kind_symbols[:3]:  # Show first 3
        print(f"      - {symbol.qualified_name} ({symbol.file_path}:{symbol.line_start}-{symbol.line_end})")

# Test line number queries
print("\n5. Testing line number extraction:")
for symbol in symbols[:5]:
    print(f"   {symbol.kind}: {symbol.qualified_name}")
    print(f"      Location: {symbol.file_path}:{symbol.line_start}-{symbol.line_end}")
    if symbol.dependencies:
        print(f"      Dependencies: {', '.join(list(symbol.dependencies)[:3])}")

# Test file-based queries
print("\n6. Testing file-based queries:")
all_files = list(set(s.file_path for s in symbols if s.file_path))
if all_files:
    test_file = all_files[0]
    file_symbols = parser.get_symbols_in_file(test_file)
    print(f"   File: {test_file}")
    print(f"   Symbols in file: {len(file_symbols)}")
    for symbol in file_symbols[:5]:
        print(f"      - {symbol.kind}: {symbol.name} (lines {symbol.line_start}-{symbol.line_end})")

# Test enum values
print("\n7. Testing enum parsing:")
enums = parser.get_symbols_by_kind(SymbolKind.ENUM)
for enum_symbol in enums[:3]:
    print(f"   {enum_symbol.qualified_name} ({enum_symbol.file_path}:{enum_symbol.line_start}-{enum_symbol.line_end})")
    if enum_symbol.enum_values:
        print(f"      Values: {', '.join([v[0] for v in enum_symbol.enum_values[:5]])}")

# Test class/struct with base classes
print("\n8. Testing class/struct inheritance:")
classes = parser.get_symbols_by_kind(SymbolKind.CLASS)
structs = parser.get_symbols_by_kind(SymbolKind.STRUCT)
for symbol in (classes + structs)[:3]:
    print(f"   {symbol.kind}: {symbol.qualified_name}")
    if symbol.base_classes:
        print(f"      Base classes: {', '.join(symbol.base_classes)}")
    print(f"      Members: {len(symbol.members)}")

print("\n" + "=" * 80)
print("✓ All tests completed successfully!")
