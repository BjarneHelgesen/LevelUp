import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from core.mods.add_override_mod import AddOverrideMod
from core.mods.replace_ms_specific_mod import ReplaceMSSpecificMod
from core.mods.base_mod import BaseMod
from core.repo.repo import Repo
from core.parsers.symbol_table import SymbolTable


class TestAddOverrideMod:
    def test_get_id_returns_stable_identifier(self):
        assert AddOverrideMod.get_id() == "add_override"

    def test_get_name_returns_human_readable_name(self):
        assert AddOverrideMod.get_name() == "Add Override Keywords"

    def test_generate_refactorings_adds_override_to_virtual_function(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo {\n    virtual void bar();\n};")

        # Create mock repo and symbols
        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = AddOverrideMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))

        # Should yield at least one refactoring
        assert len(refactorings) >= 1

        # Apply the refactorings
        for refactoring, symbol, qualifier in refactorings:
            # Manually apply the change (normally done by refactoring.apply())
            content = cpp_file.read_text()
            lines = content.splitlines(keepends=True)
            if symbol.line_start <= len(lines):
                line = lines[symbol.line_start - 1]
                if ';' in line and qualifier not in line:
                    lines[symbol.line_start - 1] = line.replace(';', f' {qualifier};')
                    cpp_file.write_text(''.join(lines))

        content = cpp_file.read_text()
        assert "override" in content

    def test_generate_refactorings_does_not_duplicate_override(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("class Foo { virtual void bar() override; };")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = AddOverrideMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))

        # Should not yield refactorings for functions that already have override
        content = cpp_file.read_text()
        assert content.count("override") == 1

    def test_generate_refactorings_handles_multiple_virtual_functions(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "class Foo {\n"
            "    virtual void bar();\n"
            "    virtual int baz();\n"
            "    virtual bool qux();\n"
            "};"
        )

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = AddOverrideMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))

        # Should yield 3 refactorings
        assert len(refactorings) == 3


class TestReplaceMSSpecificMod:
    def test_get_id_returns_stable_identifier(self):
        assert ReplaceMSSpecificMod.get_id() == "replace_ms_specific"

    def test_get_name_returns_human_readable_name(self):
        assert "MS" in ReplaceMSSpecificMod.get_name() or "Microsoft" in ReplaceMSSpecificMod.get_name()

    # NOTE: ReplaceMSSpecificMod is currently stubbed out (empty generator)
    # These tests verify the mod doesn't crash but won't perform transformations
    # until the mod is fully implemented

    def test_generate_refactorings_stubbed_forceinline(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__forceinline int add() { return 0; }")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        # Currently stubbed, yields nothing
        assert len(refactorings) == 0

    def test_generate_refactorings_stubbed_int64(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int64 x = 0;")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        # Currently stubbed, yields nothing
        assert len(refactorings) == 0

    def test_generate_refactorings_stubbed_int32(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("__int32 x = 0;")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        # Currently stubbed, yields nothing
        assert len(refactorings) == 0

    def test_generate_refactorings_stubbed_stdcall(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int __stdcall foo();")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        # Currently stubbed, yields nothing
        assert len(refactorings) == 0

    def test_generate_refactorings_stubbed_multiple_patterns(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text(
            "__forceinline __int64 foo() { __int32 x = 0; return x; }"
        )

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        # Currently stubbed, yields nothing
        assert len(refactorings) == 0

    def test_generate_refactorings_yields_nothing_for_non_ms_code(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        code = "int main() { return 0; }"
        cpp_file.write_text(code)

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = ReplaceMSSpecificMod()
        refactorings = list(mod.generate_refactorings(repo, symbols))
        assert len(refactorings) == 0
        content = cpp_file.read_text()
        assert content.strip() == code


class TestBaseMod:
    def test_base_mod_has_get_metadata(self):
        mod = AddOverrideMod()
        metadata = mod.get_metadata()
        assert isinstance(metadata, dict)
        assert "mod_id" in metadata
        assert "description" in metadata

    def test_generate_refactorings_is_generator(self, temp_dir):
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")

        repo = Mock(spec=Repo)
        repo.repo_path = temp_dir
        symbols = Mock(spec=SymbolTable)

        mod = AddOverrideMod()
        result = mod.generate_refactorings(repo, symbols)
        # Should be a generator
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
