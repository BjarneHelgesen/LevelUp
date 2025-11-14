from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


class ModSourceType(Enum):
    BUILTIN = "builtin"
    COMMIT = "commit"
    PATCH = "patch"


@dataclass
class ModRequest:
    id: str
    repo_url: str
    repo_name: str
    work_branch: str
    source_type: ModSourceType
    description: str
    mod_instance: Optional[object] = None
    commit_hash: Optional[str] = None
    patch_path: Optional[Path] = None
    allow_reorder: bool = False
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.source_type == ModSourceType.BUILTIN:
            if self.mod_instance is None:
                raise ValueError("mod_instance required for BUILTIN source")
        elif self.source_type == ModSourceType.COMMIT:
            if self.commit_hash is None:
                raise ValueError("commit_hash required for COMMIT source")
        elif self.source_type == ModSourceType.PATCH:
            if self.patch_path is None:
                raise ValueError("patch_path required for PATCH source")
