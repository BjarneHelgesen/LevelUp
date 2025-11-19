import subprocess
import os
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

from .base_compiler import BaseCompiler
from ..compiled_file import CompiledFile
from .. import logger


class MSVCCompiler(BaseCompiler):
    def __init__(self, arch="x64"):
        logger.info(f"Initializing MSVCCompiler with arch={arch}")
        self.arch = arch
        self.default_flags = [
            '/O2',
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

        super().__init__(self.cl_path)

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

    def compile(self, source_file, output_file=None, additional_flags=None):
        args = self.default_flags.copy()
        
        if additional_flags:
            args.extend(additional_flags)
        
        args.append(str(source_file))
        
        if output_file:
            args.extend(['/Fo' + str(output_file)])
        
        return self._run_cl(args, cwd=source_file.parent)

    def compile_to_asm(self, source_file, asm_output_file, additional_flags=None):
        args = self.default_flags.copy()

        args.extend([
            '/FA',
            '/Fa' + str(asm_output_file),
            '/c',
        ])

        if additional_flags:
            args.extend(additional_flags)

        args.append(str(source_file))

        result = self._run_cl(args, cwd=source_file.parent, check=False)

        if result.returncode == 0 and Path(asm_output_file).exists():
            return Path(asm_output_file)
        else:
            raise RuntimeError(f"Failed to generate ASM: {result.stderr}")

    def compile_file(self, source_file, output_dir, additional_flags=None):
        source_path = Path(source_file)
        output_path = Path(output_dir)

        base_name = source_path.stem
        asm_file = output_path / f"{base_name}.asm"
        obj_file = output_path / f"{base_name}.obj"

        # Compile to ASM
        args = self.default_flags.copy()
        args.extend([
            '/FA',
            '/Fa' + str(asm_file),
            '/c',
            '/Fo' + str(obj_file),
        ])

        if additional_flags:
            args.extend(additional_flags)

        args.append(str(source_file))

        result = self._run_cl(args, cwd=source_path.parent)

        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")

        asm_output = None
        if asm_file.exists():
            asm_output = asm_file.read_text()

        obj_path = None
        if obj_file.exists():
            obj_path = obj_file

        return CompiledFile(
            source_file=source_path,
            asm_output=asm_output,
            ast=None,
            ir=None,
            obj_file=obj_path
        )

    def get_preprocessed(self, source_file, output_file=None):
        args = [
            '/E',
            '/nologo',
            str(source_file)
        ]
        
        result = self._run_cl(args, cwd=source_file.parent, check=False)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            return Path(output_file)
        
        return result.stdout

    def check_syntax(self, source_file):
        args = [
            '/Zs',
            '/nologo',
            str(source_file)
        ]
        
        result = self._run_cl(args, cwd=source_file.parent, check=False)
        return result.returncode == 0, result.stderr

    def get_warnings(self, source_file):
        args = self.default_flags.copy()
        args.extend([
            '/Wall',
            '/c',
            str(source_file)
        ])

        result = self._run_cl(args, cwd=source_file.parent, check=False)

        warnings = []
        for line in result.stderr.split('\n'):
            if 'warning' in line.lower():
                warnings.append(line.strip())

        return warnings
