document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".admin-tab");
    const panels = {};

    // Map data-tab attributes to panels dynamically
    tabs.forEach(tab => {
        const tabName = tab.dataset.tab;
        const panel = document.getElementById(`tab-${tabName}`);
        if (panel) panels[tabName] = panel;
    });

    function setActiveTab(tabName) {
        tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.tab === tabName));
        Object.keys(panels).forEach(key => panels[key].classList.toggle("active", key === tabName));
    }

    if (tabs.length > 0) setActiveTab(tabs[0].dataset.tab);

    tabs.forEach(tab => {
        tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
    });

    // Searching
    const searchInput = document.getElementById("search-bar");
    const bookRows = document.querySelectorAll("#book-table tr");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const query = searchInput.value.toLowerCase();
            bookRows.forEach(row => {
                const title = row.children[0].textContent.toLowerCase();
                const author = row.children[1].textContent.toLowerCase();
                if (title.includes(query) || author.includes(query)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    }

    // Reserve Button Functionality
    const reserveForms = document.querySelectorAll("#book-table form");

    reserveForms.forEach(form => {
        form.addEventListener("submit", (e) => {
            e.preventDefault(); // Prevent page refresh

            const button = form.querySelector("button");
            const row = form.closest("tr");
            const statusCell = row.querySelector(".status-pill");

            // Update UI immediately
            if (button && statusCell) {
                statusCell.textContent = "Reserved";
                statusCell.classList.remove("status-active");
                statusCell.classList.add("status-inactive");
                button.textContent = "Reserved";
                button.disabled = true;
            }

            // Cloning the rows to my books tab
            
        });
    });
});