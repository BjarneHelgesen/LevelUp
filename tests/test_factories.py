import pytest
from unittest.mock import Mock, patch
from levelup_core.mods.mod_factory import ModFactory, ModType
from levelup_core.mods.remove_inline_mod import RemoveInlineMod
from levelup_core.mods.add_override_mod import AddOverrideMod
from levelup_core.mods.replace_ms_specific_mod import ReplaceMSSpecificMod
from levelup_core.validators.validator_factory import ValidatorFactory, ValidatorType
from levelup_core.validators.asm_validator import ASMValidator
from levelup_core.utils.compiler_factory import CompilerFactory, CompilerType
from levelup_core.utils.compiler import MSVCCompiler


class TestModFactory:
    def test_from_id_creates_remove_inline_mod(self):
        mod = ModFactory.from_id("remove_inline")
        assert isinstance(mod, RemoveInlineMod)

    def test_from_id_creates_add_override_mod(self):
        mod = ModFactory.from_id("add_override")
        assert isinstance(mod, AddOverrideMod)

    def test_from_id_creates_replace_ms_specific_mod(self):
        mod = ModFactory.from_id("replace_ms_specific")
        assert isinstance(mod, ReplaceMSSpecificMod)

    def test_from_id_raises_for_unknown_id(self):
        with pytest.raises(ValueError) as exc_info:
            ModFactory.from_id("nonexistent_mod")
        assert "Unsupported mod" in str(exc_info.value)

    def test_from_id_creates_new_instance_each_time(self):
        mod1 = ModFactory.from_id("remove_inline")
        mod2 = ModFactory.from_id("remove_inline")
        assert mod1 is not mod2

    def test_get_available_mods_returns_list(self):
        mods = ModFactory.get_available_mods()
        assert isinstance(mods, list)

    def test_get_available_mods_contains_all_mods(self):
        mods = ModFactory.get_available_mods()
        assert len(mods) == len(ModType)

    def test_get_available_mods_each_entry_has_id_and_name(self):
        mods = ModFactory.get_available_mods()
        for mod in mods:
            assert "id" in mod
            assert "name" in mod

    def test_get_available_mods_includes_remove_inline(self):
        mods = ModFactory.get_available_mods()
        ids = [mod["id"] for mod in mods]
        assert "remove_inline" in ids

    def test_get_available_mods_includes_add_override(self):
        mods = ModFactory.get_available_mods()
        ids = [mod["id"] for mod in mods]
        assert "add_override" in ids

    def test_get_available_mods_includes_replace_ms_specific(self):
        mods = ModFactory.get_available_mods()
        ids = [mod["id"] for mod in mods]
        assert "replace_ms_specific" in ids

    def test_all_available_mods_can_be_created(self):
        mods_info = ModFactory.get_available_mods()
        for mod_info in mods_info:
            mod = ModFactory.from_id(mod_info["id"])
            assert mod.get_id() == mod_info["id"]

    def test_mod_type_enum_matches_classes(self):
        assert ModType.REMOVE_INLINE.value == RemoveInlineMod
        assert ModType.ADD_OVERRIDE.value == AddOverrideMod
        assert ModType.REPLACE_MS_SPECIFIC.value == ReplaceMSSpecificMod


class TestValidatorFactory:
    def test_from_id_creates_asm_validator(self):
        mock_compiler = Mock()
        validator = ValidatorFactory.from_id("asm", mock_compiler)
        assert isinstance(validator, ASMValidator)

    def test_from_id_passes_compiler_to_validator(self):
        mock_compiler = Mock()
        validator = ValidatorFactory.from_id("asm", mock_compiler)
        assert validator.compiler is mock_compiler

    def test_from_id_raises_for_unknown_id(self):
        with pytest.raises(ValueError) as exc_info:
            ValidatorFactory.from_id("nonexistent_validator", Mock())
        assert "Unsupported validator" in str(exc_info.value)

    def test_from_id_creates_new_instance_each_time(self):
        mock_compiler = Mock()
        v1 = ValidatorFactory.from_id("asm", mock_compiler)
        v2 = ValidatorFactory.from_id("asm", mock_compiler)
        assert v1 is not v2

    def test_get_available_validators_returns_list(self):
        validators = ValidatorFactory.get_available_validators()
        assert isinstance(validators, list)

    def test_get_available_validators_contains_all_validators(self):
        validators = ValidatorFactory.get_available_validators()
        assert len(validators) == len(ValidatorType)

    def test_get_available_validators_each_entry_has_id_and_name(self):
        validators = ValidatorFactory.get_available_validators()
        for validator in validators:
            assert "id" in validator
            assert "name" in validator

    def test_get_available_validators_includes_asm(self):
        validators = ValidatorFactory.get_available_validators()
        ids = [v["id"] for v in validators]
        assert "asm" in ids

    def test_all_available_validators_can_be_created(self):
        validators_info = ValidatorFactory.get_available_validators()
        for validator_info in validators_info:
            validator = ValidatorFactory.from_id(validator_info["id"], Mock())
            assert validator.get_id() == validator_info["id"]

    def test_validator_type_enum_matches_classes(self):
        assert ValidatorType.ASM.value == ASMValidator


class TestCompilerFactory:
    def test_from_id_creates_msvc_compiler(self):
        compiler = CompilerFactory.from_id("msvc", "cl.exe")
        assert isinstance(compiler, MSVCCompiler)

    def test_from_id_passes_path_to_compiler(self):
        compiler = CompilerFactory.from_id("msvc", "/custom/path/cl.exe")
        assert compiler.cl_path == "/custom/path/cl.exe"

    def test_from_id_raises_for_unknown_id(self):
        with pytest.raises(ValueError) as exc_info:
            CompilerFactory.from_id("nonexistent_compiler", "path")
        assert "Unsupported compiler" in str(exc_info.value)

    def test_from_id_creates_new_instance_each_time(self):
        c1 = CompilerFactory.from_id("msvc", "cl.exe")
        c2 = CompilerFactory.from_id("msvc", "cl.exe")
        assert c1 is not c2

    def test_get_available_compilers_returns_list(self):
        compilers = CompilerFactory.get_available_compilers()
        assert isinstance(compilers, list)

    def test_get_available_compilers_contains_all_compilers(self):
        compilers = CompilerFactory.get_available_compilers()
        assert len(compilers) == len(CompilerType)

    def test_get_available_compilers_each_entry_has_id_and_name(self):
        compilers = CompilerFactory.get_available_compilers()
        for compiler in compilers:
            assert "id" in compiler
            assert "name" in compiler

    def test_get_available_compilers_includes_msvc(self):
        compilers = CompilerFactory.get_available_compilers()
        ids = [c["id"] for c in compilers]
        assert "msvc" in ids

    def test_all_available_compilers_can_be_created(self):
        compilers_info = CompilerFactory.get_available_compilers()
        for compiler_info in compilers_info:
            compiler = CompilerFactory.from_id(compiler_info["id"], "test_path")
            assert compiler.get_id() == compiler_info["id"]

    def test_compiler_type_enum_matches_classes(self):
        assert CompilerType.MSVC.value == MSVCCompiler
