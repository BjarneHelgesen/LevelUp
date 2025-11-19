# LevelUp - C++ Modernization Tool

LevelUp is a tool for modernizing legacy C++ code with zero regression risk. It validates all changes by comparing assembly output to ensure no functional changes are introduced.

## Features

### Version 1.0 - Basic Functionality
- Web-based UI for managing repositories and modifications
- Support for cppDev direct commits with automatic validation
- ASM-based validation using MSVC compiler
- Automatic rebasing of validated changes to work branch
- Queue management for asynchronous processing
- Real-time status updates in the UI

## Architecture

### Components
- **Flask Server** (`server/app.py`): Main application server
- **Repo** (`core/repo.py`): Git repository management
- **MSVC Compiler** (`core/compilers/compiler.py`): Wrapper for MSVC compilation
- **ASM Validator** (`core/validators/asm_validator.py`): Validates assembly output
- **Mod Handler** (`core/mods/mod_handler.py`): Applies modifications to code
- **Web UI** (`server/templates/index.html`): User interface

### Extensibility
The architecture supports future additions:
- New validators (AST diff, unit tests, warning checks)
- Additional compilers (GCC, Clang)
- More modification types (automated refactoring)
- Multi-repository support
- LLM integration for code modernization

## Installation

### Prerequisites
- Python 3.8+
- Git
- MSVC (Visual Studio C++ Compiler)
- Windows OS (initial version, cross-platform support planned)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/BjarneHelgesen/LevelUp.git
cd LevelUp
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (optional):
```bash
set GIT_PATH=C:\Path\To\git.exe
```

Note: MSVC compiler (cl.exe) is auto-discovered via vswhere.exe.

4. Run the server:
```bash
python server/app.py
```

5. Access the web interface at `http://localhost:5000`

## Usage

### Setting Up a Repository

1. Navigate to the "Repositories" screen
2. Click "Add Repository" and enter:
   - URL: Git repository URL
   - Post-Checkout Commands: Optional commands to run after checkout
   - Build Command: Command to build the entire project
   - Single TU Command: Command to compile a single translation unit

3. Click "Add Repository"

Note: Repository name is automatically extracted from the URL. Work branch is hardcoded to "levelup-work".

### Applying Built-in Mods

1. Select a repository from the Repositories screen
2. In the Mods screen, select a mod type:
   - Remove Inline Keywords
   - Add Override Keywords
   - Replace MS-Specific Syntax
3. Enter a description
4. Click "Submit"

### CppDev Workflow (Commit Validation)

1. Make changes to your C++ code locally
2. Commit your changes:
   ```bash
   git add .
   git commit -m "Your modernization changes"
   ```
3. Get the commit hash:
   ```bash
   git rev-parse HEAD
   ```
4. In LevelUp, select your repository
5. Select "Validate Commit" mod type
6. Enter the commit hash and description
7. Click "Submit"

LevelUp will:
- Apply your changes to a test environment
- Compile both original and modified code to assembly
- Compare the assembly output
- If validation passes, commit and push changes to the work branch
- Update the UI with the result

### Monitoring Progress

Poll the queue status endpoint or watch the UI for:
- Current queue size
- Processing status
- Completed validations (SUCCESS, PARTIAL, FAILED)
- Error conditions

Results are updated in real-time.

## Validation Process

### ASM Validation
The current validator ensures zero regression by:
1. Compiling original code to assembly with full optimization
2. Applying the modification
3. Compiling modified code to assembly with same settings
4. Comparing normalized assembly output
5. Accepting only if assembly is functionally identical

### Acceptable Differences
The validator allows:
- Comment changes
- Label reordering (when safe)
- Register substitution (same operations, different registers)
- Equivalent operations (e.g., LEA vs MOV for addresses)
- NOPs and alignment changes

### Result Statuses
- **SUCCESS**: All files passed validation
- **PARTIAL**: Some files passed, some failed
- **FAILED**: No files passed validation
- **ERROR**: An error occurred during processing

## API Endpoints

### Repository Management
- `GET /api/repos` - List repositories
- `POST /api/repos` - Add repository
- `PUT /api/repos/<id>` - Update repository
- `DELETE /api/repos/<id>` - Delete repository

### Mod Management
- `POST /api/mods` - Submit modification
- `GET /api/mods/<id>/status` - Get mod status

### Available Resources
- `GET /api/available/mods` - List available mod types
- `GET /api/available/validators` - List available validator types
- `GET /api/available/compilers` - List available compiler types

### Queue Management
- `GET /api/queue/status` - Get queue status

## Future Enhancements

### Planned Validators
- AST diff comparison
- Source diff analysis
- Unit test execution
- Warning diff analysis
- Human review workflow

### Planned Mods
- Clang-Tidy integration
- LLM-powered modernization
- Microsoft macro replacement
- Smart pointer conversion
- Container modernization
- Exception safety improvements

### Infrastructure
- Linux/macOS support
- Multiple compiler support
- Docker containerization
- CI/CD integration
- Advanced queue management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Your license here]

## Support

For issues or questions, please open an issue on GitHub.
