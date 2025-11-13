"""
Mod Factory for LevelUp
Creates mod instances based on mod type
"""

from enum import Enum
from typing import List, Dict, Any

from .base_mod import BaseMod
from .remove_inline_mod import RemoveInlineMod
from .add_override_mod import AddOverrideMod
from .replace_ms_specific_mod import ReplaceMSSpecificMod


class ModType(Enum):
    """Enum of available mod types"""
    REMOVE_INLINE = RemoveInlineMod
    ADD_OVERRIDE = AddOverrideMod
    REPLACE_MS_SPECIFIC = ReplaceMSSpecificMod


class ModFactory:
    """Factory for creating mod instances"""

    @staticmethod
    def from_id(mod_id: str) -> BaseMod:
        """
        Create a mod instance from its stable ID

        Args:
            mod_id: Stable mod identifier (e.g., 'remove_inline')

        Returns:
            Mod instance

        Raises:
            ValueError: If mod_id is not supported
        """
        for mod_type in ModType:
            if mod_type.value.get_id() == mod_id:
                return mod_type.value()
        raise ValueError(f"Unsupported mod: {mod_id}")

    @staticmethod
    def get_available_mods() -> List[Dict[str, Any]]:
        """
        Get list of available mods

        Returns:
            List of dictionaries containing mod information:
            [
                {
                    'id': 'remove_inline',
                    'name': 'Remove Inline Keywords'
                },
                ...
            ]
        """
        return [
            {
                'id': mod_type.value.get_id(),
                'name': mod_type.value.get_name()
            }
            for mod_type in ModType
        ]
