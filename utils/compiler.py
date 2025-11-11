"""
MSVC Compiler wrapper for LevelUp
"""

import subprocess
import os
import tempfile
from pathlib import Path

class MSVCCompiler:
    """Wrapper for Microsoft Visual C++ compiler"""
    
    def __init__(self, cl_path='cl.exe'):
        self.cl_path = cl_path
        self.default_flags = [
            '/O2',  # Maximum optimization
            '/EHsc',  # Enable C++ exceptions
            '/nologo',  # Suppress banner
            '/W3',  # Warning level 3
        ]
    
    def _run_cl(self, args, cwd=None, check=True):
        """Run cl.exe with arguments"""
        cmd = [self.cl_path] + args
        
        # Set up environment for MSVC if needed
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
        """Compile a C++ source file"""
        args = self.default_flags.copy()
        
        if additional_flags:
            args.extend(additional_flags)
        
        args.append(str(source_file))
        
        if output_file:
            args.extend(['/Fo' + str(output_file)])
        
        return self._run_cl(args, cwd=source_file.parent)
    
    def compile_to_asm(self, source_file, asm_output_file, additional_flags=None):
        """Compile C++ to assembly"""
        args = self.default_flags.copy()
        
        # Add ASM generation flags
        args.extend([
            '/FA',  # Generate assembly listing
            '/Fa' + str(asm_output_file),  # ASM output file
            '/c',  # Compile only, no linking
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
        """Compile C++ to object file"""
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
        """Get preprocessed source"""
        args = [
            '/E',  # Preprocess only
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
        """Check syntax without generating output"""
        args = [
            '/Zs',  # Syntax check only
            '/nologo',
            str(source_file)
        ]
        
        result = self._run_cl(args, cwd=source_file.parent, check=False)
        return result.returncode == 0, result.stderr
    
    def get_warnings(self, source_file):
        """Get all warnings for a source file"""
        args = self.default_flags.copy()
        args.extend([
            '/Wall',  # All warnings
            '/c',  # Compile only
            str(source_file)
        ])
        
        result = self._run_cl(args, cwd=source_file.parent, check=False)
        
        # Parse warnings from stderr
        warnings = []
        for line in result.stderr.split('\n'):
            if 'warning' in line.lower():
                warnings.append(line.strip())
        
        return warnings
    
    def compare_asm_output(self, source1, source2, normalize=True):
        """Compare ASM output of two source files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            asm1 = Path(tmpdir) / 'asm1.asm'
            asm2 = Path(tmpdir) / 'asm2.asm'
            
            # Generate ASM for both files
            self.compile_to_asm(source1, asm1)
            self.compile_to_asm(source2, asm2)
            
            # Read and compare
            content1 = asm1.read_text()
            content2 = asm2.read_text()
            
            if normalize:
                # Normalize ASM for comparison (remove comments, timestamps, etc.)
                content1 = self._normalize_asm(content1)
                content2 = self._normalize_asm(content2)
            
            return content1 == content2, content1, content2
    
    def _normalize_asm(self, asm_content):
        """Normalize ASM content for comparison"""
        lines = []
        for line in asm_content.split('\n'):
            # Skip comments and metadata
            if line.startswith(';'):
                continue
            if line.startswith('TITLE'):
                continue
            if line.startswith('.file'):
                continue
            if line.startswith('include'):
                continue
            
            # Remove trailing whitespace
            line = line.rstrip()
            
            if line:
                lines.append(line)
        
        return '\n'.join(lines)
