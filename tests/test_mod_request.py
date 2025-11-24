import pytest
from core.mod_request import ModRequest


class TestModRequest:
    def test_create_mod_request_with_mod_instance(self):
        mock_mod = object()  # Simulate a mod instance
        request = ModRequest(
            id="test-123",
            repo_url="https://github.com/test/repo.git",
            description="Test mod",
            mod_instance=mock_mod
        )
        assert request.id == "test-123"
        assert request.mod_instance is mock_mod

    def test_without_mod_instance_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            ModRequest(
                id="test",
                repo_url="https://github.com/test/repo.git",
                description="Missing mod instance",
                mod_instance=None
            )
        assert "mod_instance is required" in str(exc_info.value)

    def test_repo_url_stored_correctly(self):
        url = "git@github.com:user/project.git"
        request = ModRequest(
            id="test",
            repo_url=url,
            description="test",
            mod_instance=object()
        )
        assert request.repo_url == url

    def test_description_stored_correctly(self):
        desc = "Add const correctness to all methods"
        request = ModRequest(
            id="test",
            repo_url="url",
            description=desc,
            mod_instance=object()
        )
        assert request.description == desc
