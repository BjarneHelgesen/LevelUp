class GitCommit:
    def __init__(self, file_path: str, commit_message: str):
        self.file_path = file_path
        self.commit_message = commit_message
        self.commit_hash = None
        self.accepted = False

    def to_dict(self):
        return {
            'file_path': self.file_path,
            'commit_message': self.commit_message,
            'commit_hash': self.commit_hash,
            'accepted': self.accepted
        }
