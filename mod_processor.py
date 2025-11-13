"""
Mod Processor for LevelUp - Handles async mod processing
"""

from pathlib import Path
from werkzeug.utils import secure_filename

from utils.compiler import MSVCCompiler
from validators.asm_validator import ASMValidator
from mods.mod_handler import ModHandler
from result import Result, ResultStatus
from repo import Repo
from mod_request import ModRequest, ModSourceType


class ModProcessor:
    """
    Processes Mods asynchronously.

    Uses only enums and objects - no string IDs from web interface.
    """

    def __init__(self, msvc_path: str, repos_path: Path, temp_path: Path, git_path: str = 'git'):
        """
        Initialize ModProcessor with configuration paths.

        Args:
            msvc_path: Path to MSVC compiler (cl.exe)
            repos_path: Base path for repository clones
            temp_path: Path for temporary compilation files
            git_path: Path to git executable
        """
        self.compiler = MSVCCompiler(msvc_path)
        self.asm_validator = ASMValidator(self.compiler)
        self.mod_handler = ModHandler()
        self.repos_path = Path(repos_path)
        self.temp_path = Path(temp_path)
        self.git_path = git_path

    def process_mod(self, mod_request: ModRequest) -> Result:
        """
        Process a single mod request.

        Args:
            mod_request: ModRequest object with enum-based source type

        Returns:
            Result object indicating success/failure
        """
        mod_id = mod_request.id

        try:
            # Initialize repository
            repo = Repo(
                url=mod_request.repo_url,
                work_branch=mod_request.work_branch,
                repo_path=self.repos_path / secure_filename(mod_request.repo_name),
                git_path=self.git_path
            )
            repo.ensure_cloned()
            repo.prepare_work_branch()

            # Apply the mod based on source type (enum, not string!)
            if mod_request.source_type == ModSourceType.COMMIT:
                # Apply commit from cppDev
                repo.cherry_pick(mod_request.commit_hash)
            elif mod_request.source_type == ModSourceType.PATCH:
                # Apply patch file
                repo.apply_patch(mod_request.patch_path)

            # Compile and generate ASM for validation
            cpp_files = list(repo.repo_path.glob('**/*.cpp'))
            validation_results = []

            for cpp_file in cpp_files:
                # Compile original
                original_asm = self.compiler.compile_to_asm(
                    cpp_file,
                    self.temp_path / f'original_{cpp_file.stem}.asm'
                )

                # Apply mod changes (if BUILTIN)
                if mod_request.source_type == ModSourceType.BUILTIN:
                    # Use mod instance directly (not string ID!)
                    modified_cpp = self.mod_handler.apply_mod_instance(
                        cpp_file,
                        mod_request.mod_instance
                    )
                else:
                    # For COMMIT/PATCH, changes are already applied via git
                    modified_cpp = cpp_file

                # Compile modified
                modified_asm = self.compiler.compile_to_asm(
                    modified_cpp,
                    self.temp_path / f'modified_{cpp_file.stem}.asm'
                )

                # Validate ASM
                is_valid = self.asm_validator.validate(original_asm, modified_asm)
                validation_results.append({
                    'file': str(cpp_file),
                    'valid': is_valid
                })

            # Check if all validations passed
            all_valid = all(v['valid'] for v in validation_results)

            if all_valid:
                # Commit changes to work branch
                repo.commit(
                    f"LevelUp: Applied mod {mod_id} - {mod_request.description}"
                )

                return Result(
                    status=ResultStatus.SUCCESS,
                    message='Mod successfully validated and applied',
                    validation_results=validation_results
                )
            else:
                # Revert changes
                repo.reset_hard()

                return Result(
                    status=ResultStatus.FAILED,
                    message='Validation failed - changes not applied',
                    validation_results=validation_results
                )

        except Exception as e:
            return Result(
                status=ResultStatus.ERROR,
                message=str(e)
            )
