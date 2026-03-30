const API_BASE = "";

const timerDisplay = document.getElementById("timerDisplay");
const sessionTypeBadge = document.getElementById("sessionTypeBadge");
const timerProgress = document.getElementById("timerProgress");
const timerProgressLabel = document.getElementById("timerProgressLabel");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");

const studyForm = document.getElementById("studyForm");
const sessionsList = document.getElementById("sessionsList");
const suggestionsList = document.getElementById("suggestionsList");
const dailyPlanList = document.getElementById("dailyPlanList");

const streakValue = document.getElementById("streakValue");
const pointsValue = document.getElementById("pointsValue");
const predictedFocus = document.getElementById("predictedFocus");
const difficultyField = document.getElementById("difficulty");
const focusRatingField = document.getElementById("focusRating");
const usernameDisplay = document.getElementById("usernameDisplay");
const subjectsDataList = document.getElementById("subjectsDataList");

const splashOverlay = document.getElementById("splashOverlay");
const splashForm = document.getElementById("splashForm");
const usernameInput = document.getElementById("usernameInput");
const subjectsImportanceList = document.getElementById("subjectsImportanceList");
const addSubjectRowBtn = document.getElementById("addSubjectRowBtn");

const difficultyRadios = document.querySelectorAll('input[name="difficultyPreset"]');
const priorityButtons = document.querySelectorAll(".priority-btn");

const STUDY_SECONDS = 25 * 60;
const BREAK_SECONDS = 5 * 60;

let timer = null;
let timeLeft = STUDY_SECONDS;
let isRunning = false;
let sessionType = "study";
let sessionStartedAt = null;
let currentSessionTotalSeconds = STUDY_SECONDS;

const PROFILE_STORAGE_KEY = "study_profile_v1";
let profile = null;


function createSubjectImportanceRow(subject = "", importance = 5) {
    const row = document.createElement("div");
    row.className = "subject-importance-row";
    row.innerHTML = `
        <input type="text" class="splash-subject" placeholder="Subject name" value="${subject}" required>
        <input type="number" class="splash-importance" min="1" max="10" step="1" value="${importance}" required>
    `;
    return row;
}


function mountDefaultSubjectRows() {
    subjectsImportanceList.innerHTML = "";
    subjectsImportanceList.appendChild(createSubjectImportanceRow("", 5));
    subjectsImportanceList.appendChild(createSubjectImportanceRow("", 5));
}


function readProfileForm() {
    const username = usernameInput.value.trim();
    const rows = Array.from(subjectsImportanceList.querySelectorAll(".subject-importance-row"));

    const subjects = rows
        .map((row) => {
            const subject = row.querySelector(".splash-subject").value.trim();
            const rawImportance = parseInt(row.querySelector(".splash-importance").value, 10);
            const importance = Number.isNaN(rawImportance) ? 5 : Math.max(1, Math.min(10, rawImportance));
            return { subject, importance };
        })
        .filter((item) => item.subject.length > 0);

    return { username, subjects };
}


function loadProfile() {
    try {
        const saved = localStorage.getItem(PROFILE_STORAGE_KEY);
        if (!saved) {
            return null;
        }
        const parsed = JSON.parse(saved);
        if (!parsed.username || !Array.isArray(parsed.subjects)) {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}


function saveProfile(nextProfile) {
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(nextProfile));
}


function updateUsernameUI() {
    const name = profile?.username || "-";
    if (usernameDisplay) {
        usernameDisplay.textContent = `Learner: ${name}`;
    }
}


function fillSubjectsDataList() {
    if (!subjectsDataList) {
        return;
    }

    subjectsDataList.innerHTML = "";
    (profile?.subjects || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = item.subject;
        subjectsDataList.appendChild(option);
    });
}


function maybeSetFocusBySubject(subject) {
    const match = (profile?.subjects || []).find(
        (item) => item.subject.toLowerCase() === subject.trim().toLowerCase()
    );

    if (!match) {
        return;
    }

    // Map 1-10 importance to 1-5 focus rating.
    const mapped = Math.max(1, Math.min(5, Math.round(match.importance / 2)));
    focusRatingField.value = String(mapped);

    priorityButtons.forEach((btn) => btn.classList.remove("active"));
    const bestMatchBtn = Array.from(priorityButtons).find(
        (btn) => parseInt(btn.dataset.focus, 10) === mapped
    );
    if (bestMatchBtn) {
        bestMatchBtn.classList.add("active");
    }
}


