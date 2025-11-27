"""
LevelUp Entry Point - Start the LevelUp server
Run with: python run.py
"""

from core.compilers.compiler_factory import set_compiler
from server.app import app

# Configure compiler (default: clang)
# Change to 'msvc' if you want to use MSVC compiler instead
set_compiler('msvc')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
