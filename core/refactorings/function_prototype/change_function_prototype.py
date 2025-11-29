from typing import Optional
from pathlib import Path
from core.refactorings.base_refactoring import BaseRefactoring
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.repo.git_commit import GitCommit
from core.validators.validator_id import ValidatorId
from .prototype_utils import PrototypeParser, PrototypeModifier
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
            prototype = ''.join(original_lines)

            modified_prototype = self._apply_changes(prototype, change_spec)

            if modified_prototype and modified_prototype != prototype:
                modified_lines = modified_prototype.splitlines(keepends=True)

                if len(modified_lines) != len(original_lines):
                    modified_lines = [modified_prototype.replace('\n', '') + '\n']

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

    def _apply_changes(self, prototype: str, change_spec: PrototypeChangeSpec) -> Optional[str]:
        modified = prototype

        if change_spec.new_return_type:
            result = PrototypeModifier.replace_return_type(modified, change_spec.new_return_type)
            if result:
                modified = result

        if change_spec.new_function_name:
            result = PrototypeModifier.replace_function_name(modified, change_spec.new_function_name)
            if result:
                modified = result

        for param_index, new_type, new_name in change_spec.parameter_changes:
            if new_type and new_name:
                result = PrototypeModifier.replace_parameter_type(modified, param_index, new_type)
                if result:
                    modified = result
                result = PrototypeModifier.replace_parameter_name(modified, param_index, new_name)
                if result:
                    modified = result
            elif new_type:
                result = PrototypeModifier.replace_parameter_type(modified, param_index, new_type)
                if result:
                    modified = result
            elif new_name:
                result = PrototypeModifier.replace_parameter_name(modified, param_index, new_name)
                if result:
                    modified = result

        for param_index in sorted(change_spec.parameters_to_remove, reverse=True):
            result = PrototypeModifier.remove_parameter(modified, param_index)
            if result:
                modified = result

        for param_type, param_name, position in change_spec.parameters_to_add:
            result = PrototypeModifier.add_parameter(modified, param_type, param_name, position)
            if result:
                modified = result

        return modified if modified != prototype else None

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
