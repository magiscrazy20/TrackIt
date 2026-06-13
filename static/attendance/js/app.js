/* ------------------------------------------------------------------ *
 *  Attendance Manager — global UI behaviour                          *
 *  - sidebar toggle (mobile)                                          *
 *  - dark-mode toggle with localStorage persistence                  *
 * ------------------------------------------------------------------ */
(function () {
    "use strict";

    const html = document.documentElement;
    const THEME_KEY = "attendance-theme";

    // --- Restore saved theme on load ---
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme) {
        html.setAttribute("data-bs-theme", savedTheme);
    }

    document.addEventListener("DOMContentLoaded", function () {
        // Sidebar toggle (mobile) with dim backdrop.
        const sidebar = document.getElementById("sidebar");
        const sidebarToggle = document.getElementById("sidebarToggle");
        const backdrop = document.getElementById("sidebarBackdrop");

        function openSidebar() {
            if (!sidebar) return;
            sidebar.classList.add("open");
            if (backdrop) backdrop.classList.add("show");
        }
        function closeSidebar() {
            if (!sidebar) return;
            sidebar.classList.remove("open");
            if (backdrop) backdrop.classList.remove("show");
        }

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener("click", function () {
                if (sidebar.classList.contains("open")) {
                    closeSidebar();
                } else {
                    openSidebar();
                }
            });
        }
        // Tap the backdrop to close.
        if (backdrop) backdrop.addEventListener("click", closeSidebar);
        // Close the menu after picking a destination on mobile.
        sidebar && sidebar.querySelectorAll(".sidebar-nav .nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.matchMedia("(max-width: 991.98px)").matches) closeSidebar();
            });
        });
        // Reset state when resizing up to desktop.
        window.addEventListener("resize", function () {
            if (window.innerWidth > 991.98) closeSidebar();
        });

        // Theme toggle.
        const themeToggle = document.getElementById("themeToggle");
        if (themeToggle) {
            updateThemeIcon();
            themeToggle.addEventListener("click", function () {
                const current = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
                html.setAttribute("data-bs-theme", current);
                localStorage.setItem(THEME_KEY, current);
                updateThemeIcon();
            });
        }

        function updateThemeIcon() {
            if (!themeToggle) return;
            const isDark = html.getAttribute("data-bs-theme") === "dark";
            themeToggle.innerHTML = isDark
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';
        }

        // Auto-dismiss flash messages after 5 seconds.
        document.querySelectorAll(".alert-dismissible").forEach(function (alertEl) {
            setTimeout(function () {
                const instance = bootstrap.Alert.getOrCreateInstance(alertEl);
                instance.close();
            }, 5000);
        });
    });
})();
