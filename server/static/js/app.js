// LevelUp JavaScript Application

const API_BASE = '/api';
let currentRepos = [];
let selectedRepo = null;
let queuedModsInterval = null;

// Track which mods belong to which repos (persisted in localStorage)
let modToRepoMap = JSON.parse(localStorage.getItem('modToRepoMap') || '{}');

// Helper to save modToRepoMap to localStorage
function saveModToRepoMap() {
    localStorage.setItem('modToRepoMap', JSON.stringify(modToRepoMap));
}

// Modal Management
const modal = document.getElementById('add-repo-modal');
const addRepoBtn = document.getElementById('add-repo-btn');
const closeModalBtn = modal.querySelector('.close-modal');
const cancelBtn = modal.querySelector('.cancel-btn');
let editingRepoId = null; // Track if we're editing a repo

function openModal() {
    modal.classList.add('active');
}

function closeModal() {
    modal.classList.remove('active');
    document.getElementById('repo-form').reset();
    editingRepoId = null;
    // Reset modal title and button text
    modal.querySelector('.modal-header h3').textContent = 'Add New Repository';
    modal.querySelector('.primary-btn').textContent = 'Add Repo';
}

// Open modal
addRepoBtn.addEventListener('click', openModal);

// Close modal
closeModalBtn.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);

// Close modal when clicking outside
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
        closeModal();
    }
});

// Screen Navigation
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');

    // Show top bar on all screens
    const topBar = document.getElementById('top-bar');
    topBar.classList.add('visible');

    // Toggle back button visibility based on screen
    const backButton = document.getElementById('back-to-repos-btn');
    if (screenId === 'mods') {
        backButton.style.display = 'block';
    } else {
        backButton.style.display = 'none';
    }

    // Load screen-specific data
    if (screenId === 'repos') {
        loadRepositories();
        stopQueuedModsUpdates();
    } else if (screenId === 'mods') {
        loadAvailableMods();
        loadSuccessfulMods();
        startQueuedModsUpdates();
    }
}

// Load available mods from API
async function loadAvailableMods() {
    try {
        const response = await fetch(`${API_BASE}/available/mods`);
        const mods = await response.json();
        populateModSelect(mods);
    } catch (error) {
        console.error('Error loading available mods:', error);
    }
}

function populateModSelect(mods) {
    const select = document.getElementById('mod-select');

    // Clear existing options except the first one
    select.innerHTML = '<option value="">Select a mod...</option>';

    // Add all mods as plain options
    mods.forEach(mod => {
        const option = document.createElement('option');
        option.value = `builtin:${mod.id}`;
        option.textContent = mod.name;
        select.appendChild(option);
    });
}

// Back to repos button
const backToReposBtn = document.getElementById('back-to-repos-btn');
if (backToReposBtn) {
    backToReposBtn.addEventListener('click', () => {
        showScreen('repos');
    });
}

// Repository Management
async function loadRepositories() {
    try {
        const response = await fetch(`${API_BASE}/repos`);
        const repos = await response.json();
        currentRepos = repos;
        displayRepositories(repos);
    } catch (error) {
        console.error('Error loading repositories:', error);
    }
}

function selectRepo(repo) {
    selectedRepo = repo;

    // Navigate to mods screen
    showScreen('mods');
}

