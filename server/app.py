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

from core.compilers.compiler_factory import CompilerFactory
from core.validators.validator_factory import ValidatorFactory
from core.mods.mod_factory import ModFactory
from core.result import Result, ResultStatus
from core.repo import Repo
from core.mod_request import ModRequest, ModSourceType
from core.mod_processor import ModProcessor
from core.doxygen import DoxygenRunner
from core import logger

# Track Doxygen generation status per repo
doxygen_status: Dict[str, dict] = {}

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
    'git_path': os.environ.get('GIT_PATH', 'git'),
    'doxygen_path': os.environ.get('DOXYGEN_PATH', 'doxygen'),
}

# Ensure workspace directories exist
for path in CONFIG.values():
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)

def mod_worker():
    """Worker thread for processing mods"""
    logger.info("mod_worker starting")
    print("=== mod_worker starting ===")
    try:
        processor = ModProcessor(
            repos_path=CONFIG['repos'],
            git_path=CONFIG['git_path']
        )
        logger.info("ModProcessor initialized successfully")
        print("=== ModProcessor initialized ===")
    except Exception as e:
        logger.exception(f"Error initializing ModProcessor: {e}")
        print(f"=== Error initializing ModProcessor: {e} ===")
        import traceback
        traceback.print_exc()
        return

    while True:
        try:
            mod_request = mod_queue.get(timeout=1)
            logger.info(f"Dequeued mod for processing: {mod_request.id}")
            print(f"=== Processing mod: {mod_request.id} ===")

            # Set initial processing status
            results[mod_request.id] = Result(
                status=ResultStatus.PROCESSING,
                message='Starting mod processing...'
            )

            # Process mod and get result
            result = processor.process_mod(mod_request)
            logger.info(f"Mod {mod_request.id} result: {result.status} - {result.message}")
            print(f"=== Mod result: {result.status} - {result.message} ===")

            # Update results with returned result
            results[mod_request.id] = result

            mod_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.exception(f"Error in mod worker: {e}")
            print(f"Error in mod worker: {e}")
            import traceback
            traceback.print_exc()

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

        # Start Doxygen generation in background thread
        thread = threading.Thread(
            target=generate_doxygen_for_repo,
            args=(repo_config,),
            daemon=True
        )
        thread.start()
        logger.info(f"Started Doxygen generation for new repo: {repo_name}")

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

def generate_doxygen_for_repo(repo_config: dict):
    """Background task to generate Doxygen data for a repository."""
    repo_id = repo_config['id']
    repo_name = repo_config['name']

    doxygen_status[repo_id] = {
        'status': 'running',
        'message': f'Generating Doxygen data for {repo_name}...'
    }

    try:
        # Check if Doxygen is available
        runner = DoxygenRunner(doxygen_path=CONFIG['doxygen_path'])
        if not runner.is_available():
            doxygen_status[repo_id] = {
                'status': 'skipped',
                'message': 'Doxygen not found on system. Function dependency data will not be available.'
            }
            logger.warning(f"Doxygen not available, skipping for repo {repo_name}")
            return

        # Create Repo instance and ensure it's cloned
        repo = Repo(
            url=repo_config['url'],
            repos_folder=CONFIG['repos'],
            git_path=CONFIG['git_path'],
            post_checkout=repo_config.get('post_checkout', '')
        )
        repo.ensure_cloned()

        # Generate Doxygen
        xml_dir = repo.generate_doxygen(doxygen_path=CONFIG['doxygen_path'])

        doxygen_status[repo_id] = {
            'status': 'completed',
            'message': f'Doxygen data generated successfully',
            'xml_dir': str(xml_dir)
        }
        logger.info(f"Doxygen generation completed for {repo_name}")

    except Exception as e:
        doxygen_status[repo_id] = {
            'status': 'failed',
            'message': f'Doxygen generation failed: {str(e)}'
        }
        logger.exception(f"Doxygen generation failed for {repo_name}: {e}")


@app.route('/api/repos/<repo_id>/doxygen', methods=['POST'])
def regenerate_doxygen(repo_id):
    """Regenerate Doxygen data for a repository."""
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    repo_config = next((r for r in configs if r['id'] == repo_id), None)
    if repo_config is None:
        return jsonify({'error': 'Repository not found'}), 404

    # Start Doxygen generation in background thread
    thread = threading.Thread(
        target=generate_doxygen_for_repo,
        args=(repo_config,),
        daemon=True
    )
    thread.start()

    return jsonify({
        'status': 'started',
        'message': f'Doxygen generation started for {repo_config["name"]}'
    })


