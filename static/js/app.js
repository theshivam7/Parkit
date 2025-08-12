document.querySelectorAll('[data-toggle-password]').forEach(button => {
    button.addEventListener('click', () => {
        const input = button.parentElement.querySelector('input');
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        button.setAttribute('aria-pressed', show);
        button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
        button.querySelector('i').className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
});

// Sign in / sign up pop-up
const authModal = document.getElementById('authModal');
if (authModal) {
    const titles = {
        login: ['Welcome back', 'Sign in to your Parkit V1 account'],
        register: ['Create your account', 'It takes less than a minute'],
    };
    const showTab = tab => {
        document.getElementById('authTitle').textContent = titles[tab][0];
        document.getElementById('authSubtitle').textContent = titles[tab][1];
        authModal.querySelectorAll('[data-auth-tab]').forEach(button => {
            const active = button.dataset.authTab === tab;
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', active);
            button.tabIndex = active ? 0 : -1;
        });
        document.getElementById('loginPane').hidden = tab !== 'login';
        document.getElementById('registerPane').hidden = tab !== 'register';
    };
    const modal = bootstrap.Modal.getOrCreateInstance(authModal);
    let opener = null;
    const openAuth = (tab, trigger) => {
        opener = trigger;
        showTab(tab);
        modal.show();
    };

    document.querySelectorAll('[data-auth]').forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();
            openAuth(link.dataset.auth, link);
        });
    });
    authModal.querySelectorAll('[data-auth-tab]').forEach(button => {
        button.addEventListener('click', () => showTab(button.dataset.authTab));
        button.addEventListener('keydown', event => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
            const other = button.dataset.authTab === 'login' ? 'register' : 'login';
            showTab(other);
            authModal.querySelector(`[data-auth-tab="${other}"]`).focus();
        });
    });
    authModal.addEventListener('hidden.bs.modal', () => opener && opener.focus());
    authModal.addEventListener('shown.bs.modal', () => {
        authModal.querySelector('form:not([hidden]) input:not([type=hidden])').focus();
    });

    showTab(authModal.dataset.open || 'login');
    if (authModal.dataset.open) modal.show();
}
