"""
Mod Factory for LevelUp
Creates mod instances based on mod type
"""

from .base_mod import BaseMod
from .remove_inline_mod import RemoveInlineMod
from .add_override_mod import AddOverrideMod
from .replace_ms_specific_mod import ReplaceMSSpecificMod


class ModFactory:
    """Factory for creating mod instances"""

    @staticmethod
    def create_mod(mod_type: str) -> BaseMod:
        """
        Create a mod instance

        Args:
            mod_type: Type of mod ('remove_inline', 'add_override', etc.)

        Returns:
            Mod instance

        Raises:
            ValueError: If mod_type is not supported
        """
        mod_type = mod_type.lower()

        if mod_type == 'remove_inline':
            return RemoveInlineMod()
        elif mod_type == 'add_override':
            return AddOverrideMod()
        elif mod_type == 'replace_ms_specific':
            return ReplaceMSSpecificMod()
        elif mod_type == 'add_const':
            # Placeholder for AddConst mod
            raise NotImplementedError("Add const mod not yet implemented")
        elif mod_type == 'modernize_for':
            # Placeholder for ModernizeFor mod
            raise NotImplementedError("Modernize for loops mod not yet implemented")
        else:
            raise ValueError(f"Unsupported mod type: {mod_type}")

    @staticmethod
    def get_supported_mods():
        """Get list of supported mod types"""
        return ['remove_inline', 'add_override', 'replace_ms_specific']
        # 'add_const', 'modernize_for' to be added later
