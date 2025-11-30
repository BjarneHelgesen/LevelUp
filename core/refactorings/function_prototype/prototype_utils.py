import re
from pathlib import Path
from typing import Optional, List, Tuple
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.parsers.symbols.base_symbol import BaseSymbol


class Parameter:
    """Represents a single function parameter with type, name, and default value."""

    def __init__(self, param_type: str, name: str = '', default_value: str = ''):
        self.type = param_type
        self.name = name
        self.default_value = default_value

    def to_string(self) -> str:
        """Convert parameter back to string form."""
        result = self.type
        if self.name:
            result += f" {self.name}"
        if self.default_value:
            result += f" = {self.default_value}"
        return result


class PrototypeComponents:
    """
    Structured representation of a complete function prototype.

    Preserves all components for accurate reconstruction:
    - Leading qualifiers (inline, static, virtual, etc.)
    - Return type
    - Function name (with namespace/class if present)
    - Parameters (with types, names, defaults)
    - Trailing qualifiers (const, noexcept, override, final)
    - Terminator (;, {, or empty)
    - Original whitespace patterns for formatting
    """

    def __init__(self):
        self.leading_qualifiers: List[str] = []
        self.return_type: str = ''
        self.function_name: str = ''
        self.parameters: List[Parameter] = []
        self.trailing_qualifiers: List[str] = []
        self.terminator: str = ''
        self.indent: str = ''  # Indentation before prototype
        self.spacing_before_paren: str = ''  # Space between name and (
        self.spacing_after_paren: str = ''  # Space between ) and trailing content


class PrototypeLocation:
    def __init__(self, file_path: str, line_start: int, line_end: int, text: str):
        self.file_path = Path(file_path)
        self.line_start = line_start
        self.line_end = line_end
        self.text = text
        self.is_definition = '{' in text or text.strip().endswith('{')
        self.is_declaration = ';' in text or text.strip().endswith(';')


