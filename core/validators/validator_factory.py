from typing import List, Dict, Any

from .base_validator import BaseValidator
from .asm_validator import ASMValidator
from .source_diff_validator import SourceDiffValidator


# Registry of available validators: (id, name, factory_function)
_VALIDATOR_REGISTRY = [
    ('asm_o0', 'Assembly Comparison (O0)', lambda compiler: ASMValidator(compiler, optimization_level=0)),
    ('asm_o3', 'Assembly Comparison (O3)', lambda compiler: ASMValidator(compiler, optimization_level=3)),
    ('source_diff', 'Source Diff Validator', lambda compiler: SourceDiffValidator()),
]


class ValidatorFactory:
    @staticmethod
    def from_id(validator_id: str, compiler) -> BaseValidator:
        for vid, _, factory in _VALIDATOR_REGISTRY:
            if vid == validator_id:
                return factory(compiler)
        raise ValueError(f"Unsupported validator: {validator_id}")

    @staticmethod
    def get_available_validators() -> List[Dict[str, Any]]:
        return [{'id': vid, 'name': name} for vid, name, _ in _VALIDATOR_REGISTRY]
