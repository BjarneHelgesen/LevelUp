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

    def test_mod_has_correct_description(self):
        mod = RemoveInlineMod()
        assert "inline" in mod.description.lower()

    def test_can_apply_returns_true_when_file_contains_inline(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int add(int a, int b) { return a + b; }")
        mod = RemoveInlineMod()
        assert mod.can_apply(cpp_file) is True

    def test_can_apply_returns_false_when_no_inline_keyword(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int add(int a, int b) { return a + b; }")
        mod = RemoveInlineMod()
        assert mod.can_apply(cpp_file) is False

    def test_can_apply_returns_false_for_nonexistent_file(self, temp_dir):
        nonexistent = temp_dir / "nonexistent.cpp"
        mod = RemoveInlineMod()
        assert mod.can_apply(nonexistent) is False

    def test_apply_removes_inline_keyword(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int add(int a, int b) { return a + b; }")
        mod = RemoveInlineMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "inline" not in content
        assert "int add(int a, int b)" in content

    def test_apply_removes_multiple_inline_keywords(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "inline int add(int a, int b) { return a + b; }\n"
            "inline void log() {}\n"
            "inline bool check() { return true; }"
        )
        mod = RemoveInlineMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert content.count("inline") == 0
        assert "int add" in content
        assert "void log" in content
        assert "bool check" in content

    def test_apply_preserves_non_inline_content(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        original = "int main() { return 0; }"
        cpp_file.write_text(original)
        mod = RemoveInlineMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert content.strip() == original

    def test_apply_returns_different_file_path(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mod = RemoveInlineMod()
        result_path = mod.apply(cpp_file)
        assert result_path != cpp_file
        assert result_path.exists()

    def test_apply_does_not_modify_original_file(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        original_content = "inline int x = 1;"
        cpp_file.write_text(original_content)
        mod = RemoveInlineMod()
        mod.apply(cpp_file)
        assert cpp_file.read_text() == original_content

    def test_get_metadata_includes_id_and_description(self):
        mod = RemoveInlineMod()
        metadata = mod.get_metadata()
        assert metadata["mod_id"] == "remove_inline"
        assert "description" in metadata

    def test_validate_before_apply_passes_when_applicable(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mod = RemoveInlineMod()
        is_valid, message = mod.validate_before_apply(cpp_file)
        assert is_valid is True

    def test_validate_before_apply_fails_for_nonexistent_file(self, temp_dir):
        mod = RemoveInlineMod()
        is_valid, message = mod.validate_before_apply(temp_dir / "missing.cpp")
        assert is_valid is False
        assert "not applicable" in message.lower() or "does not" in message.lower()


class TestAddOverrideMod:
    def test_get_id_returns_stable_identifier(self):
        assert AddOverrideMod.get_id() == "add_override"

    def test_get_name_returns_human_readable_name(self):
        assert AddOverrideMod.get_name() == "Add Override Keywords"

    def test_can_apply_returns_true_when_file_contains_virtual(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo { virtual void bar(); };")
        mod = AddOverrideMod()
        assert mod.can_apply(cpp_file) is True

    def test_can_apply_returns_false_when_no_virtual(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo { void bar(); };")
        mod = AddOverrideMod()
        assert mod.can_apply(cpp_file) is False

    def test_apply_adds_override_to_virtual_function(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo {\n    virtual void bar();\n};")
        mod = AddOverrideMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "override" in content

    def test_apply_does_not_add_override_outside_class(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("virtual void standalone();\nclass Foo { };")
        mod = AddOverrideMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        # The virtual outside class should NOT get override
        lines = content.split('\n')
        assert "override" not in lines[0]

    def test_apply_does_not_duplicate_override(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo { virtual void bar() override; };")
        mod = AddOverrideMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert content.count("override") == 1

    def test_apply_handles_multiple_virtual_functions(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "class Foo {\n"
            "    virtual void bar();\n"
            "    virtual int baz();\n"
            "    virtual bool qux();\n"
            "};"
        )
        mod = AddOverrideMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert content.count("override") == 3


class TestReplaceMSSpecificMod:
    def test_get_id_returns_stable_identifier(self):
        assert ReplaceMSSpecificMod.get_id() == "replace_ms_specific"

    def test_get_name_returns_human_readable_name(self):
        assert "MS" in ReplaceMSSpecificMod.get_name() or "Microsoft" in ReplaceMSSpecificMod.get_name()

    def test_can_apply_returns_true_for_forceinline(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__forceinline int add(int a, int b) { return a + b; }")
        mod = ReplaceMSSpecificMod()
        assert mod.can_apply(cpp_file) is True

    def test_can_apply_returns_true_for_int64(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int64 bignum = 0;")
        mod = ReplaceMSSpecificMod()
        assert mod.can_apply(cpp_file) is True

    def test_can_apply_returns_false_for_standard_code(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int add(int a, int b) { return a + b; }")
        mod = ReplaceMSSpecificMod()
        assert mod.can_apply(cpp_file) is False

    def test_apply_replaces_forceinline_with_inline(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__forceinline int add() { return 0; }")
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "__forceinline" not in content
        assert "inline" in content

    def test_apply_replaces_int64_with_long_long(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int64 x = 0;")
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "__int64" not in content
        assert "long long" in content

    def test_apply_replaces_int32_with_int(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int32 x = 0;")
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "__int32" not in content
        assert "int" in content

    def test_apply_replaces_stdcall_with_empty(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int __stdcall foo();")
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "__stdcall" not in content

    def test_apply_replaces_multiple_patterns(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "__forceinline __int64 foo() { __int32 x = 0; return x; }"
        )
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert "__forceinline" not in content
        assert "__int64" not in content
        assert "__int32" not in content
        assert "inline" in content
        assert "long long" in content
        assert "int" in content

    def test_apply_preserves_non_ms_specific_code(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        code = "int main() { return 0; }"
        cpp_file.write_text(code)
        mod = ReplaceMSSpecificMod()
        result_path = mod.apply(cpp_file)
        content = result_path.read_text()
        assert content.strip() == code


class TestBaseMod:
    def test_base_mod_has_get_metadata(self):
        mod = RemoveInlineMod()
        metadata = mod.get_metadata()
        assert isinstance(metadata, dict)
        assert "mod_id" in metadata
        assert "description" in metadata

    def test_validate_before_apply_checks_can_apply(self, temp_dir):
        cpp_file = temp_dir / "empty.cpp"
        cpp_file.write_text("// no inline here")
        mod = RemoveInlineMod()
        is_valid, message = mod.validate_before_apply(cpp_file)
        # Should fail because can_apply returns False (no 'inline' in file)
        assert is_valid is False
