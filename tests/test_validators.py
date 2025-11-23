import pytest
from unittest.mock import Mock
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3


class TestASMValidatorO0Basics:
    def test_get_id_returns_stable_identifier(self):
        assert ASMValidatorO0.get_id() == "asm_o0"

    def test_get_name_returns_human_readable_name(self):
        assert ASMValidatorO0.get_name() == "Assembly Comparison (O0)"

    def test_get_optimization_level_returns_0(self):
        assert ASMValidatorO0.get_optimization_level() == 0

    def test_can_be_constructed_with_compiler(self):
        mock_compiler = Mock()
        validator = ASMValidatorO0(mock_compiler)
        assert validator.compiler is mock_compiler


class TestASMValidatorO3Basics:
    def test_get_id_returns_stable_identifier(self):
        assert ASMValidatorO3.get_id() == "asm_o3"

    def test_get_name_returns_human_readable_name(self):
        assert ASMValidatorO3.get_name() == "Assembly Comparison (O3)"

    def test_get_optimization_level_returns_3(self):
        assert ASMValidatorO3.get_optimization_level() == 3

    def test_can_be_constructed_with_compiler(self):
        mock_compiler = Mock()
        validator = ASMValidatorO3(mock_compiler)
        assert validator.compiler is mock_compiler


from core.validators.source_diff_validator import SourceDiffValidator


class TestSourceDiffValidatorBasics:
    def test_get_id_returns_stable_identifier(self):
        assert SourceDiffValidator.get_id() == "source_diff"

    def test_get_name_returns_human_readable_name(self):
        assert SourceDiffValidator.get_name() == "Source Diff Validator"

    def test_get_optimization_level_returns_0(self):
        assert SourceDiffValidator.get_optimization_level() == 0

    def test_can_be_constructed_with_default_allowed_removals(self):
        validator = SourceDiffValidator()
        assert validator.allowed_removals == ['inline']

    def test_can_be_constructed_with_custom_allowed_removals(self):
        validator = SourceDiffValidator(allowed_removals=['inline', 'const'])
        assert validator.allowed_removals == ['inline', 'const']
