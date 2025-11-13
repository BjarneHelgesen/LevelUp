"""
Git handler for LevelUp - manages all git operations
"""

import subprocess
import os
from pathlib import Path

class GitHandler:
    """Handles all git operations for LevelUp"""
    
    def __init__(self, repo_path, git_path='git'):
        self.repo_path = repo_path
        self.git_path = git_path
        
    def _run_git(self, args, cwd=None, check=True):
        """Run a git command and return output"""
        cmd = [self.git_path] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip()
    
    @staticmethod
    def clone(url, target_path, git_path='git'):
        """Clone a repository and return a GitHandler instance for it"""
        cmd = [git_path, 'clone', url, str(target_path)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return GitHandler(target_path, git_path)
    
    def pull(self):
        """Pull latest changes"""
        return self._run_git(['pull'], cwd=self.repo_path)
    
    def checkout_branch(self, branch_name, create=False):
        """Checkout a branch, optionally creating it"""
        if create:
            # Check if branch exists
            branches = self._run_git(['branch', '-a'], cwd=self.repo_path)
            if branch_name not in branches:
                self._run_git(['checkout', '-b', branch_name], cwd=self.repo_path)
            else:
                self._run_git(['checkout', branch_name], cwd=self.repo_path)
        else:
            self._run_git(['checkout', branch_name], cwd=self.repo_path)
    
    def cherry_pick(self, commit_hash):
        """Cherry-pick a commit"""
        return self._run_git(['cherry-pick', commit_hash], cwd=self.repo_path)
    
    def apply_patch(self, patch_path):
        """Apply a patch file"""
        return self._run_git(['apply', str(patch_path)], cwd=self.repo_path)
    
    def commit(self, message):
        """Create a commit with all changes"""
        self._run_git(['add', '-A'], cwd=self.repo_path)
        return self._run_git(['commit', '-m', message], cwd=self.repo_path)
    
    def reset_hard(self, ref='HEAD'):
        """Hard reset to a reference"""
        return self._run_git(['reset', '--hard', ref], cwd=self.repo_path)
    
    def get_current_branch(self):
        """Get current branch name"""
        return self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=self.repo_path)
    
    def get_commit_hash(self, ref='HEAD'):
        """Get commit hash for a reference"""
        return self._run_git(['rev-parse', ref], cwd=self.repo_path)
    
    def create_patch(self, from_ref, to_ref='HEAD'):
        """Create a patch between two references"""
        return self._run_git(
            ['diff', from_ref, to_ref],
            cwd=self.repo_path
        )
    
    def rebase(self, onto_branch):
        """Rebase current branch onto another branch"""
        return self._run_git(['rebase', onto_branch], cwd=self.repo_path)
    
    def merge(self, branch):
        """Merge a branch into current branch"""
        return self._run_git(['merge', branch], cwd=self.repo_path)
    
    def stash(self):
        """Stash current changes"""
        return self._run_git(['stash'], cwd=self.repo_path)
    
    def stash_pop(self):
        """Pop stashed changes"""
        return self._run_git(['stash', 'pop'], cwd=self.repo_path)
