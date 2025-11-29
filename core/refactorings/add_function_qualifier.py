"""
AddFunctionQualifier refactoring - adds a qualifier to a function.
"""

from typing import Optional, TYPE_CHECKING
from pathlib import Path

from .base_refactoring import BaseRefactoring
from ..repo.git_commit import GitCommit
from ..validators.validator_id import ValidatorId
from .. import logger

if TYPE_CHECKING:
    from ..parsers.symbols import BaseSymbol


class AddFunctionQualifier(BaseRefactoring):
    """
    Add qualifier (const, noexcept, override, etc.) to a function.
    """

    def get_probability_of_success(self) -> float:
        """Safe refactoring: adding qualifiers preserves semantics - high confidence."""
        return 0.9

    def apply(self, symbol: 'BaseSymbol', qualifier: str) -> Optional[GitCommit]:
        """
        Add qualifier to specific function at given line number.

        Args:
            symbol: Symbol object containing function metadata
            qualifier: Qualifier to add (e.g., 'override', 'const', 'noexcept')

        Returns:
            GitCommit object if successful, None if refactoring cannot be applied
        """
        try:
            file_path = Path(symbol.file_path)
            if not file_path.is_absolute():
                file_path = self.repo.repo_path / file_path
            if not file_path.exists():
                return None

            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines(keepends=True)

            line_number = symbol.line_start
            if line_number < 1 or line_number > len(lines):
                return None

            line = lines[line_number - 1]

            # Different qualifiers need different placements:
            # - const, noexcept, override, final: after ) before { or ;
            # - [[nodiscard]]: before return type

            # Handle [[nodiscard]] separately - it goes before the return type
            if qualifier.startswith('[[') and qualifier.endswith(']]'):
                # Check if already exists
                if qualifier in line:
                    return None
                # Find return type and insert before it
                # Look for patterns like "int func()" or "virtual int func()"
                import re
                # Match: (optional virtual/inline/etc) (return_type) (function_name)(
                match = re.search(r'^(\s*(?:virtual\s+|inline\s+|static\s+)*)', line)
                if match:
                    prefix = match.group(1)
                    modified_line = prefix + qualifier + ' ' + line[len(prefix):]
                    lines[line_number - 1] = modified_line
                else:
                    return None
            else:
                # For method qualifiers (const, noexcept, override, final)
                # Check if qualifier already exists as a standalone word
                import re
                if re.search(r'\b' + re.escape(qualifier) + r'\b', line):
                    return None

                # For override/final qualifiers, detect out-of-line definitions
                # These qualifiers only apply to in-class declarations, not definitions
                # Out-of-line definitions have ClassName:: in them
                if qualifier in ['override', 'final'] and '::' in line:
                    # This is an out-of-line definition - find the in-class declaration
                    # Search backwards for the in-class declaration
                    # Pattern: look for same function name without ::, ending in ; or { }
                    func_name = symbol.name
                    class_name = symbol.qualified_name.rsplit('::', 1)[0] if '::' in symbol.qualified_name else ''

                    # Search for in-class declaration
                    # Strategy: Find the class definition, then search within it for the declaration
                    declaration_line_num = None
                    class_start = None
                    class_end = None

                    # First, find the class boundaries
                    for i in range(line_number - 1, -1, -1):
                        check_line = lines[i]
                        if class_name and (f'struct {class_name}' in check_line or f'class {class_name}' in check_line):
                            class_start = i
                            # Find the closing brace
                            brace_depth = 0
                            for j in range(i, len(lines)):
                                brace_depth += lines[j].count('{') - lines[j].count('}')
                                if brace_depth == 0 and '}' in lines[j]:
                                    class_end = j
                                    break
                            break

                    # Now search within the class for the declaration
                    if class_start is not None and class_end is not None:
                        for i in range(class_start, class_end + 1):
                            check_line = lines[i]
                            # Look for declaration: has function name, has ), has ; or virtual
                            if (func_name in check_line and '(' in check_line and ')' in check_line
                                and ('virtual' in check_line or ';' in check_line)):
                                # Verify it's not a :: definition
                                if '::' not in check_line:
                                    declaration_line_num = i + 1
                                    break

                    if declaration_line_num:
                        # Use the declaration line instead
                        line_number = declaration_line_num
                        line = lines[line_number - 1]
                    else:
                        # Can't find declaration, skip this refactoring
                        return None

                # Find the position to insert qualifier
                # Look for patterns: ") {", ");", ") override {", ") const;", etc.
                if ')' not in line:
                    return None

                # Insert before semicolon or opening brace that comes after )
                modified_line = None

                # Find the closing ) and then look for what comes after it
                # Use regex to find the right insertion point

                # For inline methods: int getX() { return x; }
                # We want to insert before the { that comes after )
                if '{' in line:
                    # Find position of ) and position of {
                    paren_pos = line.rfind(')')
                    brace_pos = line.find('{', paren_pos)
                    if brace_pos > paren_pos:
                        # Insert qualifier between ) and {
                        modified_line = line[:brace_pos] + f' {qualifier} ' + line[brace_pos:]
                # For declarations: virtual int get();
                # We want to insert before the ; that comes after )
                elif ';' in line:
                    paren_pos = line.rfind(')')
                    semi_pos = line.find(';', paren_pos)
                    if semi_pos > paren_pos:
                        # Insert qualifier between ) and ;
                        modified_line = line[:semi_pos] + f' {qualifier}' + line[semi_pos:]
                # Try to find ")\n" pattern (multiline)
                elif line.rstrip().endswith(')'):
                    modified_line = line.rstrip() + f' {qualifier}' + line[len(line.rstrip()):]

                if modified_line is None:
                    return None

                lines[line_number - 1] = modified_line

            # Write modified content
            file_path.write_text(''.join(lines), encoding='utf-8')

            # Create commit message (no line number in message)
            commit_msg = f"Add {qualifier} to {symbol.name} in {file_path.name}"

            # Create and return GitCommit (all validation with ASM O0 for now)
            return GitCommit(
                repo=self.repo,
                commit_message=commit_msg,
                validator_type=ValidatorId.ASM_O0,
                affected_symbols=[symbol.qualified_name],
                probability_of_success=self.get_probability_of_success()
            )

        except Exception as e:
            logger.error(f"Failed to add {qualifier} to {symbol.name}: {e}")
            return None