@app.route('/api/repos/<repo_id>/doxygen', methods=['GET'])
def get_doxygen_status(repo_id):
    """Get Doxygen generation status for a repository."""
    if repo_id in doxygen_status:
        return jsonify(doxygen_status[repo_id])

    # Check if Doxygen data already exists
    config_file = CONFIG['workspace'] / 'repos.json'
    if config_file.exists():
        with open(config_file, 'r') as f:
            configs = json.load(f)

        repo_config = next((r for r in configs if r['id'] == repo_id), None)
        if repo_config:
            repo = Repo(
                url=repo_config['url'],
                repos_folder=CONFIG['repos'],
                git_path=CONFIG['git_path']
            )
            if repo.has_doxygen_data():
                return jsonify({
                    'status': 'completed',
                    'message': 'Doxygen data available'
                })

    return jsonify({
        'status': 'not_generated',
        'message': 'Doxygen data has not been generated for this repository'
    })


@app.route('/api/repos/<repo_id>', methods=['PUT'])
def update_repo(repo_id):
    """Update a repository configuration"""
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    # Find and update the repo
    data = request.json
    updated = False
    for repo in configs:
        if repo['id'] == repo_id:
            # Update repo name from URL if URL changed
            if 'url' in data:
                repo['url'] = data['url']
                repo['name'] = Repo.get_repo_name(data['url'])
            if 'post_checkout' in data:
                repo['post_checkout'] = data['post_checkout']
            if 'build_command' in data:
                repo['build_command'] = data['build_command']
            if 'single_tu_command' in data:
                repo['single_tu_command'] = data['single_tu_command']
            updated = True
            updated_repo = repo
            break

    if not updated:
        return jsonify({'error': 'Repository not found'}), 404

    with open(config_file, 'w') as f:
        json.dump(configs, f, indent=2)

    return jsonify(updated_repo)

