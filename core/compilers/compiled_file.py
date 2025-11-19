from pathlib import Path
from typing import Optional, Any


class CompiledFile:
    def __init__(
        self,
        source_file: Path,
        asm_file: Optional[Path] = None,
        ast: Optional[Any] = None,
        ir: Optional[str] = None,
        obj_file: Optional[Path] = None
    ):
        self.source_file = Path(source_file)
        self.ast = ast
        self.ir = ir
        self.obj_file = obj_file

        # Read ASM content from file if provided
        if asm_file and Path(asm_file).exists():
            self.asm_output = Path(asm_file).read_text(errors='ignore')
        else:
            self.asm_output = None
