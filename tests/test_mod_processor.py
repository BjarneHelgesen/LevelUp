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
        mock.get_id.return_value = "test_mod"
        mock.get_name.return_value = "Test Mod"
        mock.get_metadata.return_value = {"mod_id": "test", "description": "Test"}
        mock.get_validator_id.return_value = "asm_o0"
        # generate_changes returns empty by default, tests should override as needed
        mock.generate_changes.return_value = iter([])
        return mock

    @pytest.fixture
    def builtin_mod_request(self, mock_mod_instance):
        return ModRequest(
            id="test-123",
            repo_url="https://github.com/user/repo.git",
            source_type=ModSourceType.BUILTIN,
            description="Test builtin mod",
            mod_instance=mock_mod_instance
        )

    @pytest.fixture
    def commit_mod_request(self):
        return ModRequest(
            id="test-456",
            repo_url="https://github.com/user/repo.git",
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
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])

        # Mock compiler to return CompiledFile and validator
        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.SUCCESS

    @patch("core.mod_processor.Repo")
    def test_process_mod_pushes_on_success(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        processor.process_mod(builtin_mod_request)

        mock_repo.push.assert_called_once()

    @patch("core.mod_processor.ValidatorFactory")
    @patch("core.mod_processor.Repo")
    def test_process_mod_returns_failed_when_no_changes_accepted(
        self, mock_repo_class, mock_validator_factory, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])
        # Override get_id to not be 'remove_inline' so validation is applied
        builtin_mod_request.mod_instance.get_id.return_value = "some_other_mod"

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # Mock the validator factory to return a validator that fails
        mock_validator = Mock()
        mock_validator.validate.return_value = False
        mock_validator.get_optimization_level.return_value = 0
        mock_validator_factory.from_id.return_value = mock_validator

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.FAILED

    @patch("core.mod_processor.ValidatorFactory")
    @patch("core.mod_processor.Repo")
    def test_process_mod_reverts_file_on_validation_failure(
        self, mock_repo_class, mock_validator_factory, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        original_content = "int x = 1;"
        cpp_file.write_text(original_content)
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])
        # Override get_id to not be 'remove_inline' so validation is applied
        builtin_mod_request.mod_instance.get_id.return_value = "some_other_mod"

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # Mock the validator factory to return a validator that fails
        mock_validator = Mock()
        mock_validator.validate.return_value = False
        mock_validator.get_optimization_level.return_value = 0
        mock_validator_factory.from_id.return_value = mock_validator

        processor.process_mod(builtin_mod_request)

        # File should be reverted to original content
        assert cpp_file.read_text() == original_content

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
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        result = processor.process_mod(builtin_mod_request)

        assert result.validation_results is not None
        assert len(result.validation_results) == 1
        assert result.validation_results[0].valid is True

    @patch("core.mod_processor.Repo")
    def test_process_mod_validates_each_change(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        for f in cpp_files:
            f.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield three changes
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_files[0], "Change at test0.cpp:1"),
            (cpp_files[1], "Change at test1.cpp:1"),
            (cpp_files[2], "Change at test2.cpp:1"),
        ])

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        result = processor.process_mod(builtin_mod_request)

        assert len(result.validation_results) == 3

    @patch("core.mod_processor.ValidatorFactory")
    @patch("core.mod_processor.Repo")
    def test_process_mod_partial_when_some_changes_rejected(
        self, mock_repo_class, mock_validator_factory, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        for f in cpp_files:
            f.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield three changes
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_files[0], "Change at test0.cpp:1"),
            (cpp_files[1], "Change at test1.cpp:1"),
            (cpp_files[2], "Change at test2.cpp:1"),
        ])
        # Override get_id to not be 'remove_inline' so validation is applied
        builtin_mod_request.mod_instance.get_id.return_value = "some_other_mod"

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # Mock the validator factory to return a validator
        # Second file fails validation
        mock_validator = Mock()
        mock_validator.validate.side_effect = [True, False, True]
        mock_validator.get_optimization_level.return_value = 0
        mock_validator_factory.from_id.return_value = mock_validator

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.PARTIAL

    @patch("core.mod_processor.ValidatorFactory")
    @patch("core.mod_processor.Repo")
    def test_process_mod_restores_failed_files_on_partial_success(
        self, mock_repo_class, mock_validator_factory, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        original_contents = ["original0", "original1", "original2"]
        for i, f in enumerate(cpp_files):
            f.write_text(original_contents[i])
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield three changes
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_files[0], "Change at test0.cpp:1"),
            (cpp_files[1], "Change at test1.cpp:1"),
            (cpp_files[2], "Change at test2.cpp:1"),
        ])
        # Override get_id to not be 'remove_inline' so validation is applied
        builtin_mod_request.mod_instance.get_id.return_value = "some_other_mod"

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # Mock the validator factory to return a validator
        # File 0 passes, file 1 fails, file 2 passes
        mock_validator = Mock()
        mock_validator.validate.side_effect = [True, False, True]
        mock_validator.get_optimization_level.return_value = 0
        mock_validator_factory.from_id.return_value = mock_validator

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.PARTIAL
        # Failed file (test1.cpp) should be restored to original content
        assert cpp_files[1].read_text() == original_contents[1]

    @patch("core.mod_processor.Repo")
    def test_process_mod_squashes_and_pushes_on_partial(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(2)]
        for f in cpp_files:
            f.write_text("original")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield two changes
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_files[0], "Change at test0.cpp:1"),
            (cpp_files[1], "Change at test1.cpp:1"),
        ])
        # Override get_id to not be 'remove_inline' so validation is applied
        builtin_mod_request.mod_instance.get_id.return_value = "some_other_mod"

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

        # First passes, second fails
        processor.asm_validator.validate = Mock(side_effect=[True, False])

        result = processor.process_mod(builtin_mod_request)

        # Should still squash and push (with successful changes only)
        mock_repo.squash_and_rebase.assert_called_once()
        mock_repo.push.assert_called_once()

    @patch("core.mod_processor.Repo")
    def test_process_mod_completes_successfully_with_changes(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Mock generate_changes to yield one change
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([
            (cpp_file, "Remove inline at test.cpp:1")
        ])

        mock_compiled = Mock(spec=CompiledFile)
        mock_compiled.asm_output = "mov eax, 1"
        processor.compiler.compile_file = Mock(return_value=mock_compiled)

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
    def test_process_mod_handles_no_changes(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # generate_changes returns empty iterator (no changes needed)
        builtin_mod_request.mod_instance.generate_changes.return_value = iter([])

        result = processor.process_mod(builtin_mod_request)

        # No changes should still result in FAILED (nothing accepted)
        assert result.status == ResultStatus.FAILED


class TestModProcessorTempFileCleanup:
    @patch("core.mod_processor.Repo")
    def test_error_on_compilation_exception(
        self, mock_repo_class, temp_dir
    ):
        processor = ModProcessor(
            repos_path=temp_dir / "repos"
        )

        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path = temp_dir
        mock_repo_class.return_value = mock_repo

        # Make compiler raise an exception to test error handling
        processor.compiler.compile_file = Mock(side_effect=Exception("Compilation error"))

        mock_mod = Mock()
        mock_mod.get_id.return_value = "test_mod"
        mock_mod.get_name.return_value = "Test Mod"
        mock_mod.get_validator_id.return_value = "asm_o0"
        mock_mod.generate_changes.return_value = iter([
            (cpp_file, "Change at test.cpp:1")
        ])
        request = ModRequest(
            id="test",
            repo_url="url",
            source_type=ModSourceType.BUILTIN,
            description="test",
            mod_instance=mock_mod
        )

        result = processor.process_mod(request)

        # Result should be ERROR
        assert result.status == ResultStatus.ERROR
        assert "Compilation error" in result.message
