import subprocess
import os
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

from .base_compiler import BaseCompiler


class MSVCCompiler(BaseCompiler):
    def __init__(self, cl_path='cl.exe'):
        super().__init__(cl_path)
        self.cl_path = cl_path
        self.default_flags = [
            '/O2',
            '/EHsc',
            '/nologo',
            '/W3',
        ]

    @staticmethod
    def get_id() -> str:
        """IMPORTANT: Stable identifier used in APIs. Do not change once set."""
        return 'msvc'

    @staticmethod
    def get_name() -> str:
        return "Microsoft Visual C++"

    def _run_cl(self, args, cwd=None, check=True):
        cmd = [self.cl_path] + args
        env = os.environ.copy()

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            env=env
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
