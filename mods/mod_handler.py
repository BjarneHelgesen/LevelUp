from pathlib import Path
from datetime import datetime


class ModHandler:
    def __init__(self):
        self.mod_history = []

    def apply_mod_instance(self, cpp_file, mod_instance):
        is_valid, message = mod_instance.validate_before_apply(Path(cpp_file))
        if not is_valid:
            raise ValueError(f"Mod validation failed: {message}")

        modified_file = mod_instance.apply(Path(cpp_file))

        self.mod_history.append({
            'file': str(cpp_file),
            'mod_class': mod_instance.__class__.__name__,
            'timestamp': datetime.now().isoformat(),
            'mod_metadata': mod_instance.get_metadata()
        })

        return modified_file

    def get_mod_history(self):
        return self.mod_history
