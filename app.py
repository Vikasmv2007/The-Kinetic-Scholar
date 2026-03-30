from datetime import datetime, timedelta
import json
import os
from urllib import error, request as urlrequest
from urllib.parse import urlencode

from flask import Flask, jsonify, request, send_from_directory

from database import get_app_state, get_connection, init_db, update_points_and_streak, save_user_distribution, load_user_distribution


app = Flask(__name__, static_folder=".", static_url_path="")

DEFAULT_SUPABASE_URL = "https://cmjahbaoooliaxqfabrh.supabase.co"
DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_nqCOnL40ojDXrc6JJ2VS0g_u_wl6FrH"


def get_supabase_config():
    supabase_url = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL).strip().rstrip("/")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", DEFAULT_SUPABASE_ANON_KEY).strip()
    return supabase_url, supabase_key


def supabase_request(method, table_name, query=None, payload=None):
    """Execute a Supabase PostgREST request and return parsed JSON."""
    supabase_url, supabase_key = get_supabase_config()
    if not supabase_key:
        raise RuntimeError("Supabase key missing. Set SUPABASE_ANON_KEY.")

    endpoint = f"{supabase_url}/rest/v1/{table_name}"
    if query:
        endpoint = f"{endpoint}?{urlencode(query)}"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urlrequest.Request(
        endpoint,
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Supabase error ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach Supabase: {exc.reason}") from exc


def save_splash_profile_to_supabase(username, subjects):
    """Persist onboarding profile to Supabase using the PostgREST API."""
    supabase_url, supabase_key = get_supabase_config()
    table_name = os.getenv("SUPABASE_SPLASH_TABLE", "splash_profiles").strip()

    if not supabase_key:
        raise RuntimeError(
            "Supabase key missing. Set SUPABASE_ANON_KEY environment variable."
        )

    endpoint = f"{supabase_url}/rest/v1/{table_name}"
    payload = {
        "username": username,
        "subjects": subjects,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    req = urlrequest.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Supabase error ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach Supabase: {exc.reason}") from exc


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def reset_local_demo_data():
    """Clear local sessions and reset gamification so each new demo user starts from zero."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM sessions")
    cursor.execute(
        """
        UPDATE app_state
        SET points = 0,
            streak = 0,
            last_study_date = NULL
        WHERE id = 1
        """
    )
    connection.commit()
    connection.close()


def get_subject_stats():
    """Build quick stats used by recommendations and plan generation."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT subject,
               COUNT(*) as total_count,
               SUM(CASE WHEN difficulty = 'Hard' THEN 1 ELSE 0 END) as hard_count,
               AVG(focus_rating) as avg_focus,
               MAX(created_at) as last_studied_at
        FROM sessions
        WHERE session_type = 'study'
        GROUP BY subject
        """
    )

    rows = cursor.fetchall()
    connection.close()
    return [row_to_dict(row) for row in rows]


def predict_focus_score(subject):
    """Predict next focus score using weighted average of recent sessions."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT focus_rating
        FROM sessions
        WHERE subject = ? AND session_type = 'study'
        ORDER BY id DESC
        LIMIT 5
        """,
        (subject,),
    )
    rows = cursor.fetchall()
    connection.close()

    if not rows:
        return 3.0

    ratings = [row["focus_rating"] for row in rows]
    weights = [5, 4, 3, 2, 1][: len(ratings)]
    weighted_sum = sum(r * w for r, w in zip(ratings, weights))
    return round(weighted_sum / sum(weights), 2)


def generate_recommendations():
    """Create recommendations based on focus trends and study history."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM sessions
        WHERE session_type = 'study'
        ORDER BY id DESC
        LIMIT 12
        """
    )
    recent_sessions = [row_to_dict(row) for row in cursor.fetchall()]
    connection.close()

    recommendations = []

    if recent_sessions:
        latest = recent_sessions[0]
        latest_subject = latest["subject"]

        if latest["focus_rating"] < 3:
            recommendations.append(
                f"Focus is low ({latest['focus_rating']}/5). Switch from {latest_subject} to a lighter subject for the next session."
            )

        same_subject_streak = 0
        for session in recent_sessions:
            if session["subject"] == latest_subject:
                same_subject_streak += 1
            else:
                break

        if same_subject_streak >= 2:
            recommendations.append(
                f"You studied {latest_subject} {same_subject_streak} times in a row. Rotate to another subject to avoid burnout."
            )

    subject_stats = get_subject_stats()
    now = datetime.now()

    for stat in subject_stats:
        if stat["total_count"] > 2:
            recommendations.append(
                f"{stat['subject']} has been studied {stat['total_count']} times. Schedule a revision block later today instead of repeating now."
            )

        if stat["last_studied_at"]:
            last_time = datetime.fromisoformat(stat["last_studied_at"])
            if now - last_time > timedelta(hours=6):
                recommendations.append(
                    f"It has been more than 6 hours since {stat['subject']}. Good time for a quick revision."
                )

    if not recommendations:
        recommendations.append("Great momentum. Continue with the next planned subject.")

    # Keep response compact and actionable.
    return recommendations[:6]


def generate_daily_plan():
    """Generate a simple adaptive plan with subject rotation and difficulty balancing."""
    stats = get_subject_stats()

    if not stats:
        return []

    # Prioritize lower average focus subjects first, but avoid too many hard sessions in sequence.
    ordered = sorted(stats, key=lambda s: (s["avg_focus"] or 3, -(s["hard_count"] or 0)))

    plan = []
    hard_in_a_row = 0
    slot = 1

    while slot <= 6:
        for item in ordered:
            is_hard_heavy = (item["hard_count"] or 0) >= 2

            if is_hard_heavy and hard_in_a_row >= 1:
                continue

            plan.append(
                {
                    "slot": slot,
                    "subject": item["subject"],
                    "session": "25 min study + 5 min break",
                    "reason": "Auto-rotated to improve consistency and reduce burnout.",
                }
            )

            slot += 1
            if is_hard_heavy:
                hard_in_a_row += 1
            else:
                hard_in_a_row = 0

            if slot > 6:
                break

        if not ordered:
            break

    return plan


def minutes_to_label(minutes):
    hours = minutes // 60
    mins = minutes % 60
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def build_ai_study_flow(subjects, day_type="normal", total_minutes=360, exam_date=None):
    """Build a customizable plan for normal/exam days using subject importance weights."""
    if not subjects:
        return []

    normalized = []
    for item in subjects:
        subject = str(item.get("subject", "")).strip()
        if not subject:
            continue
        try:
            importance = int(item.get("importance", 5))
        except (TypeError, ValueError):
            importance = 5
        normalized.append({"subject": subject, "importance": max(1, min(10, importance))})

    if not normalized:
        return []

    # Exam mode emphasizes high-importance subjects with denser deep-work blocks.
    deep_ratio = 0.78 if day_type == "exam" else 0.62
    deep_minutes_total = int(total_minutes * deep_ratio)
    review_minutes_total = max(30, total_minutes - deep_minutes_total)

    weighted = sorted(normalized, key=lambda s: s["importance"], reverse=True)
    total_weight = sum(s["importance"] for s in weighted)

    blocks = []
    current_minutes = 8 * 60
    slot = 1

    for item in weighted:
        allocated = int((item["importance"] / total_weight) * deep_minutes_total)
        allocated = max(35, allocated)

        blocks.append(
            {
                "slot": slot,
                "time": f"{current_minutes // 60:02d}:{current_minutes % 60:02d}",
                "type": "Deep Work",
                "subject": item["subject"],
                "duration": minutes_to_label(allocated),
                "note": (
                    "Exam-priority block"
                    if day_type == "exam"
                    else "Primary learning block"
                ),
            }
        )
        slot += 1
        current_minutes += allocated

        blocks.append(
            {
                "slot": slot,
                "time": f"{current_minutes // 60:02d}:{current_minutes % 60:02d}",
                "type": "Break",
                "subject": "Recovery",
                "duration": "10m",
                "note": "Hydrate + mobility",
            }
        )
        slot += 1
        current_minutes += 10

    # Add review rotation block at the end.
    review_subject = weighted[0]["subject"] if day_type == "exam" else weighted[-1]["subject"]
    blocks.append(
        {
            "slot": slot,
            "time": f"{current_minutes // 60:02d}:{current_minutes % 60:02d}",
            "type": "Review",
            "subject": review_subject,
            "duration": minutes_to_label(review_minutes_total),
            "note": "Past-paper practice" if day_type == "exam" else "Active recall + recap",
        }
    )

    meta = {
        "day_type": day_type,
        "exam_date": exam_date,
        "total_minutes": total_minutes,
        "message": (
            "AI plan tuned for exam preparation."
            if day_type == "exam"
            else "AI plan tuned for a balanced normal day."
        ),
    }

    return {"meta": meta, "study_flow": blocks}


def parse_hours_value(item):
    """Normalize row hours from common Supabase schema variants."""
    hours = item.get("hours_studied")
    if hours is None:
        hours = item.get("hours")
    if hours is None and item.get("duration_minutes") is not None:
        try:
            return max(0.0, float(item.get("duration_minutes")) / 60.0)
        except (TypeError, ValueError):
            return 0.0

    try:
        return max(0.0, float(hours or 0))
    except (TypeError, ValueError):
        return 0.0


def parse_date_value(item):
    """Normalize row date from common Supabase schema variants."""
    raw = (
        item.get("studied_at")
        or item.get("study_date")
        or item.get("created_at")
        or item.get("date")
    )
    if not raw:
        return None

    text = str(raw).strip()
    if not text:
        return None

    # Accept ISO date or datetime formats.
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def load_latest_splash_subjects():
    """Load latest subject profile from Supabase splash table."""
    table_name = os.getenv("SUPABASE_SPLASH_TABLE", "splash_profiles").strip()
    rows = supabase_request(
        "GET",
        table_name,
        query={"select": "username,subjects,created_at", "order": "created_at.desc", "limit": 1},
    )

    if not rows:
        return {"username": "", "subjects": []}

    row = rows[0]
    subjects = row.get("subjects")
    if not isinstance(subjects, list):
        subjects = []

    cleaned = []
    for item in subjects:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()
        if not subject:
            continue
        try:
            importance = int(item.get("importance", 5))
        except (TypeError, ValueError):
            importance = 5
        cleaned.append({"subject": subject, "importance": max(1, min(10, importance))})

    return {"username": str(row.get("username", "")).strip(), "subjects": cleaned}


def build_supabase_insights():
    """Build subject and weekly analytics strictly from Supabase hours data."""
    hours_table = os.getenv("SUPABASE_HOURS_TABLE", "hours_studied").strip()
    weekly_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    weekly_map = {d: 0.0 for d in weekly_days}

    profile = load_latest_splash_subjects()
    profile_subjects = profile.get("subjects", [])

    subject_hours = {item["subject"]: 0.0 for item in profile_subjects}
    subject_last_studied = {item["subject"]: None for item in profile_subjects}
    importance_map = {item["subject"]: item["importance"] for item in profile_subjects}

    rows = supabase_request(
        "GET",
        hours_table,
        query={"select": "*", "order": "created_at.desc", "limit": 2000},
    )

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    for row in rows:
        if not isinstance(row, dict):
            continue

        subject = str(row.get("subject") or row.get("name") or "").strip()
        if not subject:
            continue

        hours = parse_hours_value(row)
        row_date = parse_date_value(row)

        if subject not in subject_hours:
            subject_hours[subject] = 0.0
            subject_last_studied[subject] = None
            importance_map[subject] = 5

        subject_hours[subject] += hours

        if row_date is not None:
            previous = subject_last_studied.get(subject)
            if previous is None or row_date > previous:
                subject_last_studied[subject] = row_date

            if week_start <= row_date <= week_end:
                day_key = weekly_days[row_date.weekday()]
                weekly_map[day_key] += hours

    total_hours_all = sum(subject_hours.values())
    total_hours_week = sum(weekly_map.values())

    subjects_payload = []
    for subject, hours in subject_hours.items():
        percent = 0 if total_hours_all <= 0 else round((hours / total_hours_all) * 100)
        last_studied = subject_last_studied.get(subject)
        subjects_payload.append(
            {
                "subject": subject,
                "importance": importance_map.get(subject, 5),
                "hours_studied": round(hours, 2),
                "progress_percent": max(0, min(100, percent)),
                "last_studied": last_studied.isoformat() if last_studied else None,
            }
        )

    subjects_payload.sort(key=lambda item: (-item["importance"], item["subject"].lower()))

    distribution_payload = [
        {
            "subject": item["subject"],
            "hours_studied": item["hours_studied"],
            "percent": item["progress_percent"],
        }
        for item in subjects_payload
    ]

    weekly_payload = [
        {"day": day, "hours": round(weekly_map[day], 2)}
        for day in weekly_days
    ]

    # Load user-configured distribution
    user_dist = load_user_distribution()

    return {
        "username": profile.get("username", ""),
        "subjects": subjects_payload,
        "distribution": distribution_payload,
        "user_distribution": user_dist,
        "weekly": weekly_payload,
        "total_hours_week": round(total_hours_week, 2),
        "total_hours_all": round(total_hours_all, 2),
    }


@app.route("/")
def serve_index():
    return send_from_directory(".", "Dash.html")


@app.route("/planner")
def serve_planner():
    return send_from_directory(".", "index.html")


@app.post("/add-session")
def add_session():
    data = request.get_json(force=True)

    subject = data.get("subject", "").strip()
    difficulty = data.get("difficulty", "Medium")
    focus_rating = int(data.get("focus_rating", 3))
    session_type = data.get("session_type", "study")
    duration_minutes = int(data.get("duration_minutes", 25))
    started_at = data.get("started_at")
    ended_at = data.get("ended_at")

    if not subject:
        return jsonify({"error": "Subject is required."}), 400

    if difficulty not in ["Easy", "Medium", "Hard"]:
        return jsonify({"error": "Difficulty must be Easy, Medium, or Hard."}), 400

    if focus_rating < 1 or focus_rating > 5:
        return jsonify({"error": "Focus rating must be between 1 and 5."}), 400

    created_at = datetime.now().isoformat(timespec="seconds")

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO sessions
        (subject, difficulty, focus_rating, session_type, duration_minutes, started_at, ended_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subject,
            difficulty,
            focus_rating,
            session_type,
            duration_minutes,
            started_at,
            ended_at,
            created_at,
        ),
    )
    connection.commit()
    connection.close()

    update_points_and_streak(duration_minutes, focus_rating, session_type)

    return jsonify({"message": "Session added successfully."}), 201


@app.post("/api/splash-profile")
def save_splash_profile():
    data = request.get_json(force=True)

    username = str(data.get("username", "")).strip()
    subjects = data.get("subjects", [])
    reset_local_data = bool(data.get("reset_local_data", True))

    if not username:
        return jsonify({"error": "Username is required."}), 400

    if not isinstance(subjects, list) or not subjects:
        return jsonify({"error": "At least one subject with importance is required."}), 400

    cleaned_subjects = []
    for item in subjects:
        if not isinstance(item, dict):
            continue

        subject = str(item.get("subject", "")).strip()
        importance = item.get("importance", 0)

        try:
            importance = int(importance)
        except (TypeError, ValueError):
            return jsonify({"error": f"Importance for '{subject or 'subject'}' must be a number."}), 400

        if not subject:
            continue

        if importance < 1 or importance > 10:
            return jsonify({"error": f"Importance for '{subject}' must be between 1 and 10."}), 400

        cleaned_subjects.append({"subject": subject, "importance": importance})

    if not cleaned_subjects:
        return jsonify({"error": "Provide at least one valid subject."}), 400

    try:
        saved = save_splash_profile_to_supabase(username, cleaned_subjects)
        if reset_local_data:
            reset_local_demo_data()
        return jsonify({"message": "Splash profile saved.", "data": saved}), 201
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/sessions")
def get_sessions():
    today = datetime.now().date().isoformat()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT *
        FROM sessions
        WHERE DATE(created_at) = ?
        ORDER BY id DESC
        """,
        (today,),
    )
    sessions = [row_to_dict(row) for row in cursor.fetchall()]
    connection.close()

    return jsonify(sessions)


@app.get("/recommendations")
def get_recommendations():
    recommendations = generate_recommendations()
    app_state = get_app_state()
    daily_plan = generate_daily_plan()

    subject_for_prediction = daily_plan[0]["subject"] if daily_plan else ""
    predicted_focus = predict_focus_score(subject_for_prediction) if subject_for_prediction else 0.0

    if not daily_plan:
        recommendations = ["No data yet. Add your first study session to unlock recommendations."]

    return jsonify(
        {
            "suggestions": recommendations,
            "daily_plan": daily_plan,
            "gamification": app_state,
            "predicted_focus_score": predicted_focus,
        }
    )


@app.post("/api/ai-plan")
def generate_ai_plan():
    data = request.get_json(force=True)

    subjects = data.get("subjects", [])
    day_type = str(data.get("day_type", "normal")).strip().lower()
    exam_date = str(data.get("exam_date", "")).strip() or None

    try:
        total_minutes = int(data.get("total_minutes", 360))
    except (TypeError, ValueError):
        return jsonify({"error": "total_minutes must be a number."}), 400

    if day_type not in ["normal", "exam"]:
        return jsonify({"error": "day_type must be either 'normal' or 'exam'."}), 400

    if total_minutes < 60 or total_minutes > 900:
        return jsonify({"error": "total_minutes must be between 60 and 900."}), 400

    plan = build_ai_study_flow(
        subjects=subjects,
        day_type=day_type,
        total_minutes=total_minutes,
        exam_date=exam_date,
    )

    if not plan:
        return jsonify({"error": "Add at least one valid subject first."}), 400

    return jsonify(plan)


@app.get("/api/insights")
def get_insights():
    try:
        payload = build_supabase_insights()
        return jsonify(payload)
    except RuntimeError as exc:
        # Keep UI stable with zero state when Supabase table/schema is not ready.
        return (
            jsonify(
                {
                    "username": "",
                    "subjects": [],
                    "distribution": [],
                    "user_distribution": [],
                    "weekly": [
                        {"day": "MON", "hours": 0.0},
                        {"day": "TUE", "hours": 0.0},
                        {"day": "WED", "hours": 0.0},
                        {"day": "THU", "hours": 0.0},
                        {"day": "FRI", "hours": 0.0},
                        {"day": "SAT", "hours": 0.0},
                        {"day": "SUN", "hours": 0.0},
                    ],
                    "total_hours_week": 0.0,
                    "total_hours_all": 0.0,
                    "error": str(exc),
                }
            ),
            200,
        )


def generate_ai_distribution_suggestion(subjects):
    """Generate AI-suggested distribution based on subject importance levels.
    
    Algorithm:
    - Higher importance subjects get more allocation
    - Uses weighted distribution: importance / total_importance
    - Ensures all subjects have at least 5% (minimum viable time)
    - Allocates remaining percentage proportionally to importance
    """
    if not subjects or not isinstance(subjects, list):
        return []
    
    # Clean and filter subjects
    valid_subjects = []
    for item in subjects:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()
        importance = item.get("importance", 5)
        try:
            importance = int(importance)
            importance = max(1, min(10, importance))
        except (TypeError, ValueError):
            importance = 5
        
        if subject:
            valid_subjects.append({"subject": subject, "importance": importance})
    
    if not valid_subjects:
        return []
    
    # Calculate total importance weight
    total_importance = sum(s["importance"] for s in valid_subjects)
    num_subjects = len(valid_subjects)
    
    # Minimum 5% per subject if feasible
    min_per_subject = 5
    reserved_percent = min_per_subject * num_subjects
    
    suggested = []
    
    if reserved_percent > 100:
        # Too many subjects, use weighted distribution only
        for item in valid_subjects:
            percent = round((item["importance"] / total_importance) * 100)
            suggested.append({
                "subject": item["subject"],
                "percent": percent,
                "importance": item["importance"]
            })
    else:
        # First allocate minimum 5% to each, then distribute remaining based on importance
        remaining_percent = 100 - reserved_percent
        
        for item in valid_subjects:
            # Base 5% + proportional share of remaining
            allocated = min_per_subject + round((item["importance"] / total_importance) * remaining_percent)
            suggested.append({
                "subject": item["subject"],
                "percent": allocated,
                "importance": item["importance"]
            })
    
    # Normalize to ensure exactly 100%
    total = sum(s["percent"] for s in suggested)
    if total != 100:
        difference = 100 - total
        # Adjust the highest importance subject
        if suggested:
            max_idx = max(range(len(suggested)), key=lambda i: suggested[i]["importance"])
            suggested[max_idx]["percent"] += difference
    
    # Sort by importance (highest first)
    suggested.sort(key=lambda x: (-x["importance"], x["subject"]))
    
    return suggested


@app.post("/api/ai-distribution")
def get_ai_distribution():
    """Get AI-suggested distribution based on subject importance."""
    try:
        # Load subjects from splash profile
        profile = load_latest_splash_subjects()
        subjects = profile.get("subjects", [])
        
        if not subjects:
            return jsonify({"error": "No subjects found. Please set up your profile first."}), 400
        
        suggested = generate_ai_distribution_suggestion(subjects)
        
        if not suggested:
            return jsonify({"error": "Unable to generate suggestion."}), 400
        
        return jsonify({
            "message": "AI-generated distribution suggestion",
            "distribution": suggested
        }), 200
    
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/distribution")
def save_distribution():
    data = request.get_json(force=True)
    distribution = data.get("distribution", [])

    if not isinstance(distribution, list):
        return jsonify({"error": "Distribution must be a list."}), 400

    # Validate and clean distribution
    cleaned_distribution = []
    total_percent = 0

    for item in distribution:
        if not isinstance(item, dict):
            continue

        subject = str(item.get("subject", "")).strip()
        percent = item.get("percent", 0)

        try:
            percent = int(percent)
        except (TypeError, ValueError):
            return jsonify({"error": f"Percent for '{subject}' must be a number."}), 400

        if not subject:
            continue

        if percent < 0 or percent > 100:
            return jsonify({"error": f"Percent for '{subject}' must be between 0 and 100."}), 400

        cleaned_distribution.append({"subject": subject, "percent": percent})
        total_percent += percent

    if total_percent != 100:
        return jsonify({"error": f"Distribution percentages must add up to 100% (currently {total_percent}%)."}), 400

    if not cleaned_distribution:
        return jsonify({"error": "Provide at least one valid subject with percentage."}), 400

    try:
        save_user_distribution(cleaned_distribution)
        return jsonify({"message": "Distribution saved successfully.", "data": cleaned_distribution}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