function displayRepositories(repos) {
    const container = document.getElementById('repo-list');
    container.innerHTML = '';

    if (repos.length === 0) {
        container.innerHTML = '<p>No repositories configured yet.</p>';
        selectedRepo = null;
        return;
    }

    repos.forEach(repo => {
        const repoElement = document.createElement('div');
        repoElement.className = 'repo-item';
        repoElement.dataset.repoId = repo.id;

        repoElement.innerHTML = `
            <div class="repo-info">
                <h4>${repo.name}</h4>
                <p>URL: ${repo.url}</p>
            </div>
            <div class="repo-actions">
                <button class="edit-repo-btn" onclick="event.stopPropagation(); editRepo('${repo.id}')" title="Edit repository"></button>
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
        let response;
        let successMessage;

        if (editingRepoId) {
            // Update existing repo
            response = await fetch(`${API_BASE}/repos/${editingRepoId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            successMessage = 'Repository updated successfully';
        } else {
            // Add new repo
            response = await fetch(`${API_BASE}/repos`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            successMessage = 'Repository added successfully';
        }

        if (response.ok) {
            const repo = await response.json();
            showNotification(successMessage, 'success');
            closeModal();
            loadRepositories();
        } else {
            showNotification(editingRepoId ? 'Failed to update repository' : 'Failed to add repository', 'error');
        }
    } catch (error) {
        console.error('Error saving repository:', error);
        showNotification('Error saving repository', 'error');
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
    }
});

document.getElementById('mod-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    console.log('Form submitted, selectedRepo:', selectedRepo);

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
        type = modSelect; // 'commit'
    }

    const data = {
        repo_name: selectedRepo.name,
        repo_url: selectedRepo.url,
        type: type,
        description: formData.get('description'),
        validators: ['asm'] // Always use ASM validator
    };

    // Add type-specific data
    if (type === 'commit') {
        data.commit_hash = formData.get('commit_hash');
    } else if (type === 'builtin') {
        data.mod_type = modType;
    }

    try {
        console.log('Sending mod request:', data);
        const response = await fetch(`${API_BASE}/mods`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        console.log('Response status:', response.status);

        if (response.ok) {
            const mod = await response.json();
            // Track which repo this mod belongs to
            modToRepoMap[mod.id] = selectedRepo.name;
            saveModToRepoMap();
            e.target.reset();
            trackModStatus(mod.id);
            loadQueuedMods(); // Refresh queued mods list
            loadSuccessfulMods(); // Refresh successful mods list
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

    let displayStatus, statusClass;
    if (result.status === 'success') {
        displayStatus = 'Success';
        statusClass = 'status-success';
    } else if (result.status === 'partial') {
        displayStatus = 'Partial';
        statusClass = 'status-partial';
    } else {
        displayStatus = 'Failed';
        statusClass = 'status-fail';
    }

    const filesModified = result.validation_results ? result.validation_results.length : 0;

    item.innerHTML = `
        <div class="result-header">
            <div>
                <strong>${result.message}</strong>
                <br>
                <small>${filesModified} file${filesModified !== 1 ? 's' : ''} modified</small>
            </div>
            <span class="result-status ${statusClass}">${displayStatus}</span>
        </div>
    `;

    return item;
}

// Status Tracking
async function trackModStatus(modId) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/mods/${modId}/status`);
            const status = await response.json();

            // If mod is completed (success, partial, failed, or error), refresh the completed mods list
            if (status.status === 'success' || status.status === 'partial' || status.status === 'failed' || status.status === 'error') {
                loadSuccessfulMods();
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
        .filter(([id, result]) => result.status === 'queued' || result.status === 'processing');

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

// Completed Mods Management
async function loadSuccessfulMods() {
    if (!selectedRepo) return;

    try {
        const response = await fetch(`${API_BASE}/queue/status`);
        const status = await response.json();
        displayCompletedMods(status);
    } catch (error) {
        console.error('Error loading completed mods:', error);
    }
}

function displayCompletedMods(status) {
    const container = document.getElementById('mod-results');
    container.innerHTML = '';

    if (!selectedRepo) {
        container.innerHTML = '<p class="no-items">No repository selected</p>';
        return;
    }

    // Filter for completed items (success, failed, or error) that belong to the current repo
    const completedItems = Object.entries(status.results)
        .filter(([id, result]) => {
            const isCompleted = result.status === 'success' || result.status === 'partial' || result.status === 'failed' || result.status === 'error';
            return isCompleted && modToRepoMap[id] === selectedRepo.name;
        });

    if (completedItems.length === 0) {
        container.innerHTML = '<p class="no-items">No completed mods yet</p>';
        return;
    }

    completedItems.forEach(([id, result]) => {
        const item = createResultItem(id, result);
        item.dataset.modId = id;
        container.appendChild(item);
    });
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

// Edit Repository
function editRepo(repoId) {
    const repo = currentRepos.find(r => r.id === repoId);
    if (!repo) {
        showNotification('Repository not found', 'error');
        return;
    }

    // Set editing mode
    editingRepoId = repoId;

    // Update modal title and button text
    modal.querySelector('.modal-header h3').textContent = 'Edit Repository';
    modal.querySelector('.primary-btn').textContent = 'Update Repo';

    // Populate form with current values
    document.getElementById('repo-url').value = repo.url || '';
    document.getElementById('post-checkout').value = repo.post_checkout || '';
    document.getElementById('build-command').value = repo.build_command || '';
    document.getElementById('single-tu-command').value = repo.single_tu_command || '';

    openModal();
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
    // Show top bar on initial load (Repos screen)
    const topBar = document.getElementById('top-bar');
    topBar.classList.add('visible');

    // Hide back button on Repos screen
    const backButton = document.getElementById('back-to-repos-btn');
    backButton.style.display = 'none';

    loadRepositories();
});
