import subprocess
import os
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

from .base_compiler import BaseCompiler


class MSVCCompiler(BaseCompiler):
    def __init__(self, arch="x64"):
        self.arch = arch
        self.default_flags = [
            '/O2',
            '/EHsc',
            '/nologo',
            '/W3',
        ]

        # Locate vswhere
        vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
        if not Path(vswhere).exists():
            raise FileNotFoundError("vswhere.exe not found at expected location.")

        # Query VS installation path
        result = subprocess.run(
            [vswhere, "-latest", "-products", "*", "-property", "installationPath"],
            capture_output=True,
            text=True
        )
        install_path = result.stdout.strip()
        if not install_path:
            raise RuntimeError("Unable to locate Visual Studio installation via vswhere.")

        # Locate vcvarsall.bat
        self.vcvarsall = Path(install_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        if not self.vcvarsall.exists():
            raise FileNotFoundError(f"vcvarsall.bat not found at: {self.vcvarsall}")

        # Extract environment variables set by vcvarsall
        self.env = self._load_msvc_environment()

        # Locate cl.exe
        cl_path = self._find_cl()
        if not cl_path:
            raise RuntimeError("cl.exe was not found in configured environment.")
        self.cl_path = cl_path

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

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=self.env
        )
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
        
        result = self._run_cl(args, cwd=source_file.parent)
        
        if result.returncode == 0 and Path(asm_output_file).exists():
            return Path(asm_output_file)
        else:
            raise RuntimeError(f"Failed to generate ASM: {result.stderr}")

    def compile_to_obj(self, source_file, obj_output_file, additional_flags=None):
        args = self.default_flags.copy()
        
        args.extend([
            '/c',  # Compile only
            '/Fo' + str(obj_output_file),
        ])
        
        if additional_flags:
            args.extend(additional_flags)
        
        args.append(str(source_file))
        
        return self._run_cl(args, cwd=source_file.parent)

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

    def compare_asm_output(self, source1, source2, normalize=True):
        with tempfile.TemporaryDirectory() as tmpdir:
            asm1 = Path(tmpdir) / 'asm1.asm'
            asm2 = Path(tmpdir) / 'asm2.asm'

            self.compile_to_asm(source1, asm1)
            self.compile_to_asm(source2, asm2)

            content1 = asm1.read_text()
            content2 = asm2.read_text()

            if normalize:
                content1 = self._normalize_asm(content1)
                content2 = self._normalize_asm(content2)

            return content1 == content2, content1, content2

    def _normalize_asm(self, asm_content):
        lines = []
        for line in asm_content.split('\n'):
            if line.startswith(';'):
                continue
            if line.startswith('TITLE'):
                continue
            if line.startswith('.file'):
                continue
            if line.startswith('include'):
                continue

            line = line.rstrip()

            if line:
                lines.append(line)

        return '\n'.join(lines)
