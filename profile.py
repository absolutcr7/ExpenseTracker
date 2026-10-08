"""
profile.py
----------
Profile module: update username/email, change password, and
show a quick account summary.
"""

import streamlit as st

from auth import update_profile, update_password, logout
from income import get_total_income
from expense import get_total_expense


def render_profile_page(user_id):
    st.markdown("## 👤 My Profile")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total Income Recorded", f"₹{get_total_income(user_id):,.2f}")
    with c2:
        st.metric("Total Expense Recorded", f"₹{get_total_expense(user_id):,.2f}")

    st.markdown("---")

    tab_details, tab_password = st.tabs(["✏️ Update Details", "🔒 Change Password"])

    # ---------------- UPDATE DETAILS ----------------
    with tab_details:
        with st.form("update_profile_form"):
            username = st.text_input("Username", value=st.session_state.get("username", ""))
            email = st.text_input("Email", value=st.session_state.get("email", ""))
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
            if submitted:
                success, msg = update_profile(user_id, username, email)
                st.success(msg) if success else st.error(msg)

    # ---------------- CHANGE PASSWORD ----------------
    with tab_password:
        with st.form("change_password_form", clear_on_submit=True):
            old_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Update Password", use_container_width=True)
            if submitted:
                success, msg = update_password(user_id, old_password, new_password, confirm_password)
                st.success(msg) if success else st.error(msg)

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
