import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from core.repo import Repo
from core.compilers import CompiledFile


class TestRepoGetRepoName:
    def test_extracts_name_from_https_url(self):
        url = "https://github.com/user/project.git"
        assert Repo.get_repo_name(url) == "project"

    def test_extracts_name_from_https_url_without_git_suffix(self):
        url = "https://github.com/user/project"
        assert Repo.get_repo_name(url) == "project"

    def test_extracts_name_from_ssh_url(self):
        url = "git@github.com:user/my-repo.git"
        assert Repo.get_repo_name(url) == "my-repo"

    def test_handles_trailing_slash(self):
        url = "https://github.com/user/project.git/"
        assert Repo.get_repo_name(url) == "project"

    def test_handles_multiple_slashes_at_end(self):
        url = "https://github.com/user/project///"
        assert Repo.get_repo_name(url) == "project"

    def test_extracts_name_with_hyphens(self):
        url = "https://github.com/user/my-awesome-project.git"
        assert Repo.get_repo_name(url) == "my-awesome-project"

    def test_extracts_name_with_underscores(self):
        url = "https://github.com/user/my_project.git"
        assert Repo.get_repo_name(url) == "my_project"

    def test_extracts_name_with_numbers(self):
        url = "https://github.com/user/project123.git"
        assert Repo.get_repo_name(url) == "project123"


