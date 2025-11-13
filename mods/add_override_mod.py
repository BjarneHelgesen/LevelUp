"""
Add Override Mod - Adds override keyword to virtual functions
"""

import re
import tempfile
import shutil
from pathlib import Path

from .base_mod import BaseMod


class AddOverrideMod(BaseMod):
    """Adds override keyword to virtual functions"""

    def __init__(self):
        super().__init__(
            mod_id='add_override',
            description='Add override keyword to virtual functions'
        )

    @staticmethod
    def get_id() -> str:
        """Get the stable identifier for this mod"""
        # STABLE: This ID is used in APIs and databases. Do not change.
        return 'add_override'

    @staticmethod
    def get_name() -> str:
        """Get the human-readable name of the mod"""
        return 'Add Override Keywords'

    def can_apply(self, source_file: Path) -> bool:
        """Check if file contains virtual functions without override"""
        if not source_file.exists():
            return False

        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Check if there are virtual functions
                return 'virtual' in content
        except Exception:
            return False

    def apply(self, source_file: Path) -> Path:
        """Add override keyword to virtual functions"""
        # Create a temporary copy
        temp_file = Path(tempfile.mktemp(suffix=source_file.suffix))
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
