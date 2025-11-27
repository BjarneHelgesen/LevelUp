# LevelUp

LevelUp is local server that safely and efficiently modernizes code in legacy C/C++ repos without functional changes 


## Objective
* Modernizations are guaranteed - proven - to be regression free
* It should be possible to do all modernizations on-prem. (i.e. no source code or other data is transmitted)
* 80% automation (i.e. the human effort is 20% compared to upgrading the code manually)
* 80% of the codebase is coded in a way that LevelUp can upgrade it
* The upgraded code is 80% modern, 20% legacy
* Improving architecture, behaviour, user experience, performance, etc. are not objectives. 

## Use cases
Modernization could involve:
* Replace MS specific syntax by standards compliant syntax (where possible). This step enables more tools and updates
* Make changes required by new C++ standards (e.g. don't allow modification of a temporary)
* Make the code safer against accidental edits (e.g. const correctness, override, etc)
* Use modern OOP constructs (e.g. range-based for, exceptions, RAAI, smart pointers, standard containers, string classes, etc)
* Use a better architecture (e.g. transition the codebase from one internal api to another)
* Update libraries to more modern versions. This will only have limited support
* Remove unwanted undefined behaviour
* Fix/remove warnings

## Installation

### Server Prerequisites
- Python 3.8+
- Git
- Supported compiler MSVC (Visual Studio C++ Compiler) and/or Clang
- Windows OS (initial version, cross-platform support planned)
- Doxygen

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

LevelUp Server is a Python Flask server that gets instruction (called Mods) via a web interface. Skilled C++ developers, called cppDevs, will select the Mods that LevelUp will perform.
Both cppDevs and LevelUp Server have access to the git repo for the legacy C++.
LevelUp Server should be able to handle at least 2-3 cppDevs working on the same repo or different repos at the same time.
Mods to LevelUp may be time-consuming, so LevelUp will queue up Mods and execute asyncronously.

### Setting Up a Repository

1. Navigate to the "Repositories" screen
2. Click "Add Repository" and enter:
   - URL: Git repository URL
   - Post-Checkout Commands: Optional commands to run after checkout
   - Build Command: Command to build the entire project
   - Single TU Command: Command to compile a single translation unit

3. Click "Add Repository"

Note: Repository name is automatically extracted from the URL. Work branch is hardcoded to "levelup-work".

### Applying Mods

1. Select a repository from the Repositories screen
2. In the Mods screen, select a mod type:
   - Remove Inline Keywords
   - Add Override Keywords
   - Replace MS-Specific Syntax
3. Enter a description
4. Click "Submit"

LevelUp will:
- Apply your changes to a test environment
- Compile both original and modified code
- If validation of the object files passes, commit and push changes to the work branch
- Update the UI with the result


### Monitoring Progress

Poll the queue status endpoint or watch the UI for:
- Current queue size
- Processing status
- Completed validations (SUCCESS, PARTIAL, FAILED)
- Error conditions

Results are updated in real-time.

## Validation Process

### Methodology
LevelUp can use a variety of tools to make changes to code, including custom code, LLMS and Clang-Tidy fixups.
Mods will be introduced as small changes on a separate branch. Each Mod has to be validated (or regression tested/tested/inspected/approved) which is to declare it regression free,
No Mods will be merged to the main branch without validation.
Each Mod will have a list of required validators to be run before merge.
Regression-free does not mean the exact same behaviour. There can be differences in performance or memory use and still be considered regression free:
* Delaying a delete operation by a fixed number of cycles is okay.
* If the old code was leaking memory on error, the updated code is allowed delete it.
* If the old code did not print out usage to stdout, the new code can add it if deemed useful
* Slight performance regressions are allowed
* All performance improvements are allowed

### ASM Validation
The current validator ensures zero regression by comparing the builds from two versions of the source code. both builds have the same optimization settings. Subsequent builds may use different optimization settings and other compiler options. 


### Acceptable Differences
The validator allows:
- Function reordering
- NOPs and alignment changes

### Result Statuses
- **SUCCESS**: All files passed validation
- **PARTIAL**: Some files passed, some failed
- **FAILED**: No files passed validation
- **ERROR**: An error occurred during processing

## API Endpoints

For detailed API documentation, see [APIs.md](APIs.md).

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

## Validators
The initial list of validators is
* Compiling with full optimization gives the exact same Assembly or intermediary representation  
* The AST diff is as expected 
* Source diff is as expected (e.g. the change to remove inline functions gives a diff that only contains removal of inline)
* When splitting CPP files into one file per function, including all these CPP into a CPP using #include will produce the same binary
* Unit testing with all permutations of input data gives the same result, including exceptions, crashes, undefined behaviour, etc.
* Human validator. In obvious cases, this can be done the the cppDev. In non obvious cases customers will  have to be the validator, as there is risk involved
* Unit tests with all dependencies as logging stubs give the same result

More validators may be added later. 
LLMS are not validators, but may be added as extra checks.

## Refactorings
The Mods are using a series of specific refactorings, where each refactoring result in an atomic change that can be validated. There are many different Refactorings

## Tools 
* MSVC for compiling MS code. This will be used to verify that compiling succeeds and no new warnings are introduced
* Clang for general compile. All projects should compile with Clang after standardization
* Doxygen to parse symbols
* Clang-Tidy fixups
* TODO: CppDevs can make their own Mods (i.e. git commits) and run them through validators
* TODO: Warning diff to extract which warnings are added or removed.
* TODO: Local LLM
* TODO: Clang plugins that work on the AST

## Web UI
The web interface provides:
- Repository management (add, configure repositories)
- Mod submission and queue management
- Real-time status updates for processing mods
- Validation results display (SUCCESS, PARTIAL, FAILED, ERROR)

The UI allows cppDevs to:
- Configure repository settings (URL, post-checkout commands, build commands)
- Select and submit built-in mods (Remove Inline, Add Override, etc.)
- Submit cppDev commits for validation
- Monitor progress and view validation outcomes
- Work on multiple repositories concurrently

Work branch is hardcoded to "levelup-work" and is automatically created from main. Customer reviews changes on this branch before merging to main. 

## Implementation
The main priority is that upgraded C++ code will have no regressions.
All code, both Flask code (Python) and web code (HTML/JS/CSS) are hosted in this repo.
Flask serves the web page and takes input from cppDevs. It is not a SPA.
We may require tools to be installed on cppDev workstations, such as diff tools, git, etc., but all LevelUp code runs on the Flask server.
Code simplicity and correctness is prioritized over UI beauty and covering special cases, unless the special case has been found to be important.
The system applies code transformations called "Mods" to legacy C++ codebases and validates changes using assembly comparison and other validators.
Mods generate atomic refactorings; each refactoring modifies files in-place and creates a git commit that is validated before being kept or rolled back.
We prefer compute-intensive Mods, and many validations, if that gives a better end result.
LevelUp server runs on Windows initially, but is written using cross-platform syntax.
The architecture allows adding:
* New compilers
* New refactorings
* New validators
* New mods

## Future enhancements
* Mod, Refactor and validate against multiple builds (multiple repos, multiple branches, multiple platforms, multiple compilers, multiple compiler flags)
  * multi-repo Mods
  * multi-platform targets
  * multiple sets of #defines
  * libraries with several clients
* GCC extensions