function applyProfileToUI() {
    updateUsernameUI();
    fillSubjectsDataList();
}


function setupSplash() {
    if (!splashOverlay || !splashForm) {
        return;
    }

    profile = loadProfile();

    if (profile) {
        splashOverlay.classList.remove("open");
        applyProfileToUI();
        return;
    }

    mountDefaultSubjectRows();
    splashOverlay.classList.add("open");

    addSubjectRowBtn.addEventListener("click", () => {
        subjectsImportanceList.appendChild(createSubjectImportanceRow("", 5));
    });

    splashForm.addEventListener("submit", (event) => {
        event.preventDefault();

        const draft = readProfileForm();

        if (!draft.username) {
            alert("Please enter a username.");
            return;
        }

        if (!draft.subjects.length) {
            alert("Please add at least one subject with importance.");
            return;
        }

        profile = draft;
        saveProfile(profile);
        applyProfileToUI();

        const firstSubject = profile.subjects[0]?.subject || "";
        if (firstSubject) {
            document.getElementById("subject").value = firstSubject;
            maybeSetFocusBySubject(firstSubject);
        }

        // Show demo instead of immediately going to app
        splashOverlay.classList.add("open");
        splashOverlay.style.display = "none";
        const demoOverlay = document.getElementById("demoOverlay");
        if (demoOverlay) {
            demoOverlay.style.display = "flex";
        }
    });
}


function formatTime(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}


function renderTimer() {
    timerDisplay.textContent = formatTime(timeLeft);
    sessionTypeBadge.textContent = sessionType === "study" ? "Study" : "Break";

    const progress = Math.max(0, Math.min(100, (timeLeft / currentSessionTotalSeconds) * 100));
    timerProgress.style.width = `${progress}%`;
    timerProgressLabel.textContent = `${Math.round(progress)}%`;
}


function getFormValues() {
    const subject = document.getElementById("subject").value.trim();
    const difficulty = difficultyField.value;
    const focusRating = parseInt(focusRatingField.value, 10);

    return { subject, difficulty, focusRating };
}


