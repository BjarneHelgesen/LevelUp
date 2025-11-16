from pathlib import Path
import os

from .compilers.compiler import MSVCCompiler
from .validators.asm_validator import ASMValidator
from .mods.mod_handler import ModHandler
from .result import Result, ResultStatus
from .repo import Repo
from .mod_request import ModRequest, ModSourceType
from .validation_result import ValidationResult


class ModProcessor:
    def __init__(self, msvc_path: str, repos_path: Path, temp_path: Path, git_path: str = 'git'):
        self.compiler = MSVCCompiler(msvc_path)
        self.asm_validator = ASMValidator(self.compiler)
        self.mod_handler = ModHandler()
        self.repos_path = Path(repos_path)
        self.temp_path = Path(temp_path)
        self.git_path = git_path


    def process_mod(self, mod_request: ModRequest) -> Result:
        mod_id = mod_request.id
        temp_files = []  # Track temp files for cleanup

        try:
            # Initialize repository
            repo = Repo(
                url=mod_request.repo_url,
                repos_folder=self.repos_path,
                git_path=self.git_path
            )
            repo.ensure_cloned()
            repo.prepare_work_branch()

            if mod_request.source_type == ModSourceType.COMMIT:
                repo.cherry_pick(mod_request.commit_hash)

            cpp_files = list(repo.repo_path.glob('**/*.cpp'))
            validation_results = []

            for cpp_file in cpp_files:
                original_asm = self.compiler.compile_to_asm(
                    cpp_file,
                    self.temp_path / f'original_{cpp_file.stem}.asm'
                )
                temp_files.append(original_asm)

                if mod_request.source_type == ModSourceType.BUILTIN:
                    modified_cpp = self.mod_handler.apply_mod_instance(
                        cpp_file,
                        mod_request.mod_instance
                    )
                    temp_files.append(modified_cpp)
                else:
                    modified_cpp = cpp_file

                modified_asm = self.compiler.compile_to_asm(
                    modified_cpp,
                    self.temp_path / f'modified_{cpp_file.stem}.asm'
                )
                temp_files.append(modified_asm)

                is_valid = self.asm_validator.validate(original_asm, modified_asm)
                validation_results.append(ValidationResult(
                    file=str(cpp_file),
                    valid=is_valid
                ))

            all_valid = all(v.valid for v in validation_results)

            if all_valid:
                repo.commit(
                    f"LevelUp: Applied mod {mod_id} - {mod_request.description}"
                )

                return Result(
                    status=ResultStatus.SUCCESS,
                    message='Mod successfully validated and applied',
                    validation_results=validation_results
                )
            else:
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
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if temp_file and Path(temp_file).exists():
                        os.remove(temp_file)
                except Exception:
                    pass  # Best effort cleanup