class PrototypeParser:
    @staticmethod
    def find_prototype_locations(symbol: FunctionSymbol) -> List[PrototypeLocation]:
        locations = []

        file_path = Path(symbol.file_path)
        if not file_path.exists():
            return locations

        try:
            lines = file_path.read_text(encoding='utf-8').splitlines(keepends=True)
        except Exception:
            return locations

        if symbol.line_start < 1 or symbol.line_start > len(lines):
            return locations

        line_idx = symbol.line_start - 1
        prototype_lines = []

        while line_idx < len(lines):
            line = lines[line_idx]
            prototype_lines.append(line)

            if ';' in line or '{' in line:
                break

            line_idx += 1
            if line_idx >= len(lines):
                break

        if prototype_lines:
            prototype_text = ''.join(prototype_lines)
            locations.append(PrototypeLocation(
                file_path=str(file_path),
                line_start=symbol.line_start,
                line_end=symbol.line_start + len(prototype_lines) - 1,
                text=prototype_text
            ))

        return locations

    @staticmethod
    def extract_return_type(prototype: str) -> Optional[str]:
        prototype = prototype.strip()

        prototype = re.sub(r'/\*.*?\*/', ' ', prototype)
        prototype = re.sub(r'//.*?$', '', prototype, flags=re.MULTILINE)

        prototype = re.sub(r'\s+', ' ', prototype).strip()

        paren_idx = prototype.find('(')
        if paren_idx == -1:
            return None

        before_paren = prototype[:paren_idx].strip()

        qualifiers = ['inline', 'static', 'virtual', 'explicit', 'constexpr', 'extern']
        tokens = before_paren.split()

        return_tokens = []
        for token in tokens:
            if token not in qualifiers:
                return_tokens.append(token)

        if len(return_tokens) >= 1:
            return_tokens.pop()

        if return_tokens:
            return ' '.join(return_tokens)

        return None

    @staticmethod
    def extract_function_name(prototype: str) -> Optional[str]:
        prototype = prototype.strip()

        prototype = re.sub(r'/\*.*?\*/', ' ', prototype)
        prototype = re.sub(r'//.*?$', '', prototype, flags=re.MULTILINE)
        prototype = re.sub(r'\s+', ' ', prototype).strip()

        paren_idx = prototype.find('(')
        if paren_idx == -1:
            return None

        before_paren = prototype[:paren_idx].strip()

        tokens = before_paren.split()
        if not tokens:
            return None

        name_token = tokens[-1]

        name_token = re.sub(r'^.*::', '', name_token)

        return name_token

    @staticmethod
    def extract_parameters(prototype: str) -> List[Tuple[str, str]]:
        prototype = prototype.strip()

        paren_start = prototype.find('(')
        paren_end = prototype.rfind(')')

        if paren_start == -1 or paren_end == -1 or paren_end <= paren_start:
            return []

        params_str = prototype[paren_start + 1:paren_end].strip()

        if not params_str or params_str == 'void':
            return []

        params = []
        current_param = ''
        depth = 0

        for char in params_str:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == ',' and depth == 0:
                param = current_param.strip()
                if param:
                    params.append(PrototypeParser._parse_parameter(param))
                current_param = ''
                continue

            current_param += char

        if current_param.strip():
            params.append(PrototypeParser._parse_parameter(current_param.strip()))

        return params

    @staticmethod
    def _parse_parameter(param_str: str) -> Tuple[str, str]:
        param_str = re.sub(r'/\*.*?\*/', ' ', param_str)
        param_str = re.sub(r'//.*?$', '', param_str)
        param_str = re.sub(r'\s+', ' ', param_str).strip()

        default_idx = param_str.find('=')
        if default_idx != -1:
            param_str = param_str[:default_idx].strip()

        tokens = param_str.split()
        if not tokens:
            return ('', '')

        if len(tokens) == 1:
            return (tokens[0], '')

        name = tokens[-1]
        name = re.sub(r'[\*&]', '', name)

        param_type = ' '.join(tokens[:-1])

        if name.startswith('['):
            param_type = param_str
            name = ''

        return (param_type, name)

    @staticmethod
    def extract_qualifiers_after_params(prototype: str) -> List[str]:
        paren_end = prototype.rfind(')')
        if paren_end == -1:
            return []

        after_params = prototype[paren_end + 1:].strip()

        semicolon = after_params.find(';')
        brace = after_params.find('{')

        if semicolon != -1:
            after_params = after_params[:semicolon].strip()
        elif brace != -1:
            after_params = after_params[:brace].strip()

        qualifiers = []
        qualifier_keywords = ['const', 'noexcept', 'override', 'final']

        for keyword in qualifier_keywords:
            if re.search(r'\b' + keyword + r'\b', after_params):
                qualifiers.append(keyword)

        return qualifiers

    @staticmethod
    def parse_prototype(prototype: str) -> Optional[PrototypeComponents]:
        """
        Parse a complete prototype into structured components.

        Extracts all parts including qualifiers, return type, name, parameters
        with defaults, trailing qualifiers, and terminator.
        """
        if not prototype or not prototype.strip():
            return None

        components = PrototypeComponents()

        # Extract indentation
        lines = prototype.split('\n')
        if lines:
            first_line = lines[0]
            components.indent = first_line[:len(first_line) - len(first_line.lstrip())]

        # Clean up for parsing but preserve original
        clean_proto = prototype.strip()

        # Remove comments for parsing
        clean_proto = re.sub(r'/\*.*?\*/', ' ', clean_proto)
        clean_proto = re.sub(r'//.*?$', '', clean_proto, flags=re.MULTILINE)
        clean_proto = re.sub(r'\s+', ' ', clean_proto).strip()

        # Extract terminator
        if clean_proto.endswith(';'):
            components.terminator = ';'
            clean_proto = clean_proto[:-1].strip()
        elif clean_proto.endswith('{'):
            components.terminator = '{'
            clean_proto = clean_proto[:-1].strip()
        elif '{' in clean_proto:
            brace_idx = clean_proto.find('{')
            components.terminator = '{'
            clean_proto = clean_proto[:brace_idx].strip()

        # Extract trailing qualifiers (after parameters)
        paren_end = clean_proto.rfind(')')
        if paren_end != -1:
            after_params = clean_proto[paren_end + 1:].strip()
            qualifier_keywords = ['const', 'noexcept', 'override', 'final']
            for keyword in qualifier_keywords:
                if re.search(r'\b' + keyword + r'\b', after_params):
                    components.trailing_qualifiers.append(keyword)
            # Remove trailing qualifiers from clean_proto
            for qual in components.trailing_qualifiers:
                after_params = re.sub(r'\b' + qual + r'\b', '', after_params).strip()
            clean_proto = clean_proto[:paren_end + 1] + ' ' + after_params
            clean_proto = clean_proto.strip()

        # Extract parameters
        paren_start = clean_proto.find('(')
        paren_end = clean_proto.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        params_str = clean_proto[paren_start + 1:paren_end].strip()
        before_params = clean_proto[:paren_start].strip()

        # Parse parameters with default values
        if params_str and params_str != 'void':
            components.parameters = PrototypeParser._parse_parameters_with_defaults(params_str)

        # Extract function name, return type, and leading qualifiers
        tokens = before_params.split()
        if not tokens:
            return None

        # Function name is the last token
        components.function_name = tokens[-1]

        # Leading qualifiers and return type
        leading_qualifier_keywords = ['inline', 'static', 'virtual', 'explicit', 'constexpr', 'extern']
        remaining_tokens = tokens[:-1]

        # Extract leading qualifiers
        return_type_tokens = []
        for token in remaining_tokens:
            if token in leading_qualifier_keywords:
                components.leading_qualifiers.append(token)
            else:
                return_type_tokens.append(token)

        components.return_type = ' '.join(return_type_tokens) if return_type_tokens else ''

        # Try to detect spacing patterns (simple heuristic)
        if '(' in prototype:
            idx = prototype.find('(')
            before = prototype[:idx]
            if before.endswith(' '):
                components.spacing_before_paren = ' '

        return components

    @staticmethod
    def _parse_parameters_with_defaults(params_str: str) -> List[Parameter]:
        """Parse parameters including default values."""
        params = []
        current_param = ''
        depth = 0

        for char in params_str:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == ',' and depth == 0:
                param = current_param.strip()
                if param:
                    params.append(PrototypeParser._parse_single_parameter(param))
                current_param = ''
                continue

            current_param += char

        if current_param.strip():
            params.append(PrototypeParser._parse_single_parameter(current_param.strip()))

        return params

    @staticmethod
    def _parse_single_parameter(param_str: str) -> Parameter:
        """Parse a single parameter including type, name, and default value."""
        param_str = re.sub(r'/\*.*?\*/', ' ', param_str)
        param_str = re.sub(r'//.*?$', '', param_str)
        param_str = re.sub(r'\s+', ' ', param_str).strip()

        # Check for default value
        default_value = ''
        default_idx = param_str.find('=')
        if default_idx != -1:
            default_value = param_str[default_idx + 1:].strip()
            param_str = param_str[:default_idx].strip()

        # Parse type and name
        tokens = param_str.split()
        if not tokens:
            return Parameter('', '', default_value)

        if len(tokens) == 1:
            # Only type, no name
            return Parameter(tokens[0], '', default_value)

        # Last token is the name (unless it's a pointer/reference symbol)
        name = tokens[-1]
        name = re.sub(r'[\*&]', '', name)

        param_type = ' '.join(tokens[:-1])

        # Handle array parameters like int[]
        if name.startswith('['):
            param_type = param_str
            name = ''

        return Parameter(param_type, name, default_value)


