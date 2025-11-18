from enum import Enum
from typing import List, Dict, Any

from .base_validator import BaseValidator
from .asm_validator import ASMValidator
from .source_diff_validator import SourceDiffValidator


class ValidatorType(Enum):
    ASM = ASMValidator
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
