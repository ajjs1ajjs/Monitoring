// Login page logic. Kept out of the HTML so the Content-Security-Policy can
// drop 'unsafe-inline' from script-src.
(function () {
    'use strict';
    // Clear old tokens on login page load to prevent 401 loops
    localStorage.removeItem('token');

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const errorBox = document.getElementById('error');
        errorBox.style.display = 'none';

        try {
            const resp = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });

            if (resp.ok) {
                const data = await resp.json();
                localStorage.setItem('token', data.access_token);
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
