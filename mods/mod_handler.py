"""
Mod Handler for LevelUp - Manages and applies modifications to C++ code
"""

from pathlib import Path
from datetime import datetime

from .mod_factory import ModFactory


class ModHandler:
    """Handles application of mods to C++ code"""

    def __init__(self):
        self.mod_history = []
        self.mod_factory = ModFactory()

    def apply_mod(self, cpp_file, mod_data):
        """
        Apply a mod to a C++ file
        Returns path to modified file
        """
        mod_type = mod_data.get('mod_type', 'custom')

        # Create the mod instance using the factory
        try:
            mod_instance = self.mod_factory.from_id(mod_type)
        except (ValueError, NotImplementedError) as e:
            raise ValueError(f"Cannot create mod: {e}")

        # Validate before applying
        is_valid, message = mod_instance.validate_before_apply(Path(cpp_file))
        if not is_valid:
            raise ValueError(f"Mod validation failed: {message}")

        # Apply the mod
        modified_file = mod_instance.apply(Path(cpp_file))

        # Record in history
        self.mod_history.append({
            'file': str(cpp_file),
            'mod_type': mod_type,
            'timestamp': datetime.now().isoformat(),
            'mod_data': mod_data,
            'mod_metadata': mod_instance.get_metadata()
        })

        return modified_file

    def get_mod_history(self):
        """Get the history of applied mods"""
        return self.mod_history
