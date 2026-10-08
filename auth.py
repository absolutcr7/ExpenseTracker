"""
auth.py
-------
Authentication module: registration, login, logout and session
management for the Personal Expense Tracker.

Session state keys used across the app:
    st.session_state['logged_in']  -> bool
    st.session_state['user_id']    -> int
    st.session_state['username']   -> str
    st.session_state['email']      -> str
"""

import re
import sqlite3
from datetime import datetime

import streamlit as st

from database import get_connection, hash_password


EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+\@[\w\-]+\.[a-zA-Z]{2,}$")


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------
def _validate_registration(username, email, password, confirm_password):
    """Return (is_valid, error_message)."""
    if not username or not email or not password or not confirm_password:
        return False, "All fields are required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if password != confirm_password:
        return False, "Password and Confirm Password do not match."
    return True, ""


# --------------------------------------------------------------------------
# Core auth functions
# --------------------------------------------------------------------------
def register_user(username, email, password, confirm_password):
    """Create a new user account.

    Returns (success: bool, message: str)
    """
    is_valid, err = _validate_registration(username, email, password, confirm_password)
    if not is_valid:
        return False, err

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username.strip(), email.strip().lower(), hash_password(password),
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "Account created successfully! Please log in."
    except sqlite3.IntegrityError as e:
        # UNIQUE constraint failed on username or email
        if "username" in str(e):
            return False, "That username is already taken."
        return False, "An account with that email already exists."
    except Exception as e:  # pragma: no cover - generic safety net
        return False, f"Unexpected error while registering: {e}"
    finally:
        conn.close()


def login_user(identifier, password):
    """Authenticate using username OR email + password.

    Returns (success: bool, message_or_user: str | sqlite3.Row)
    """
    if not identifier or not password:
        return False, "Please enter both username/email and password."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier.strip(), identifier.strip().lower()),
        )
        user = cur.fetchone()
        if user is None:
            return False, "No account found with that username/email."
        if user["password_hash"] != hash_password(password):
            return False, "Incorrect password. Please try again."
        return True, user
    except Exception as e:  # pragma: no cover
        return False, f"Unexpected error while logging in: {e}"
    finally:
        conn.close()


def start_session(user):
    """Populate st.session_state after a successful login."""
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["email"] = user["email"]


def logout():
    """Clear all session state related to the logged-in user."""
    for key in ("logged_in", "user_id", "username", "email"):
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["logged_in"] = False


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def update_password(user_id, old_password, new_password, confirm_password):
    """Change a user's password after verifying the old one."""
    if not old_password or not new_password or not confirm_password:
        return False, "All password fields are required."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
    if new_password != confirm_password:
        return False, "New password and confirmation do not match."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row is None:
            return False, "User not found."
        if row["password_hash"] != hash_password(old_password):
            return False, "Current password is incorrect."
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        conn.commit()
        return True, "Password updated successfully."
    except Exception as e:  # pragma: no cover
        return False, f"Unexpected error: {e}"
    finally:
        conn.close()


def update_profile(user_id, username, email):
    """Update a user's username/email (used by profile.py)."""
    if not username or not email:
        return False, "Username and email cannot be empty."
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET username = ?, email = ? WHERE id = ?",
            (username.strip(), email.strip().lower(), user_id),
        )
        conn.commit()
        st.session_state["username"] = username.strip()
        st.session_state["email"] = email.strip().lower()
        return True, "Profile updated successfully."
    except sqlite3.IntegrityError:
        return False, "That username or email is already in use by another account."
    except Exception as e:  # pragma: no cover
        return False, f"Unexpected error: {e}"
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Streamlit UI for the login / register screen
# --------------------------------------------------------------------------
def render_auth_page():
    """Render the Login / Register tabs shown when nobody is logged in."""
    st.markdown(
        "<h1 style='text-align:center;'>💰 Personal Expense Tracker</h1>"
        "<p style='text-align:center; color:#6b7280;'>Track smarter. Spend wiser.</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        # ---------------- LOGIN ----------------
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                identifier = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                if submitted:
                    success, result = login_user(identifier, password)
                    if success:
                        start_session(result)
                        st.success(f"Welcome back, {result['username']}!")
                        st.rerun()
                    else:
                        st.error(result)
            st.caption("Demo account → username: **demo**  |  password: **demo1234**")

        # ---------------- REGISTER ----------------
        with tab_register:
            with st.form("register_form", clear_on_submit=True):
                username = st.text_input("Username")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                if submitted:
                    success, message = register_user(username, email, password, confirm_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
