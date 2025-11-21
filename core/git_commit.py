from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repo.repo import Repo


class GitCommit:
    def __init__(self, repo: 'Repo', commit_message: str):
        self.repo = repo
        self.commit_message = commit_message

        if not self.repo.commit(self.commit_message):
            raise ValueError(f"No changes to commit: {commit_message}")
        self.commit_hash = self.repo.get_commit_hash()

    def rollback(self) -> None:
        self.repo.reset_hard(f'{self.commit_hash}~1')

    def to_dict(self):
        return {
            'commit_message': self.commit_message,
            'commit_hash': self.commit_hash
        }
