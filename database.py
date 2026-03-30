import sqlite3
from datetime import datetime


DB_NAME = "study_planner.db"


def get_connection():
    """Return a SQLite connection with dict-like row access."""
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create required tables if they do not exist."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            focus_rating INTEGER NOT NULL,
            session_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            points INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            last_study_date TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_distribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL UNIQUE,
            target_percent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Ensure a single state row is always available.
    cursor.execute(
        """
        INSERT OR IGNORE INTO app_state (id, points, streak, last_study_date)
        VALUES (1, 0, 0, NULL)
        """
    )

    connection.commit()
    connection.close()


def update_points_and_streak(duration_minutes, focus_rating, session_type):
    """Update gamification values after a session is logged."""
    if session_type != "study":
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT points, streak, last_study_date FROM app_state WHERE id = 1")
    state = cursor.fetchone()

    today = datetime.now().date()
    last_date = (
        datetime.strptime(state["last_study_date"], "%Y-%m-%d").date()
        if state["last_study_date"]
        else None
    )

    if last_date is None:
        new_streak = 1
    elif (today - last_date).days == 0:
        new_streak = state["streak"]
    elif (today - last_date).days == 1:
        new_streak = state["streak"] + 1
    else:
        new_streak = 1

    # Points reward time investment and quality of focus.
    earned_points = int(duration_minutes * 0.5) + (focus_rating * 2)
    new_points = state["points"] + earned_points

    cursor.execute(
        """
        UPDATE app_state
        SET points = ?, streak = ?, last_study_date = ?
        WHERE id = 1
        """,
        (new_points, new_streak, today.isoformat()),
    )

    connection.commit()
    connection.close()


def get_app_state():
    """Retrieve current gamification state."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT points, streak, last_study_date FROM app_state WHERE id = 1")
    row = cursor.fetchone()
    connection.close()

    if row:
        return {"points": row["points"], "streak": row["streak"]}
    return {"points": 0, "streak": 0}


def save_user_distribution(distribution_list):
    """Save or update user-configured subject distribution percentages."""
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now().isoformat()

    # Clear existing distribution
    cursor.execute("DELETE FROM user_distribution")

    # Insert new distribution
    for item in distribution_list:
        subject = str(item.get("subject", "")).strip()
        percent = int(item.get("percent", 0))
        if subject and 0 <= percent <= 100:
            cursor.execute(
                """
                INSERT INTO user_distribution (subject, target_percent, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (subject, percent, now, now),
            )

    connection.commit()
    connection.close()


def load_user_distribution():
    """Load user-configured subject distribution percentages."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT subject, target_percent FROM user_distribution
        ORDER BY subject ASC
        """
    )
    rows = cursor.fetchall()
    connection.close()

    return [
        {
            "subject": row["subject"],
            "percent": row["target_percent"],
        }
        for row in rows
    ]


def get_app_state():
    """Fetch points and streak values for dashboard display."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT points, streak, last_study_date FROM app_state WHERE id = 1")
    state = cursor.fetchone()
    connection.close()

    return {
        "points": state["points"],
        "streak": state["streak"],
        "last_study_date": state["last_study_date"],
    }
