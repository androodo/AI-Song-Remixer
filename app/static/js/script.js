/**
 * AI Song Remixer - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Dark mode toggle functionality
    initThemeToggle();
    
    // Initialize keyboard shortcuts
    initKeyboardShortcuts();
    
    // Check if browser supports audio processing
    checkBrowserCompatibility();
    
    // Make effect cards clickable to toggle checkboxes
    const effectCards = document.querySelectorAll('.effect-card');
    
    effectCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't trigger if the click was on the checkbox itself
            if (e.target.type !== 'checkbox') {
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                
                // Trigger change event for any listeners
                const event = new Event('change');
                checkbox.dispatchEvent(event);
            }
        });
    });
    
    // Add loading overlay when form is submitted
    const remixForm = document.querySelector('form');
    
    if (remixForm) {
        remixForm.addEventListener('submit', function(e) {
            if (this.checkValidity()) {
                // Check if at least one file is selected
                const fileInput = document.getElementById('file');
                if (fileInput && fileInput.files.length > 0) {
                    // Create and show loading overlay
                    showLoadingOverlay('Processing your song... This may take a moment.');
                }
            }
        });
    }
    
    // Social sharing buttons functionality
    const shareButtons = document.querySelectorAll('.btn-outline-primary, .btn-outline-info, .btn-outline-danger, .btn-outline-success');
    
    shareButtons.forEach(button => {
        button.addEventListener('click', function() {
            // This would normally open share dialogs
            // Just showing an alert for demo purposes
            alert('Sharing functionality would be implemented here in production!');
        });
    });
    
    // Audio player enhancements
    const audioPlayer = document.querySelector('audio');
    
    if (audioPlayer) {
        // Add play event visualization
        audioPlayer.addEventListener('play', function() {
            const discIcon = document.querySelector('.fa-compact-disc');
            if (discIcon) {
                discIcon.classList.add('fa-spin');
            }
        });
        
        audioPlayer.addEventListener('pause', function() {
            const discIcon = document.querySelector('.fa-compact-disc');
            if (discIcon) {
                discIcon.classList.remove('fa-spin');
            }
        });
    }
});

/**
 * Theme toggle functionality
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlEl = document.documentElement;
    
    // Check for saved theme preference or respect OS preference
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const storedTheme = localStorage.getItem('theme');
    
    // Set initial theme
    if (storedTheme === 'dark' || (!storedTheme && prefersDarkMode)) {
        htmlEl.setAttribute('data-bs-theme', 'dark');
        if (themeIcon) {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        }
    }
    
    // Toggle theme when button is clicked
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlEl.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            htmlEl.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Toggle icon
            if (themeIcon) {
                if (newTheme === 'dark') {
                    themeIcon.classList.remove('fa-moon');
                    themeIcon.classList.add('fa-sun');
                } else {
                    themeIcon.classList.remove('fa-sun');
                    themeIcon.classList.add('fa-moon');
                }
            }
            
            // Custom event that other parts of the application can listen for
            document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
        });
    }
}

/**
 * Keyboard shortcuts for common actions
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Check if not in an input field
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            // Space - Play/Pause audio if on result page
            if (e.code === 'Space' && document.getElementById('play-btn')) {
                e.preventDefault();
                document.getElementById('play-btn').click();
            }
            
            // Alt+D - Download remixed song if on result page
            if (e.altKey && e.code === 'KeyD' && document.getElementById('download-btn')) {
                e.preventDefault();
                document.getElementById('download-btn').click();
            }
            
            // Alt+R - Go to remix page
            if (e.altKey && e.code === 'KeyR') {
                e.preventDefault();
                window.location.href = '/';
            }
            
            // Alt+T - Toggle theme
            if (e.altKey && e.code === 'KeyT' && document.getElementById('theme-toggle')) {
                e.preventDefault();
                document.getElementById('theme-toggle').click();
            }
        }
    });
    
    // Show keyboard shortcuts help when pressing "?"
    document.addEventListener('keydown', function(e) {
        if (e.code === 'Slash' && e.shiftKey) {
            e.preventDefault();
            showKeyboardShortcutsHelp();
        }
    });
}

/**
 * Display keyboard shortcuts in a modal
 */
