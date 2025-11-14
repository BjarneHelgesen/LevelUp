"""
LevelUp Entry Point - Start the LevelUp server
Run with: python run.py
"""

import sys
from pathlib import Path

# Add project root to Python path to enable imports
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the Flask app
from levelup_server.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
