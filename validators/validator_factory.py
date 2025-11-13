"""
Validator Factory for LevelUp
Creates validator instances based on validator type
"""

from enum import Enum
from typing import List, Dict, Any

from .base_validator import BaseValidator
from .asm_validator import ASMValidator


class ValidatorType(Enum):
    """Enum of available validator types"""
    ASM = ASMValidator


class ValidatorFactory:
    """Factory for creating validator instances"""

    @staticmethod
    def from_id(validator_id: str, compiler) -> BaseValidator:
        """
        Create a validator instance from its stable ID

        Args:
            validator_id: Stable validator identifier (e.g., 'asm')
            compiler: Compiler instance to use for validation

        Returns:
            Validator instance

        Raises:
            ValueError: If validator_id is not supported
        """
        for validator_type in ValidatorType:
            if validator_type.value.get_id() == validator_id:
                return validator_type.value(compiler=compiler)
        raise ValueError(f"Unsupported validator: {validator_id}")

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]:
        """
        Get list of available validators

        Returns:
            List of dictionaries containing validator information:
            [
                {
                    'id': 'asm',
                    'name': 'Assembly Comparison'
                },
                ...
            ]
        """
        return [
            {
                'id': validator_type.value.get_id(),
                'name': validator_type.value.get_name()
            }
            for validator_type in ValidatorType
        ]
