document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".admin-tab");
    const panels = {};

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

    // SEARCH
    const searchInput = document.getElementById("search-bar");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const query = searchInput.value.toLowerCase();
            const rows = document.querySelectorAll("#book-table tr");

            rows.forEach(row => {
                const title = row.children[0].textContent.toLowerCase();
                const author = row.children[1].textContent.toLowerCase();
                row.style.display = (title.includes(query) || author.includes(query)) ? "" : "none";
            });
        });
    }

});
