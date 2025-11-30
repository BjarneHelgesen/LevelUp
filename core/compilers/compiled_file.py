from pathlib import Path


class CompiledFile:
    def __init__(
        self,
        source_file: Path,
        asm_file: Path = None,
        ast=None,
        ir: str = None,
        obj_file: Path = None,
        warnings: str = None
    ):
        self.source_file = Path(source_file)
        self.ast = ast
        self.ir = ir
        self.obj_file = obj_file
        self.warnings = warnings

        # Read ASM content from file if provided
        if asm_file and Path(asm_file).exists():
            self.asm_output = Path(asm_file).read_text(errors='ignore')
        else:
            self.asm_output = None
