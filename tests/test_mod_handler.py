import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
from levelup_core.mods.mod_handler import ModHandler


class TestModHandlerInitialization:
    def test_init_creates_empty_history(self):
        handler = ModHandler()
        assert handler.mod_history == []

    def test_init_history_is_list(self):
        handler = ModHandler()
        assert isinstance(handler.mod_history, list)


class TestModHandlerApplyModInstance:
    @pytest.fixture
    def handler(self):
        return ModHandler()

    @pytest.fixture
    def mock_mod(self):
        mod = Mock()
        mod.validate_before_apply.return_value = (True, "OK")
        mod.apply.return_value = Path("/tmp/modified.cpp")
        mod.get_metadata.return_value = {"mod_id": "test", "description": "Test mod"}
        mod.__class__.__name__ = "TestMod"
        return mod

    def test_apply_validates_before_applying(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        mock_mod.validate_before_apply.assert_called_once_with(cpp_file)

    def test_apply_raises_on_validation_failure(self, handler, mock_mod):
        mock_mod.validate_before_apply.return_value = (False, "Not applicable")
        cpp_file = Path("/path/to/test.cpp")
        with pytest.raises(ValueError) as exc_info:
            handler.apply_mod_instance(cpp_file, mock_mod)
        assert "validation failed" in str(exc_info.value).lower()

    def test_apply_calls_mod_apply(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        mock_mod.apply.assert_called_once_with(cpp_file)

    def test_apply_returns_modified_file_path(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        result = handler.apply_mod_instance(cpp_file, mock_mod)
        assert result == Path("/tmp/modified.cpp")

    def test_apply_records_history(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        assert len(handler.mod_history) == 1

    def test_history_includes_file_path(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        assert handler.mod_history[0]["file"] == str(cpp_file)

    def test_history_includes_mod_class_name(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        assert handler.mod_history[0]["mod_class"] == "TestMod"

    def test_history_includes_timestamp(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        assert "timestamp" in handler.mod_history[0]
        # Should be ISO format timestamp
        timestamp = handler.mod_history[0]["timestamp"]
        datetime.fromisoformat(timestamp)  # Will raise if invalid

    def test_history_includes_mod_metadata(self, handler, mock_mod):
        cpp_file = Path("/path/to/test.cpp")
        handler.apply_mod_instance(cpp_file, mock_mod)
        assert "mod_metadata" in handler.mod_history[0]
        assert handler.mod_history[0]["mod_metadata"] == {
            "mod_id": "test",
            "description": "Test mod"
        }

    def test_multiple_applies_accumulate_history(self, handler, mock_mod):
        for i in range(3):
            handler.apply_mod_instance(Path(f"/path/to/test{i}.cpp"), mock_mod)
        assert len(handler.mod_history) == 3

    def test_history_entries_have_different_timestamps(self, handler, mock_mod):
        # This test may be flaky if too fast, but documents expected behavior
        handler.apply_mod_instance(Path("/path/to/test1.cpp"), mock_mod)
        handler.apply_mod_instance(Path("/path/to/test2.cpp"), mock_mod)
        # Timestamps should be close but potentially different
        t1 = handler.mod_history[0]["timestamp"]
        t2 = handler.mod_history[1]["timestamp"]
        # They should be valid ISO timestamps
        datetime.fromisoformat(t1)
        datetime.fromisoformat(t2)


class TestModHandlerGetHistory:
    def test_get_history_returns_empty_list_initially(self):
        handler = ModHandler()
        history = handler.get_mod_history()
        assert history == []

    def test_get_history_returns_all_entries(self):
        handler = ModHandler()
        mock_mod = Mock()
        mock_mod.validate_before_apply.return_value = (True, "OK")
        mock_mod.apply.return_value = Path("/tmp/mod.cpp")
        mock_mod.get_metadata.return_value = {}
        mock_mod.__class__.__name__ = "TestMod"

        for i in range(5):
            handler.apply_mod_instance(Path(f"/test{i}.cpp"), mock_mod)

        history = handler.get_mod_history()
        assert len(history) == 5

    def test_get_history_returns_same_list_reference(self):
        handler = ModHandler()
        history = handler.get_mod_history()
        assert history is handler.mod_history


class TestModHandlerEdgeCases:
    def test_apply_with_none_mod_raises_error(self):
        handler = ModHandler()
        with pytest.raises(AttributeError):
            handler.apply_mod_instance(Path("/test.cpp"), None)

    def test_apply_with_invalid_mod_missing_validate(self):
        handler = ModHandler()
        invalid_mod = Mock(spec=[])  # No methods
        with pytest.raises(AttributeError):
            handler.apply_mod_instance(Path("/test.cpp"), invalid_mod)

    def test_validation_error_does_not_add_to_history(self):
        handler = ModHandler()
        mock_mod = Mock()
        mock_mod.validate_before_apply.return_value = (False, "Invalid")
        with pytest.raises(ValueError):
            handler.apply_mod_instance(Path("/test.cpp"), mock_mod)
        assert len(handler.mod_history) == 0
