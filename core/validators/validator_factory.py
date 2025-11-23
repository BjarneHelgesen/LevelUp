from enum import Enum
from typing import List, Dict, Any

from .base_validator import BaseValidator
from .asm_validator import ASMValidatorO0, ASMValidatorO3
from .source_diff_validator import SourceDiffValidator


class ValidatorType(Enum):
    ASM_O0 = ASMValidatorO0
    ASM_O3 = ASMValidatorO3
    SOURCE_DIFF = SourceDiffValidator


class ValidatorFactory:
    @staticmethod
    def from_id(validator_id: str, compiler) -> BaseValidator:
        for validator_type in ValidatorType:
            if validator_type.value.get_id() == validator_id:
                return validator_type.value(compiler=compiler)
        raise ValueError(f"Unsupported validator: {validator_id}")

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]:
        return [
            {
                'id': validator_type.value.get_id(),
                'name': validator_type.value.get_name()
            }
            for validator_type in ValidatorType
        ]
