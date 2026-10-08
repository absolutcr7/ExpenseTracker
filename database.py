"""
database.py
------------
Handles all SQLite database setup and low-level access for the
Personal Expense Tracker application.

Tables
    users     - registered app users
    income    - income transactions   (FK -> users)
    expenses  - expense transactions  (FK -> users)
    budget    - per-category monthly budgets (FK -> users)

Run this file directly (python database.py) to (re)create the database
and populate it with sample/demo data.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
import random

DB_NAME = "expenses.db"

# Fixed category list used across the whole app (Income + Expense)
CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills",
    "Education", "Entertainment", "Medical", "Other",
]

INCOME_SOURCES = ["Salary", "Business", "Freelance", "Gift", "Investment", "Other"]


def get_connection():
    """Return a new SQLite connection with foreign keys enabled.

    A fresh connection is created per call because Streamlit re-runs the
    script on every interaction; this keeps things simple and thread-safe.
    """
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn = get_connection()
    cur = conn.cursor()

    # ---------------- users ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # ---------------- income ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            source TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Income',
            date TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # ---------------- expenses ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # ---------------- budget ----------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            month TEXT NOT NULL,              -- format: YYYY-MM
            limit_amount REAL NOT NULL CHECK (limit_amount > 0),
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, category, month)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Simple SHA-256 hash with a static pepper.

    NOTE: For a real production system use bcrypt/argon2 with a per-user
    salt. SHA-256 is used here to keep the mini-project dependency-free.
    """
    salted = f"expense_tracker_salt_{password}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def seed_sample_data():
    """Insert a demo user with sample income/expense/budget rows,
    but only if that demo user does not already exist.
    Credentials -> username: demo | password: demo1234
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", ("demo",))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return  # already seeded

    now = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("demo", "demo@example.com", hash_password("demo1234"), now),
    )
    user_id = cur.lastrowid

    # ---- sample income (last 2 months) ----
    income_rows = [
        (user_id, 45000, "Salary", "Income", _days_ago(40), "Monthly salary", now),
        (user_id, 5000, "Freelance", "Income", _days_ago(25), "Logo design gig", now),
        (user_id, 45000, "Salary", "Income", _days_ago(10), "Monthly salary", now),
        (user_id, 1500, "Gift", "Income", _days_ago(5), "Birthday gift", now),
    ]
    cur.executemany(
        "INSERT INTO income (user_id, amount, source, category, date, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        income_rows,
    )

    # ---- sample expenses (spread across categories & dates) ----
    sample_expenses = [
        ("Food", 450), ("Food", 320), ("Transport", 150), ("Shopping", 2200),
        ("Bills", 1800), ("Education", 1200), ("Entertainment", 600),
        ("Medical", 350), ("Food", 280), ("Transport", 100), ("Other", 500),
        ("Bills", 999), ("Shopping", 1500), ("Food", 390), ("Transport", 220),
    ]
    expense_rows = []
    for i, (cat, amt) in enumerate(sample_expenses):
        expense_rows.append(
            (user_id, amt, cat, _days_ago(random.randint(1, 45)), f"Sample {cat.lower()} expense", now)
        )
    cur.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        expense_rows,
    )

    # ---- sample budgets for current month ----
    this_month = datetime.now().strftime("%Y-%m")
    budget_rows = [
        (user_id, "Food", this_month, 3000, now),
        (user_id, "Transport", this_month, 1500, now),
        (user_id, "Shopping", this_month, 4000, now),
        (user_id, "Bills", this_month, 3500, now),
        (user_id, "Entertainment", this_month, 1200, now),
    ]
    cur.executemany(
        "INSERT INTO budget (user_id, category, month, limit_amount, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        budget_rows,
    )

    conn.commit()
    conn.close()


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


if __name__ == "__main__":
    # Allows running:  python database.py   to (re)initialise the DB manually
    init_db()
    seed_sample_data()
    print(f"Database '{DB_NAME}' initialised and seeded with demo data.")
    print("Demo login -> username: demo | password: demo1234")
