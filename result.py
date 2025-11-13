"""
Result class for tracking mod processing status
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any


class ResultStatus(Enum):
    """Valid status values for mod processing results"""
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class Result:
    """
    Type-safe result object for mod processing.

    Provides result tracking with validation and JSON serialization.
    Raises AttributeError on typos, preventing silent errors.
    """

    def __init__(
        self,
        status: ResultStatus,
        message: str,
        timestamp: Optional[str] = None,
        validation_results: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Create a new Result instance.

        Args:
            status: Result status from ResultStatus enum
            message: Human-readable status message
            timestamp: ISO format timestamp (auto-generated if None)
            validation_results: List of validation results (for success/failed status)

        Raises:
            TypeError: If status is not a ResultStatus enum value
        """
        if not isinstance(status, ResultStatus):
            raise TypeError(f"status must be ResultStatus enum, got {type(status)}")

        self.status = status
        self.message = message
        self.timestamp = timestamp or datetime.now().isoformat()
        self.validation_results = validation_results

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Result to dictionary for JSON serialization.

        Returns:
            Dictionary with status, message, timestamp, and optional validation_results
        """
        result_dict = {
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp
        }

        if self.validation_results is not None:
            result_dict['validation_results'] = self.validation_results

        return result_dict

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Result(status={self.status.value}, message={self.message[:50]}...)"
