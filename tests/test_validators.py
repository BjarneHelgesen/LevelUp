import pytest
from unittest.mock import Mock
from core.validators.asm_validator import ASMValidator


class TestASMValidatorBasics:
    def test_get_id_returns_stable_identifier_o0(self):
        validator = ASMValidator(Mock(), optimization_level=0)
        assert validator.get_id() == "asm_o0"

    def test_get_id_returns_stable_identifier_o3(self):
        validator = ASMValidator(Mock(), optimization_level=3)
        assert validator.get_id() == "asm_o3"

    def test_get_name_returns_human_readable_name_o0(self):
        validator = ASMValidator(Mock(), optimization_level=0)
        assert validator.get_name() == "Assembly Comparison (O0)"

    def test_get_name_returns_human_readable_name_o3(self):
        validator = ASMValidator(Mock(), optimization_level=3)
        assert validator.get_name() == "Assembly Comparison (O3)"

    def test_get_optimization_level_returns_0(self):
        validator = ASMValidator(Mock(), optimization_level=0)
        assert validator.get_optimization_level() == 0

    def test_get_optimization_level_returns_3(self):
        validator = ASMValidator(Mock(), optimization_level=3)
        assert validator.get_optimization_level() == 3

    def test_can_be_constructed_with_compiler(self):
        mock_compiler = Mock()
        validator = ASMValidator(mock_compiler, optimization_level=0)
        assert validator.compiler is mock_compiler

    def test_default_optimization_level_is_0(self):
        validator = ASMValidator(Mock())
        assert validator.get_optimization_level() == 0


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
