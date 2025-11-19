import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from core.repo import Repo


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

    @patch("subprocess.run")
    def test_clone_calls_git_clone_with_url_and_path(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.clone()
        args, kwargs = mock_run.call_args
        assert "clone" in args[0]
        assert "https://github.com/user/project.git" in args[0]

    @patch("subprocess.run")
    def test_clone_returns_self(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        result = repo.clone()
        assert result is repo

    @patch("subprocess.run")
    def test_pull_calls_git_pull(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="Already up to date.\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.pull()
        args, kwargs = mock_run.call_args
        assert "pull" in args[0]

    @patch("subprocess.run")
    def test_commit_adds_all_files_then_commits(self, mock_run, temp_dir):
        # Mock to return changes to commit when status is checked
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            if 'status' in cmd and '--porcelain' in cmd:
                return Mock(stdout="M test.cpp\n", returncode=0)
            return Mock(stdout="", returncode=0)

        mock_run.side_effect = mock_run_side_effect
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        result = repo.commit("Test commit message")
        calls = mock_run.call_args_list
        # Should have called git add, status, and commit
        add_called = any("add" in str(call) for call in calls)
        commit_called = any("commit" in str(call) for call in calls)
        assert add_called
        assert commit_called
        assert result is True

    @patch("subprocess.run")
    def test_reset_hard_calls_git_reset(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.reset_hard()
        args, kwargs = mock_run.call_args
        assert "reset" in args[0]
        assert "--hard" in args[0]

    @patch("subprocess.run")
    def test_reset_hard_defaults_to_head(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.reset_hard()
        args, kwargs = mock_run.call_args
        assert "HEAD" in args[0]

    @patch("subprocess.run")
    def test_reset_hard_accepts_custom_ref(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.reset_hard("abc123")
        args, kwargs = mock_run.call_args
        assert "abc123" in args[0]

    @patch("subprocess.run")
    def test_cherry_pick_calls_git_cherry_pick(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.cherry_pick("abc123def456")
        args, kwargs = mock_run.call_args
        assert "cherry-pick" in args[0]
        assert "abc123def456" in args[0]

    @patch("subprocess.run")
    def test_get_current_branch_returns_branch_name(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="main\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        branch = repo.get_current_branch()
        assert branch == "main"

    @patch("subprocess.run")
    def test_get_commit_hash_returns_hash(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="abc123def456\n", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        hash_val = repo.get_commit_hash()
        assert hash_val == "abc123def456"

    @patch("subprocess.run")
    def test_stash_calls_git_stash(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.stash()
        args, kwargs = mock_run.call_args
        assert "stash" in args[0]

    @patch("subprocess.run")
    def test_stash_pop_calls_git_stash_pop(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.stash_pop()
        args, kwargs = mock_run.call_args
        assert "stash" in args[0]
        assert "pop" in args[0]


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
    @patch.object(Repo, "_run_git")
    def test_pulls_if_repo_path_exists(self, mock_run_git, mock_pull, mock_clone, temp_dir):
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        # Create the repo path so it exists
        repo.repo_path.mkdir(parents=True, exist_ok=True)
        repo.ensure_cloned()
        # Should have attempted checkout and pull
        mock_pull.assert_called_once()
        mock_clone.assert_not_called()
        # Should have tried to checkout main/master
        assert any('checkout' in str(call) for call in mock_run_git.call_args_list)


class TestRepoCheckoutBranch:
    @patch("subprocess.run")
    def test_checkout_existing_branch(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.checkout_branch("feature")
        args, kwargs = mock_run.call_args
        assert "checkout" in args[0]
        assert "feature" in args[0]

    @patch("subprocess.run")
    def test_checkout_defaults_to_work_branch(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.checkout_branch()
        args, kwargs = mock_run.call_args
        assert "levelup-work" in args[0]

    @patch("subprocess.run")
    def test_checkout_runs_post_checkout_command(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir,
            post_checkout="npm install"
        )
        repo.checkout_branch()
        # Should have called checkout and then shell command
        calls = mock_run.call_args_list
        assert len(calls) >= 2  # at least checkout and post_checkout

    @patch("subprocess.run")
    def test_checkout_skips_post_checkout_if_empty(self, mock_run, temp_dir):
        mock_run.return_value = Mock(stdout="", returncode=0)
        repo = Repo(
            url="https://github.com/user/project.git",
            repos_folder=temp_dir
        )
        repo.checkout_branch()
        # Should only call checkout, not post_checkout
        calls = mock_run.call_args_list
        assert len(calls) == 1


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
