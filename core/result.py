from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .validation_result import ValidationResult


class ResultStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"


class Result:
    def __init__(
        self,
        status: ResultStatus,
        message: str,
        timestamp: Optional[str] = None,
        validation_results: Optional[List['ValidationResult']] = None,
        accepted_commits: Optional[List[Dict[str, Any]]] = None,
        rejected_commits: Optional[List[Dict[str, Any]]] = None
    ):
        if not isinstance(status, ResultStatus):
            raise TypeError(f"status must be ResultStatus enum, got {type(status)}")

        self.status = status
        self.message = message
        self.timestamp = timestamp or datetime.now().isoformat()
        self.validation_results = validation_results
        self.accepted_commits = accepted_commits or []
        self.rejected_commits = rejected_commits or []

    def to_dict(self) -> Dict[str, Any]:
        result_dict = {
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp
        }

        if self.validation_results is not None:
            result_dict['validation_results'] = [vr.to_dict() for vr in self.validation_results]

        if self.accepted_commits:
            result_dict['accepted_commits'] = self.accepted_commits

        if self.rejected_commits:
            result_dict['rejected_commits'] = self.rejected_commits

        return result_dict

    def __repr__(self) -> str:
        return f"Result(status={self.status.value}, message={self.message[:50]}...)"
