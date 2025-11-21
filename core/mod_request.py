from enum import Enum


class ModSourceType(Enum):
    BUILTIN = "builtin"
    COMMIT = "commit"


class ModRequest:
    def __init__(
        self,
        id: str,
        repo_url: str,
        repo_name: str,
        source_type: ModSourceType,
        description: str,
        mod_instance: object = None,
        commit_hash: str = None,
        timestamp: str = None
    ):
        self.id = id
        self.repo_url = repo_url
        self.repo_name = repo_name
        self.source_type = source_type
        self.description = description
        self.mod_instance = mod_instance
        self.commit_hash = commit_hash
        self.timestamp = timestamp

        if self.source_type == ModSourceType.BUILTIN:
            if self.mod_instance is None:
                raise ValueError("mod_instance required for BUILTIN source")
        elif self.source_type == ModSourceType.COMMIT:
            if self.commit_hash is None:
                raise ValueError("commit_hash required for COMMIT source")
