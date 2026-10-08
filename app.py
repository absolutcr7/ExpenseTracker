"""
app.py
------
Main entry point for the Personal Expense Tracker Streamlit application.

Run with:
    streamlit run app.py

Responsibilities:
    - Page configuration & global CSS styling
    - Database initialisation + demo data seeding (runs once, automatically)
    - Session-state based authentication gate
    - Sidebar navigation and routing to each module
"""

import streamlit as st

from database import init_db, seed_sample_data
from auth import render_auth_page, is_logged_in, logout
from dashboard import render_dashboard
from income import render_income_page
from expense import render_expense_page
from budget import render_budget_page
from reports import render_reports_page
from profile import render_profile_page


# --------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Personal Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Global CSS — modern, professional look
# --------------------------------------------------------------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background-color: #F7F9FC;
    }
    section[data-testid="stSidebar"] {
        background-color: #10243E;
    }
    section[data-testid="stSidebar"] * {
        color: #F1F5F9 !important;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E9F0;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 2px 6px rgba(16, 36, 62, 0.06);
    }
    div[data-testid="stMetricValue"] {
        color: #10243E;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }
    div.stButton > button, div.stDownloadButton > button {
        background-color: #1F6FEB;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #164FB3;
        color: white;
    }
    h1, h2, h3 {
        color: #10243E;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# One-time setup: create tables + seed a demo account (safe to call every run)
# --------------------------------------------------------------------------
init_db()
seed_sample_data()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


# --------------------------------------------------------------------------
# Main routing
# --------------------------------------------------------------------------
def main():
    if not is_logged_in():
        render_auth_page()
        return

    user_id = st.session_state["user_id"]
    username = st.session_state["username"]

    # ---------------- SIDEBAR NAVIGATION ----------------
    with st.sidebar:
        st.markdown(
            f"<h2 style='margin-bottom:0;'>💰 ExpenseTracker</h2>"
            f"<p style='opacity:0.75;margin-top:2px;'>Hello, <b>{username}</b> 👋</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["🏠 Dashboard", "💵 Income", "🧾 Expenses", "🎯 Budget", "📑 Reports & Analytics", "👤 Profile"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
        st.caption("Personal Expense Tracker v1.0 · SE Mini Project")

    # ---------------- PAGE ROUTING ----------------
    if page == "🏠 Dashboard":
        render_dashboard(user_id, username)
    elif page == "💵 Income":
        render_income_page(user_id)
    elif page == "🧾 Expenses":
        render_expense_page(user_id)
    elif page == "🎯 Budget":
        render_budget_page(user_id)
    elif page == "📑 Reports & Analytics":
        render_reports_page(user_id)
    elif page == "👤 Profile":
        render_profile_page(user_id)


if __name__ == "__main__":
    main()
