import subprocess
import tempfile
from pathlib import Path

from .base_compiler import BaseCompiler
from .compiled_file import CompiledFile
from .. import logger


class MSVCCompiler(BaseCompiler):
    OPTIMIZATION_FLAGS = {
        0: '/Od',
        1: '/O1',
        2: '/O2',
        3: '/Ox',
    }

    def __init__(self, arch="x64"):
        logger.info(f"Initializing MSVCCompiler with arch={arch}")
        self.arch = arch
        self.default_flags = [
            '/EHsc',
            '/nologo',
            '/W3',
        ]

        # Locate vswhere
        vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
        logger.assert_true(Path(vswhere).exists(), f"vswhere.exe not found at {vswhere}")

        # Query VS installation path
        logger.debug(f"Running vswhere to find VS installation")
        result = subprocess.run(
            [vswhere, "-latest", "-products", "*", "-property", "installationPath"],
            capture_output=True,
            text=True
        )
        install_path = result.stdout.strip()
        logger.assert_true(install_path, "vswhere returned empty installation path")

        logger.debug(f"Found VS installation at: {install_path}")

        # Locate vcvarsall.bat
        self.vcvarsall = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        logger.assert_true(self.vcvarsall.exists(), f"vcvarsall.bat not found at: {self.vcvarsall}")

        # Extract environment variables set by vcvarsall
        logger.debug("Loading MSVC environment variables")
        self.env = self._load_msvc_environment()

        # Locate cl.exe
        cl_path = self._find_cl()
        logger.assert_true(cl_path, "cl.exe not found in configured environment PATH")
        self.cl_path = cl_path
        logger.info(f"MSVCCompiler initialized with cl.exe at: {self.cl_path}")

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'msvc'

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

    def _find_cl(self):
        path_dirs = self.env.get("PATH", "").split(";")
        for p in path_dirs:
            cl = Path(p) / "cl.exe"
            if cl.exists():
                return str(cl)
        return None

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
