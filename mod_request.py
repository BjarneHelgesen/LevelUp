"""
Data classes for mod processing requests
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


class ModSourceType(Enum):
    """Type of mod source"""
    BUILTIN = "builtin"  # Built-in mod from mod_factory
    COMMIT = "commit"    # Git commit to cherry-pick
    PATCH = "patch"      # Patch file to apply


@dataclass
class ModRequest:
    """
    Type-safe representation of a mod processing request.

    Used internally by backend code. app.py converts JSON to this.
    """
    # Identifiers
    id: str  # UUID for tracking (used in results dict)

    # Repository info
    repo_url: str
    repo_name: str
    work_branch: str

    # Mod source
    source_type: ModSourceType
    description: str

    # Mod instance (for BUILTIN) or None
    mod_instance: Optional[object] = None

    # Commit hash (for COMMIT) or None
    commit_hash: Optional[str] = None

    # Patch path (for PATCH) or None
    patch_path: Optional[Path] = None

    # Options
    allow_reorder: bool = False
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Validate that correct fields are set for source_type"""
        if self.source_type == ModSourceType.BUILTIN:
            if self.mod_instance is None:
                raise ValueError("mod_instance required for BUILTIN source")
        elif self.source_type == ModSourceType.COMMIT:
            if self.commit_hash is None:
                raise ValueError("commit_hash required for COMMIT source")
        elif self.source_type == ModSourceType.PATCH:
            if self.patch_path is None:
                raise ValueError("patch_path required for PATCH source")
