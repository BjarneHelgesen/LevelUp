import re
from pathlib import Path
from typing import Optional, List, Tuple
from core.parsers.symbols.function_symbol import FunctionSymbol
from core.parsers.symbols.base_symbol import BaseSymbol


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
