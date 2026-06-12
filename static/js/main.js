/* MyMediFile - Main JavaScript Utilities & Client interactions */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Dark Mode Initialization & Handling
    initDarkMode();
    
    // 2. Mobile Sidebar Toggle Handler
    initMobileSidebar();
    
    // 3. Password Strength Monitor Setup
    initPasswordStrength();
    
    // 4. Form Custom Validation Utilities
    initFormValidation();
});

// Toast Manager
function showToast(title, message, type = 'primary') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const bgClass = type === 'danger' ? 'bg-danger text-white' : 
                    type === 'success' ? 'bg-success text-white' : 
                    type === 'warning' ? 'bg-warning text-dark' : 'bg-primary text-white';
                    
    const toastHTML = `
        <div class="toast align-items-center ${bgClass} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong>: ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    const wrapper = document.createElement('div');
    wrapper.innerHTML = toastHTML.trim();
    const toastElement = wrapper.firstChild;
    
    container.appendChild(toastElement);
    const bsToast = new bootstrap.Toast(toastElement);
    bsToast.show();
    
    // Clean up toast element after hide
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Dark Mode Toggle Logic
function initDarkMode() {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (!toggleBtn) return;
    
    const themeIcon = toggleBtn.querySelector('i');
    const getSavedTheme = () => localStorage.getItem('theme') || 'light';
    const applyTheme = (theme) => {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        if (theme === 'dark') {
            themeIcon.className = 'fas fa-sun';
        } else {
            themeIcon.className = 'fas fa-moon';
        }
    };
    
    // Load initial theme
    applyTheme(getSavedTheme());
    
    toggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);
    });
}

// Mobile Navbar Toggle Function
function initMobileSidebar() {
    const toggleBtn = document.getElementById('sidebar-mobile-toggle');
    const sidebar = document.getElementById('sidebar-nav');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar if user clicks outside of it on mobile screen sizes
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('show') && !sidebar.contains(e.target) && e.target !== toggleBtn) {
                sidebar.classList.remove('show');
            }
        });
    }
}

// Password Strength Scoring Helper
function initPasswordStrength() {
    const passwordInput = document.getElementById('register-password');
    const strengthBar = document.getElementById('password-strength-bar');
    const strengthText = document.getElementById('password-strength-text');
    
    if (!passwordInput || !strengthBar || !strengthText) return;
    
    passwordInput.addEventListener('input', () => {
        const password = passwordInput.value;
        let score = 0;
        
        if (password.length >= 8) score += 20;
        if (/[A-Z]/.test(password)) score += 20;
        if (/[a-z]/.test(password)) score += 20;
        if (/[0-9]/.test(password)) score += 20;
        if (/[^A-Za-z0-9]/.test(password)) score += 20;
        
        strengthBar.style.width = score + '%';
        
        if (score === 0) {
            strengthBar.className = 'progress-bar bg-secondary';
            strengthText.innerText = 'Strength: Empty';
        } else if (score <= 40) {
            strengthBar.className = 'progress-bar bg-danger';
            strengthText.innerText = 'Strength: Weak';
        } else if (score <= 80) {
            strengthBar.className = 'progress-bar bg-warning';
            strengthText.innerText = 'Strength: Moderate';
        } else {
            strengthBar.className = 'progress-bar bg-success';
            strengthText.innerText = 'Strength: Excellent';
        }
    });
}

// Form validation listeners
function initFormValidation() {
    const regForm = document.getElementById('register-form');
    if (regForm) {
        regForm.addEventListener('submit', (e) => {
            const pass = document.getElementById('register-password').value;
            const confirm = document.getElementById('register-confirm-password').value;
            if (pass !== confirm) {
                e.preventDefault();
                showToast('Registration Error', 'Passwords do not match.', 'danger');
            }
        });
    }
}
