import pytest
from unittest.mock import Mock, patch
from core.mods.mod_factory import ModFactory, ModType
from core.mods.remove_inline_mod import RemoveInlineMod
from core.mods.add_override_mod import AddOverrideMod
from core.mods.replace_ms_specific_mod import ReplaceMSSpecificMod
from core.validators.validator_factory import ValidatorFactory, ValidatorType
from core.validators.asm_validator import ASMValidatorO0, ASMValidatorO3
from core.compilers.compiler_factory import CompilerFactory, get_compiler
from core.compilers.msvc_compiler import MSVCCompiler
from core.compilers.clang_compiler import ClangCompiler
from config import CompilerType


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
    def test_from_id_creates_asm_o0_validator(self):
        validator = ValidatorFactory.from_id("asm_o0")
        assert isinstance(validator, ASMValidatorO0)

    def test_from_id_creates_asm_o3_validator(self):
        validator = ValidatorFactory.from_id("asm_o3")
        assert isinstance(validator, ASMValidatorO3)

    def test_from_id_raises_for_unknown_id(self):
        with pytest.raises(ValueError) as exc_info:
            ValidatorFactory.from_id("nonexistent_validator")
        assert "Unsupported validator" in str(exc_info.value)

    def test_from_id_creates_new_instance_each_time(self):
        v1 = ValidatorFactory.from_id("asm_o0")
        v2 = ValidatorFactory.from_id("asm_o0")
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

    def test_get_available_validators_includes_asm_o0(self):
        validators = ValidatorFactory.get_available_validators()
        ids = [v["id"] for v in validators]
        assert "asm_o0" in ids

    def test_get_available_validators_includes_asm_o3(self):
        validators = ValidatorFactory.get_available_validators()
        ids = [v["id"] for v in validators]
        assert "asm_o3" in ids

    def test_all_available_validators_can_be_created(self):
        validators_info = ValidatorFactory.get_available_validators()
        for validator_info in validators_info:
            validator = ValidatorFactory.from_id(validator_info["id"])
            assert validator.get_id() == validator_info["id"]

    def test_validator_type_enum_matches_classes(self):
        assert ValidatorType.ASM_O0.value == ASMValidatorO0
        assert ValidatorType.ASM_O3.value == ASMValidatorO3


class TestCompilerFactory:
    def test_msvc_compiler_can_be_created(self):
        # MSVCCompiler auto-discovers cl.exe, so we just verify it can be created
        compiler = MSVCCompiler()
        assert isinstance(compiler, MSVCCompiler)

    def test_msvc_auto_discovers_cl_path(self):
        # MSVCCompiler now auto-discovers cl.exe path
        compiler = MSVCCompiler()
        assert compiler.cl_path is not None
        assert "cl.exe" in compiler.cl_path.lower()

    def test_get_compiler_returns_configured_compiler(self):
        from core.compilers.compiler_factory import reset_compiler
        from config import COMPILER_TYPE, CompilerType
        reset_compiler()
        compiler = get_compiler()
        # Check it matches configured type
        if COMPILER_TYPE == CompilerType.MSVC:
            assert isinstance(compiler, MSVCCompiler)
        elif COMPILER_TYPE == CompilerType.CLANG:
            assert isinstance(compiler, ClangCompiler)

    def test_get_compiler_returns_same_instance(self):
        from core.compilers.compiler_factory import reset_compiler
        reset_compiler()
        c1 = get_compiler()
        c2 = get_compiler()
        assert c1 is c2

    def test_get_available_compilers_returns_list(self):
        compilers = CompilerFactory.get_available_compilers()
        assert isinstance(compilers, list)

    def test_get_available_compilers_contains_both_compilers(self):
        compilers = CompilerFactory.get_available_compilers()
        assert len(compilers) == 2  # MSVC and Clang

    def test_get_available_compilers_each_entry_has_id_and_name(self):
        compilers = CompilerFactory.get_available_compilers()
        for compiler in compilers:
            assert "id" in compiler
            assert "name" in compiler

    def test_get_available_compilers_includes_msvc(self):
        compilers = CompilerFactory.get_available_compilers()
        ids = [c["id"] for c in compilers]
        assert "msvc" in ids

    def test_get_available_compilers_includes_clang(self):
        compilers = CompilerFactory.get_available_compilers()
        ids = [c["id"] for c in compilers]
        assert "clang" in ids

    def test_compiler_type_enum_has_msvc_and_clang(self):
        assert CompilerType.MSVC.value == 'msvc'
        assert CompilerType.CLANG.value == 'clang'