async function addSession(payload) {
    const response = await fetch(`${API_BASE}/add-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Unable to log session.");
    }
}


async function fetchSessions() {
    const response = await fetch(`${API_BASE}/sessions`);
    if (!response.ok) {
        throw new Error("Failed to fetch sessions.");
    }
    return response.json();
}


async function fetchRecommendations() {
    const response = await fetch(`${API_BASE}/recommendations`);
    if (!response.ok) {
        throw new Error("Failed to fetch recommendations.");
    }
    return response.json();
}


function renderSessions(sessions) {
    sessionsList.innerHTML = "";

    if (!sessions.length) {
        sessionsList.innerHTML = '<li class="empty">No sessions logged today yet.</li>';
        return;
    }

    sessions.forEach((session) => {
        const item = document.createElement("li");
        item.innerHTML = `
            <strong>${session.subject}</strong> (${session.difficulty})
            <br>
            Focus: ${session.focus_rating}/5 | ${session.duration_minutes} min | ${session.session_type}
        `;
        sessionsList.appendChild(item);
    });
}


function renderSuggestions(data) {
    suggestionsList.innerHTML = "";

    if (!data.suggestions.length) {
        suggestionsList.innerHTML = '<li class="empty">No suggestions yet.</li>';
    }

    data.suggestions.forEach((suggestion) => {
        const item = document.createElement("li");
        item.textContent = suggestion;
        suggestionsList.appendChild(item);
    });

    dailyPlanList.innerHTML = "";
    if (!data.daily_plan.length) {
        dailyPlanList.innerHTML = '<li class="empty">No plan yet. Add subjects in splash and log a session.</li>';
    }

    data.daily_plan.forEach((slot) => {
        const item = document.createElement("li");
        item.innerHTML = `<strong>Slot ${slot.slot}: ${slot.subject}</strong><br>${slot.session}<br>${slot.reason}`;
        dailyPlanList.appendChild(item);
    });

    streakValue.textContent = `${data.gamification.streak || 0} days`;
    pointsValue.textContent = `${data.gamification.points || 0} pts`;
    predictedFocus.textContent = `${data.predicted_focus_score || 0} / 5`;
}


async function refreshDashboard() {
    try {
        const [sessions, recommendations] = await Promise.all([
            fetchSessions(),
            fetchRecommendations()
        ]);

        renderSessions(sessions);
        renderSuggestions(recommendations);
    } catch (error) {
        alert(error.message);
    }
}


async function completeCurrentTimerSession() {
    const { subject, difficulty, focusRating } = getFormValues();

    if (!subject) {
        alert("Please add a subject name before running the timer.");
        return;
    }

    const endedAt = new Date();
    const startedAt = sessionStartedAt || new Date(endedAt.getTime() - (sessionType === "study" ? STUDY_SECONDS : BREAK_SECONDS) * 1000);

    const payload = {
        subject,
        difficulty,
        focus_rating: focusRating,
        session_type: sessionType,
        duration_minutes: sessionType === "study" ? 25 : 5,
        started_at: startedAt.toISOString(),
        ended_at: endedAt.toISOString()
    };

    await addSession(payload);
    await refreshDashboard();
}


function tick() {
    if (timeLeft <= 0) {
        clearInterval(timer);
        timer = null;
        isRunning = false;

        completeCurrentTimerSession()
            .then(() => {
                // Toggle session mode automatically when current cycle is complete.
                if (sessionType === "study") {
                    sessionType = "break";
                    timeLeft = BREAK_SECONDS;
                    currentSessionTotalSeconds = BREAK_SECONDS;
                    alert("Study session complete. Break session started.");
                } else {
                    sessionType = "study";
                    timeLeft = STUDY_SECONDS;
                    currentSessionTotalSeconds = STUDY_SECONDS;
                    alert("Break complete. Back to study mode.");
                }
                sessionStartedAt = null;
                renderTimer();
            })
            .catch((error) => {
                alert(error.message);
                sessionStartedAt = null;
                renderTimer();
            });

        return;
    }

    timeLeft -= 1;
    renderTimer();
}


function startTimer() {
    if (isRunning) {
        return;
    }

    const { subject } = getFormValues();
    if (!subject) {
        alert("Please enter a subject first.");
        return;
    }

    isRunning = true;
    sessionStartedAt = sessionStartedAt || new Date();
    timer = setInterval(tick, 1000);
}


function pauseTimer() {
    if (!isRunning) {
        return;
    }

    clearInterval(timer);
    timer = null;
    isRunning = false;
}


function resetTimer() {
    clearInterval(timer);
    timer = null;
    isRunning = false;
    sessionType = "study";
    timeLeft = STUDY_SECONDS;
    currentSessionTotalSeconds = STUDY_SECONDS;
    sessionStartedAt = null;
    renderTimer();
}


function bindDifficultyOptions() {
    difficultyRadios.forEach((radio) => {
        radio.addEventListener("change", () => {
            difficultyField.value = radio.value;
        });
    });
}


function bindPriorityOptions() {
    priorityButtons.forEach((button) => {
        button.addEventListener("click", () => {
            priorityButtons.forEach((btn) => btn.classList.remove("active"));
            button.classList.add("active");
            focusRatingField.value = button.dataset.focus;
        });
    });
}


studyForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const { subject, difficulty, focusRating } = getFormValues();
    if (!subject) {
        alert("Subject name is required.");
        return;
    }

    try {
        await addSession({
            subject,
            difficulty,
            focus_rating: focusRating,
            session_type: "study",
            duration_minutes: 25,
            started_at: new Date().toISOString(),
            ended_at: new Date().toISOString()
        });
        await refreshDashboard();
        alert("Session logged successfully.");
    } catch (error) {
        alert(error.message);
    }
});


document.getElementById("subject").addEventListener("change", (event) => {
    maybeSetFocusBySubject(event.target.value || "");
});

document.getElementById("subject").addEventListener("blur", (event) => {
    maybeSetFocusBySubject(event.target.value || "");
});


startBtn.addEventListener("click", startTimer);
pauseBtn.addEventListener("click", pauseTimer);
resetBtn.addEventListener("click", resetTimer);

bindDifficultyOptions();
bindPriorityOptions();
setupSplash();

renderTimer();
predictedFocus.textContent = "0 / 5";
refreshDashboard();

// Setup demo tour button
const startDemoBtn = document.getElementById("startDemoBtn");
if (startDemoBtn) {
    startDemoBtn.addEventListener("click", () => {
        window.location.href = "Dash.html";
    });
}
