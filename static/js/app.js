// LevelUp JavaScript Application

const API_BASE = '/api';
let currentRepos = [];
let selectedRepo = null;
let queueUpdateInterval = null;

// Tab Navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();

        // Check if link is disabled
        if (link.classList.contains('disabled')) {
            return;
        }

        const target = link.getAttribute('href').substring(1);

        // Don't allow switching away from repos tab if no repo selected
        if (!selectedRepo && target !== 'repos') {
            showNotification('Please select a repository first', 'warning');
            return;
        }

        showTab(target);

        // Update active nav
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
    });
});

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');
    
    // Load tab-specific data
    if (tabId === 'repos') {
        loadRepositories();
    } else if (tabId === 'queue') {
        loadQueueStatus();
        startQueueUpdates();
    } else {
        stopQueueUpdates();
    }
}

// Repository Management
async function loadRepositories() {
    try {
        const response = await fetch(`${API_BASE}/repos`);
        const repos = await response.json();
        currentRepos = repos;
        displayRepositories(repos);
        updateRepoSelects(repos);

        // Auto-select first repo if none selected
        if (repos.length > 0 && !selectedRepo) {
            selectRepo(repos[0]);
        }

        // Update tab states
        updateTabStates();
    } catch (error) {
        console.error('Error loading repositories:', error);
    }
}

function selectRepo(repo) {
    selectedRepo = repo;

    // Update UI to show selection
    document.querySelectorAll('.repo-item').forEach(item => {
        item.classList.remove('selected');
    });

    const selectedElement = document.querySelector(`[data-repo-id="${repo.id}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }

    // Update tab states
    updateTabStates();
}

function updateTabStates() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        const target = link.getAttribute('href').substring(1);
        if (target !== 'repos') {
            if (selectedRepo) {
                link.classList.remove('disabled');
            } else {
                link.classList.add('disabled');
            }
        }
    });
}

function displayRepositories(repos) {
    const container = document.getElementById('repo-list');
    container.innerHTML = '';

    if (repos.length === 0) {
        container.innerHTML = '<p>No repositories configured yet.</p>';
        selectedRepo = null;
        updateTabStates();
        return;
    }

    repos.forEach(repo => {
        const repoElement = document.createElement('div');
        repoElement.className = 'repo-item';
        repoElement.dataset.repoId = repo.id;

        // Check if this is the selected repo
        if (selectedRepo && selectedRepo.id === repo.id) {
            repoElement.classList.add('selected');
        }

        repoElement.innerHTML = `
            <div class="repo-info">
                <h4>${repo.name}</h4>
                <p>URL: ${repo.url}</p>
                <p>Work Branch: ${repo.work_branch}</p>
            </div>
            <div class="repo-actions">
                <button class="delete-repo-btn" onclick="event.stopPropagation(); removeRepo('${repo.id}')" title="Remove repository"></button>
            </div>
        `;

        // Make repo item clickable
        repoElement.addEventListener('click', () => {
            selectRepo(repo);
        });

        container.appendChild(repoElement);
    });
}

function updateRepoSelects(repos) {
    const selects = ['mod-repo', 'cppdev-repo'];
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            // Save current selection
            const currentValue = select.value;
            
            // Clear and rebuild options
            select.innerHTML = '<option value="">Select a repository...</option>';
            repos.forEach(repo => {
                const option = document.createElement('option');
                option.value = repo.name;
                option.textContent = repo.name;
                option.dataset.url = repo.url;
                option.dataset.branch = repo.work_branch;
                select.appendChild(option);
            });
            
            // Restore selection if possible
            if (currentValue) {
                select.value = currentValue;
            }
        }
    });
}

// Repository Form
document.getElementById('repo-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch(`${API_BASE}/repos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const repo = await response.json();
            showNotification('Repository added successfully', 'success');
            e.target.reset();
            loadRepositories();
        } else {
            showNotification('Failed to add repository', 'error');
        }
    } catch (error) {
        console.error('Error adding repository:', error);
        showNotification('Error adding repository', 'error');
    }
});

