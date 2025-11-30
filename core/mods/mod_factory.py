from enum import Enum
from typing import List, Dict, Any

from .base_mod import BaseMod
from .add_override_mod import AddOverrideMod
from .replace_ms_specific_mod import ReplaceMSSpecificMod
from .ms_macro_replacement import MSMacroReplacementMod


class ModType(Enum):
    ADD_OVERRIDE = AddOverrideMod
    REPLACE_MS_SPECIFIC = ReplaceMSSpecificMod
    MS_MACRO_REPLACEMENT = MSMacroReplacementMod


class ModFactory:
    @staticmethod
    def from_id(mod_id: str) -> BaseMod:
        for mod_type in ModType:
            if mod_type.value.get_id() == mod_id:
                return mod_type.value()
        raise ValueError(f"Unsupported mod: {mod_id}")

    @staticmethod
    def get_available_mods() -> List[Dict[str, Any]]:
        return [
            {
                'id': mod_type.value.get_id(),
                'name': mod_type.value.get_name()
            }
            for mod_type in ModType
        ]
