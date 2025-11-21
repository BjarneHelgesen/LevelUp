from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repo.repo import Repo


class GitCommit:
    def __init__(self, repo: 'Repo', commit_message: str):
        self.repo = repo
        self.commit_message = commit_message
        self.commit_hash = None
        self.accepted = False

        if self.repo.commit(self.commit_message):
            self.commit_hash = self.repo.get_commit_hash()
            self.accepted = True

    def rollback(self) -> None:
        """Rollback this commit if it was accepted."""
        if self.accepted and self.commit_hash:
            # Reset to parent of this commit
            self.repo.reset_hard(f'{self.commit_hash}~1')
            self.accepted = False

    def to_dict(self):
        return {
            'commit_message': self.commit_message,
            'commit_hash': self.commit_hash,
            'accepted': self.accepted
        }
