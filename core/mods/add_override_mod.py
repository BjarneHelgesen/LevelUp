import re
import shutil
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

    def apply(self, source_file: Path) -> Path:
        # Create temp file in same directory as original so includes work
        temp_file = source_file.parent / f"_levelup_modified_{source_file.name}"
        shutil.copy2(source_file, temp_file)

        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
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

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)

        return temp_file
