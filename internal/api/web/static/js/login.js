// Login page logic. Kept out of the HTML so the Content-Security-Policy can
// drop 'unsafe-inline' from script-src.
(function () {
    'use strict';

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorBox = document.getElementById('error');
        errorBox.style.display = 'none';

        try {
            const resp = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });

            if (resp.ok) {
                const data = await resp.json();
                // The session cookie is set by the server; nothing is kept in
                // localStorage.
                window.location.href = data.user && data.user.must_change_password
                    ? '/dashboard/?mustChange=1'
                    : '/dashboard/';
            } else {
                errorBox.style.display = 'block';
            }
        } catch (e) {
            errorBox.textContent = 'SYSTEM TIMEOUT - CHECK CONNECTION';
            errorBox.style.display = 'block';
        }
    });
})();
