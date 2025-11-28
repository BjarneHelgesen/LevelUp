import subprocess
import tempfile
from pathlib import Path

from .base_compiler import BaseCompiler
from .compiled_file import CompiledFile
from .compiler_type import CompilerType
from .. import logger
from ..tool_config import ToolConfig


class MSVCCompiler(BaseCompiler):
    OPTIMIZATION_FLAGS = {
        0: '/Od',
        1: '/O1',
        2: '/O2',
        3: '/Ox',
    }

    _cache = {}

    def __init__(self):
        logger.info("Initializing MSVCCompiler")
        self.default_flags = [
            '/EHsc',
            '/nologo',
            '/W3',
        ]

        config = ToolConfig()
        self.cl_path = config.cl_path
        self.vcvarsall = config.vcvarsall_path
        self.arch = config.msvc_arch

        logger.assert_true(Path(self.cl_path).exists(), f"cl.exe not found at {self.cl_path}")
        logger.assert_true(Path(self.vcvarsall).exists(), f"vcvarsall.bat not found at {self.vcvarsall}")

        cache_key = f"msvc_{self.arch}"
        if cache_key in MSVCCompiler._cache:
            self.env = MSVCCompiler._cache[cache_key]
            logger.info(f"MSVCCompiler initialized from cache: cl.exe at {self.cl_path}")
            return

        logger.debug("Loading MSVC environment variables")
        self.env = self._load_msvc_environment()
        MSVCCompiler._cache[cache_key] = self.env
        logger.info(f"MSVCCompiler initialized with cl.exe at: {self.cl_path}")

    @staticmethod
    def get_id() -> CompilerType:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return CompilerType.MSVC

    @staticmethod
    def get_name() -> str:
        return "Microsoft Visual C++"

    def _load_msvc_environment(self):
        cmd = f'"{self.vcvarsall}" {self.arch} && set'

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True
        )

        if result.returncode != 0:
            raise RuntimeError("Failed to run vcvarsall.bat")

        env = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                env[key.upper()] = val
        return env

    def _run_cl(self, args, cwd=None, check=True):
        cmd = [self.cl_path] + args
        logger.debug(f"Running cl.exe: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=self.env
        )

        if result.returncode != 0:
            logger.error(f"cl.exe failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            if result.stdout:
                logger.debug(f"stdout: {result.stdout}")
        else:
            logger.debug(f"cl.exe completed successfully")

        return result

    def compile_file(self, source_file: Path, additional_flags: str = None,
                     optimization_level: int = 2) -> CompiledFile:
        source_path = Path(source_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            base_name = source_path.stem
            asm_file = temp_path / f"{base_name}.asm"
            obj_file = temp_path / f"{base_name}.obj"

            # Compile to ASM
            args = self.default_flags.copy()
            args.append(self.OPTIMIZATION_FLAGS.get(optimization_level, '/O2'))

            # Disable iterator debugging for O3 to allow range-based for loop optimizations
            if optimization_level >= 3:
                args.append('/D_ITERATOR_DEBUG_LEVEL=0')

            args.extend([
                '/FA',
                '/Fa' + str(asm_file),
                '/c',
                '/Fo' + str(obj_file),
            ])

            if additional_flags:
                args.extend(additional_flags.split())

            args.append(str(source_file))

            result = self._run_cl(args, cwd=source_path.parent, check=False)

            if result.returncode != 0:
                raise RuntimeError(f"Compilation failed: {result.stderr}")

            return CompiledFile(
                source_file=source_path,
                asm_file=asm_file if asm_file.exists() else None
            )
