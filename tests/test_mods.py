import pytest
import tempfile
from pathlib import Path
from core.mods.remove_inline_mod import RemoveInlineMod
from core.mods.add_override_mod import AddOverrideMod
from core.mods.replace_ms_specific_mod import ReplaceMSSpecificMod
from core.mods.base_mod import BaseMod


class TestRemoveInlineMod:
    def test_get_id_returns_stable_identifier(self):
        assert RemoveInlineMod.get_id() == "remove_inline"

    def test_get_name_returns_human_readable_name(self):
        assert RemoveInlineMod.get_name() == "Remove Inline Keywords"

    # Removed: get_validator_id() no longer exists - validator type is per-refactoring

    def test_mod_has_correct_description(self):
        mod = RemoveInlineMod()
        assert "inline" in mod.description.lower()

    # TODO: Update these tests to use generate_refactorings instead of generate_changes
    # These tests need to be rewritten for the new refactoring architecture

    def test_get_metadata_includes_id_and_description(self):
        mod = RemoveInlineMod()
        metadata = mod.get_metadata()
        assert metadata["mod_id"] == "remove_inline"
        assert "description" in metadata


class TestAddOverrideMod:
    def test_get_id_returns_stable_identifier(self):
        assert AddOverrideMod.get_id() == "add_override"

    def test_get_name_returns_human_readable_name(self):
        assert AddOverrideMod.get_name() == "Add Override Keywords"

    def test_get_validator_id_returns_asm_o0(self):
        assert AddOverrideMod.get_validator_id() == "asm_o0"

    def test_generate_changes_adds_override_to_virtual_function(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo {\n    virtual void bar();\n};")
        mod = AddOverrideMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 1
        content = cpp_file.read_text()
        assert "override" in content

    def test_generate_changes_does_not_duplicate_override(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo { virtual void bar() override; };")
        mod = AddOverrideMod()
        changes = list(mod.generate_changes(temp_dir))
        content = cpp_file.read_text()
        assert content.count("override") == 1

    def test_generate_changes_handles_multiple_virtual_functions(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "class Foo {\n"
            "    virtual void bar();\n"
            "    virtual int baz();\n"
            "    virtual bool qux();\n"
            "};"
        )
        mod = AddOverrideMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) == 3
        content = cpp_file.read_text()
        assert content.count("override") == 3


class TestReplaceMSSpecificMod:
    def test_get_id_returns_stable_identifier(self):
        assert ReplaceMSSpecificMod.get_id() == "replace_ms_specific"

    def test_get_name_returns_human_readable_name(self):
        assert "MS" in ReplaceMSSpecificMod.get_name() or "Microsoft" in ReplaceMSSpecificMod.get_name()

    def test_get_validator_id_returns_asm_o0(self):
        assert ReplaceMSSpecificMod.get_validator_id() == "asm_o0"

    def test_generate_changes_replaces_forceinline_with_inline(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__forceinline int add() { return 0; }")
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 1
        content = cpp_file.read_text()
        assert "__forceinline" not in content
        assert "inline" in content

    def test_generate_changes_replaces_int64_with_long_long(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int64 x = 0;")
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 1
        content = cpp_file.read_text()
        assert "__int64" not in content
        assert "long long" in content

    def test_generate_changes_replaces_int32_with_int(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int32 x = 0;")
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 1
        content = cpp_file.read_text()
        assert "__int32" not in content
        assert "int" in content

    def test_generate_changes_replaces_stdcall_with_empty(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int __stdcall foo();")
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 1
        content = cpp_file.read_text()
        assert "__stdcall" not in content

    def test_generate_changes_replaces_multiple_patterns(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "__forceinline __int64 foo() { __int32 x = 0; return x; }"
        )
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) >= 3
        content = cpp_file.read_text()
        assert "__forceinline" not in content
        assert "__int64" not in content
        assert "__int32" not in content
        assert "inline" in content
        assert "long long" in content
        assert "int" in content

    def test_generate_changes_yields_nothing_for_non_ms_code(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        code = "int main() { return 0; }"
        cpp_file.write_text(code)
        mod = ReplaceMSSpecificMod()
        changes = list(mod.generate_changes(temp_dir))
        assert len(changes) == 0
        content = cpp_file.read_text()
        assert content.strip() == code


class TestBaseMod:
    def test_base_mod_has_get_metadata(self):
        mod = RemoveInlineMod()
        metadata = mod.get_metadata()
        assert isinstance(metadata, dict)
        assert "mod_id" in metadata
        assert "description" in metadata

    def test_generate_changes_is_generator(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mod = RemoveInlineMod()
        result = mod.generate_changes(temp_dir)
        # Should be a generator
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
