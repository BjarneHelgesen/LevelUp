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

    def test_can_be_constructed(self):
        validator = ASMValidatorO0()
        assert validator is not None


class TestASMValidatorO3Basics:
    def test_get_id_returns_stable_identifier(self):
        assert ASMValidatorO3.get_id() == "asm_o3"

    def test_get_name_returns_human_readable_name(self):
        assert ASMValidatorO3.get_name() == "Assembly Comparison (O3)"

    def test_get_optimization_level_returns_3(self):
        assert ASMValidatorO3.get_optimization_level() == 3

    def test_can_be_constructed(self):
        validator = ASMValidatorO3()
        assert validator is not None
