// LevelUp JavaScript Application

const API_BASE = '/api';
let currentRepos = [];
let selectedRepo = null;
let queuedModsInterval = null;

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
        stopQueuedModsUpdates();
    } else if (tabId === 'mods') {
        startQueuedModsUpdates();
    } else {
        stopQueuedModsUpdates();
    }
}

// Repository Management
async function loadRepositories() {
    try {
        const response = await fetch(`${API_BASE}/repos`);
        const repos = await response.json();
        currentRepos = repos;
        displayRepositories(repos);

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
document.getElementById('mod-select').addEventListener('change', (e) => {
    const value = e.target.value;
    document.querySelectorAll('.mod-options').forEach(opt => {
        opt.style.display = 'none';
    });

    if (value === 'commit') {
        document.getElementById('commit-options').style.display = 'block';
    } else if (value === 'patch') {
        document.getElementById('patch-options').style.display = 'block';
    }
});

document.getElementById('mod-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Check if a repository is selected
    if (!selectedRepo) {
        showNotification('Please select a repository from the Repositories tab first', 'error');
        return;
    }

    const formData = new FormData(e.target);
    const modSelect = formData.get('mod_select');

    // Determine type and mod details
    let type, modType;
    if (modSelect.startsWith('builtin:')) {
        type = 'builtin';
        modType = modSelect.replace('builtin:', '');
    } else {
        type = modSelect; // 'commit' or 'patch'
    }

    const data = {
        repo_name: selectedRepo.name,
        repo_url: selectedRepo.url,
        work_branch: selectedRepo.work_branch,
        type: type,
        description: formData.get('description'),
        validators: ['asm'], // Always use ASM validator
        allow_reorder: formData.has('allow_reorder')
    };

    // Add type-specific data
    if (type === 'commit') {
        data.commit_hash = formData.get('commit_hash');
    } else if (type === 'builtin') {
        data.mod_type = modType;
    }

    try {
        let response;
        if (type === 'patch') {
            // Handle file upload
            const patchFormData = new FormData();
            Object.keys(data).forEach(key => {
                if (Array.isArray(data[key])) {
                    data[key].forEach(v => patchFormData.append(key, v));
                } else {
                    patchFormData.append(key, data[key]);
                }
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
            loadQueuedMods(); // Refresh queued mods list
        } else {
            showNotification('Failed to submit mod', 'error');
        }
    } catch (error) {
        console.error('Error submitting mod:', error);
        showNotification('Error submitting mod', 'error');
    }
});

// Status Tracking
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

// Queued Mods Management
async function loadQueuedMods() {
    try {
        const response = await fetch(`${API_BASE}/queue/status`);
        const status = await response.json();
        displayQueuedMods(status);
    } catch (error) {
        console.error('Error loading queued mods:', error);
    }
}

function displayQueuedMods(status) {
    const container = document.getElementById('queued-mods-list');
    container.innerHTML = '';

    // Filter for queued and processing items
    const queuedItems = Object.entries(status.results)
        .filter(([id, result]) => result.status === 'queued' || result.status === 'processing')
        .sort((a, b) => new Date(a[1].timestamp) - new Date(b[1].timestamp));

    if (queuedItems.length === 0) {
        container.innerHTML = '<p class="no-items">No mods in queue</p>';
        return;
    }

    const list = document.createElement('ul');
    list.className = 'queued-list';
    queuedItems.forEach(([id, result]) => {
        const item = document.createElement('li');
        const statusBadge = result.status === 'processing' ? '<span class="processing-badge">Processing</span>' : '';
        item.innerHTML = `${result.description || result.message || `Mod ${id}`} ${statusBadge}`;
        list.appendChild(item);
    });
    container.appendChild(list);
}

function startQueuedModsUpdates() {
    stopQueuedModsUpdates();
    loadQueuedMods();
    queuedModsInterval = setInterval(loadQueuedMods, 1000); // Update every second
}

function stopQueuedModsUpdates() {
    if (queuedModsInterval) {
        clearInterval(queuedModsInterval);
        queuedModsInterval = null;
    }
}

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
