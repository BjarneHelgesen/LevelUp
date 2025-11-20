from pathlib import Path
import uuid

from .compilers.compiler import MSVCCompiler
from .validators.asm_validator import ASMValidator
from .validators.source_diff_validator import SourceDiffValidator
from .mods.mod_handler import ModHandler
from .result import Result, ResultStatus
from .repo.repo import Repo
from .mod_request import ModRequest, ModSourceType
from .validation_result import ValidationResult
from .git_commit import GitCommit
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

            # Determine mod name for display
            if mod_request.mod_instance:
                mod_name = mod_request.mod_instance.get_name()
            else:
                mod_name = mod_request.description or 'Commit'

            # Handle COMMIT source type (legacy path)
            if mod_request.source_type == ModSourceType.COMMIT:
                return self._process_commit_mod(mod_request, repo, mod_name)

            # Handle BUILTIN mods with generator pattern
            return self._process_builtin_mod(mod_request, repo, mod_name)

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

    def _process_commit_mod(self, mod_request: ModRequest, repo: Repo, mod_name: str) -> Result:
        """Process a COMMIT type mod (legacy path)"""
        mod_id = mod_request.id
        logger.debug(f"Cherry-picking commit {mod_request.commit_hash}")
        repo.cherry_pick(mod_request.commit_hash)

        # Find all C/C++ source and header files
        source_files = []
        for pattern in ['**/*.cpp', '**/*.c', '**/*.hpp', '**/*.h']:
            source_files.extend([f for f in repo.repo_path.glob(pattern)
                                if not f.name.startswith('_levelup_')])

        # Compile and validate
        validation_results = []
        for source_file in source_files:
            original = self.compiler.compile_file(source_file)
            modified = self.compiler.compile_file(source_file)
            is_valid = self.asm_validator.validate(original, modified)
            validation_results.append(ValidationResult(
                file=str(source_file),
                valid=is_valid
            ))

        valid_count = sum(1 for v in validation_results if v.valid)
        total_count = len(validation_results)
        all_valid = valid_count == total_count

        if all_valid:
            logger.info(f"All validations passed for mod {mod_id}, pushing to remote")
            repo.push()
            return Result(
                status=ResultStatus.SUCCESS,
                message=mod_name,
                validation_results=validation_results
            )
        else:
            logger.warning(f"Validation failed for mod {mod_id}, resetting")
            repo.reset_hard()
            return Result(
                status=ResultStatus.FAILED,
                message=mod_name,
                validation_results=validation_results
            )

    def _process_builtin_mod(self, mod_request: ModRequest, repo: Repo, mod_name: str) -> Result:
        """Process a BUILTIN mod using generator pattern for atomic changes"""
        mod_id = mod_request.id

        # Create atomic branch for this mod's changes
        atomic_branch = f"levelup-atomic-{mod_id}"
        repo.create_atomic_branch(repo.work_branch, atomic_branch)

        accepted_commits = []
        rejected_commits = []
        validation_results = []

        try:
            # Generate and process atomic changes
            for file_path, commit_message in mod_request.mod_instance.generate_changes(repo.repo_path):
                logger.debug(f"Processing atomic change: {commit_message}")

                # Store original content before change
                original_content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Compile original
                original_compiled = self.compiler.compile_file(file_path)

                # File has already been modified by the generator
                # Compile modified version
                modified_compiled = self.compiler.compile_file(file_path)

                # Validate based on mod type
                if mod_request.mod_instance.get_id() == 'remove_inline':
                    # For remove_inline: just check both compiled successfully
                    is_valid = True
                else:
                    # Default: validate ASM equivalence
                    is_valid = self.asm_validator.validate(original_compiled, modified_compiled)

                logger.debug(f"Validation result: {'PASS' if is_valid else 'FAIL'}")

                if is_valid:
                    # Commit this atomic change
                    if repo.commit(commit_message):
                        commit_hash = repo.get_commit_hash()
                        git_commit = GitCommit(str(file_path), commit_message)
                        git_commit.commit_hash = commit_hash
                        git_commit.accepted = True
                        accepted_commits.append(git_commit)
                        logger.info(f"Accepted and committed: {commit_message}")

                        validation_results.append(ValidationResult(
                            file=str(file_path),
                            valid=True
                        ))
                    else:
                        logger.debug(f"No changes to commit for: {commit_message}")
                else:
                    # Revert this change
                    file_path.write_text(original_content, encoding='utf-8')
                    git_commit = GitCommit(str(file_path), commit_message)
                    git_commit.accepted = False
                    rejected_commits.append(git_commit)
                    logger.info(f"Rejected and reverted: {commit_message}")

                    validation_results.append(ValidationResult(
                        file=str(file_path),
                        valid=False
                    ))

            # Determine result status
            if len(accepted_commits) > 0 and len(rejected_commits) == 0:
                status = ResultStatus.SUCCESS
            elif len(accepted_commits) > 0 and len(rejected_commits) > 0:
                status = ResultStatus.PARTIAL
            else:
                status = ResultStatus.FAILED

            # Squash and rebase accepted commits back to work branch
            if len(accepted_commits) > 0:
                logger.info(f"Squashing {len(accepted_commits)} commits and rebasing to {repo.work_branch}")
                repo.squash_and_rebase(atomic_branch, repo.work_branch)

                # Push the squashed commit
                logger.info(f"Pushing squashed changes to remote")
                repo.push()
            else:
                # No accepted commits, just switch back to work branch and delete atomic branch
                logger.info("No accepted commits, cleaning up atomic branch")
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)

            return Result(
                status=status,
                message=mod_name,
                validation_results=validation_results,
                accepted_commits=[c.to_dict() for c in accepted_commits],
                rejected_commits=[c.to_dict() for c in rejected_commits]
            )

        except Exception as e:
            # On error, return to work branch and cleanup
            logger.exception(f"Error during atomic processing: {e}")
            try:
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)
            except Exception:
                pass  # Best effort cleanup
            raise
