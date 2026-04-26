document.addEventListener("DOMContentLoaded", () => {
    const addPatronForm = document.querySelector(".add-patron-form");
    if (!addPatronForm) {
        return;
    }

    const passwordInput = addPatronForm.querySelector("#patron-password");
    const confirmInput = addPatronForm.querySelector("#patron-password-confirm");
    const toggleButton = addPatronForm.querySelector("[data-toggle-target='patron-password']");

    if (toggleButton && passwordInput) {
        toggleButton.addEventListener("click", () => {
            const shouldShow = passwordInput.type === "password";
            passwordInput.type = shouldShow ? "text" : "password";
            toggleButton.textContent = shouldShow ? "Hide" : "Show";
        });
    }

    if (passwordInput && confirmInput) {
        addPatronForm.addEventListener("submit", (event) => {
            if (passwordInput.value !== confirmInput.value) {
                event.preventDefault();
                confirmInput.setCustomValidity("Passwords do not match.");
                confirmInput.reportValidity();
                return;
            }
            confirmInput.setCustomValidity("");
        });

        confirmInput.addEventListener("input", () => {
            confirmInput.setCustomValidity("");
        });
    }
});
