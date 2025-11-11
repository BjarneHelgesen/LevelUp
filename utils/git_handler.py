"""
Git handler for LevelUp - manages all git operations
"""

import subprocess
import os
from pathlib import Path

class GitHandler:
    """Handles all git operations for LevelUp"""
    
    def __init__(self, git_path='git'):
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
    
    def clone(self, url, target_path):
        """Clone a repository"""
        self._run_git(['clone', url, str(target_path)])
        return target_path
    
    def pull(self, repo_path):
        """Pull latest changes"""
        return self._run_git(['pull'], cwd=repo_path)
    
    def checkout_branch(self, repo_path, branch_name, create=False):
        """Checkout a branch, optionally creating it"""
        if create:
            # Check if branch exists
            branches = self._run_git(['branch', '-a'], cwd=repo_path)
            if branch_name not in branches:
                self._run_git(['checkout', '-b', branch_name], cwd=repo_path)
            else:
                self._run_git(['checkout', branch_name], cwd=repo_path)
        else:
            self._run_git(['checkout', branch_name], cwd=repo_path)
    
    def cherry_pick(self, repo_path, commit_hash):
        """Cherry-pick a commit"""
        return self._run_git(['cherry-pick', commit_hash], cwd=repo_path)
    
    def apply_patch(self, repo_path, patch_path):
        """Apply a patch file"""
        return self._run_git(['apply', str(patch_path)], cwd=repo_path)
    
    def commit(self, repo_path, message):
        """Create a commit with all changes"""
        self._run_git(['add', '-A'], cwd=repo_path)
        return self._run_git(['commit', '-m', message], cwd=repo_path)
    
    def reset_hard(self, repo_path, ref='HEAD'):
        """Hard reset to a reference"""
        return self._run_git(['reset', '--hard', ref], cwd=repo_path)
    
    def get_current_branch(self, repo_path):
        """Get current branch name"""
        return self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path)
    
    def get_commit_hash(self, repo_path, ref='HEAD'):
        """Get commit hash for a reference"""
        return self._run_git(['rev-parse', ref], cwd=repo_path)
    
    def create_patch(self, repo_path, from_ref, to_ref='HEAD'):
        """Create a patch between two references"""
        return self._run_git(
            ['diff', from_ref, to_ref],
            cwd=repo_path
        )
    
    def rebase(self, repo_path, onto_branch):
        """Rebase current branch onto another branch"""
        return self._run_git(['rebase', onto_branch], cwd=repo_path)
    
    def merge(self, repo_path, branch):
        """Merge a branch into current branch"""
        return self._run_git(['merge', branch], cwd=repo_path)
    
    def stash(self, repo_path):
        """Stash current changes"""
        return self._run_git(['stash'], cwd=repo_path)
    
    def stash_pop(self, repo_path):
        """Pop stashed changes"""
        return self._run_git(['stash', 'pop'], cwd=repo_path)
