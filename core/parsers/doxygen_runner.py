"""
Doxygen runner for generating XML output with function dependency information.
"""

import subprocess
import tempfile
from pathlib import Path

from .. import logger


class DoxygenRunner:
    """
    Runs Doxygen to generate XML output containing function prototypes,
    file locations, and call dependency graphs.
    """

    # Template Doxyfile configuration optimized for XML output with call graphs
    DOXYFILE_TEMPLATE = """
# Project
PROJECT_NAME           = "{project_name}"
OUTPUT_DIRECTORY       = "{output_dir}"
INPUT                  = "{input_dir}"

# Input settings
RECURSIVE              = YES
FILE_PATTERNS          = *.cpp *.cxx *.cc *.c *.hpp *.hxx *.h *.hh
EXTENSION_MAPPING      =

# Parsing - C++ focus
EXTRACT_ALL            = YES
EXTRACT_PRIVATE        = YES
EXTRACT_STATIC         = YES
EXTRACT_LOCAL_CLASSES  = YES
EXTRACT_LOCAL_METHODS  = YES

# Macro expansion - controlled by parameter
MACRO_EXPANSION        = {macro_expansion}
EXPAND_ONLY_PREDEF     = NO
SKIP_FUNCTION_MACROS   = NO

# Call graph generation
HAVE_DOT               = NO
CALL_GRAPH             = NO
CALLER_GRAPH           = NO
REFERENCES_RELATION    = YES
REFERENCED_BY_RELATION = YES

# Output settings - XML only
GENERATE_HTML          = NO
GENERATE_LATEX         = NO
GENERATE_RTF           = NO
GENERATE_MAN           = NO
GENERATE_DOCBOOK       = NO
GENERATE_XML           = YES
XML_OUTPUT             = {xml_output}
XML_PROGRAMLISTING     = YES

# Performance
QUIET                  = YES
WARNINGS               = NO
WARN_IF_UNDOCUMENTED   = NO
WARN_IF_DOC_ERROR      = NO

# Source browsing - needed for cross-references
SOURCE_BROWSER         = YES
INLINE_SOURCES         = NO
REFERENCED_BY_RELATION = YES
REFERENCES_RELATION    = YES
"""

    def __init__(self, doxygen_path: str = 'doxygen'):
        self.doxygen_path = doxygen_path

    def _create_doxyfile(self, project_name: str, input_dir: Path, output_dir: Path,
                        macro_expansion: bool = False, xml_output: str = 'xml') -> str:
        """Generate Doxyfile content with proper settings."""
        return self.DOXYFILE_TEMPLATE.format(
            project_name=project_name,
            input_dir=str(input_dir).replace('\\', '/'),
            output_dir=str(output_dir).replace('\\', '/'),
            macro_expansion='YES' if macro_expansion else 'NO',
            xml_output=xml_output
        )

    def _run_single(self, repo_path: Path, output_dir: Path, project_name: str,
                   macro_expansion: bool, xml_output: str) -> Path:
        """
        Run Doxygen with specific configuration.

        Args:
            repo_path: Path to the repository to analyze
            output_dir: Output directory
            project_name: Project name
            macro_expansion: Whether to expand macros
            xml_output: Subdirectory name for XML output

        Returns:
            Path to the generated XML directory
        """
        xml_dir = output_dir / xml_output

        # Create Doxyfile
        doxyfile_content = self._create_doxyfile(
            project_name, repo_path, output_dir,
            macro_expansion=macro_expansion,
            xml_output=xml_output
        )
        doxyfile_path = output_dir / f'Doxyfile.{xml_output}'

        with open(doxyfile_path, 'w') as f:
            f.write(doxyfile_content)

        expansion_str = "with macro expansion" if macro_expansion else "without macro expansion"
        logger.info(f"Running Doxygen on {repo_path} {expansion_str}")

        try:
            result = subprocess.run(
                [self.doxygen_path, str(doxyfile_path)],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning(f"Doxygen returned non-zero exit code: {result.returncode}")
                if result.stderr:
                    logger.debug(f"Doxygen stderr: {result.stderr[:500]}")

            # Check if XML was generated
            if not xml_dir.exists():
                raise RuntimeError(f"Doxygen did not generate XML output at {xml_dir}")

            logger.info(f"Doxygen XML generated at {xml_dir}")
            return xml_dir

        except FileNotFoundError:
            raise RuntimeError(
                f"Doxygen executable not found at '{self.doxygen_path}'. "
                "Please install Doxygen and ensure it's in PATH."
            )

    def run(self, repo_path: Path, output_dir: Path = None) -> tuple[Path, Path]:
        """
        Run Doxygen on a repository to generate XML output both with and without macro expansion.

        Args:
            repo_path: Path to the repository to analyze
            output_dir: Optional output directory. If not provided, uses repo_path/.doxygen

        Returns:
            Tuple of (xml_unexpanded_dir, xml_expanded_dir) paths
        """
        if output_dir is None:
            output_dir = repo_path / '.doxygen'

        output_dir.mkdir(parents=True, exist_ok=True)
        project_name = repo_path.name

        # Run Doxygen without macro expansion (original behavior)
        xml_unexpanded = self._run_single(
            repo_path, output_dir, project_name,
            macro_expansion=False,
            xml_output='xml_unexpanded'
        )

        # Run Doxygen with macro expansion
        xml_expanded = self._run_single(
            repo_path, output_dir, project_name,
            macro_expansion=True,
            xml_output='xml_expanded'
        )

        return (xml_unexpanded, xml_expanded)

    def is_available(self) -> bool:
        """Check if Doxygen is available on the system."""
        try:
            result = subprocess.run(
                [self.doxygen_path, '--version'],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_version(self) -> str:
        """Get Doxygen version string."""
        try:
            result = subprocess.run(
                [self.doxygen_path, '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
