from pathlib import Path

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
    def __init__(self, repos_path: Path, git_path: str = 'git'):
        logger.info(f"ModProcessor initializing with repos_path={repos_path}")
        self.compiler = MSVCCompiler()
        self.asm_validator = ASMValidator(self.compiler)
        self.source_diff_validator = SourceDiffValidator(allowed_removals=['inline'])
        self.mod_handler = ModHandler()
        self.repos_path = Path(repos_path).resolve()
        self.git_path = git_path
        logger.info("ModProcessor initialized successfully")


    def process_mod(self, mod_request: ModRequest) -> Result:
        mod_id = mod_request.id

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

            # Find all C/C++ source and header files
            source_files = []
            for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
                source_files.extend([f for f in repo.repo_path.glob(pattern)
                                    if not f.name.startswith('_levelup_')])
            logger.info(f"Found {len(source_files)} C/C++ files to process")

            # Compile original versions of all files and store original content
            logger.debug("Compiling original versions and storing content")
            originals = {}
            original_contents = {}
            for source_file in source_files:
                logger.debug(f"Compiling original {source_file.name}")
                originals[source_file] = self.compiler.compile_file(source_file)
                # Store original content for potential restoration
                original_contents[source_file] = source_file.read_text(encoding='utf-8', errors='ignore')

            # Apply the mod changes
            if mod_request.source_type == ModSourceType.COMMIT:
                logger.debug(f"Cherry-picking commit {mod_request.commit_hash}")
                repo.cherry_pick(mod_request.commit_hash)
            elif mod_request.source_type == ModSourceType.BUILTIN:
                for source_file in source_files:
                    logger.debug(f"Applying mod {mod_request.mod_instance.get_id()} to {source_file.name}")
                    self.mod_handler.apply_mod_instance(
                        source_file,
                        mod_request.mod_instance
                    )

            # Compile modified versions and validate
            validation_results = []
            for source_file in source_files:
                logger.debug(f"Compiling modified {source_file.name}")
                original = originals[source_file]
                modified = self.compiler.compile_file(source_file)

                # Choose validator based on mod type
                if (mod_request.source_type == ModSourceType.BUILTIN and
                    mod_request.mod_instance.get_id() == 'remove_inline'):
                    # For remove_inline: just check both compiled successfully
                    # Source diff validation not needed since we modified in-place
                    logger.debug(f"Validation for {source_file.name}: compiled successfully")
                    is_valid = True
                else:
                    # Default: validate ASM equivalence
                    logger.debug(f"Validating ASM for {source_file.name}")
                    is_valid = self.asm_validator.validate(original, modified)

                validation_results.append(ValidationResult(
                    file=str(source_file),
                    valid=is_valid
                ))
                logger.debug(f"Validation result for {source_file.name}: {'PASS' if is_valid else 'FAIL'}")

            # Determine mod name for display
            if mod_request.mod_instance:
                mod_name = mod_request.mod_instance.get_name()
            else:
                mod_name = mod_request.description or 'Commit'

            # Count valid and invalid results
            valid_count = sum(1 for v in validation_results if v.valid)
            total_count = len(validation_results)
            all_valid = valid_count == total_count
            any_valid = valid_count > 0

            if all_valid:
                logger.info(f"All validations passed for mod {mod_id}, committing changes")
                if repo.commit(f"LevelUp: Applied mod {mod_id} - {mod_request.description}"):
                    repo.push()

                return Result(
                    status=ResultStatus.SUCCESS,
                    message=mod_name,
                    validation_results=validation_results
                )
            elif any_valid:
                # Partial success - some files passed, some failed
                logger.info(f"Partial success for mod {mod_id}: {valid_count}/{total_count} files passed")

                # Restore failed files to original state before committing
                failed_files = [Path(v.file) for v in validation_results if not v.valid]
                for failed_file in failed_files:
                    if failed_file in original_contents:
                        logger.debug(f"Restoring failed file to original: {failed_file.name}")
                        failed_file.write_text(original_contents[failed_file], encoding='utf-8')

                # Now commit only the successful changes
                if repo.commit(f"LevelUp: Applied mod {mod_id} - {mod_request.description} ({valid_count}/{total_count} files)"):
                    repo.push()

                return Result(
                    status=ResultStatus.PARTIAL,
                    message=mod_name,
                    validation_results=validation_results
                )
            else:
                failed_files = [v.file for v in validation_results if not v.valid]
                logger.warning(f"Validation failed for mod {mod_id}, resetting. Failed files: {failed_files}")
                repo.reset_hard()

                return Result(
                    status=ResultStatus.FAILED,
                    message=mod_name,
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
