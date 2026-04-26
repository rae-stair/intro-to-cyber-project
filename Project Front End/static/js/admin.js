document.addEventListener("DOMContentLoaded", () => {
    const MIN_PASSWORD_LENGTH = 12;
    const COMMON_PASSWORDS = new Set([
        "password",
        "password1",
        "123456",
        "12345678",
        "123456789",
        "qwerty",
        "abc123",
        "letmein",
        "welcome",
        "admin",
        "admin123",
        "iloveyou",
    ]);

    const addPatronForm = document.querySelector(".add-patron-form");
    if (!addPatronForm) {
        return;
    }

    const passwordInput = addPatronForm.querySelector("#patron-password");
    const confirmInput = addPatronForm.querySelector("#patron-password-confirm");
    const toggleButton = addPatronForm.querySelector("[data-toggle-target='patron-password']");
    const strengthMeter = addPatronForm.querySelector("#patron-password-strength");
    const strengthLabel = addPatronForm.querySelector("#patron-password-strength-label");

    const getPasswordPolicyError = (password) => {
        if (password.length < MIN_PASSWORD_LENGTH) {
            return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
        }
        if (COMMON_PASSWORDS.has(password.toLowerCase())) {
            return "Password is too common. Choose a less guessable password.";
        }
        if (!/[A-Z]/.test(password)) {
            return "Password must include at least one uppercase letter.";
        }
        if (!/[a-z]/.test(password)) {
            return "Password must include at least one lowercase letter.";
        }
        if (!/[0-9]/.test(password)) {
            return "Password must include at least one number.";
        }
        if (!/[^A-Za-z0-9]/.test(password)) {
            return "Password must include at least one symbol.";
        }
        return "";
    };

    const updateStrengthMeter = () => {
        if (!passwordInput || !strengthMeter || !strengthLabel) {
            return;
        }

        const value = passwordInput.value;
        let score = 0;
        if (value.length >= MIN_PASSWORD_LENGTH) score += 1;
        if (/[A-Z]/.test(value)) score += 1;
        if (/[a-z]/.test(value)) score += 1;
        if (/[0-9]/.test(value)) score += 1;
        if (/[^A-Za-z0-9]/.test(value)) score += 1;
        if (COMMON_PASSWORDS.has(value.toLowerCase())) score = Math.min(score, 1);

        strengthMeter.value = score;

        const labels = ["Very weak", "Weak", "Fair", "Good", "Strong", "Very strong"];
        strengthLabel.textContent = labels[score];
    };

    if (toggleButton && passwordInput) {
        toggleButton.addEventListener("click", () => {
            const shouldShow = passwordInput.type === "password";
            passwordInput.type = shouldShow ? "text" : "password";
            toggleButton.textContent = shouldShow ? "Hide" : "Show";
        });
    }

    if (passwordInput && confirmInput) {
        passwordInput.addEventListener("input", () => {
            const policyError = getPasswordPolicyError(passwordInput.value);
            passwordInput.setCustomValidity(policyError);
            if (confirmInput.value) {
                confirmInput.setCustomValidity(
                    passwordInput.value === confirmInput.value ? "" : "Passwords do not match."
                );
            }
            updateStrengthMeter();
        });

        addPatronForm.addEventListener("submit", (event) => {
            const policyError = getPasswordPolicyError(passwordInput.value);
            if (policyError) {
                event.preventDefault();
                passwordInput.setCustomValidity(policyError);
                passwordInput.reportValidity();
                return;
            }

            if (passwordInput.value !== confirmInput.value) {
                event.preventDefault();
                confirmInput.setCustomValidity("Passwords do not match.");
                confirmInput.reportValidity();
                return;
            }
            confirmInput.setCustomValidity("");
            passwordInput.setCustomValidity("");
        });

        confirmInput.addEventListener("input", () => {
            confirmInput.setCustomValidity(
                passwordInput.value === confirmInput.value ? "" : "Passwords do not match."
            );
        });
    }

    updateStrengthMeter();
});
