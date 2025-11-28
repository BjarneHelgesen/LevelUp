import json
from pathlib import Path
from typing import Dict

class ToolConfig:
    _instance = None
    _config: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = Path(__file__).parent.parent / "tools.json"
        if not config_path.exists():
            raise FileNotFoundError(f"tools.json not found at {config_path}")

        with open(config_path, 'r') as f:
            self._config = json.load(f)

    def get_tool_path(self, tool_name: str) -> str:
        if tool_name not in self._config:
            raise KeyError(f"Tool '{tool_name}' not found in tools.json")
        return self._config[tool_name]

    @property
    def git_path(self) -> str:
        return self.get_tool_path('git')

    @property
    def doxygen_path(self) -> str:
        return self.get_tool_path('doxygen')

    @property
    def cl_path(self) -> str:
        return self.get_tool_path('cl')

    @property
    def clang_path(self) -> str:
        return self.get_tool_path('clang')

    @property
    def vcvarsall_path(self) -> str:
        return self.get_tool_path('vcvarsall')

    @property
    def msvc_arch(self) -> str:
        return self.get_tool_path('msvc_arch')
