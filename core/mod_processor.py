from pathlib import Path
import uuid

from .compilers.compiler_factory import get_compiler
from .validators.validator_factory import ValidatorFactory
from .mods.mod_handler import ModHandler
from .result import Result, ResultStatus
from .repo.repo import Repo
from .mod_request import ModRequest
from .validation_result import ValidationResult
from . import logger


class ModProcessor:
    def __init__(self, repos_path: Path, git_path: str = 'git'):
        logger.info(f"ModProcessor initializing with repos_path={repos_path}")
        self.compiler = get_compiler()
        self.asm_validator = ValidatorFactory.from_id('asm_o0')
        self.mod_handler = ModHandler()
        self.repos_path = Path(repos_path).resolve()
        self.git_path = git_path
        logger.info("ModProcessor initialized successfully")


    def process_mod(self, mod_request: ModRequest) -> Result:
        mod_id = mod_request.id

        logger.info(f"Processing mod {mod_id}: {mod_request.description}")
        logger.debug(f"Mod details: repo={mod_request.repo_url}")

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

            # Get mod name for display
            mod_name = mod_request.mod_instance.get_name()

            # Process the mod
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

    def _process_builtin_mod(self, mod_request: ModRequest, repo: Repo, mod_name: str) -> Result:
        """Process a BUILTIN mod using generator pattern for atomic changes"""
        mod_id = mod_request.id

        # Get validator from mod, optimization level from validator
        validator_id = mod_request.mod_instance.get_validator_id()
        validator = ValidatorFactory.from_id(validator_id)
        optimization_level = validator.get_optimization_level()
        logger.debug(f"Using validator '{validator_id}' with optimization level {optimization_level}")

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

                # Compile original with the optimization level specified by the validator
                original_compiled = self.compiler.compile_file(file_path, optimization_level=optimization_level)

                # File has already been modified by the generator
                # Compile modified version
                modified_compiled = self.compiler.compile_file(file_path, optimization_level=optimization_level)

                # Validate using the mod's specified validator
                is_valid = validator.validate(original_compiled, modified_compiled)

                logger.debug(f"Validation result: {'PASS' if is_valid else 'FAIL'}")

                if is_valid:
                    # Commit this atomic change
                    repo.commit(commit_message)
                    accepted_commits.append(commit_message)
                    logger.info(f"Accepted and committed: {commit_message}")

                    validation_results.append(ValidationResult(
                        file=str(file_path),
                        valid=True
                    ))
                else:
                    # Revert this change
                    file_path.write_text(original_content, encoding='utf-8')
                    rejected_commits.append(commit_message)
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
                rejected_commits=rejected_commits
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