function showKeyboardShortcutsHelp() {
    // Create modal if it doesn't exist
    let modal = document.getElementById('shortcuts-modal');
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'shortcuts-modal';
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Keyboard Shortcuts</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="list-group">
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span><kbd>Space</kbd></span>
                                <span>Play/Pause Audio</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span><kbd>Alt</kbd> + <kbd>D</kbd></span>
                                <span>Download Remixed Song</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span><kbd>Alt</kbd> + <kbd>R</kbd></span>
                                <span>Go to Remix Page</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span><kbd>Alt</kbd> + <kbd>T</kbd></span>
                                <span>Toggle Light/Dark Theme</span>
                            </div>
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span><kbd>?</kbd></span>
                                <span>Show This Help</span>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Check browser compatibility for audio processing
 */
function checkBrowserCompatibility() {
    // Check for necessary AudioContext support
    const hasAudioContext = (window.AudioContext || window.webkitAudioContext);
    const hasFileReader = (window.FileReader);
    
    // Check for audio decoding capabilities
    const audio = document.createElement('audio');
    const canPlayMp3 = audio.canPlayType('audio/mpeg;') !== '';
    const canPlayWav = audio.canPlayType('audio/wav;') !== '';
    
    if (!hasAudioContext || !hasFileReader || (!canPlayMp3 && !canPlayWav)) {
        showCompatibilityWarning();
    }
}

/**
 * Show compatibility warning if browser doesn't support needed features
 */
function showCompatibilityWarning() {
    const warningContainer = document.createElement('div');
    warningContainer.className = 'alert alert-warning alert-dismissible fade show';
    warningContainer.setAttribute('role', 'alert');
    
    warningContainer.innerHTML = `
        <div class="d-flex">
            <div class="me-3">
                <i class="fas fa-exclamation-triangle fa-2x"></i>
            </div>
            <div>
                <h4 class="alert-heading">Browser Compatibility Notice</h4>
                <p>Your browser may not fully support all the audio processing features. For the best experience, please use the latest version of Chrome, Firefox, or Edge.</p>
            </div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insert at the top of the main content area
    const mainContent = document.querySelector('main');
    if (mainContent && mainContent.firstChild) {
        mainContent.insertBefore(warningContainer, mainContent.firstChild);
    } else if (mainContent) {
        mainContent.appendChild(warningContainer);
    } else {
        document.body.insertBefore(warningContainer, document.body.firstChild);
    }
}

/**
 * Add a new remix to history
 * @param {Object} remixData - The remix data to add
 */
function addToHistory(remixData) {
    if (!remixData) return;
    
    let recentRemixes = JSON.parse(localStorage.getItem('recentRemixes')) || [];
    
    // Add to beginning of array and limit to 10 items
    recentRemixes.unshift(remixData);
    if (recentRemixes.length > 10) {
        recentRemixes = recentRemixes.slice(0, 10);
    }
    
    localStorage.setItem('recentRemixes', JSON.stringify(recentRemixes));
    
    // Refresh history display if it exists on the page
    if (document.getElementById('history-container')) {
        loadRecentRemixes();
    }
}

/**
 * Load recent remixes from localStorage
 */
function loadRecentRemixes() {
    const historyContainer = document.getElementById('history-container');
    const noHistoryMessage = document.getElementById('no-history-message');
    
    if (!historyContainer) return;
    
    let recentRemixes = JSON.parse(localStorage.getItem('recentRemixes')) || [];
    
    if (recentRemixes.length > 0) {
        if (noHistoryMessage) noHistoryMessage.style.display = 'none';
        historyContainer.innerHTML = '';
        
        recentRemixes.slice(0, 5).forEach(remix => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            
            let effectIcon = 'headphones-alt';
            if (remix.effect === 'Jazz') effectIcon = 'music';
            if (remix.effect === 'Dubstep') effectIcon = 'volume-up';
            
            historyItem.innerHTML = `
                <div class="history-icon">
                    <i class="fas fa-${effectIcon}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${remix.originalName}</strong>
                            <div class="text-muted small">${remix.date}</div>
                        </div>
                        <span class="effect-badge">${remix.effect}</span>
                    </div>
                </div>
            `;
            
            historyContainer.appendChild(historyItem);
        });
    }
}

// Function to show loading overlay during processing
function showLoadingOverlay(message) {
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-content">
            <div class="spinner-border text-light mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>${message}</p>
        </div>
    `;
    
    // Style the overlay
    Object.assign(overlay.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: '9999',
        color: 'white',
        textAlign: 'center'
    });
    
    // Add to body
    document.body.appendChild(overlay);
    
    // Return overlay so it can be removed later if needed
    return overlay;
} 