class PrototypeBuilder:
    """Reconstructs a complete prototype string from PrototypeComponents."""

    @staticmethod
    def build(components: PrototypeComponents) -> str:
        """
        Build a complete prototype string from components.

        Reconstructs the prototype preserving all qualifiers, parameters with
        defaults, and formatting hints.
        """
        parts = []

        # Add indentation if present
        if components.indent:
            parts.append(components.indent)

        # Add leading qualifiers
        if components.leading_qualifiers:
            parts.append(' '.join(components.leading_qualifiers))

        # Add return type
        if components.return_type:
            if parts and parts[-1] != components.indent:
                parts.append(' ')
            parts.append(components.return_type)

        # Add function name
        if parts and parts[-1] != components.indent and not parts[-1].endswith(' '):
            parts.append(' ')
        parts.append(components.function_name)

        # Add spacing before parenthesis if needed
        if components.spacing_before_paren:
            parts.append(components.spacing_before_paren)

        # Add parameters
        parts.append('(')
        if components.parameters:
            param_strs = [param.to_string() for param in components.parameters]
            parts.append(', '.join(param_strs))
        parts.append(')')

        # Add spacing after parenthesis if needed
        if components.spacing_after_paren:
            parts.append(components.spacing_after_paren)

        # Add trailing qualifiers
        if components.trailing_qualifiers:
            if parts[-1] != ')':
                parts.append(' ')
            else:
                parts.append(' ')
            parts.append(' '.join(components.trailing_qualifiers))

        # Add terminator
        if components.terminator:
            parts.append(components.terminator)

        return ''.join(parts)

    @staticmethod
    def modify_components(components: PrototypeComponents, change_spec) -> PrototypeComponents:
        """
        Apply changes from a PrototypeChangeSpec to components.

        Returns a new PrototypeComponents with the changes applied.
        """
        # Import here to avoid circular dependency
        from .prototype_change_spec import PrototypeChangeSpec

        # Create a copy to avoid modifying original
        modified = PrototypeComponents()
        modified.leading_qualifiers = components.leading_qualifiers.copy()
        modified.return_type = components.return_type
        modified.function_name = components.function_name
        modified.parameters = [Parameter(p.type, p.name, p.default_value) for p in components.parameters]
        modified.trailing_qualifiers = components.trailing_qualifiers.copy()
        modified.terminator = components.terminator
        modified.indent = components.indent
        modified.spacing_before_paren = components.spacing_before_paren
        modified.spacing_after_paren = components.spacing_after_paren

        # Apply return type change
        if change_spec.new_return_type:
            modified.return_type = change_spec.new_return_type

        # Apply function name change
        if change_spec.new_function_name:
            # Preserve namespace/class qualification if present
            if '::' in modified.function_name:
                namespace_part = modified.function_name.rsplit('::', 1)[0]
                modified.function_name = namespace_part + '::' + change_spec.new_function_name
            else:
                modified.function_name = change_spec.new_function_name

        # Apply parameter changes (type/name modifications)
        for param_index, new_type, new_name in change_spec.parameter_changes:
            if 0 <= param_index < len(modified.parameters):
                if new_type:
                    modified.parameters[param_index].type = new_type
                if new_name:
                    modified.parameters[param_index].name = new_name

        # Remove parameters (in reverse order to maintain indices)
        for param_index in sorted(change_spec.parameters_to_remove, reverse=True):
            if 0 <= param_index < len(modified.parameters):
                modified.parameters.pop(param_index)

        # Add parameters
        for param_type, param_name, position in change_spec.parameters_to_add:
            new_param = Parameter(param_type, param_name)
            if position == -1 or position >= len(modified.parameters):
                modified.parameters.append(new_param)
            else:
                modified.parameters.insert(position, new_param)

        return modified


