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
- **Flask Server** (`app.py`): Main application server
- **Git Handler** (`utils/git_handler.py`): Manages git operations
- **MSVC Compiler** (`utils/compiler.py`): Wrapper for MSVC compilation
- **ASM Validator** (`validators/asm_validator.py`): Validates assembly output
- **Mod Handler** (`mods/mod_handler.py`): Applies modifications to code
- **Web UI** (`templates/index.html`): User interface

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
set MSVC_PATH=C:\Path\To\cl.exe
set GIT_PATH=C:\Path\To\git.exe
```

4. Run the server:
```bash
python app.py
```

5. Access the web interface at `http://localhost:5000`

## Usage

### Setting Up a Repository

1. Navigate to the "Repositories" tab
2. Enter repository details:
   - Name: A friendly name for the repository
   - URL: Git repository URL
   - Work Branch: Branch for LevelUp changes (default: levelup-work)
   - Post-Checkout Commands: Optional commands to run after checkout
   - Build Command: Command to build the entire project
   - Single TU Command: Command to compile a single translation unit

3. Click "Add Repository"

### CppDev Workflow

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
4. Go to the "CppDev Tools" tab in LevelUp
5. Select your repository
6. Enter the commit hash
7. Click "Validate & Rebase"

LevelUp will:
- Apply your changes to a test environment
- Compile both original and modified code to assembly
- Compare the assembly output
- If validation passes, rebase changes to the work branch
- Update the UI with the result

### Monitoring Progress

The "Queue Status" tab shows:
- Current queue size
- Processing status
- Completed validations
- Failed validations

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

## Testing with 7zip

To test LevelUp with your 7zip repository:

1. Add the 7zip repository in the UI:
   - Name: "7zip"
   - URL: Your 7zip repo URL
   - Work Branch: "levelup-work"

2. Make a simple change to a CPP file (e.g., remove an `inline` keyword)

3. Commit and submit through CppDev tools

4. Watch the validation process

5. Check the work branch for successfully validated changes

## API Endpoints

### Repository Management
- `GET /api/repos` - List repositories
- `POST /api/repos` - Add repository

### Mod Management
- `POST /api/mods` - Submit modification
- `GET /api/mods/<id>/status` - Get mod status

### Available Resources
- `GET /api/available/mods` - List available mod types
- `GET /api/available/validators` - List available validator types
- `GET /api/available/compilers` - List available compiler types

### Queue Management
- `GET /api/queue/status` - Get queue status

### CppDev Tools
- `POST /api/cppdev/commit` - Submit cppDev commit

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
