# LevelUp

## Objective
The objective of LevelUp is to use update legacy C++ code to more modern code, with zero regressions. 
The estimate is that 80% of the code can be updated, and that the updates within that part of the code reaches 80% of the desired moderization. 
The reason for the expected shortfall is that some of the potential changes will have regression risks that have not been mitigated.

## Use cases
Modernizatition could involve: 
* Replace MS specific syntax by standards compliant syntax (where possible). This is a required step
* Make changes required by new C++ standards (e.g. don't allow modifiction of a temporary)
* Make the code safer against accidental edits (e.g. const correctness, override, etc)
* Use modern OOP constructs (e.g. range based for, exceptions, RAAI, smart pointers, standard containers, string classes, etc)
* Use a better architecture (i.e. transition code from an old style interal api to a new style)
* Update libraries to more modern versions. This will only have limited support

## Use
LevelUp Server is a Python Flask server that gets instruction (called Mods)  via a web interface. Skilled C++ developers, called cppDevs, will send thee Mods to LevelUp.
Both cppDevs and LevelUp Server have access to the git repo for the legacy C++. 
LevelUp Server should be able to handle at least 2-3 cppDevs working on the same repo or different repos at the same time. 
Mods to LevelUp may be time-consuming, so LevelUp will queue up Mods  and execute asyncronously. 

## Methodolgy 
LevelUp can use a variety of tools to make changes to code, including custom code, LLMS and Clang-Tidy fixups.  
Mods will be introduced as small changes on a separate branch. Each Mod has to be validated (or regression tested/tested/inspected/approved) which is to declare it regression free,
No Mods will be merged to the main branch without validation.
Each Mod will have a list of required validators to be run before merge. 
Regression-free does not mean the exact same behaviour:  
* Delaying a delete operation by a fixed number of cycles is okay.
* If the old code was leaking memory on error, the updated code is allowed delete it.
* If the old code did not print out usage to stdout, the new code can add it if deemed useful
* Slight performance regressions are allowed
* All performance improvements are allowed 

## Validators
The initial list of validators is
* Compiling the source with full optimization gives the exact same binary
* The AST diff is as expected
* Source diff is as expected (e.g. the change to remove inline functions gives a diff that only contains removal of inline)
* When splitting CPP files into one file per function, including all these CPP into a CPP using #include will produce the same binary
* Unit testing with all permutations of input data gives the same result, including exceptions, crashes, undefined behaviour, etc.
* Human validator. In obvious cases, this can be done the the cppDev. In non obvious cases customers will  have to be the validator, as there is risk involved

LLMS are not validators, but may be added as extra checks.

## Tools 
* Microsoft macro tool.
  * This will replace Microsoft specific code with macros. Example:
  * The macro definition will be different for other compilers, so macro LEVELUP__FORCEINLINE will be defined as  __forceinline for microsoft compilers and inline for other standars-compliant compilers.
  * Normally, Microsoft macros will be reintroduced to compile with MSVC.
* MSVC for compiling MS code. This will be used to verify that compiling succeeds and no new warnings are introduced
* Clang for general compile. All projects should compile with Clang after standardization
* CppDevs can make their own Mods and run them through validators
* Warning diff to extract which warnings are added or removed.
* Clang-Tidy fixups
* Splitting a cpp file into separate files for each method
* LLMs

## Setup
CppDevs need to provide git repo location, post-checkout commmands (if any),  build command for building the whole project, build command for single translation unit, and work branch name
If there is a conflict between concurrent Mods, the cppDev needs to decide whether he will do a manual merge or re-run all subsequent Mods. 

## Implementation
The main priority is that no upgraded code will have regressions. 
All code, both Flask code (Python) and web code (HTML/JS/CSS) will be hosted in a single repo. 
Flask will serve Web page and take the input from the cppDevs. It will not be a SPA. 
We may demand tools to be installed on the cppDev workstations, such as diff tools, git, etc. but all LevelUp code should be run or served from Flask.
Code simplicity and correctness will be prioritzed over UI beauty and covering special cases, as long as we don't allow regressions in upgraded code.   
We allow compute-intensive Mods, and many Mods, if that gives better end results than fewer and less compute-intensive Mods. 