// Mod Management
document.getElementById('mod-type').addEventListener('change', (e) => {
    const type = e.target.value;
    document.querySelectorAll('.mod-options').forEach(opt => {
        opt.style.display = 'none';
    });
    
    if (type === 'commit') {
        document.getElementById('commit-options').style.display = 'block';
    } else if (type === 'patch') {
        document.getElementById('patch-options').style.display = 'block';
    } else if (type === 'builtin') {
        document.getElementById('builtin-options').style.display = 'block';
    }
});

document.getElementById('mod-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    // Get repository details
    const repoSelect = document.getElementById('mod-repo');
    const selectedOption = repoSelect.options[repoSelect.selectedIndex];
    
    const data = {
        repo_name: formData.get('repo_name'),
        repo_url: selectedOption.dataset.url,
        work_branch: selectedOption.dataset.branch,
        type: formData.get('type'),
        description: formData.get('description'),
        validators: Array.from(formData.getAll('validators')),
        allow_reorder: formData.has('allow_reorder')
    };
    
    // Add type-specific data
    if (data.type === 'commit') {
        data.commit_hash = formData.get('commit_hash');
    } else if (data.type === 'builtin') {
        data.mod_type = formData.get('builtin_mod');
    }
    
    try {
        let response;
        if (data.type === 'patch') {
            // Handle file upload
            const patchFormData = new FormData();
            Object.keys(data).forEach(key => {
                patchFormData.append(key, data[key]);
            });
            patchFormData.append('patch_file', document.getElementById('patch-file').files[0]);
            
            response = await fetch(`${API_BASE}/mods`, {
                method: 'POST',
                body: patchFormData
            });
        } else {
            response = await fetch(`${API_BASE}/mods`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
        }
        
        if (response.ok) {
            const mod = await response.json();
            showNotification('Mod submitted successfully', 'success');
            e.target.reset();
            trackModStatus(mod.id);
        } else {
            showNotification('Failed to submit mod', 'error');
        }
    } catch (error) {
        console.error('Error submitting mod:', error);
        showNotification('Error submitting mod', 'error');
    }
});

// CppDev Tools
document.getElementById('cppdev-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    // Get repository details
    const repoSelect = document.getElementById('cppdev-repo');
    const selectedOption = repoSelect.options[repoSelect.selectedIndex];
    
    const data = {
        repo_name: formData.get('repo_name'),
        repo_url: selectedOption.dataset.url,
        work_branch: selectedOption.dataset.branch,
        commit_hash: formData.get('commit_hash'),
        message: formData.get('message')
    };
    
    try {
        const response = await fetch(`${API_BASE}/cppdev/commit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const mod = await response.json();
            showNotification('Commit submitted for validation', 'success');
            e.target.reset();
            trackCppDevResult(mod.id);
        } else {
            showNotification('Failed to submit commit', 'error');
        }
    } catch (error) {
        console.error('Error submitting commit:', error);
        showNotification('Error submitting commit', 'error');
    }
});

// Queue Status
async function loadQueueStatus() {
    try {
        const response = await fetch(`${API_BASE}/queue/status`);
        const status = await response.json();
        displayQueueStatus(status);
    } catch (error) {
        console.error('Error loading queue status:', error);
    }
}

function displayQueueStatus(status) {
    // Update stats
    document.getElementById('queue-size').textContent = status.queue_size;
    
    // Count statuses
    let processing = 0;
    let completed = 0;
    let failed = 0;
    
    Object.values(status.results).forEach(result => {
        if (result.status === 'processing') processing++;
        else if (result.status === 'success') completed++;
        else if (result.status === 'failed') failed++;
    });
    
    document.getElementById('processing-count').textContent = processing;
    document.getElementById('completed-count').textContent = completed;
    document.getElementById('failed-count').textContent = failed;
    
    // Display queue details
    const container = document.getElementById('queue-details');
    container.innerHTML = '';
    
    Object.entries(status.results).forEach(([id, result]) => {
        const item = createResultItem(id, result);
        container.appendChild(item);
    });
}

function createResultItem(id, result) {
    const item = document.createElement('div');
    item.className = `result-item ${result.status}`;
    
    const statusClass = `status-${result.status}`;
    
    item.innerHTML = `
        <div class="result-header">
            <div>
                <strong>Mod ID:</strong> ${id}
                <br>
                <small>${result.timestamp}</small>
            </div>
            <span class="result-status ${statusClass}">${result.status}</span>
        </div>
        <div class="result-message">
            ${result.message}
        </div>
        ${result.validation_results ? `
            <div class="validation-details">
                <strong>Validation Results:</strong>
                <ul>
                    ${result.validation_results.map(v => 
                        `<li>${v.file}: ${v.valid ? '✓' : '✗'}</li>`
                    ).join('')}
                </ul>
            </div>
        ` : ''}
    `;
    
    return item;
}

// Status Tracking
async function trackModStatus(modId) {
    const container = document.getElementById('mod-results');
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/mods/${modId}/status`);
            const status = await response.json();
            
            // Update or add result item
            let item = container.querySelector(`[data-mod-id="${modId}"]`);
            if (!item) {
                item = createResultItem(modId, status);
                item.dataset.modId = modId;
                container.prepend(item);
            } else {
                const newItem = createResultItem(modId, status);
                newItem.dataset.modId = modId;
                item.replaceWith(newItem);
            }
            
            // Continue checking if still processing
            if (status.status === 'processing' || status.status === 'queued') {
                setTimeout(checkStatus, 2000);
            }
        } catch (error) {
            console.error('Error checking mod status:', error);
        }
    };
    
    checkStatus();
}

