import sqlite3
import json
import os
from typing import Dict, Any, List

# Get the directory of the current script
_current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up two levels to project root (src/robin -> src -> root)
_project_root = os.path.dirname(os.path.dirname(_current_dir))
DB_FILE = os.path.join(_project_root, "data", "robin.db")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create 'runs' table to store history of investigation runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        query TEXT NOT NULL,
        refined_query TEXT,
        results TEXT,
        filtered_results TEXT,
        scraped_content TEXT,
        summary TEXT
    );
    """)

    # Create 'scheduled_queries' table for automated monitoring
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        query_text TEXT NOT NULL,
        search_engines TEXT,
        schedule TEXT NOT NULL,
        last_run_timestamp TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)

    # Create 'artifacts' table to store extracted IOCs and other intelligence
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        artifact_type TEXT NOT NULL,
        value TEXT NOT NULL,
        context TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)

    # Create 'notifications' table for user alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_query_id INTEGER,
        run_id INTEGER,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        FOREIGN KEY (scheduled_query_id) REFERENCES scheduled_queries (id),
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)

    conn.commit()
    conn.close()

def save_run(run_data: Dict[str, Any]):
    """Saves a completed investigation run to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Convert list/dict fields to JSON strings for storage
    results_json = json.dumps(run_data.get("results", []))
    filtered_results_json = json.dumps(run_data.get("filtered", []))
    scraped_content_json = json.dumps(run_data.get("scraped", {}))

    cursor.execute("""
    INSERT INTO runs (timestamp, query, refined_query, results, filtered_results, scraped_content, summary)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_data.get("timestamp"),
        run_data.get("query"),
        run_data.get("refined"),
        results_json,
        filtered_results_json,
        scraped_content_json,
        run_data.get("summary")
    ))

    conn.commit()
    run_id = cursor.lastrowid
    conn.close()
    return run_id

def load_runs(max_items: int = 20) -> List[Dict[str, Any]]:
    """Loads the most recent investigation runs from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (max_items,))

    runs = []
    for row in cursor.fetchall():
        run = dict(row)
        # Deserialize JSON fields back into Python objects
        run['results'] = json.loads(run['results'])
        run['filtered_results'] = json.loads(run['filtered_results'])
        run['scraped_content'] = json.loads(run['scraped_content'])
        runs.append(run)

    conn.close()
    return runs

# --- Scheduled Query Management ---

def save_scheduled_query(name: str, query_text: str, schedule: str, search_engines: List[str] = None):
    """Saves a new scheduled query or updates an existing one by name."""
    conn = get_db_connection()
    cursor = conn.cursor()

    search_engines_json = json.dumps(search_engines) if search_engines else "[]"

    cursor.execute("""
    INSERT INTO scheduled_queries (name, query_text, schedule, search_engines, is_active)
    VALUES (?, ?, ?, ?, 1)
    ON CONFLICT(name) DO UPDATE SET
        query_text=excluded.query_text,
        schedule=excluded.schedule,
        search_engines=excluded.search_engines;
    """, (name, query_text, schedule, search_engines_json))

    conn.commit()
    conn.close()

def load_scheduled_queries() -> List[Dict[str, Any]]:
    """Loads all scheduled queries from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduled_queries ORDER BY name")

    queries = [dict(row) for row in cursor.fetchall()]
    for query in queries:
        query['search_engines'] = json.loads(query['search_engines'])

    conn.close()
    return queries

def delete_scheduled_query(query_id: int):
    """Deletes a scheduled query by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scheduled_queries WHERE id = ?", (query_id,))
    conn.commit()
    conn.close()

def update_scheduled_query_status(query_id: int, is_active: bool):
    """Activates or deactivates a scheduled query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE scheduled_queries SET is_active = ? WHERE id = ?", (1 if is_active else 0, query_id))
    conn.commit()
    conn.close()

def get_active_queries() -> List[Dict[str, Any]]:
    """
    Retrieves all active scheduled queries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduled_queries WHERE is_active = 1")

    active_queries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return active_queries

def update_last_run_timestamp(query_id: int, timestamp: str):
    """Updates the last run timestamp for a scheduled query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE scheduled_queries SET last_run_timestamp = ? WHERE id = ?", (timestamp, query_id))
    conn.commit()
    conn.close()

# --- Notifications Management ---

def create_notification(scheduled_query_id: int, run_id: int, message: str):
    """Creates a new notification entry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO notifications (scheduled_query_id, run_id, message, timestamp, is_read)
    VALUES (?, ?, ?, ?, 0)
    """, (scheduled_query_id, run_id, message, datetime.utcnow().isoformat() + "Z"))
    conn.commit()
    conn.close()

def load_notifications(read_status: bool = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Loads notifications from the database.
    :param read_status: If True, loads only read notifications. If False, loads only unread. If None, loads all.
    :param limit: Maximum number of notifications to load.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM notifications"
    params = []
    if read_status is not None:
        query += " WHERE is_read = ?"
        params.append(1 if read_status else 0)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))

    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notifications

def mark_notification_as_read(notification_id: int):
    """Marks a specific notification as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()

def get_unread_notifications_count() -> int:
    """Returns the count of unread notifications."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE is_read = 0")
    count = cursor.fetchone()[0]
    conn.close()
    return count

if __name__ == "__main__":
    print("Initializing Robin database...")
    initialize_database()
    print(f"Database created at {DB_FILE}")
    # Example usage:
    # print(load_runs())
