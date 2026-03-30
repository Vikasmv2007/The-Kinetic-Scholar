📘 The Kinetic Scholar

A smart study companion designed to help students track progress, manage subjects, and stay productive with built-in tools like timers, dashboards, and planners.

🚀 Overview

The Kinetic Scholar is a lightweight web-based productivity and study tracking system that enables students to:

📊 Monitor academic progress
⏱️ Track study time using a timer
📚 Organize subjects and study data
🧠 Stay consistent with a “Do It Now” productivity UI
📈 Visualize performance via dashboards

This project combines frontend (HTML, CSS, JS) with a Python backend and database support.

🧩 Features
📊 Dashboard
Visual overview of study progress
Performance insights
⏱️ Study Timer
Focus sessions (Pomodoro-style usage possible)
Tracks time spent on tasks
📚 Subject Management
Add and manage subjects
Organize study data efficiently
📈 Data Tracking
Store and retrieve study activity
Persistent database support
⚡ Do-It-Now UI
Encourages instant productivity
Minimal friction task interface
👤 Profile System
Personalized study tracking
🛠️ Tech Stack
Frontend
HTML
CSS
JavaScript
Backend
Python
Database
SQLite (study_planner.db)
Other Tools
Flask (assumed from app.py)
Custom JS modules (nav.js, profile.js)
📁 Project Structure
The-Kinetic-Scholar/
│
├── app.py                 # Main backend application
├── database.py            # Database handling
├── study_planner.db       # SQLite database
├── requirements.txt       # Python dependencies
│
├── index.html             # Main entry UI
├── Dash.html              # Dashboard page
├── Data.html              # Data tracking page
├── Subjects.html          # Subject management
├── Timer.html             # Study timer
├── do-it-now-ui.html      # Productivity UI
│
├── script.js              # Core JS logic
├── nav.js                 # Navigation logic
├── profile.js             # Profile handling
│
├── style.css              # Styling
│
└── IMPLEMENTATION_SUMMARY.md
⚙️ Installation & Setup
1️⃣ Clone the repository
git clone https://github.com/Vikasmv2007/The-Kinetic-Scholar.git
cd The-Kinetic-Scholar
2️⃣ Install dependencies
pip install -r requirements.txt
3️⃣ Run the application
python app.py
4️⃣ Open in browser
http://127.0.0.1:5000
📸 Usage
Open the dashboard to view progress
Add subjects and study data
Use the timer to track study sessions
Monitor improvement over time
🎯 Future Improvements
📱 Mobile responsiveness improvements
🔔 Notifications & reminders
☁️ Cloud sync
📊 Advanced analytics
👥 Multi-user support
