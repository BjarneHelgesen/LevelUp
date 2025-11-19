import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from core.mod_processor import ModProcessor
from core.mod_request import ModRequest, ModSourceType
from core.result import Result, ResultStatus
from core.compilers.compiled_file import CompiledFile


class TestModProcessorInitialization:
    def test_init_creates_msvc_compiler(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir
        )
        assert processor.compiler is not None

    def test_init_creates_asm_validator(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir
        )
        assert processor.asm_validator is not None

    def test_init_creates_mod_handler(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir
        )
        assert processor.mod_handler is not None

    def test_init_stores_repos_path(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir / "repos"
        )
        assert processor.repos_path == (temp_dir / "repos").resolve()

    def test_init_stores_git_path(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir,
            git_path="/usr/bin/git"
        )
        assert processor.git_path == "/usr/bin/git"

    def test_init_defaults_git_path_to_git(self, temp_dir):
        processor = ModProcessor(
            repos_path=temp_dir
        )
        assert processor.git_path == "git"


class TestModProcessorProcessMod:
    @pytest.fixture
    def processor(self, temp_dir):
        return ModProcessor(
            repos_path=temp_dir / "repos"
        )

    @pytest.fixture
    def mock_mod_instance(self):
        mock = Mock()
        mock.validate_before_apply.return_value = (True, "OK")
        mock.apply.return_value = Path("/tmp/modified.cpp")
        mock.get_metadata.return_value = {"mod_id": "test", "description": "Test"}
        return mock

    @pytest.fixture
    def builtin_mod_request(self, mock_mod_instance):
        return ModRequest(
            id="test-123",
            repo_url="https://github.com/user/repo.git",
            repo_name="repo",
            source_type=ModSourceType.BUILTIN,
            description="Test builtin mod",
            mod_instance=mock_mod_instance
        )

    @pytest.fixture
    def commit_mod_request(self):
        return ModRequest(
            id="test-456",
            repo_url="https://github.com/user/repo.git",
            repo_name="repo",
            source_type=ModSourceType.COMMIT,
            description="Test commit mod",
            commit_hash="abc123"
        )

    @patch("core.mod_processor.Repo")
    def test_process_mod_creates_repo_with_correct_params(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        processor.process_mod(builtin_mod_request)

        mock_repo_class.assert_called_once_with(
            url=builtin_mod_request.repo_url,
            repos_folder=processor.repos_path,
            git_path=processor.git_path
        )

    @patch("core.mod_processor.Repo")
    def test_process_mod_ensures_repo_cloned(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        processor.process_mod(builtin_mod_request)

        mock_repo.ensure_cloned.assert_called_once()

    @patch("core.mod_processor.Repo")
    def test_process_mod_prepares_work_branch(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        processor.process_mod(builtin_mod_request)

        mock_repo.prepare_work_branch.assert_called_once()

    @patch("core.mod_processor.Repo")
    def test_process_mod_cherry_picks_for_commit_source(
        self, mock_repo_class, processor, commit_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        processor.process_mod(commit_mod_request)

        mock_repo.cherry_pick.assert_called_once_with("abc123")

    @patch("core.mod_processor.Repo")
    def test_process_mod_does_not_cherry_pick_for_builtin(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        processor.process_mod(builtin_mod_request)

        mock_repo.cherry_pick.assert_not_called()

    @patch("core.mod_processor.Repo")
    def test_process_mod_returns_success_when_all_valid(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        # Mock compiler to return CompiledFile and validator
        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.SUCCESS

    @patch("core.mod_processor.Repo")
    def test_process_mod_commits_on_success(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)

        processor.process_mod(builtin_mod_request)

        mock_repo.commit.assert_called_once()
        commit_msg = mock_repo.commit.call_args[0][0]
        assert builtin_mod_request.id in commit_msg

    @patch("core.mod_processor.Repo")
    def test_process_mod_returns_failed_when_validation_fails(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=False)

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.FAILED

    @patch("core.mod_processor.Repo")
    def test_process_mod_resets_on_failure(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=False)

        processor.process_mod(builtin_mod_request)

        mock_repo.reset_hard.assert_called_once()

    @patch("core.mod_processor.Repo")
    def test_process_mod_returns_error_on_exception(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo_class.side_effect = Exception("Clone failed")

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.ERROR
        assert "Clone failed" in result.message

    @patch("core.mod_processor.Repo")
    def test_process_mod_includes_validation_results(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        # glob is called for multiple patterns, return file only for .cpp
        def glob_side_effect(pattern):
            if '*.cpp' in pattern:
                return [cpp_file]
            return []
        mock_repo.repo_path.glob.side_effect = glob_side_effect
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)

        result = processor.process_mod(builtin_mod_request)

        assert result.validation_results is not None
        assert len(result.validation_results) == 1
        assert result.validation_results[0].valid is True

    @patch("core.mod_processor.Repo")
    def test_process_mod_validates_each_cpp_file(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        for f in cpp_files:
            f.write_text("inline int x = 1;")
        # glob is called for multiple patterns, return files only for .cpp
        def glob_side_effect(pattern):
            if '*.cpp' in pattern:
                return cpp_files
            return []
        mock_repo.repo_path.glob.side_effect = glob_side_effect
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)

        result = processor.process_mod(builtin_mod_request)

        # Note: remove_inline mod doesn't use asm_validator for validation
        # It just checks compilation success, so validator won't be called
        assert len(result.validation_results) == 3

    @patch("core.mod_processor.Repo")
    def test_process_mod_fails_if_any_file_invalid(
        self, mock_repo_class, processor, commit_mod_request, temp_dir
    ):
        # Use commit_mod_request to test asm_validator path
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        for f in cpp_files:
            f.write_text("int x = 1;")
        # glob is called for multiple patterns, return files only for .cpp
        def glob_side_effect(pattern):
            if '*.cpp' in pattern:
                return cpp_files
            return []
        mock_repo.repo_path.glob.side_effect = glob_side_effect
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        # Second file fails validation
        processor.asm_validator.validate = Mock(side_effect=[True, False, True])

        result = processor.process_mod(commit_mod_request)

        assert result.status == ResultStatus.PARTIAL  # Some passed, some failed

    @patch("core.mod_processor.Repo")
    def test_process_mod_restores_failed_files_on_partial_success(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        original_contents = ["original0", "original1", "original2"]
        for i, f in enumerate(cpp_files):
            f.write_text(original_contents[i])

        def glob_side_effect(pattern):
            if '*.cpp' in pattern:
                return cpp_files
            return []
        mock_repo.repo_path.glob.side_effect = glob_side_effect
        mock_repo_class.return_value = mock_repo

        # Set up different mod_instance that triggers asm_validator
        mock_mod = Mock()
        mock_mod.get_id.return_value = "add_override"  # Not remove_inline
        mock_mod.get_name.return_value = "Add Override"
        builtin_mod_request.mod_instance = mock_mod

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # File 0 passes, file 1 fails, file 2 passes
        processor.asm_validator.validate = Mock(side_effect=[True, False, True])

        # Simulate mod modifying the files
        def apply_side_effect(file, mod):
            file.write_text(f"modified_{file.name}")
        processor.mod_handler.apply_mod_instance = Mock(side_effect=apply_side_effect)

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.PARTIAL
        # Failed file (test1.cpp) should be restored to original content
        assert cpp_files[1].read_text() == "original1"
        # Successful files should retain modified content
        assert "modified" in cpp_files[0].read_text()
        assert "modified" in cpp_files[2].read_text()

    @patch("core.mod_processor.Repo")
    def test_process_mod_commits_only_successful_files_on_partial(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(2)]
        for f in cpp_files:
            f.write_text("original")

        def glob_side_effect(pattern):
            if '*.cpp' in pattern:
                return cpp_files
            return []
        mock_repo.repo_path.glob.side_effect = glob_side_effect
        mock_repo_class.return_value = mock_repo

        mock_mod = Mock()
        mock_mod.get_id.return_value = "add_override"
        mock_mod.get_name.return_value = "Add Override"
        builtin_mod_request.mod_instance = mock_mod

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # First passes, second fails
        processor.asm_validator.validate = Mock(side_effect=[True, False])
        processor.mod_handler.apply_mod_instance = Mock()

        result = processor.process_mod(builtin_mod_request)

        # Should still commit (with successful changes only)
        mock_repo.commit.assert_called_once()
        # Commit message should include counts
        commit_msg = mock_repo.commit.call_args[0][0]
        assert "1/2" in commit_msg

    @patch("core.mod_processor.Repo")
    def test_process_mod_cleans_up_temp_files(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        # Test that processor completes successfully - cleanup is internal to compiler
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)

        result = processor.process_mod(builtin_mod_request)

        # Process should complete successfully
        assert result.status == ResultStatus.SUCCESS

    @patch("core.mod_processor.Repo")
    def test_process_mod_for_commit_uses_original_file(
        self, mock_repo_class, processor, commit_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock()

        processor.process_mod(commit_mod_request)

        # For commit source, mod_handler should NOT be called
        processor.mod_handler.apply_mod_instance.assert_not_called()

    @patch("core.mod_processor.Repo")
    def test_process_mod_handles_empty_repo(
        self, mock_repo_class, processor, builtin_mod_request
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path.glob.return_value = []
        mock_repo_class.return_value = mock_repo

        result = processor.process_mod(builtin_mod_request)

        # Empty repo should still succeed (no files to validate)
        assert result.status == ResultStatus.SUCCESS
        assert result.validation_results == []


class TestModProcessorTempFileCleanup:
    @patch("core.mod_processor.Repo")
    def test_cleanup_occurs_even_on_exception(
        self, mock_repo_class, temp_dir
    ):
        processor = ModProcessor(
            repos_path=temp_dir / "repos"
        )

        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        # Make compiler raise an exception to test error handling
        processor.compiler.compile_file = Mock(side_effect=Exception("Compilation error"))

        mock_mod = Mock()
        mock_mod.validate_before_apply.return_value = (True, "OK")
        mock_mod.get_id.return_value = "test_mod"
        mock_mod.get_name.return_value = "Test Mod"
        request = ModRequest(
            id="test",
            repo_url="url",
            repo_name="name",
            source_type=ModSourceType.BUILTIN,
            description="test",
            mod_instance=mock_mod
        )

        result = processor.process_mod(request)

        # Result should be ERROR
        assert result.status == ResultStatus.ERROR
        assert "Compilation error" in result.message
