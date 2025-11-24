class ModRequest:
    def __init__(
        self,
        id: str,
        repo_url: str,
        description: str,
        mod_instance: object
    ):
        if mod_instance is None:
            raise ValueError("mod_instance is required")

        self.id = id
        self.repo_url = repo_url
        self.description = description
        self.mod_instance = mod_instance
