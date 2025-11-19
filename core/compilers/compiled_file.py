from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any


@dataclass
class CompiledFile:
    source_file: Path
    asm_output: Optional[str] = None
    ast: Optional[Any] = None
    ir: Optional[str] = None
    obj_file: Optional[Path] = None