async function trackCppDevResult(modId) {
    const container = document.getElementById('cppdev-results');
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/mods/${modId}/status`);
            const status = await response.json();
            
            // Update or add result item
            let item = container.querySelector(`[data-mod-id="${modId}"]`);
            if (!item) {
                item = createResultItem(modId, status);
                item.dataset.modId = modId;
                container.prepend(item);
            } else {
                const newItem = createResultItem(modId, status);
                newItem.dataset.modId = modId;
                item.replaceWith(newItem);
            }
            
            // Continue checking if still processing
            if (status.status === 'processing' || status.status === 'queued') {
                setTimeout(checkStatus, 2000);
            }
        } catch (error) {
            console.error('Error checking cppdev status:', error);
        }
    };
    
    checkStatus();
}

// Queue Updates
function startQueueUpdates() {
    stopQueueUpdates();
    loadQueueStatus();
    queueUpdateInterval = setInterval(loadQueueStatus, 5000);
}

function stopQueueUpdates() {
    if (queueUpdateInterval) {
        clearInterval(queueUpdateInterval);
        queueUpdateInterval = null;
    }
}

// Refresh Button
document.getElementById('refresh-queue').addEventListener('click', () => {
    loadQueueStatus();
    showNotification('Queue status refreshed', 'success');
});

// Remove Repository
async function removeRepo(repoId) {
    if (!confirm('Are you sure you want to remove this repository?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/repos/${repoId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Repository removed successfully', 'success');

            // If the removed repo was selected, clear selection
            if (selectedRepo && selectedRepo.id === repoId) {
                selectedRepo = null;
            }

            // Reload repositories
            loadRepositories();
        } else {
            showNotification('Failed to remove repository', 'error');
        }
    } catch (error) {
        console.error('Error removing repository:', error);
        showNotification('Error removing repository', 'error');
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    // Simple notification - could be enhanced with a proper notification system
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    let bgColor = '#2563eb'; // info (blue)
    if (type === 'success') bgColor = '#10b981';
    else if (type === 'error') bgColor = '#ef4444';
    else if (type === 'warning') bgColor = '#f59e0b';

    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${bgColor};
        color: white;
        border-radius: 4px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRepositories();
});
