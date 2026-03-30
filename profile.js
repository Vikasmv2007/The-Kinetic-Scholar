/**
 * Profile Dropdown Management
 * Handles user profile display, editing, and reset
 */

const PROFILE_STORAGE_KEY = "dash_splash_profile_v1";

function initProfileDropdown() {
    const profileBtn = document.getElementById('profileBtn') || document.getElementById('openProfileBtn');
    const profileDropdown = document.getElementById('profileDropdown');
    
    if (!profileBtn || !profileDropdown) {
        // Try to create the dropdown if it doesn't exist
        createProfileDropdownIfMissing();
        return;
    }

    // Toggle dropdown on button click
    profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileDropdown.classList.toggle('hidden');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!profileDropdown.contains(e.target) && e.target !== profileBtn) {
            profileDropdown.classList.add('hidden');
        }
    });

    // Prevent dropdown from closing when clicking inside it
    profileDropdown.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // Setup menu items
    setupProfileMenuItems(profileDropdown);
}

function setupProfileMenuItems(dropdown) {
    const profile = loadProfile();
    const profileStatus = dropdown.querySelector('[data-menu="profile-status"]');
    
    // Update status display
    if (profileStatus) {
        if (profile) {
            profileStatus.textContent = 'Logged in as';
        } else {
            profileStatus.textContent = 'Not logged in';
        }
    }
    
    // Update username display
    const usernameEl = dropdown.querySelector('[data-menu="username"]');
    if (usernameEl) {
        usernameEl.textContent = profile?.username || 'Guest';
    }

    // Setup buttons  
    const loginBtn = dropdown.querySelector('[data-action="login"]');
    const editBtn = dropdown.querySelector('[data-action="edit"]');
    const resetBtn = dropdown.querySelector('[data-action="reset"]');
    const logoutBtn = dropdown.querySelector('[data-action="logout"]');

    if (loginBtn) {
        loginBtn.classList.toggle('hidden', Boolean(profile));
        if (!profile) {
            loginBtn.addEventListener('click', () => {
                // For pages that have the splash, open it
                const splash = document.getElementById('dashSplashOverlay');
                if (splash) {
                    splash.classList.add('open');
                }
            });
        }
    }

    if (editBtn) {
        editBtn.classList.toggle('hidden', !Boolean(profile));
        editBtn.addEventListener('click', () => {
            openEditProfileModal();
        });
    }

    if (resetBtn) {
        resetBtn.classList.toggle('hidden', !Boolean(profile));
        resetBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to reset your profile? This cannot be undone.')) {
                resetProfile();
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.classList.toggle('hidden', !Boolean(profile));
        logoutBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to logout?')) {
                logout();
            }
        });
    }
}

function loadProfile() {
    try {
        const saved = localStorage.getItem(PROFILE_STORAGE_KEY);
        if (!saved) {
            return null;
        }
        const parsed = JSON.parse(saved);
        if (!parsed.username || !Array.isArray(parsed.subjects)) {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

function saveProfile(profile) {
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

function openEditProfileModal() {
    const profile = loadProfile();
    const modal = createEditProfileModal(profile);
    document.body.appendChild(modal);
    modal.classList.add('open');

    // Setup modal handlers
    const closeBtn = modal.querySelector('[data-action="close"]');
    const saveBtn = modal.querySelector('[data-action="save"]');

    closeBtn?.addEventListener('click', () => {
        modal.remove();
    });

    saveBtn?.addEventListener('click', () => {
        const username = modal.querySelector('[data-field="username"]').value.trim();
        
        if (!username) {
            alert('Username cannot be empty');
            return;
        }

        const updatedProfile = {
            ...profile,
            username
        };

        saveProfile(updatedProfile);
        modal.remove();
        
        // Refresh dropdown
        updateProfileDisplay();
        alert('Profile updated successfully!');
        location.reload();
    });

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

function createEditProfileModal(profile) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-[999] flex items-center justify-center';
    modal.innerHTML = `
        <div class="bg-surface border-4 border-inverse-surface p-8 max-w-md w-full m-4 neo-shadow">
            <h2 class="text-2xl font-black uppercase mb-6">Edit Profile</h2>
            
            <div class="space-y-4 mb-6">
                <div>
                    <label class="block text-sm font-bold uppercase mb-2">Username</label>
                    <input type="text" data-field="username" value="${profile?.username || ''}" 
                           class="w-full border-4 border-inverse-surface p-3 font-bold" 
                           placeholder="Enter your name">
                </div>
                
                <div>
                    <p class="text-sm font-bold uppercase mb-2">Subjects:</p>
                    <div class="space-y-2">
                        ${(profile?.subjects || []).map(s => `
                            <div class="flex justify-between p-2 bg-surface-container border-2 border-inverse-surface">
                                <span class="font-bold">${s.subject}</span>
                                <span class="text-xs bg-primary-container px-2 py-1">IMP: ${s.importance}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>

            <div class="flex gap-2">
                <button data-action="close" class="flex-1 bg-surface-container border-4 border-inverse-surface p-3 font-black uppercase neo-shadow active:translate-x-1 active:translate-y-1 active:shadow-none transition-all">
                    Cancel
                </button>
                <button data-action="save" class="flex-1 bg-primary-container border-4 border-inverse-surface p-3 font-black uppercase neo-shadow active:translate-x-1 active:translate-y-1 active:shadow-none transition-all">
                    Save
                </button>
            </div>
        </div>
    `;
    return modal;
}

function resetProfile() {
    localStorage.removeItem(PROFILE_STORAGE_KEY);
    alert('Profile reset successfully. Please refresh the page.');
    location.reload();
}

function logout() {
    localStorage.removeItem(PROFILE_STORAGE_KEY);
    alert('Logged out successfully.');
    window.location.href = '/';
}

function updateProfileDisplay() {
    const profile = loadProfile();
    const usernameEl = document.querySelector('[data-menu="username"]');
    if (usernameEl) {
        usernameEl.textContent = profile?.username || 'Guest';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initProfileDropdown);
