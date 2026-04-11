document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".admin-tab");
    const panels = {
        analytics: document.getElementById("tab-analytics"),
        users: document.getElementById("tab-users"),
        settings: document.getElementById("tab-settings")
    };

    function setActiveTab(tabName) {
        tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.tab === tabName));
        Object.keys(panels).forEach(key => panels[key].classList.toggle("active", key === tabName));
    }

    setActiveTab("analytics");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
    });
});