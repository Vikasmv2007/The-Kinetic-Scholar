(function () {
    const DARK_MODE_KEY = "kinetic_dark_mode";

    const pageMap = {
        "": "dash",
        "index.html": "dash",
        "planner": "dash",
        "dash.html": "dash",
        "subjects.html": "plan",
        "timer.html": "focus",
        "data.html": "data"
    };

    const path = window.location.pathname.split("/").pop().toLowerCase();
    const activeKey = pageMap[path] || "";

    const links = document.querySelectorAll("a[data-nav]");
    links.forEach((link) => {
        const isActive = link.dataset.nav === activeKey;
        link.classList.toggle("nav-active", isActive);
        if (isActive) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });

        const style = document.createElement("style");
        style.textContent = `
            body.dark-mode {
                background:
                    radial-gradient(circle at 85% 8%, rgba(0, 227, 253, 0.14), transparent 26%),
                    radial-gradient(circle at 12% 88%, rgba(235, 245, 0, 0.1), transparent 30%),
                    #07090f !important;
                color: #eef2ff !important;
            }

            body.dark-mode h1,
            body.dark-mode h2,
            body.dark-mode h3,
            body.dark-mode h4,
            body.dark-mode p,
            body.dark-mode span,
            body.dark-mode small,
            body.dark-mode a,
            body.dark-mode label,
            body.dark-mode li,
            body.dark-mode strong {
                color: #eef2ff !important;
            }

            body.dark-mode header,
            body.dark-mode nav {
                background: rgba(9, 11, 18, 0.94) !important;
                border-color: rgba(255, 255, 255, 0.18) !important;
            }

            body.dark-mode section,
            body.dark-mode article,
            body.dark-mode .card,
            body.dark-mode .splash-card,
            body.dark-mode .neo-shadow,
            body.dark-mode .neo-shadow-lg,
            body.dark-mode .hard-shadow {
                background-color: rgba(16, 20, 32, 0.86) !important;
                border-color: rgba(255, 255, 255, 0.18) !important;
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45) !important;
            }

            body.dark-mode input,
            body.dark-mode textarea,
            body.dark-mode select {
                color: #ffffff !important;
                border-color: rgba(255, 255, 255, 0.24) !important;
                background: rgba(255, 255, 255, 0.08) !important;
            }

            body.dark-mode .splash-overlay {
                background: rgba(2, 4, 10, 0.85) !important;
            }

            /* Keep button/fill color themes intact while ensuring text readability. */
            body.dark-mode button,
            body.dark-mode .btn,
            body.dark-mode .cta-btn {
                color: #ffffff;
            }

            #darkModeToggle {
                position: fixed;
                right: 14px;
                top: 88px;
                z-index: 95;
                border: 3px solid #0c0f0f;
                background: #ebf500;
                color: #0c0f0f;
                box-shadow: 3px 3px 0 #0c0f0f;
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                cursor: pointer;
            }

            body.dark-mode #darkModeToggle {
                border-color: #eef2ff;
                box-shadow: 3px 3px 0 #eef2ff;
                color: #0c0f0f !important;
            }

            @media (max-width: 768px) {
                #darkModeToggle {
                    top: 84px;
                    right: 10px;
                    padding: 7px 9px;
                    font-size: 10px;
                }
            }
        `;
        document.head.appendChild(style);

        function setDarkMode(enabled) {
                document.documentElement.classList.toggle("dark", enabled);
                document.body.classList.toggle("dark-mode", enabled);
                localStorage.setItem(DARK_MODE_KEY, enabled ? "1" : "0");
                const toggleBtn = document.getElementById("darkModeToggle");
                if (toggleBtn) {
                        toggleBtn.textContent = enabled ? "Light" : "Dark";
                }
        }

        const savedDarkMode = localStorage.getItem(DARK_MODE_KEY) === "1";
        setDarkMode(savedDarkMode);

        const darkModeToggle = document.createElement("button");
        darkModeToggle.id = "darkModeToggle";
        darkModeToggle.type = "button";
        darkModeToggle.setAttribute("aria-label", "Toggle dark mode");
        darkModeToggle.textContent = savedDarkMode ? "Light" : "Dark";
        darkModeToggle.addEventListener("click", () => {
                const next = !document.body.classList.contains("dark-mode");
                setDarkMode(next);
        });
        document.body.appendChild(darkModeToggle);
})();