class PrototypeModifier:
    @staticmethod
    def replace_return_type(prototype: str, new_return_type: str) -> Optional[str]:
        current_return = PrototypeParser.extract_return_type(prototype)
        if not current_return:
            return None

        paren_idx = prototype.find('(')
        if paren_idx == -1:
            return None

        before_paren = prototype[:paren_idx]
        after_paren = prototype[paren_idx:]

        pattern = r'\b' + re.escape(current_return) + r'\b'

        new_before = re.sub(pattern, new_return_type, before_paren, count=1)

        return new_before + after_paren

    @staticmethod
    def replace_function_name(prototype: str, new_name: str) -> Optional[str]:
        paren_idx = prototype.find('(')
        if paren_idx == -1:
            return None

        before_paren = prototype[:paren_idx]
        after_paren = prototype[paren_idx:]

        tokens = before_paren.strip().split()
        if not tokens:
            return None

        old_name = tokens[-1]

        if '::' in old_name:
            namespace_part = old_name.rsplit('::', 1)[0]
            new_qualified_name = namespace_part + '::' + new_name
        else:
            new_qualified_name = new_name

        new_before = before_paren.rsplit(old_name, 1)[0] + new_qualified_name

        return new_before + after_paren

    @staticmethod
    def replace_parameter_type(prototype: str, param_index: int, new_type: str) -> Optional[str]:
        params = PrototypeParser.extract_parameters(prototype)

        if param_index < 0 or param_index >= len(params):
            return None

        paren_start = prototype.find('(')
        paren_end = prototype.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        before_params = prototype[:paren_start + 1]
        after_params = prototype[paren_end:]

        new_params = []
        for i, (param_type, param_name) in enumerate(params):
            if i == param_index:
                if param_name:
                    new_params.append(f"{new_type} {param_name}")
                else:
                    new_params.append(new_type)
            else:
                if param_name:
                    new_params.append(f"{param_type} {param_name}")
                else:
                    new_params.append(param_type)

        return before_params + ', '.join(new_params) + after_params

    @staticmethod
    def replace_parameter_name(prototype: str, param_index: int, new_name: str) -> Optional[str]:
        params = PrototypeParser.extract_parameters(prototype)

        if param_index < 0 or param_index >= len(params):
            return None

        paren_start = prototype.find('(')
        paren_end = prototype.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        before_params = prototype[:paren_start + 1]
        after_params = prototype[paren_end:]

        new_params = []
        for i, (param_type, param_name) in enumerate(params):
            if i == param_index:
                new_params.append(f"{param_type} {new_name}")
            else:
                if param_name:
                    new_params.append(f"{param_type} {param_name}")
                else:
                    new_params.append(param_type)

        return before_params + ', '.join(new_params) + after_params

    @staticmethod
    def add_parameter(prototype: str, new_type: str, new_name: str, position: int = -1) -> Optional[str]:
        params = PrototypeParser.extract_parameters(prototype)

        paren_start = prototype.find('(')
        paren_end = prototype.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        before_params = prototype[:paren_start + 1]
        after_params = prototype[paren_end:]

        if position == -1 or position >= len(params):
            position = len(params)

        new_params = []
        for i, (param_type, param_name) in enumerate(params):
            if i == position:
                if new_name:
                    new_params.append(f"{new_type} {new_name}")
                else:
                    new_params.append(new_type)

            if param_name:
                new_params.append(f"{param_type} {param_name}")
            else:
                new_params.append(param_type)

        if position >= len(params):
            if new_name:
                new_params.append(f"{new_type} {new_name}")
            else:
                new_params.append(new_type)

        if not new_params:
            params_str = f"{new_type} {new_name}" if new_name else new_type
        else:
            params_str = ', '.join(new_params)

        return before_params + params_str + after_params

    @staticmethod
    def remove_parameter(prototype: str, param_index: int) -> Optional[str]:
        params = PrototypeParser.extract_parameters(prototype)

        if param_index < 0 or param_index >= len(params):
            return None

        paren_start = prototype.find('(')
        paren_end = prototype.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        before_params = prototype[:paren_start + 1]
        after_params = prototype[paren_end:]

        new_params = []
        for i, (param_type, param_name) in enumerate(params):
            if i != param_index:
                if param_name:
                    new_params.append(f"{param_type} {param_name}")
                else:
                    new_params.append(param_type)

        if not new_params:
            params_str = ''
        else:
            params_str = ', '.join(new_params)

        return before_params + params_str + after_params
