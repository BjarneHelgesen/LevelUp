import pytest
from pathlib import Path
from unittest.mock import Mock
from levelup_core.validators.asm_validator import ASMValidator


class TestASMValidatorBasics:
    def test_get_id_returns_stable_identifier(self):
        assert ASMValidator.get_id() == "asm"

    def test_get_name_returns_human_readable_name(self):
        assert ASMValidator.get_name() == "Assembly Comparison"

    def test_can_be_constructed_with_compiler(self):
        mock_compiler = Mock()
        validator = ASMValidator(mock_compiler)
        assert validator.compiler is mock_compiler

    def test_has_ignore_patterns(self):
        validator = ASMValidator(Mock())
        assert len(validator.ignore_patterns) > 0


class TestASMValidatorNormalization:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_normalize_removes_comment_lines(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("; This is a comment\nmov eax, 1\n; Another comment\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert "comment" not in str(normalized).lower()
        assert any("mov" in line for line in normalized)

    def test_normalize_removes_title_directive(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("    TITLE   C:\\path\\to\\file.cpp\nmov eax, 1\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert not any("TITLE" in line for line in normalized)

    def test_normalize_removes_file_directive(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("    .file   \"test.cpp\"\nmov eax, 1\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert not any(".file" in line for line in normalized)

    def test_normalize_removes_includelib_directive(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("INCLUDELIB MSVCRT\nmov eax, 1\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert not any("INCLUDELIB" in line for line in normalized)

    def test_normalize_collapses_whitespace(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("    mov     eax,    1\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert any("mov eax, 1" in line or "mov eax,1" in line for line in normalized)

    def test_normalize_raises_for_nonexistent_file(self, temp_dir, validator):
        with pytest.raises(FileNotFoundError):
            validator._normalize_asm_file(temp_dir / "nonexistent.asm")

    def test_normalize_removes_empty_lines_outside_functions(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text("\n\nmov eax, 1\n\n")
        normalized = validator._normalize_asm_file(asm_file)
        assert "" not in normalized

    def test_normalize_preserves_function_code(self, temp_dir, validator):
        asm_file = temp_dir / "test.asm"
        asm_file.write_text(
            "_TEXT SEGMENT\n"
            "mov eax, 1\n"
            "add eax, 2\n"
            "ret\n"
            "_TEXT ENDS\n"
        )
        normalized = validator._normalize_asm_file(asm_file)
        assert any("mov eax" in line for line in normalized)
        assert any("add eax" in line for line in normalized)
        assert any("ret" in line for line in normalized)


class TestASMValidatorValidation:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_identical_files_validate_true(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        content = "mov eax, 1\nadd eax, 2\nret\n"
        asm1.write_text(content)
        asm2.write_text(content)
        assert validator.validate(asm1, asm2) is True

    def test_different_files_validate_false(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        asm1.write_text("mov eax, 1\nret\n")
        asm2.write_text("mov eax, 2\nret\n")
        # This should fail because the constant changed
        result = validator.validate(asm1, asm2)
        assert result is False

    def test_files_with_only_comment_differences_validate_true(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        asm1.write_text("; Comment v1\nmov eax, 1\nret\n")
        asm2.write_text("; Different comment\nmov eax, 1\nret\n")
        assert validator.validate(asm1, asm2) is True

    def test_files_with_only_title_differences_validate_true(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        asm1.write_text("    TITLE   C:\\path1\\file.cpp\nmov eax, 1\nret\n")
        asm2.write_text("    TITLE   C:\\path2\\different.cpp\nmov eax, 1\nret\n")
        assert validator.validate(asm1, asm2) is True


class TestASMValidatorRegisterSubstitution:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_eax_ebx_substitution_detected(self, validator):
        orig = "mov eax, 1"
        mod = "mov ebx, 1"
        assert validator._is_register_substitution(orig, mod) is True

    def test_rax_rbx_substitution_detected(self, validator):
        orig = "mov rax, 1"
        mod = "mov rbx, 1"
        assert validator._is_register_substitution(orig, mod) is True

    def test_al_bl_substitution_detected(self, validator):
        orig = "mov al, 1"
        mod = "mov bl, 1"
        assert validator._is_register_substitution(orig, mod) is True

    def test_different_operations_not_register_substitution(self, validator):
        orig = "mov eax, 1"
        mod = "add eax, 1"
        assert validator._is_register_substitution(orig, mod) is False

    def test_different_operands_not_register_substitution(self, validator):
        orig = "mov eax, 1"
        mod = "mov eax, 2"
        assert validator._is_register_substitution(orig, mod) is False


class TestASMValidatorEquivalentOperations:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_lea_and_mov_considered_equivalent(self, validator):
        orig = "lea eax, [ebx]"
        mod = "mov eax, ebx"
        assert validator._are_equivalent_operations(orig, mod) is True

    def test_add_and_lea_considered_equivalent(self, validator):
        orig = "add eax, 4"
        mod = "lea eax, [eax+4]"
        assert validator._are_equivalent_operations(orig, mod) is True

    def test_completely_different_ops_not_equivalent(self, validator):
        orig = "push eax"
        mod = "pop eax"
        assert validator._are_equivalent_operations(orig, mod) is False


class TestASMValidatorReorderingSafety:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_small_block_reordering_is_safe(self, validator):
        orig = ["mov eax, 1", "mov ebx, 2"]
        mod = ["mov ebx, 2", "mov eax, 1"]
        # Small blocks (<=3 lines) are considered safe
        assert validator._check_reordering_safety(orig, mod) is True

    def test_large_block_reordering_is_unsafe(self, validator):
        orig = ["mov eax, 1", "mov ebx, 2", "mov ecx, 3", "mov edx, 4"]
        mod = ["mov edx, 4", "mov ecx, 3", "mov ebx, 2", "mov eax, 1"]
        # Large blocks are considered unsafe
        assert validator._check_reordering_safety(orig, mod) is False


class TestASMValidatorDeletions:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_deleting_mov_is_unsafe(self, validator):
        lines = ["mov eax, 1"]
        assert validator._is_safe_to_delete(lines) is False

    def test_deleting_call_is_unsafe(self, validator):
        lines = ["call some_function"]
        assert validator._is_safe_to_delete(lines) is False

    def test_deleting_jmp_is_unsafe(self, validator):
        lines = ["jmp label"]
        assert validator._is_safe_to_delete(lines) is False

    def test_deleting_ret_is_unsafe(self, validator):
        lines = ["ret"]
        assert validator._is_safe_to_delete(lines) is False

    def test_deleting_nop_is_safe(self, validator):
        lines = ["nop"]
        assert validator._is_safe_to_delete(lines) is True

    def test_deleting_label_is_safe(self, validator):
        lines = ["$label:"]
        assert validator._is_safe_to_delete(lines) is True


class TestASMValidatorInsertions:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_inserting_nop_is_safe(self, validator):
        lines = ["nop"]
        assert validator._is_safe_to_insert(lines) is True

    def test_inserting_align_is_safe(self, validator):
        lines = ["align 16"]
        assert validator._is_safe_to_insert(lines) is True

    def test_inserting_mov_is_unsafe(self, validator):
        lines = ["mov eax, 1"]
        assert validator._is_safe_to_insert(lines) is False

    def test_inserting_call_is_unsafe(self, validator):
        lines = ["call extra_function"]
        assert validator._is_safe_to_insert(lines) is False


class TestASMValidatorDiffReport:
    @pytest.fixture
    def validator(self):
        return ASMValidator(Mock())

    def test_diff_report_returns_string(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        asm1.write_text("mov eax, 1\n")
        asm2.write_text("mov eax, 2\n")
        report = validator.get_diff_report(asm1, asm2)
        assert isinstance(report, str)

    def test_diff_report_shows_differences(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        asm1.write_text("mov eax, 1\n")
        asm2.write_text("mov eax, 2\n")
        report = validator.get_diff_report(asm1, asm2)
        # Unified diff format uses - and +
        assert "-" in report or "+" in report

    def test_diff_report_empty_for_identical_files(self, temp_dir, validator):
        asm1 = temp_dir / "original.asm"
        asm2 = temp_dir / "modified.asm"
        content = "mov eax, 1\nret\n"
        asm1.write_text(content)
        asm2.write_text(content)
        report = validator.get_diff_report(asm1, asm2)
        # Empty diff should have no content
        assert report.strip() == ""
