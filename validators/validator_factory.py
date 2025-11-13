"""
Validator Factory for LevelUp
Creates validator instances based on validator type
"""

from typing import List, Dict, Any

from .base_validator import BaseValidator
from .asm_validator import ASMValidator


class ValidatorFactory:
    """Factory for creating validator instances"""

    # Registry of available validators with their metadata
    _VALIDATOR_REGISTRY = {
        'asm': {
            'class': ASMValidator,
            'name': 'Assembly Comparison',
            'description': 'Validates that assembly output remains identical'
        }
    }

    @staticmethod
    def create_validator(validator_type: str, compiler) -> BaseValidator:
        """
        Create a validator instance

        Args:
            validator_type: Type of validator ('asm', 'ast', 'warnings', etc.)
            compiler: Compiler instance to use for validation

        Returns:
            Validator instance

        Raises:
            ValueError: If validator_type is not supported
        """
        validator_type = validator_type.lower()

        if validator_type not in ValidatorFactory._VALIDATOR_REGISTRY:
            raise ValueError(f"Unsupported validator type: {validator_type}")

        validator_class = ValidatorFactory._VALIDATOR_REGISTRY[validator_type]['class']
        return validator_class(compiler=compiler)

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]:
        """
        Get list of available validators with their metadata

        Returns:
            List of dictionaries containing validator information:
            [
                {
                    'id': 'asm',
                    'name': 'Assembly Comparison',
                    'description': 'Validates that assembly output remains identical'
                },
                ...
            ]
        """
        return [
            {
                'id': validator_id,
                'name': info['name'],
                'description': info['description']
            }
            for validator_id, info in ValidatorFactory._VALIDATOR_REGISTRY.items()
        ]
