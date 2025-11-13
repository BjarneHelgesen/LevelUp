"""
Mod Factory for LevelUp
Creates mod instances based on mod type
"""

from typing import List, Dict, Any

from .base_mod import BaseMod
from .remove_inline_mod import RemoveInlineMod
from .add_override_mod import AddOverrideMod
from .replace_ms_specific_mod import ReplaceMSSpecificMod


class ModFactory:
    """Factory for creating mod instances"""

    # Registry of available mods with their metadata
    _MOD_REGISTRY = {
        'remove_inline': {
            'class': RemoveInlineMod,
            'name': 'Remove Inline Keywords',
            'description': 'Remove inline keywords from functions'
        },
        'add_override': {
            'class': AddOverrideMod,
            'name': 'Add Override Keywords',
            'description': 'Add override keyword to virtual functions'
        },
        'replace_ms_specific': {
            'class': ReplaceMSSpecificMod,
            'name': 'Replace MS-Specific Syntax',
            'description': 'Replace Microsoft-specific syntax with standard C++'
        }
    }

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

        if mod_type not in ModFactory._MOD_REGISTRY:
            raise ValueError(f"Unsupported mod type: {mod_type}")

        mod_class = ModFactory._MOD_REGISTRY[mod_type]['class']
        return mod_class()

    @staticmethod
    def get_available_mods() -> List[Dict[str, Any]]:
        """
        Get list of available mods with their metadata

        Returns:
            List of dictionaries containing mod information:
            [
                {
                    'id': 'remove_inline',
                    'name': 'Remove Inline Keywords',
                    'description': 'Remove inline keywords from functions'
                },
                ...
            ]
        """
        return [
            {
                'id': mod_id,
                'name': info['name'],
                'description': info['description']
            }
            for mod_id, info in ModFactory._MOD_REGISTRY.items()
        ]
