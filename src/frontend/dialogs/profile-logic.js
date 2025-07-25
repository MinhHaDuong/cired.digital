// ==========================================
// ==========================================

const PROFILE_STORAGE_KEY = 'user-profile';

const profileDialog = document.getElementById('profile-dialog');
const profileBtn = document.getElementById('profile-btn');
const profileCloseBtn = document.getElementById('profile-close-btn');
const saveProfileBtn = document.getElementById('save-profile-btn');
const clearProfileBtn = document.getElementById('clear-profile-btn');
const onboardingBtn = document.getElementById('onboarding-btn');

const defaultProfile = {
    organization: '',
    knowledge: '',
    usage: '',
    createdAt: null,
    updatedAt: null
};

// ==========================================
// ==========================================


function getProfile() {
    try {
        const stored = localStorage.getItem(PROFILE_STORAGE_KEY);
        return stored ? { ...defaultProfile, ...JSON.parse(stored) } : { ...defaultProfile };
    } catch (error) {
        debugLog('Error loading profile', error);
        return { ...defaultProfile };
    }
}

function collectFormData(formPrefix = 'profile-') {
    return {
        knowledge: document.querySelector('input[name="profile-knowledge"]:checked')?.value || '',
        usage: document.querySelector('input[name="profile-usage"]:checked')?.value || '',
        organization: document.querySelector('input[name="profile-organization"]:checked')?.value || ''
    };
}

function saveProfile(profileData) {
    try {
        const stored = localStorage.getItem(PROFILE_STORAGE_KEY);
        const existing = stored ? JSON.parse(stored) : {};
        const profile = {
            ...defaultProfile,
            ...existing,
            ...profileData,
            id: existing.id || generateUUID(),
            updatedAt: new Date().toISOString()
        };
        if (!profile.createdAt) {
            profile.createdAt = profile.updatedAt;
        }
        localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));

        debugLog('Profile saved', profile);
        updateProfileDialog(); // Update the UI to reflect the new profile
        monitor(MonitorEventType.USER_PROFILE, {
            action: 'profile_updated',
            profile: profile
        });
        return profile;
    } catch (error) {
        debugLog('Error saving profile', error);
        return null;
    }
}

function clearProfile() {
    monitor(MonitorEventType.USER_PROFILE, {
        action: 'profile_clearing',
        profile: getProfile()
    });
    try {
        localStorage.removeItem(PROFILE_STORAGE_KEY);
        localStorage.removeItem(PROFILE_ONBOARDED_KEY);

        updateProfileDialog(); // Update the UI to reflect the cleared profile
        debugLog('Profile cleared');
        return true;
    } catch (error) {
        debugLog('Error clearing profile', error);
        return false;
    }
}


// ==========================================
// Button Handlers
// ==========================================


function showProfileDialog() {
    if (profileDialog) {
        updateProfileDialog();
        profileDialog.hidden = false;
    }
}

function hideProfileDialog() {
    if (profileDialog) {
        profileDialog.hidden = true;
    }
}

function handleSaveProfile() {
    const profileData = collectFormData('edit-profile-');

    const hasAllAnswers = profileData.organization && profileData.knowledge && profileData.usage;

    if (!hasAllAnswers) {
        showProfileValidationError();
        return;
    }

    clearProfileValidationError();

    const savedProfile = saveProfile(profileData);
    if (savedProfile) {
        onProfileCompleted();
        hideProfileDialog();
    }
}

function handleClearProfile() {
    clearProfile()
    restartOnboarding();
}

function showProfileValidationError() {
    clearProfileValidationError();

    const errorDiv = document.createElement('div');
    errorDiv.id = 'profile-validation-error';
    errorDiv.className = 'error-message';
    errorDiv.style.marginTop = '1rem';
    errorDiv.textContent = 'Veuillez répondre aux trois questions avant de sauvegarder votre profil.';

    const actionsDiv = document.getElementById('profile-actions');
    if (actionsDiv) {
        actionsDiv.parentNode.insertBefore(errorDiv, actionsDiv);
    }
}

function clearProfileValidationError() {
    const existingError = document.getElementById('profile-validation-error');
    if (existingError) {
        existingError.remove();
    }
}

function handleOpenOnboarding() {
    debugLog('Opening onboarding guide');
    hideProfileDialog();
    showOnboardingPanel();
}

// ==========================================
// INITIALIZATION
// ==========================================

function initializeProfile() {
    debugLog('Initializing profile system');

    attach('profile-btn', 'click', showProfileDialog);
    attach('profile-close-btn', 'click', hideProfileDialog);
    attach('save-profile-btn', 'click', handleSaveProfile);
    attach('clear-profile-btn', 'click', handleClearProfile);
    attach('onboarding-btn', 'click', handleOpenOnboarding);
}
