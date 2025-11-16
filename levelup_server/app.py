"""
LevelUp Server - Modernize legacy C++ code with zero regression risk
"""

import os
import json
import asyncio
import threading
import queue
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
import uuid
from typing import Dict

from levelup_core.utils.compiler_factory import CompilerFactory
from levelup_core.validators.validator_factory import ValidatorFactory
from levelup_core.mods.mod_factory import ModFactory
from levelup_core.result import Result, ResultStatus
from levelup_core.repo import Repo
from levelup_core.mod_request import ModRequest, ModSourceType
from levelup_core.mod_processor import ModProcessor

app = Flask(__name__)
app.secret_key = 'levelup-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global queue for async processing
mod_queue = queue.Queue()
results: Dict[str, Result] = {}  # Store results by mod_id

# Configuration
CONFIG = {
    'workspace': Path('workspace'),
    'repos': Path('workspace/repos'),
    'temp': Path('workspace/temp'),
    'msvc_path': os.environ.get('MSVC_PATH', 'cl.exe'),
    'git_path': os.environ.get('GIT_PATH', 'git'),
}

# Ensure workspace directories exist
for path in CONFIG.values():
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)

def mod_worker():
    """Worker thread for processing mods"""
    processor = ModProcessor(
        msvc_path=CONFIG['msvc_path'],
        repos_path=CONFIG['repos'],
        temp_path=CONFIG['temp'],
        git_path=CONFIG['git_path']
    )
    
    while True:
        try:
            mod_request = mod_queue.get(timeout=1)

            # Set initial processing status
            results[mod_request.id] = Result(
                status=ResultStatus.PROCESSING,
                message='Starting mod processing...'
            )

            # Process mod and get result
            result = processor.process_mod(mod_request)

            # Update results with returned result
            results[mod_request.id] = result

            mod_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in mod worker: {e}")

# Start worker thread
worker_thread = threading.Thread(target=mod_worker, daemon=True)
worker_thread.start()

@app.route('/')
def index():
    """Main UI page"""
    return render_template('index.html')

@app.route('/api/repos', methods=['GET', 'POST', 'DELETE'])
def manage_repos():
    """Manage repository configurations"""
    if request.method == 'POST':
        data = request.json
        # Extract repo name from URL
        repo_name = Repo.get_repo_name(data['url'])

        repo_config = {
            'id': str(uuid.uuid4()),
            'name': repo_name,
            'url': data['url'],
            'work_branch': data['work_branch'],
            'post_checkout': data.get('post_checkout', ''),
            'build_command': data.get('build_command', ''),
            'single_tu_command': data.get('single_tu_command', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store repo configuration
        config_file = CONFIG['workspace'] / 'repos.json'
        configs = []
        if config_file.exists():
            with open(config_file, 'r') as f:
                configs = json.load(f)
        configs.append(repo_config)
        
        with open(config_file, 'w') as f:
            json.dump(configs, f, indent=2)
        
        return jsonify(repo_config)
    
    else:
        config_file = CONFIG['workspace'] / 'repos.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify([])

@app.route('/api/repos/<repo_id>', methods=['DELETE'])
def delete_repo(repo_id):
    """Delete a repository configuration"""
    config_file = CONFIG['workspace'] / 'repos.json'
    if config_file.exists():
        with open(config_file, 'r') as f:
            configs = json.load(f)

        # Filter out the repo with matching ID
        configs = [repo for repo in configs if repo['id'] != repo_id]

        with open(config_file, 'w') as f:
            json.dump(configs, f, indent=2)

        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/mods', methods=['POST'])
def submit_mod():
    """Submit a new mod for processing"""
    data = request.json
    mod_id = str(uuid.uuid4())

    # Determine source type and create appropriate objects
    type_str = data['type']
    if type_str == 'builtin':
        source_type = ModSourceType.BUILTIN
        # Create mod instance from string ID (only place string ID is used!)
        mod_type_id = data['mod_type']
        mod_instance = ModFactory.from_id(mod_type_id)
        commit_hash = None
    elif type_str == 'commit':
        source_type = ModSourceType.COMMIT
        mod_instance = None
        commit_hash = data['commit_hash']
    else:
        return jsonify({'error': f'Invalid type: {type_str}'}), 400

    # Create type-safe ModRequest
    mod_request = ModRequest(
        id=mod_id,
        repo_url=data['repo_url'],
        repo_name=data['repo_name'],
        work_branch=data['work_branch'],
        source_type=source_type,
        description=data['description'],
        mod_instance=mod_instance,
        commit_hash=commit_hash,
        allow_reorder=data.get('allow_reorder', False),
        timestamp=datetime.now().isoformat()
    )

    # Initialize result
    results[mod_id] = Result(
        status=ResultStatus.QUEUED,
        message='Mod queued for processing'
    )

    # Queue the ModRequest object (not dict!)
    mod_queue.put(mod_request)

    # Return JSON response with string IDs for frontend
    response_data = {
        'id': mod_id,
        'repo_name': data['repo_name'],
        'repo_url': data['repo_url'],
        'work_branch': data['work_branch'],
        'type': type_str,
        'description': data['description'],
        'validators': data.get('validators', ['asm']),
        'allow_reorder': data.get('allow_reorder', False),
        'timestamp': mod_request.timestamp
    }
    if type_str == 'builtin':
        response_data['mod_type'] = data['mod_type']
    elif type_str == 'commit':
        response_data['commit_hash'] = commit_hash

    return jsonify(response_data)

@app.route('/api/mods/<mod_id>/status')
def get_mod_status(mod_id):
    """Get the status of a specific mod"""
    if mod_id in results:
        return jsonify(results[mod_id].to_dict())
    return jsonify({'status': 'not_found'}), 404

@app.route('/api/queue/status')
def get_queue_status():
    """Get overall queue status"""
    return jsonify({
        'queue_size': mod_queue.qsize(),
        'results': {k: v.to_dict() for k, v in results.items()},
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/available/mods')
def get_available_mods():
    """Get list of available mods"""
    return jsonify(ModFactory.get_available_mods())

@app.route('/api/available/validators')
def get_available_validators():
    """Get list of available validators"""
    return jsonify(ValidatorFactory.get_available_validators())

@app.route('/api/available/compilers')
def get_available_compilers():
    """Get list of available compilers"""
    return jsonify(CompilerFactory.get_available_compilers())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
