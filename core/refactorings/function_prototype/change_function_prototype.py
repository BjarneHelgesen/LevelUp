from typing import Optional
from pathlib import Path
from core.refactorings.base_refactoring import BaseRefactoring
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.repo.git_commit import GitCommit
from core.validators.validator_id import ValidatorId
from .prototype_utils import PrototypeParser, PrototypeBuilder
from .prototype_change_spec import PrototypeChangeSpec


class ChangeFunctionPrototypeRefactoring(BaseRefactoring):
    def get_probability_of_success(self) -> float:
        return 0.5

    def apply(self, symbol: FunctionSymbol, change_spec: PrototypeChangeSpec) -> Optional[GitCommit]:
        if not change_spec.has_changes():
            return None

        locations = PrototypeParser.find_prototype_locations(symbol)
        if not locations:
            return None

        file_path = Path(symbol.file_path)
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines(keepends=True)
        except Exception:
            return None

        modified = False

        for location in locations:
            if location.line_start < 1 or location.line_start > len(lines):
                continue

            start_idx = location.line_start - 1
            end_idx = location.line_end - 1

            if end_idx >= len(lines):
                continue

            original_lines = lines[start_idx:end_idx + 1]
            original_prototype = ''.join(original_lines)

            # Parse prototype into components
            components = PrototypeParser.parse_prototype(original_prototype)
            if not components:
                continue

            # Modify components based on change spec
            modified_components = PrototypeBuilder.modify_components(components, change_spec)

            # Rebuild prototype from modified components
            new_prototype = PrototypeBuilder.build(modified_components)

            # Only apply if actually changed
            if new_prototype != original_prototype:
                # Preserve line breaks if original had them
                if '\n' in original_prototype:
                    modified_lines = new_prototype.splitlines(keepends=True)
                    if not modified_lines[-1].endswith('\n'):
                        modified_lines[-1] += '\n'
                else:
                    modified_lines = [new_prototype]
                    if not modified_lines[-1].endswith('\n') and original_lines[-1].endswith('\n'):
                        modified_lines[-1] += '\n'

                lines[start_idx:end_idx + 1] = modified_lines
                modified = True

        if not modified:
            return None

        try:
            file_path.write_text(''.join(lines), encoding='utf-8')
        except Exception:
            return None

        commit_message = self._generate_commit_message(symbol, change_spec)

        try:
            return GitCommit(
                repo=self.repo,
                commit_message=commit_message,
                validator_type=ValidatorId.ASM_O0,
                affected_symbols=[symbol.qualified_name],
                probability_of_success=self.get_probability_of_success()
            )
        except ValueError:
            return None

    def _generate_commit_message(self, symbol: FunctionSymbol, change_spec: PrototypeChangeSpec) -> str:
        changes = []

        if change_spec.new_return_type:
            changes.append(f"return type to {change_spec.new_return_type}")

        if change_spec.new_function_name:
            changes.append(f"name to {change_spec.new_function_name}")

        if change_spec.parameter_changes:
            changes.append(f"{len(change_spec.parameter_changes)} parameter(s)")

        if change_spec.parameters_to_add:
            changes.append(f"add {len(change_spec.parameters_to_add)} parameter(s)")

        if change_spec.parameters_to_remove:
            changes.append(f"remove {len(change_spec.parameters_to_remove)} parameter(s)")

        change_desc = ", ".join(changes) if changes else "prototype"

        return f"Change {change_desc} for {symbol.name}"
