"""
GitCommit class representing a single atomic git commit.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .repo.repo import Repo


class GitCommit:
    """
    Represents a single atomic git commit.

    Created by refactorings after successfully applying a code change.
    Used for tracking commits and enabling rollback on validation failure.
    """

    def __init__(self, repo: 'Repo', commit_message: str,
                 validator_type: str, affected_symbols: List[str],
                 regression_risk_percent: int):
        """
        Create a git commit.

        Args:
            repo: Repository where commit is made
            commit_message: Commit message
            validator_type: Validator type ID (e.g., "asm_o0", "asm_o3")
            affected_symbols: List of qualified symbol names affected by this change
            regression_risk_percent: Estimated regression risk as percentage (0-100)
                                    Low values (e.g., 10%) = safe/low risk
                                    High values (e.g., 90%) = speculative/high risk

        Raises:
            ValueError: If no changes to commit
        """
        self.repo = repo
        self.commit_message = commit_message
        self.validator_type = validator_type
        self.affected_symbols = affected_symbols if affected_symbols else []
        self.regression_risk_percent = regression_risk_percent

        # Perform the commit
        if not self.repo.commit(self.commit_message):
            raise ValueError(f"No changes to commit: {commit_message}")

        self.commit_hash = self.repo.get_commit_hash()

    def rollback(self):
        """Rollback this commit (used when validation fails)."""
        self.repo.reset_hard(f'{self.commit_hash}~1')

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'commit_message': self.commit_message,
            'commit_hash': self.commit_hash,
            'validator_type': self.validator_type,
            'affected_symbols': self.affected_symbols,
            'regression_risk_percent': self.regression_risk_percent
        }
