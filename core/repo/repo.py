"""
Repository class for LevelUp - manages git operations and repo configuration
"""

import subprocess
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any

from . import logger


class Repo:
    """
    Represents a repository with git operations and configuration.

    Merges GitHandler functionality with repository metadata management.
    """

    WORK_BRANCH = "levelup-work"

    def __init__(
        self,
        url: str,
        repos_folder: Path,
        git_path: str = 'git',
        post_checkout: str = ''
    ):
        """
        Initialize a Repo instance.

        Args:
            url: Git repository URL
            repo_path: Local filesystem path for the repository
            git_path: Path to git executable
            post_checkout: Commands to run after checkout
        """
        self.url = url
        self.work_branch = self.WORK_BRANCH
        repo_name = Repo.get_repo_name(url)
        self.repo_path = Path(repos_folder / Repo.repo_filename(repo_name))
        self.git_path = git_path
        self.post_checkout = post_checkout

    @staticmethod
    def get_repo_name(repo_url: str) -> str:
        """
        Extract repository name from URL.
        Returns: Repository name (last part of URL without .git suffix)
        """
        # Remove .git suffix if present
        url = repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        # Get the last part of the URL path
        return url.split('/')[-1]
        
    @staticmethod
    def repo_filename(repo_name):
        '''Accept subset of ASCII characters in the filename '''
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#()-.=[]{}~" 

        filename = []
        for char in unicodedata.normalize('NFD', repo_name):
            if char in allowed_chars:
                filename.append(char)
        return ''.join(filename)


    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        repos_base_path: Path,
        git_path: str = 'git'
    ) -> 'Repo':
        """
        Create a Repo instance from a configuration dictionary.

        Args:
            config: Repository configuration dict (from repos.json)
            repos_base_path: Base path where repos are stored
            git_path: Path to git executable

        Returns:
            Repo instance
        """
        repo_name = config['name']

        return cls(
            url=config['url'],
            repos_folder=repos_base_path,
            git_path=git_path,
            post_checkout=config.get('post_checkout', '')
        )

    def _run_git(self, args, cwd=None, check=True):
        """Run a git command and return output"""
        cmd = [self.git_path] + args
        logger.debug(f"Running git: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout.strip():
                logger.debug(f"git output: {result.stdout.strip()[:200]}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"git command failed: {' '.join(cmd)}")
            logger.error(f"stderr: {e.stderr}")
            raise

    def _run_shell_command(self, command: str):
        """Run a shell command in the repository directory"""
        result = subprocess.run(
            command,
            cwd=self.repo_path,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def clone(self) -> 'Repo':
        """Clone the repository to repo_path"""
        logger.info(f"Cloning repository {self.url} to {self.repo_path}")
        cmd = [self.git_path, 'clone', self.url, str(self.repo_path)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Repository cloned successfully")
        return self

    def ensure_cloned(self) -> None:
        """Ensure repository is cloned locally. Clone if not present, pull if exists."""
        if not self.repo_path.exists():
            logger.debug(f"Repo path {self.repo_path} does not exist, cloning")
            self.clone()
        else:
            logger.debug(f"Repo path {self.repo_path} exists, pulling latest")
            # Checkout main branch and pull latest
            try:
                self._run_git(['checkout', 'main'])
            except subprocess.CalledProcessError:
                # Try 'master' if 'main' doesn't exist
                logger.debug("'main' branch not found, trying 'master'")
                self._run_git(['checkout', 'master'])
            self.pull()

    def pull(self):
        """Pull latest changes"""
        return self._run_git(['pull'])

    def checkout_branch(self, branch_name: Optional[str] = None, create: bool = False):
        """
        Checkout a branch, optionally creating it.

        Args:
            branch_name: Branch to checkout (defaults to self.work_branch)
            create: Whether to create the branch if it doesn't exist
        """
        branch = branch_name or self.work_branch

        if create:
            # Check if branch exists
            branches = self._run_git(['branch', '-a'])
            if branch not in branches:
                self._run_git(['checkout', '-b', branch])
            else:
                self._run_git(['checkout', branch])
        else:
            self._run_git(['checkout', branch])

        # Execute post-checkout commands if configured
        if self.post_checkout:
            self._run_shell_command(self.post_checkout)

    def prepare_work_branch(self) -> None:
        """Checkout the work branch for this repository and run post-checkout commands."""
        self.checkout_branch(create=True)

    def cherry_pick(self, commit_hash: str):
        """Cherry-pick a commit"""
        return self._run_git(['cherry-pick', commit_hash])

    def commit(self, message: str):
        """Create a commit with all changes"""
        self._run_git(['add', '-A'])
        return self._run_git(['commit', '-m', message])

    def push(self, branch: Optional[str] = None):
        """Push branch to remote origin"""
        branch = branch or self.work_branch
        logger.info(f"Pushing branch {branch} to origin")
        return self._run_git(['push', '-u', 'origin', branch])

    def reset_hard(self, ref: str = 'HEAD'):
        """Hard reset to a reference"""
        return self._run_git(['reset', '--hard', ref])

    def get_current_branch(self):
        """Get current branch name"""
        return self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'])

    def get_commit_hash(self, ref: str = 'HEAD'):
        """Get commit hash for a reference"""
        return self._run_git(['rev-parse', ref])

    def create_patch(self, from_ref: str, to_ref: str = 'HEAD'):
        """Create a patch between two references"""
        return self._run_git(['diff', from_ref, to_ref])

    def rebase(self, onto_branch: str):
        """Rebase current branch onto another branch"""
        return self._run_git(['rebase', onto_branch])

    def merge(self, branch: str):
        """Merge a branch into current branch"""
        return self._run_git(['merge', branch])

    def stash(self):
        """Stash current changes"""
        return self._run_git(['stash'])

    def stash_pop(self):
        """Pop stashed changes"""
        return self._run_git(['stash', 'pop'])

    def __repr__(self) -> str:
        """String representation for debugging"""
        name = self.get_repo_name(self.url)
        return f"Repo(name={name}, url={self.url}, path={self.repo_path})"