class TestRepoInitialization:
    def test_init_sets_url(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        assert repo.url == "https://github.com/user/project.git"

    def test_init_sets_hardcoded_work_branch(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        assert repo.work_branch == "levelup-work"

    def test_init_sets_repo_path_from_repos_folder(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        # repo_path should be a subdirectory of repos_folder
        assert temp_dir in repo.repo_path.parents or repo.repo_path.parent == temp_dir

    def test_init_sets_default_git_path(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        assert repo.git_path == "git"

    def test_init_accepts_custom_git_path(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir,
            git_path="/usr/local/bin/git"
        )
        assert repo.git_path == "/usr/local/bin/git"

    def test_init_sets_empty_post_checkout_by_default(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        assert repo.post_checkout == ""

    def test_init_accepts_post_checkout_commands(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir,
            post_checkout="npm install"
        )
        assert repo.post_checkout == "npm install"


class TestRepoFromConfig:
    def test_creates_repo_from_config_dict(self, temp_dir):
        config = {
            "name": "my-project",
            "url": "https://github.com/user/my-project.git",
            "post_checkout": ""
        }
        repo = Repo.from_config(config, temp_dir)
        assert repo.url == config["url"]
        assert repo.work_branch == "levelup-work"

    def test_uses_post_checkout_from_config(self, temp_dir):
        config = {
            "name": "project",
            "url": "https://github.com/user/project.git",
            "post_checkout": "make setup"
        }
        repo = Repo.from_config(config, temp_dir)
        assert repo.post_checkout == "make setup"

    def test_defaults_post_checkout_to_empty_string(self, temp_dir):
        config = {
            "name": "project",
            "url": "https://github.com/user/project.git"
        }
        repo = Repo.from_config(config, temp_dir)
        assert repo.post_checkout == ""

    def test_uses_provided_git_path(self, temp_dir):
        config = {
            "name": "project",
            "url": "https://github.com/user/project.git"
        }
        repo = Repo.from_config(config, temp_dir, git_path="/custom/git")
        assert repo.git_path == "/custom/git"


class TestRepoGitOperations:
    @patch("subprocess.run")
    def test_run_git_constructs_correct_command(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="output\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo._run_git(["status"])
        args, kwargs = mock_run.call_args
        assert args[0][0] == "git"
        assert "status" in args[0]

    @patch("subprocess.run")
    def test_run_git_uses_repo_path_as_cwd(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="output\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo._run_git(["status"])
        args, kwargs = mock_run.call_args
        assert kwargs["cwd"] == repo.repo_path

    @patch("subprocess.run")
    def test_run_git_captures_output(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="output\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo._run_git(["status"])
        args, kwargs = mock_run.call_args
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    @patch("subprocess.run")
    def test_run_git_strips_output(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="  output with spaces  \n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        result = repo._run_git(["status"])
        assert result == "output with spaces"

    def test_clone_returns_self(self, temp_dir, git_repo):
        # Create a source repo to clone from
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create Repo object pointing to a new location
        target_dir = temp_dir / "target"
        repo = Repo(
            url=str(git_repo.working_dir),  # Clone from the git_repo fixture
            repos_folder=target_dir.parent
        )
        repo.repo_path = target_dir

        result = repo.clone()
        assert result is repo
        assert target_dir.exists()
        assert (target_dir / "README.md").exists()

    def test_pull_calls_git_pull(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Mock the pull operation since we don't have a real remote
        from unittest.mock import Mock
        mock_remote = Mock()
        mock_remote.pull.return_value = "Already up to date"
        git_repo.remote = Mock(return_value=mock_remote)

        result = repo.pull()
        assert result is not None
        git_repo.remote.assert_called_with('origin')

    def test_commit_adds_all_files_then_commits(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Create a new file to commit
        test_file = temp_dir / "test.cpp"
        test_file.write_text("int main() { return 0; }")

        result = repo.commit("Test commit message")
        assert result is True

        # Verify commit was made
        assert "Test commit message" in git_repo.head.commit.message

    def test_reset_hard_calls_git_reset(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Create a file and commit
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")
        git_repo.index.add(['test.txt'])
        git_repo.index.commit('Add test file')

        # Modify the file
        test_file.write_text("modified")

        # Reset hard should revert changes
        repo.reset_hard()
        assert test_file.read_text() == "original"

    def test_reset_hard_defaults_to_head(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        result = repo.reset_hard()
        assert "HEAD" in result or "Reset" in result

    def test_reset_hard_accepts_custom_ref(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Get current commit hash
        commit_hash = git_repo.head.commit.hexsha

        result = repo.reset_hard(commit_hash)
        assert result is not None

    def test_get_current_branch_returns_branch_name(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        branch = repo.get_current_branch()
        # Should return the current branch (fixture uses 'main')
        assert branch in ['main', 'master']  # Could be either depending on git config

    def test_get_commit_hash_returns_hash(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        hash_val = repo.get_commit_hash()
        assert len(hash_val) == 40  # Git hash is 40 characters
        assert hash_val == git_repo.head.commit.hexsha

    def test_stash_calls_git_stash(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Create an uncommitted change
        test_file = temp_dir / "test.txt"
        test_file.write_text("uncommitted change")

        result = repo.stash()
        assert result is not None

    def test_stash_pop_calls_git_stash_pop(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Create a file, commit it, then modify and stash
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")
        git_repo.index.add(['test.txt'])
        git_repo.index.commit('Add test file')

        # Modify and stash
        test_file.write_text("modified")
        git_repo.git.stash('push')

        # Now pop should work
        result = repo.stash_pop()
        assert result is not None


class TestRepoEnsureCloned:
    @patch.object(Repo, "clone")
    @patch.object(Repo, "pull")
    def test_clones_if_repo_path_does_not_exist(self, mock_pull, mock_clone, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        # Ensure repo_path doesn't exist
        if repo.repo_path.exists():
            repo.repo_path.rmdir()
        repo.ensure_cloned()
        mock_clone.assert_called_once()
        mock_pull.assert_not_called()

    @patch.object(Repo, "clone")
    @patch.object(Repo, "pull")
    def test_pulls_if_repo_path_exists(self, mock_pull, mock_clone, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        repo.ensure_cloned()
        # Should have attempted pull
        mock_pull.assert_called_once()
        mock_clone.assert_not_called()


class TestRepoCheckoutBranch:
    def test_checkout_existing_branch(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Create a feature branch
        git_repo.create_head('feature')

        repo.checkout_branch("feature")
        assert git_repo.active_branch.name == "feature"

    def test_checkout_defaults_to_work_branch(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        repo.checkout_branch(create=True)  # Need to create the branch
        assert git_repo.active_branch.name == "levelup-work"

    @patch("subprocess.run")
    def test_checkout_runs_post_checkout_command(self, mock_run, temp_dir, git_repo):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent,
            post_checkout="npm install"
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        repo.checkout_branch(create=True)  # Need to create the branch
        # Should have called the post_checkout command
        mock_run.assert_called_once()
        assert "npm install" in mock_run.call_args[0][0]

    def test_checkout_skips_post_checkout_if_empty(self, temp_dir, git_repo):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        repo._git_repo = git_repo

        # Should not raise an error
        repo.checkout_branch(create=True)  # Need to create the branch
        assert repo.get_current_branch() == "levelup-work"


class TestRepoRepr:
    def test_repr_includes_url(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repr_str = repr(repo)
        assert "https://github.com/user/project.git" in repr_str

    def test_repr_includes_name(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/myproject.git",
            repos_folder=temp_dir
        )
        repr_str = repr(repo)
        assert "myproject" in repr_str


class TestRepoCompilation:
    def test_compiled_files_initialized_as_empty_list(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        assert repo.compiled_files == []

    def test_find_source_files_returns_cpp_and_c_files(self, temp_dir):
        # Create a repo with source files
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir

        # Create source files
        (temp_dir / "main.cpp").write_text("int main() { return 0; }")
        (temp_dir / "utils.c").write_text("void util() {}")
        (temp_dir / "header.h").write_text("// header file")
        subdir = temp_dir / "src"
        subdir.mkdir()
        (subdir / "foo.cpp").write_text("void foo() {}")

        source_files = repo.find_source_files()

        # Should find .cpp and .c files, but not .h files
        assert len(source_files) == 3
        filenames = {f.name for f in source_files}
        assert "main.cpp" in filenames
        assert "utils.c" in filenames
        assert "foo.cpp" in filenames
        assert "header.h" not in filenames

    def test_find_source_files_returns_sorted_list(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir

        # Create files in non-alphabetical order
        (temp_dir / "z.cpp").write_text("// z")
        (temp_dir / "a.cpp").write_text("// a")
        (temp_dir / "m.cpp").write_text("// m")

        source_files = repo.find_source_files()

        # Should be sorted
        filenames = [f.name for f in source_files]
        assert filenames == sorted(filenames)

    def test_find_source_files_returns_empty_list_for_empty_repo(self, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir

        source_files = repo.find_source_files()
        assert source_files == []

    @patch("core.repo.repo.get_compiler")
    def test_compile_all_files_compiles_each_source_file(self, mock_get_compiler, temp_dir):
        # Setup mock compiler
        mock_compiler = Mock()
        mock_compiled1 = CompiledFile(
            source_file=temp_dir / "main.cpp",
            asm_file=None
        )
        mock_compiled2 = CompiledFile(
            source_file=temp_dir / "utils.cpp",
            asm_file=None
        )
        mock_compiler.compile_file.side_effect = [mock_compiled1, mock_compiled2]
        mock_get_compiler.return_value = mock_compiler

        # Create repo with source files
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        (temp_dir / "main.cpp").write_text("int main() { return 0; }")
        (temp_dir / "utils.cpp").write_text("void util() {}")

        # Compile all files
        compiled_files = repo.compile_all_files(optimization_level=0)

        # Should have compiled both files
        assert len(compiled_files) == 2
        assert mock_compiler.compile_file.call_count == 2

        # Check calls were made with correct arguments
        calls = mock_compiler.compile_file.call_args_list
        assert calls[0][0][1] == 0  # optimization_level

    @patch("core.repo.repo.get_compiler")
    def test_compile_all_files_stores_results_in_compiled_files(self, mock_get_compiler, temp_dir):
        # Setup mock compiler
        mock_compiler = Mock()
        mock_compiled = CompiledFile(
            source_file=temp_dir / "main.cpp",
            asm_file=None
        )
        mock_compiler.compile_file.return_value = mock_compiled
        mock_get_compiler.return_value = mock_compiler

        # Create repo with source file
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        (temp_dir / "main.cpp").write_text("int main() { return 0; }")

        # Compile all files
        repo.compile_all_files()

        # Should store results in compiled_files
        assert len(repo.compiled_files) == 1
        assert repo.compiled_files[0] == mock_compiled

    @patch("core.repo.repo.get_compiler")
    def test_compile_all_files_continues_on_compilation_error(self, mock_get_compiler, temp_dir):
        # Setup mock compiler that fails on first file but succeeds on second
        mock_compiler = Mock()
        mock_compiled = CompiledFile(
            source_file=temp_dir / "good.cpp",
            asm_file=None
        )
        mock_compiler.compile_file.side_effect = [
            RuntimeError("Compilation failed"),
            mock_compiled
        ]
        mock_get_compiler.return_value = mock_compiler

        # Create repo with two source files
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        (temp_dir / "bad.cpp").write_text("invalid c++ code @#$%")
        (temp_dir / "good.cpp").write_text("int main() { return 0; }")

        # Compile all files - should not raise exception
        compiled_files = repo.compile_all_files()

        # Should have compiled only the successful file
        assert len(compiled_files) == 1
        assert compiled_files[0].source_file.name == "good.cpp"

    @patch("core.repo.repo.get_compiler")
    def test_compile_all_files_uses_custom_optimization_level(self, mock_get_compiler, temp_dir):
        # Setup mock compiler
        mock_compiler = Mock()
        mock_compiled = CompiledFile(
            source_file=temp_dir / "main.cpp",
            asm_file=None
        )
        mock_compiler.compile_file.return_value = mock_compiled
        mock_get_compiler.return_value = mock_compiler

        # Create repo with source file
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        (temp_dir / "main.cpp").write_text("int main() { return 0; }")

        # Compile with O3
        repo.compile_all_files(optimization_level=3)

        # Should pass optimization level to compiler
        mock_compiler.compile_file.assert_called_once()
        assert mock_compiler.compile_file.call_args[0][1] == 3

    @patch("core.repo.repo.get_compiler")
    def test_compile_all_files_returns_compiled_files_list(self, mock_get_compiler, temp_dir):
        # Setup mock compiler
        mock_compiler = Mock()
        mock_compiled1 = CompiledFile(
            source_file=temp_dir / "a.cpp",
            asm_file=None
        )
        mock_compiled2 = CompiledFile(
            source_file=temp_dir / "b.cpp",
            asm_file=None
        )
        mock_compiler.compile_file.side_effect = [mock_compiled1, mock_compiled2]
        mock_get_compiler.return_value = mock_compiler

        # Create repo with source files
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir.parent
        )
        repo.repo_path = temp_dir
        (temp_dir / "a.cpp").write_text("void a() {}")
        (temp_dir / "b.cpp").write_text("void b() {}")

        # Compile all files
        result = repo.compile_all_files()

        # Should return the list of compiled files
        assert isinstance(result, list)
        assert len(result) == 2
        assert mock_compiled1 in result
        assert mock_compiled2 in result
