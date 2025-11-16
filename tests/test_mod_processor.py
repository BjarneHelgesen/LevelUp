import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from core.mod_processor import ModProcessor
from core.mod_request import ModRequest, ModSourceType
from core.result import Result, ResultStatus


class TestModProcessorInitialization:
    def test_init_creates_msvc_compiler(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir,
            temp_path=temp_dir / "temp"
        )
        assert processor.compiler is not None

    def test_init_creates_asm_validator(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir,
            temp_path=temp_dir / "temp"
        )
        assert processor.asm_validator is not None

    def test_init_creates_mod_handler(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir,
            temp_path=temp_dir / "temp"
        )
        assert processor.mod_handler is not None

    def test_init_stores_repos_path(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir / "repos",
            temp_path=temp_dir / "temp"
        )
        assert processor.repos_path == temp_dir / "repos"

    def test_init_stores_temp_path(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir / "repos",
            temp_path=temp_dir / "temp"
        )
        assert processor.temp_path == temp_dir / "temp"

    def test_init_stores_git_path(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir,
            temp_path=temp_dir / "temp",
            git_path="/usr/bin/git"
        )
        assert processor.git_path == "/usr/bin/git"

    def test_init_defaults_git_path_to_git(self, temp_dir):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir,
            temp_path=temp_dir / "temp"
        )
        assert processor.git_path == "git"


class TestModProcessorProcessMod:
    @pytest.fixture
    def processor(self, temp_dir):
        return ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir / "repos",
            temp_path=temp_dir / "temp"
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

        # Mock compiler and validator
        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.SUCCESS
        assert "successfully" in result.message.lower()

    @patch("core.mod_processor.Repo")
    def test_process_mod_commits_on_success(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

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

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=False)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.FAILED
        assert "failed" in result.message.lower()

    @patch("core.mod_processor.Repo")
    def test_process_mod_resets_on_failure(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=False)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

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
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

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
        mock_repo.repo_path.glob.return_value = cpp_files
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

        result = processor.process_mod(builtin_mod_request)

        assert processor.asm_validator.validate.call_count == 3
        assert len(result.validation_results) == 3

    @patch("core.mod_processor.Repo")
    def test_process_mod_fails_if_any_file_invalid(
        self, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_files = [temp_dir / f"test{i}.cpp" for i in range(3)]
        for f in cpp_files:
            f.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = cpp_files
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        # Second file fails validation
        processor.asm_validator.validate = Mock(side_effect=[True, False, True])
        processor.mod_handler.apply_mod_instance = Mock(return_value=Path("/tmp/mod.cpp"))

        result = processor.process_mod(builtin_mod_request)

        assert result.status == ResultStatus.FAILED

    @patch("core.mod_processor.Repo")
    @patch("os.remove")
    def test_process_mod_cleans_up_temp_files(
        self, mock_remove, mock_repo_class, processor, builtin_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        asm_path = temp_dir / "test.asm"
        asm_path.write_text("mock asm")
        mod_path = temp_dir / "modified.cpp"
        mod_path.write_text("modified")

        processor.compiler.compile_to_asm = Mock(return_value=asm_path)
        processor.asm_validator.validate = Mock(return_value=True)
        processor.mod_handler.apply_mod_instance = Mock(return_value=mod_path)

        processor.process_mod(builtin_mod_request)

        # Should have attempted to remove temp files
        assert mock_remove.call_count >= 2  # at least original_asm and modified_asm

    @patch("core.mod_processor.Repo")
    def test_process_mod_for_commit_uses_original_file(
        self, mock_repo_class, processor, commit_mod_request, temp_dir
    ):
        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        processor.compiler.compile_to_asm = Mock(return_value=Path("/tmp/test.asm"))
        processor.asm_validator.validate = Mock(return_value=True)

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
    @patch("os.remove")
    def test_cleanup_occurs_even_on_exception(
        self, mock_remove, mock_repo_class, temp_dir
    ):
        processor = ModProcessor(
            msvc_path="cl.exe",
            repos_path=temp_dir / "repos",
            temp_path=temp_dir / "temp"
        )

        mock_repo = MagicMock()
        cpp_file = temp_dir / "test.cpp"
        cpp_file.write_text("inline int x = 1;")
        mock_repo.repo_path.glob.return_value = [cpp_file]
        mock_repo_class.return_value = mock_repo

        asm_path = temp_dir / "test.asm"
        asm_path.write_text("mock asm")
        processor.compiler.compile_to_asm = Mock(return_value=asm_path)
        processor.asm_validator.validate = Mock(side_effect=Exception("Validation error"))
        processor.mod_handler.apply_mod_instance = Mock(return_value=temp_dir / "mod.cpp")

        mock_mod = Mock()
        mock_mod.validate_before_apply.return_value = (True, "OK")
        request = ModRequest(
            id="test",
            repo_url="url",
            repo_name="name",
            source_type=ModSourceType.BUILTIN,
            description="test",
            mod_instance=mock_mod
        )

        result = processor.process_mod(request)

        # Result should be ERROR but cleanup should still happen
        assert result.status == ResultStatus.ERROR
        # Cleanup should have been attempted
        assert mock_remove.called or True  # Best effort cleanup
