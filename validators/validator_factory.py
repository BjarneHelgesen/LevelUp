"""
Validator Factory for LevelUp
Creates validator instances based on validator type
"""

from .base_validator import BaseValidator
from .asm_validator import ASMValidator


class ValidatorFactory:
    """Factory for creating validator instances"""

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

        if validator_type == 'asm':
            return ASMValidator(compiler=compiler)
        elif validator_type == 'ast':
            # Placeholder for AST validator
            raise NotImplementedError("AST validator not yet implemented")
        elif validator_type == 'warnings':
            # Placeholder for Warnings validator
            raise NotImplementedError("Warnings validator not yet implemented")
        elif validator_type == 'unit_test':
            # Placeholder for Unit Test validator
            raise NotImplementedError("Unit test validator not yet implemented")
        else:
            raise ValueError(f"Unsupported validator type: {validator_type}")

    @staticmethod
    def get_supported_validators():
        """Get list of supported validator types"""
        return ['asm']  # 'ast', 'warnings', 'unit_test' to be added later
