"""
ModProcessor - processes mod requests using the refactoring architecture.
"""

from pathlib import Path

from .compilers.compiler_factory import get_compiler
from .validators.validator_factory import ValidatorFactory
from .result import Result, ResultStatus
from .repo.repo import Repo
from .mod_request import ModRequest
from .validators.validation_result import ValidationResult
from .parsers.symbol_table import SymbolTable
from . import logger


class ModProcessor:
    """
    Processes mod requests using the refactoring architecture.

    All mods follow the same pattern:
    1. Ensure Doxygen data exists
    2. Load symbol table
    3. Generate refactorings from mod
    4. Apply each refactoring (creates GitCommit)
    5. Validate each commit
    6. Rollback invalid commits
    """

    def __init__(self, repos_path: Path, git_path: str = 'git'):
        logger.info(f"ModProcessor initializing with repos_path={repos_path}")
        self.compiler = get_compiler()
        self.repos_path = Path(repos_path).resolve()
        self.git_path = git_path
        logger.info("ModProcessor initialized successfully")

    def process_mod(self, mod_request: ModRequest) -> Result:
        """Process a mod request using refactorings."""
        mod_id = mod_request.id
        mod_instance = mod_request.mod_instance

        logger.info(f"Processing mod {mod_id}: {mod_instance.get_name()}")

        try:
            # Initialize repository
            repo = Repo(
                url=mod_request.repo_url,
                repos_folder=self.repos_path,
                git_path=self.git_path
            )
            repo.ensure_cloned()
            repo.prepare_work_branch()

            # Load symbol table (generates Doxygen if needed)
            symbols = self._load_symbols(repo)

            # Process mod with refactorings
            return self._process_refactorings(mod_request, repo, symbols)

        except Exception as e:
            logger.exception(f"Error processing mod {mod_id}: {e}")
            try:
                repo.reset_hard()
            except Exception:
                pass
            return Result(
                status=ResultStatus.ERROR,
                message=str(e)
            )

    def _load_symbols(self, repo: Repo) -> SymbolTable:
        """Load symbol table from Doxygen XML."""
        symbols = SymbolTable(repo)
        symbols.load_from_doxygen()
        logger.info(f"Loaded {len(symbols._symbols)} symbols from Doxygen")
        return symbols

    def _process_refactorings(self, mod_request: ModRequest,
                              repo: Repo, symbols: SymbolTable) -> Result:
        """
        Process mod using refactoring pattern.

        Each refactoring is applied, validated, and either kept or rolled back.
        """
        mod_id = mod_request.id
        mod_instance = mod_request.mod_instance

        # Create atomic branch for this mod's changes
        atomic_branch = f"levelup-atomic-{mod_id}"
        repo.create_atomic_branch(repo.work_branch, atomic_branch)

        accepted_commits = []
        rejected_commits = []
        validation_results = []

        try:
            # Generate refactorings from mod
            for refactoring, *args in mod_instance.generate_refactorings(repo, symbols):
                logger.debug(f"Applying {refactoring.__class__.__name__}")

                # Get file path from first argument (symbol)
                symbol = args[0]
                file_path = Path(symbol.file_path)

                # Store original content for potential rollback
                original_content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Apply refactoring with arguments
                # Refactoring modifies file and creates git commit
                git_commit = refactoring.apply(*args)

                if git_commit is None:
                    # Refactoring could not be applied (preconditions failed)
                    logger.debug(f"Refactoring skipped: {refactoring.__class__.__name__}")
                    continue

                # Get validator and optimization level from git_commit
                validator = ValidatorFactory.from_id(git_commit.validator_type)
                optimization_level = validator.get_optimization_level()

                # Compile original (need to restore original content first)
                file_path.write_text(original_content, encoding='utf-8')
                original_compiled = self.compiler.compile_file(
                    file_path,
                    optimization_level=optimization_level
                )

                # Restore modified content and compile
                repo.checkout_file(file_path)  # Restore from git commit
                modified_compiled = self.compiler.compile_file(
                    file_path,
                    optimization_level=optimization_level
                )

                # Validate
                is_valid = validator.validate(original_compiled, modified_compiled)

                if is_valid:
                    # Keep commit
                    accepted_commits.append(git_commit.commit_message)
                    logger.info(f"Accepted: {git_commit.commit_message}")

                    validation_results.append(ValidationResult(
                        file=str(file_path),
                        valid=True
                    ))

                    # Refresh symbols from modified source
                    for affected_symbol_name in git_commit.affected_symbols:
                        symbols.refresh_symbol_from_source(affected_symbol_name)
                else:
                    # Rollback commit
                    git_commit.rollback()
                    rejected_commits.append(git_commit.commit_message)
                    logger.info(f"Rejected: {git_commit.commit_message}")

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

            # Squash and rebase accepted commits
            if len(accepted_commits) > 0:
                logger.info(f"Squashing {len(accepted_commits)} commits")
                repo.squash_and_rebase(atomic_branch, repo.work_branch)
                repo.push()
            else:
                logger.info("No accepted commits, cleaning up")
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)

            return Result(
                status=status,
                message=mod_instance.get_name(),
                validation_results=validation_results,
                accepted_commits=accepted_commits,
                rejected_commits=rejected_commits
            )

        except Exception as e:
            logger.exception(f"Error during refactoring processing: {e}")
            try:
                repo.checkout_branch(repo.work_branch)
                repo.delete_branch(atomic_branch, force=True)
            except Exception:
                pass
            raise
