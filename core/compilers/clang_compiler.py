import subprocess
import tempfile
from pathlib import Path

from .base_compiler import BaseCompiler
from .compiled_file import CompiledFile
from .compiler_type import CompilerType
from .. import logger
from ..tool_config import ToolConfig


class ClangCompiler(BaseCompiler):
    OPTIMIZATION_FLAGS = {
        0: '-O0',
        1: '-O1',
        2: '-O2',
        3: '-O3',
    }

    def __init__(self):
        logger.info("Initializing ClangCompiler")
        self.default_flags = [
            '-std=c++17',
            '-Wall',
        ]

        config = ToolConfig()
        self.clang_path = config.clang_path

        try:
            result = subprocess.run(
                [self.clang_path, '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"clang not found at {self.clang_path}")
            version_line = result.stdout.splitlines()[0]
            logger.info(f"ClangCompiler initialized: {version_line}")
        except FileNotFoundError:
            raise RuntimeError(f"clang not found at {self.clang_path}")

    @staticmethod
    def get_id() -> CompilerType:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return CompilerType.CLANG

    @staticmethod
    def get_name() -> str:
        return "Clang/LLVM"

    def _run_clang(self, args, cwd=None, check=True):
        cmd = [self.clang_path] + args
        logger.debug(f"Running clang: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )

        if result.returncode != 0:
            logger.error(f"clang failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            if result.stdout:
                logger.debug(f"stdout: {result.stdout}")
        else:
            logger.debug(f"clang completed successfully")

        return result

    def compile_file(self, source_file: Path, additional_flags: str = None,
                     optimization_level: int = 2) -> CompiledFile:
        source_path = Path(source_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            base_name = source_path.stem
            asm_file = temp_path / f"{base_name}.s"

            # Compile to ASM (using Intel syntax to match MSVC)
            args = self.default_flags.copy()
            args.append(self.OPTIMIZATION_FLAGS.get(optimization_level, '-O2'))
            args.extend(['-S', '-masm=intel', '-o', str(asm_file)])

            if additional_flags:
                args.extend(additional_flags.split())

            args.append(str(source_path))

            result = self._run_clang(args, cwd=source_path.parent, check=False)

            if result.returncode != 0:
                raise RuntimeError(f"Compilation failed: {result.stderr}")

            return CompiledFile(
                source_file=source_path,
                asm_file=asm_file if asm_file.exists() else None
            )
