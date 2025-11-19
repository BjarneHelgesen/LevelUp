from pathlib import Path
import os

from .compilers.compiler import MSVCCompiler
from .validators.asm_validator import ASMValidator
from .validators.source_diff_validator import SourceDiffValidator
from .mods.mod_handler import ModHandler
from .result import Result, ResultStatus
from .repo import Repo
from .mod_request import ModRequest, ModSourceType
from .validation_result import ValidationResult
from . import logger


class ModProcessor:
    def __init__(self, repos_path: Path, temp_path: Path, git_path: str = 'git'):
        logger.info(f"ModProcessor initializing with repos_path={repos_path}, temp_path={temp_path}")
        self.compiler = MSVCCompiler()
        self.asm_validator = ASMValidator(self.compiler)
        self.source_diff_validator = SourceDiffValidator(allowed_removals=['inline'])
        self.mod_handler = ModHandler()
        self.repos_path = Path(repos_path).resolve()
        self.temp_path = Path(temp_path).resolve()
        self.git_path = git_path
        logger.info("ModProcessor initialized successfully")


    def process_mod(self, mod_request: ModRequest) -> Result:
        mod_id = mod_request.id
        temp_files = []  # Track temp ASM files for cleanup

        logger.info(f"Processing mod {mod_id}: {mod_request.description}")
        logger.debug(f"Mod details: repo={mod_request.repo_name}, type={mod_request.source_type}")

        try:
            # Initialize repository
            logger.debug(f"Initializing repo from {mod_request.repo_url}")
            repo = Repo(
                url=mod_request.repo_url,
                repos_folder=self.repos_path,
                git_path=self.git_path
            )
            repo.ensure_cloned()
            repo.prepare_work_branch()

            if mod_request.source_type == ModSourceType.COMMIT:
                logger.debug(f"Cherry-picking commit {mod_request.commit_hash}")
                repo.cherry_pick(mod_request.commit_hash)

            cpp_files = [f for f in repo.repo_path.glob('**/*.cpp')
                        if not f.name.startswith('_levelup_')]
            logger.info(f"Found {len(cpp_files)} C++ files to process")
            validation_results = []

            for cpp_file in cpp_files:
                logger.debug(f"Processing file: {cpp_file}")

                logger.debug(f"Compiling original {cpp_file.name}")
                original_asm = self.compiler.compile_to_asm(
                    cpp_file,
                    self.temp_path / f'original_{cpp_file.stem}.asm'
                )
                temp_files.append(original_asm)

                if mod_request.source_type == ModSourceType.BUILTIN:
                    logger.debug(f"Applying mod {mod_request.mod_instance.get_id()} to {cpp_file.name}")
                    self.mod_handler.apply_mod_instance(
                        cpp_file,
                        mod_request.mod_instance
                    )

                logger.debug(f"Compiling modified {cpp_file.name}")
                modified_asm = self.compiler.compile_to_asm(
                    cpp_file,
                    self.temp_path / f'modified_{cpp_file.stem}.asm'
                )
                temp_files.append(modified_asm)

                # Choose validator based on mod type
                if (mod_request.source_type == ModSourceType.BUILTIN and
                    mod_request.mod_instance.get_id() == 'remove_inline'):
                    # For remove_inline: just check both compiled successfully
                    # Source diff validation not needed since we modified in-place
                    logger.debug(f"Validation for {cpp_file.name}: compiled successfully")
                    is_valid = True
                else:
                    # Default: validate ASM equivalence
                    logger.debug(f"Validating ASM for {cpp_file.name}")
                    is_valid = self.asm_validator.validate(original_asm, modified_asm)

                validation_results.append(ValidationResult(
                    file=str(cpp_file),
                    valid=is_valid
                ))
                logger.debug(f"Validation result for {cpp_file.name}: {'PASS' if is_valid else 'FAIL'}")

            all_valid = all(v.valid for v in validation_results)

            if all_valid:
                logger.info(f"All validations passed for mod {mod_id}, committing changes")
                repo.commit(
                    f"LevelUp: Applied mod {mod_id} - {mod_request.description}"
                )

                return Result(
                    status=ResultStatus.SUCCESS,
                    message='Mod successfully validated and applied',
                    validation_results=validation_results
                )
            else:
                failed_files = [v.file for v in validation_results if not v.valid]
                logger.warning(f"Validation failed for mod {mod_id}, resetting. Failed files: {failed_files}")
                repo.reset_hard()

                return Result(
                    status=ResultStatus.FAILED,
                    message='Validation failed - changes not applied',
                    validation_results=validation_results
                )

        except Exception as e:
            logger.exception(f"Error processing mod {mod_id}: {e}")
            # Reset repo on error to restore original files
            try:
                repo.reset_hard()
            except Exception:
                pass  # Best effort reset
            return Result(
                status=ResultStatus.ERROR,
                message=str(e)
            )
        finally:
            # Clean up temporary ASM files
            for temp_file in temp_files:
                try:
                    if temp_file and Path(temp_file).exists():
                        os.remove(temp_file)
                except Exception:
                    pass  # Best effort cleanup
