import re
from pathlib import Path

from .base_mod import BaseMod


class AddOverrideMod(BaseMod):
    def __init__(self):
        super().__init__(
            mod_id='add_override',
            description='Add override keyword to virtual functions'
        )

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'add_override'

    @staticmethod
    def get_name() -> str:
        return 'Add Override Keywords'

    def apply(self, source_file: Path) -> None:
        # Modify file in-place
        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        modified_lines = []
        in_class = False

        for line in lines:
            # Detect class declaration
            if re.match(r'^\s*class\s+\w+', line):
                in_class = True
            elif re.match(r'^\s*};', line):
                in_class = False

            # Add override to virtual functions
            if in_class and 'virtual' in line and 'override' not in line:
                if ';' in line:  # Function declaration
                    line = re.sub(r';', ' override;', line)

            modified_lines.append(line)

        with open(source_file, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
