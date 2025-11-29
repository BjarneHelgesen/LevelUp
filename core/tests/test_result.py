import pytest
from core.result import Result, ResultStatus
from core.validators.validation_result import ValidationResult


class TestResultStatus:
    def test_queued_status_value(self):
        assert ResultStatus.QUEUED.value == "queued"

    def test_processing_status_value(self):
        assert ResultStatus.PROCESSING.value == "processing"

    def test_success_status_value(self):
        assert ResultStatus.SUCCESS.value == "success"

    def test_failed_status_value(self):
        assert ResultStatus.FAILED.value == "failed"

    def test_error_status_value(self):
        assert ResultStatus.ERROR.value == "error"


class TestResult:
    def test_create_result_with_valid_status(self):
        result = Result(status=ResultStatus.SUCCESS, message="Test message")
        assert result.status == ResultStatus.SUCCESS
        assert result.message == "Test message"

    def test_create_result_with_invalid_status_raises_type_error(self):
        with pytest.raises(TypeError) as exc_info:
            Result(status="success", message="Test")
        assert "must be ResultStatus enum" in str(exc_info.value)

    def test_result_with_validation_results(self):
        validation_results = [
            ValidationResult(file="test.cpp", valid=True),
            ValidationResult(file="test2.cpp", valid=False)
        ]
        result = Result(
            status=ResultStatus.FAILED,
            message="Validation failed",
            validation_results=validation_results
        )
        assert result.validation_results == validation_results
        assert len(result.validation_results) == 2

    def test_result_without_validation_results_is_none(self):
        result = Result(status=ResultStatus.SUCCESS, message="Test")
        assert result.validation_results is None

    def test_to_dict_includes_status_value(self):
        result = Result(status=ResultStatus.SUCCESS, message="Done")
        d = result.to_dict()
        assert d["status"] == "success"

    def test_to_dict_includes_message(self):
        result = Result(status=ResultStatus.ERROR, message="Something failed")
        d = result.to_dict()
        assert d["message"] == "Something failed"

    def test_to_dict_includes_validation_results_when_present(self):
        validation_results = [ValidationResult(file="a.cpp", valid=True)]
        result = Result(
            status=ResultStatus.SUCCESS,
            message="OK",
            validation_results=validation_results
        )
        d = result.to_dict()
        assert "validation_results" in d
        assert d["validation_results"] == [{"file": "a.cpp", "valid": True}]

    def test_to_dict_excludes_validation_results_when_none(self):
        result = Result(status=ResultStatus.QUEUED, message="Waiting")
        d = result.to_dict()
        assert "validation_results" not in d

    def test_repr_includes_status_value(self):
        result = Result(status=ResultStatus.FAILED, message="Test failed")
        repr_str = repr(result)
        assert "failed" in repr_str

    def test_repr_truncates_long_message(self):
        long_message = "A" * 100
        result = Result(status=ResultStatus.SUCCESS, message=long_message)
        repr_str = repr(result)
        assert "..." in repr_str
        assert len(repr_str) < len(long_message)

    def test_all_result_statuses_can_be_created(self):
        for status in ResultStatus:
            result = Result(status=status, message=f"Testing {status.value}")
            assert result.status == status
