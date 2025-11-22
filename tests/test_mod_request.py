import pytest
from core.mod_request import ModRequest, ModSourceType


class TestModSourceType:
    def test_builtin_value(self):
        assert ModSourceType.BUILTIN.value == "builtin"

    def test_commit_value(self):
        assert ModSourceType.COMMIT.value == "commit"


class TestModRequest:
    def test_create_builtin_mod_request_with_mod_instance(self):
        mock_mod = object()  # Simulate a mod instance
        request = ModRequest(
            id="test-123",
            repo_url="https://github.com/test/repo.git",
            source_type=ModSourceType.BUILTIN,
            description="Test mod",
            mod_instance=mock_mod
        )
        assert request.id == "test-123"
        assert request.source_type == ModSourceType.BUILTIN
        assert request.mod_instance is mock_mod

    def test_create_commit_mod_request_with_commit_hash(self):
        request = ModRequest(
            id="test-456",
            repo_url="https://github.com/test/repo.git",
            source_type=ModSourceType.COMMIT,
            description="Apply commit",
            commit_hash="abc123def456"
        )
        assert request.source_type == ModSourceType.COMMIT
        assert request.commit_hash == "abc123def456"

    def test_builtin_without_mod_instance_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            ModRequest(
                id="test",
                repo_url="https://github.com/test/repo.git",
                source_type=ModSourceType.BUILTIN,
                description="Missing mod instance"
            )
        assert "mod_instance required" in str(exc_info.value)

    def test_commit_without_commit_hash_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            ModRequest(
                id="test",
                repo_url="https://github.com/test/repo.git",
                source_type=ModSourceType.COMMIT,
                description="Missing commit hash"
            )
        assert "commit_hash required" in str(exc_info.value)

    def test_repo_url_stored_correctly(self):
        url = "git@github.com:user/project.git"
        request = ModRequest(
            id="test",
            repo_url=url,
            source_type=ModSourceType.COMMIT,
            description="test",
            commit_hash="hash"
        )
        assert request.repo_url == url

    def test_description_stored_correctly(self):
        desc = "Add const correctness to all methods"
        request = ModRequest(
            id="test",
            repo_url="url",
            source_type=ModSourceType.COMMIT,
            description=desc,
            commit_hash="hash"
        )
        assert request.description == desc

    def test_builtin_with_commit_hash_ignores_hash(self):
        mock_mod = object()
        request = ModRequest(
            id="test",
            repo_url="url",
            source_type=ModSourceType.BUILTIN,
            description="desc",
            mod_instance=mock_mod,
            commit_hash="this-will-be-ignored"
        )
        assert request.commit_hash == "this-will-be-ignored"
        assert request.mod_instance is mock_mod

    def test_commit_with_mod_instance_ignores_instance(self):
        mock_mod = object()
        request = ModRequest(
            id="test",
            repo_url="url",
            source_type=ModSourceType.COMMIT,
            description="desc",
            commit_hash="abc123",
            mod_instance=mock_mod
        )
        assert request.mod_instance is mock_mod
        assert request.commit_hash == "abc123"