@app.route('/api/mods', methods=['POST'])
def submit_mod():
    """Submit a new mod for processing"""
    logger.info("submit_mod called")
    print("=== submit_mod called ===")
    data = request.json
    logger.debug(f"Received mod submission: {data}")
    print(f"Received data: {data}")
    mod_id = str(uuid.uuid4())
    logger.info(f"Generated mod_id: {mod_id}")

    # Determine source type and create appropriate objects
    type_str = data['type']
    mod_type_id = data.get('mod_type')

    # Check if this is a commit validation
    if type_str == 'commit':
        source_type = ModSourceType.COMMIT
        mod_instance = None  # Not needed for COMMIT type
        commit_hash = data.get('commit_hash', 'HEAD')
    elif type_str == 'builtin':
        source_type = ModSourceType.BUILTIN
        # Create mod instance from string ID (only place string ID is used!)
        mod_instance = ModFactory.from_id(mod_type_id)
        commit_hash = None
    else:
        return jsonify({'error': f'Invalid type: {type_str}'}), 400

    # Create type-safe ModRequest
    mod_request = ModRequest(
        id=mod_id,
        repo_url=data['repo_url'],
        source_type=source_type,
        description=data['description'],
        mod_instance=mod_instance,
        commit_hash=commit_hash
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
        'type': type_str,
        'description': data['description'],
        'validators': data.get('validators', ['asm'])
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
        'results': {k: v.to_dict() for k, v in results.items()}
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


# ==================== Function Dependency API ====================

@app.route('/api/repos/<repo_id>/functions', methods=['GET'])
def get_repo_functions(repo_id):
    """
    Get function information for a repository.

    Query parameters:
        - name: Filter by function name
        - file: Filter by file path
    """
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    repo_config = next((r for r in configs if r['id'] == repo_id), None)
    if repo_config is None:
        return jsonify({'error': 'Repository not found'}), 404

    repo = Repo(
        url=repo_config['url'],
        repos_folder=CONFIG['repos'],
        git_path=CONFIG['git_path']
    )

    if not repo.has_doxygen_data():
        return jsonify({
            'error': 'Doxygen data not available',
            'message': 'Run POST /api/repos/{repo_id}/doxygen to generate'
        }), 404

    parser = repo.get_doxygen_parser()
    if parser is None:
        return jsonify({'error': 'Failed to load Doxygen data'}), 500

    # Get query parameters
    name_filter = request.args.get('name')
    file_filter = request.args.get('file')

    if name_filter:
        functions = parser.get_functions_by_name(name_filter)
    elif file_filter:
        functions = parser.get_functions_in_file(file_filter)
    else:
        functions = parser.get_all_functions()

    # Convert to JSON-serializable format
    result = []
    for func in functions:
        result.append({
            'name': func.name,
            'qualified_name': func.qualified_name,
            'file_path': func.file_path,
            'line_number': func.line_number,
            'return_type': func.return_type,
            'parameters': [{'type': t, 'name': n} for t, n in func.parameters],
            'signature': func.get_signature(),
            'is_member': func.is_member,
            'class_name': func.class_name,
            'calls_count': len(func.calls),
            'called_by_count': len(func.called_by),
            'doxygen_id': func.doxygen_id
        })

    return jsonify({
        'count': len(result),
        'functions': result
    })


@app.route('/api/repos/<repo_id>/functions/<path:doxygen_id>/callers', methods=['GET'])
def get_function_callers(repo_id, doxygen_id):
    """Get all functions that call a specific function."""
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    repo_config = next((r for r in configs if r['id'] == repo_id), None)
    if repo_config is None:
        return jsonify({'error': 'Repository not found'}), 404

    repo = Repo(
        url=repo_config['url'],
        repos_folder=CONFIG['repos'],
        git_path=CONFIG['git_path']
    )

    parser = repo.get_doxygen_parser()
    if parser is None:
        return jsonify({'error': 'Doxygen data not available'}), 404

    func = parser.get_function_by_id(doxygen_id)
    if func is None:
        return jsonify({'error': 'Function not found'}), 404

    callers = parser.get_callers(func)
    result = [{
        'name': f.name,
        'qualified_name': f.qualified_name,
        'file_path': f.file_path,
        'line_number': f.line_number,
        'doxygen_id': f.doxygen_id
    } for f in callers]

    return jsonify({
        'function': func.qualified_name,
        'callers': result
    })


@app.route('/api/repos/<repo_id>/functions/<path:doxygen_id>/callees', methods=['GET'])
def get_function_callees(repo_id, doxygen_id):
    """Get all functions called by a specific function."""
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    repo_config = next((r for r in configs if r['id'] == repo_id), None)
    if repo_config is None:
        return jsonify({'error': 'Repository not found'}), 404

    repo = Repo(
        url=repo_config['url'],
        repos_folder=CONFIG['repos'],
        git_path=CONFIG['git_path']
    )

    parser = repo.get_doxygen_parser()
    if parser is None:
        return jsonify({'error': 'Doxygen data not available'}), 404

    func = parser.get_function_by_id(doxygen_id)
    if func is None:
        return jsonify({'error': 'Function not found'}), 404

    callees = parser.get_callees(func)
    result = [{
        'name': f.name,
        'qualified_name': f.qualified_name,
        'file_path': f.file_path,
        'line_number': f.line_number,
        'doxygen_id': f.doxygen_id
    } for f in callees]

    return jsonify({
        'function': func.qualified_name,
        'callees': result
    })


@app.route('/api/repos/<repo_id>/files', methods=['GET'])
def get_repo_files(repo_id):
    """Get list of all files with parsed functions in a repository."""
    config_file = CONFIG['workspace'] / 'repos.json'
    if not config_file.exists():
        return jsonify({'error': 'No repositories found'}), 404

    with open(config_file, 'r') as f:
        configs = json.load(f)

    repo_config = next((r for r in configs if r['id'] == repo_id), None)
    if repo_config is None:
        return jsonify({'error': 'Repository not found'}), 404

    repo = Repo(
        url=repo_config['url'],
        repos_folder=CONFIG['repos'],
        git_path=CONFIG['git_path']
    )

    parser = repo.get_doxygen_parser()
    if parser is None:
        return jsonify({'error': 'Doxygen data not available'}), 404

    files = parser.get_all_files()
    return jsonify({
        'count': len(files),
        'files': files
    })


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
