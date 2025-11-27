"""
Repository class for LevelUp - manages git operations and repo configuration
"""

import subprocess
import unicodedata
from pathlib import Path
from typing import Optional

import git

from .. import logger
from ..doxygen import DoxygenRunner, DoxygenParser


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
            git_path: Path to git executable (deprecated, kept for compatibility)
            post_checkout: Commands to run after checkout
        """
        self.url = url
        self.work_branch = self.WORK_BRANCH
        repo_name = Repo.get_repo_name(url)
        self.repo_path = Path(repos_folder / Repo.repo_filename(repo_name))
        self.git_path = git_path
        self.post_checkout = post_checkout
        self._doxygen_parser: Optional[DoxygenParser] = None
        self._git_repo: Optional[git.Repo] = None

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
        config: dict,
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

    @property
    def git_repo(self) -> git.Repo:
        """Get GitPython Repo object, initializing if needed."""
        if self._git_repo is None:
            if self.repo_path.exists():
                self._git_repo = git.Repo(self.repo_path)
            else:
                raise RuntimeError(f"Git repository not found at {self.repo_path}")
        return self._git_repo

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
        git.Repo.clone_from(self.url, self.repo_path)
        self._git_repo = None  # Reset to force re-initialization
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
                self.git_repo.heads['main'].checkout()
            except (IndexError, git.exc.GitCommandError):
                # Try 'master' if 'main' doesn't exist
                logger.debug("'main' branch not found, trying 'master'")
                self.git_repo.heads['master'].checkout()
            self.pull()

    def pull(self):
        """Pull latest changes"""
        logger.debug("Pulling latest changes")
        origin = self.git_repo.remote('origin')
        result = origin.pull()
        logger.debug(f"Pull completed: {result}")
        return str(result)

    def checkout_branch(self, branch_name: str = None, create: bool = False):
        """
        Checkout a branch, optionally creating it.

        Args:
            branch_name: Branch to checkout (defaults to self.work_branch)
            create: Whether to create the branch if it doesn't exist
        """
        branch = branch_name or self.work_branch

        if create:
            # Check if branch exists locally
            if branch in self.git_repo.heads:
                self.git_repo.heads[branch].checkout()
            else:
                # Create new branch
                self.git_repo.create_head(branch)
                self.git_repo.heads[branch].checkout()
        else:
            self.git_repo.heads[branch].checkout()

        # Execute post-checkout commands if configured
        if self.post_checkout:
            self._run_shell_command(self.post_checkout)

    def prepare_work_branch(self) -> None:
        """Checkout the work branch for this repository and run post-checkout commands."""
        self.checkout_branch(create=True)

    def commit(self, message: str):
        """Create a commit with all changes. Returns True if commit was made, False if nothing to commit."""
        self.git_repo.index.add('*')

        # Check if there are changes to commit
        if not self.git_repo.is_dirty(untracked_files=True):
            logger.info("No changes to commit")
            return False

        self.git_repo.index.commit(message)
        return True

    def push(self, branch: str = None):
        """Push branch to remote origin"""
        branch = branch or self.work_branch
        logger.info(f"Pushing branch {branch} to remote origin")
        try:
            origin = self.git_repo.remote('origin')
            result = origin.push(branch, set_upstream=True)
            logger.info(f"Successfully pushed {branch} to remote origin")
            return str(result)
        except git.exc.GitCommandError as e:
            logger.error(f"Failed to push {branch} to remote origin: {e}")
            raise

    def reset_hard(self, ref: str = 'HEAD'):
        """Hard reset to a reference"""
        logger.debug(f"Hard reset to {ref}")
        self.git_repo.head.reset(ref, index=True, working_tree=True)
        return f"Reset to {ref}"

    def checkout_file(self, file_path: Path):
        """Checkout a file from HEAD (restore from last commit)"""
        logger.debug(f"Checking out file from HEAD: {file_path}")
        self.git_repo.index.checkout([str(file_path)], force=True)
        return f"Checked out {file_path}"

    def get_current_branch(self):
        """Get current branch name"""
        return self.git_repo.active_branch.name

    def get_commit_hash(self, ref: str = 'HEAD'):
        """Get commit hash for a reference"""
        return self.git_repo.commit(ref).hexsha

    def stash(self):
        """Stash current changes"""
        logger.debug("Stashing changes")
        self.git_repo.git.stash('push')
        return "Stashed"

    def stash_pop(self):
        """Pop stashed changes"""
        logger.debug("Popping stashed changes")
        self.git_repo.git.stash('pop')
        return "Popped stash"

    def create_atomic_branch(self, base_branch: str, atomic_branch_name: str):
        """Create a new branch for atomic commits from a base branch"""
        self.git_repo.heads[base_branch].checkout()
        new_branch = self.git_repo.create_head(atomic_branch_name)
        new_branch.checkout()
        return atomic_branch_name

    def squash_and_rebase(self, atomic_branch: str, target_branch: str):
        """Squash all commits on atomic_branch and rebase onto target_branch"""
        # Get the merge base (where atomic_branch diverged from target_branch)
        merge_base = self.git_repo.merge_base(atomic_branch, target_branch)[0].hexsha

        # Checkout the atomic branch
        self.git_repo.heads[atomic_branch].checkout()

        # Reset soft to merge base (keeps all changes staged)
        self.git_repo.head.reset(merge_base, index=False, working_tree=False)

        # Create single squashed commit if there are staged changes
        if self.git_repo.is_dirty(untracked_files=True):
            self.git_repo.index.commit(f'Squashed atomic changes from {atomic_branch}')

        # Rebase onto target branch
        self.git_repo.git.rebase(target_branch)

        # Checkout target branch and merge the squashed commit
        self.git_repo.heads[target_branch].checkout()
        self.git_repo.git.merge(atomic_branch, ff_only=True)

        # Delete the atomic branch
        self.git_repo.delete_head(atomic_branch)

    def delete_branch(self, branch_name: str, force: bool = False):
        """Delete a branch"""
        logger.debug(f"Deleting branch {branch_name} (force={force})")
        self.git_repo.delete_head(branch_name, force=force)
        return f"Deleted branch {branch_name}"

    def __repr__(self) -> str:
        """String representation for debugging"""
        name = self.get_repo_name(self.url)
        return f"Repo(name={name}, url={self.url}, path={self.repo_path})"

    # ==================== Doxygen Integration ====================

    def get_doxygen_dir(self) -> Path:
        """Get the path to the Doxygen output directory."""
        return self.repo_path / '.doxygen'

    def get_doxygen_xml_unexpanded_dir(self) -> Path:
        """Get the path to the Doxygen XML output directory (unexpanded macros)."""
        return self.get_doxygen_dir() / 'xml_unexpanded'

    def get_doxygen_xml_expanded_dir(self) -> Path:
        """Get the path to the Doxygen XML output directory (expanded macros)."""
        return self.get_doxygen_dir() / 'xml_expanded'

    def get_doxygen_xml_dir(self) -> Path:
        """Get the path to the Doxygen XML unexpanded directory (for backward compatibility)."""
        return self.get_doxygen_xml_unexpanded_dir()

    def has_doxygen_data(self) -> bool:
        """Check if Doxygen data has been generated for this repo."""
        xml_unexpanded = self.get_doxygen_xml_unexpanded_dir()
        return xml_unexpanded.exists() and (xml_unexpanded / 'index.xml').exists()

    def generate_doxygen(self, doxygen_path: str = 'doxygen') -> tuple[Path, Path]:
        """
        Run Doxygen on this repository to generate function dependency data.
        Generates both unexpanded and expanded versions.

        Args:
            doxygen_path: Path to the doxygen executable

        Returns:
            Tuple of (xml_unexpanded_dir, xml_expanded_dir) paths
        """
        runner = DoxygenRunner(doxygen_path=doxygen_path)
        xml_dirs = runner.run(self.repo_path, self.get_doxygen_dir())
        # Invalidate cached parser
        self._doxygen_parser = None
        return xml_dirs

    def get_doxygen_parser(self) -> Optional[DoxygenParser]:
        """
        Get a DoxygenParser for this repo's function dependency data.

        Returns:
            DoxygenParser instance if Doxygen data exists, None otherwise
        """
        if not self.has_doxygen_data():
            return None

        if self._doxygen_parser is None:
            xml_unexpanded = self.get_doxygen_xml_unexpanded_dir()
            xml_expanded = self.get_doxygen_xml_expanded_dir()
            # Pass expanded dir only if it exists
            if xml_expanded.exists() and (xml_expanded / 'index.xml').exists():
                self._doxygen_parser = DoxygenParser(xml_unexpanded, xml_expanded)
            else:
                self._doxygen_parser = DoxygenParser(xml_unexpanded)

        return self._doxygen_parser

    def get_function_info(self, function_name: str):
        """
        Get information about a function by name.

        Args:
            function_name: Name of the function to look up

        Returns:
            List of FunctionInfo objects matching the name, or empty list if
            no Doxygen data or no matches
        """
        parser = self.get_doxygen_parser()
        if parser is None:
            return []
        return parser.get_functions_by_name(function_name)

    def get_functions_in_file(self, file_path: str):
        """
        Get all functions defined in a source file.

        Args:
            file_path: Path to the source file

        Returns:
            List of FunctionInfo objects, or empty list if no Doxygen data
        """
        parser = self.get_doxygen_parser()
        if parser is None:
            return []
        return parser.get_functions_in_file(file_path)
