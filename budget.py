"""
budget.py
---------
Budget Management module: Set monthly per-category budgets, track
spending against them, show progress bars and warning alerts.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from database import get_connection, CATEGORIES
from expense import get_category_totals


def set_budget(user_id, category, month, limit_amount):
    if limit_amount is None or limit_amount <= 0:
        return False, "Budget limit must be greater than ₹0."
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO budget (user_id, category, month, limit_amount, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, category, month)
               DO UPDATE SET limit_amount = excluded.limit_amount""",
            (user_id, category, month, limit_amount, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, f"Budget for {category} ({month}) set to ₹{limit_amount:,.2f}."
    except Exception as e:  # pragma: no cover
        return False, f"Error setting budget: {e}"
    finally:
        conn.close()


def delete_budget(budget_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM budget WHERE id=?", (budget_id,))
        conn.commit()
        return True, "Budget removed."
    except Exception as e:  # pragma: no cover
        return False, f"Error deleting budget: {e}"
    finally:
        conn.close()


def get_budget_df(user_id, month):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, category, limit_amount FROM budget WHERE user_id=? AND month=? ORDER BY category",
        conn, params=(user_id, month),
    )
    conn.close()
    return df


def get_budget_progress(user_id, month):
    """Return a merged DataFrame: category, limit_amount, spent, pct_used."""
    budget_df = get_budget_df(user_id, month)
    if budget_df.empty:
        return budget_df

    start_date = f"{month}-01"
    # last day of month (safe generic approach)
    year, mon = map(int, month.split("-"))
    if mon == 12:
        next_month = f"{year + 1}-01-01"
    else:
        next_month = f"{year}-{mon + 1:02d}-01"
    end_date = (pd.to_datetime(next_month) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    spent_df = get_category_totals(user_id, start_date, end_date)
    merged = budget_df.merge(spent_df, on="category", how="left")
    merged["total"] = merged["total"].fillna(0)
    merged["pct_used"] = (merged["total"] / merged["limit_amount"] * 100).round(1)
    merged = merged.rename(columns={"total": "spent"})
    return merged


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
def render_budget_page(user_id):
    st.markdown("## 🎯 Budget Management")

    current_month = datetime.now().strftime("%Y-%m")

    tab_set, tab_track = st.tabs(["⚙️ Set Monthly Budget", "📊 Track Spending"])

    # ---------------- SET BUDGET ----------------
    with tab_set:
        with st.form("set_budget_form"):
            c1, c2 = st.columns(2)
            with c1:
                category = st.selectbox("Category", CATEGORIES)
                month = st.text_input("Month (YYYY-MM)", value=current_month)
            with c2:
                limit_amount = st.number_input("Monthly Limit (₹)", min_value=0.0, step=500.0, format="%.2f")
            submitted = st.form_submit_button("Save Budget", use_container_width=True)
            if submitted:
                success, msg = set_budget(user_id, category, month, limit_amount)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

        existing = get_budget_df(user_id, current_month)
        if not existing.empty:
            st.markdown(f"#### Current budgets for {current_month}")
            for row in existing.itertuples():
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{row.category}** — ₹{row.limit_amount:,.2f}")
                if c2.button("🗑️ Remove", key=f"del_budget_{row.id}"):
                    delete_budget(row.id)
                    st.rerun()

    # ---------------- TRACK SPENDING ----------------
    with tab_track:
        month = st.text_input("View budget progress for month (YYYY-MM)", value=current_month, key="track_month")
        progress_df = get_budget_progress(user_id, month)

        if progress_df.empty:
            st.info(f"No budgets set for {month} yet. Set one in the 'Set Monthly Budget' tab.")
            return

        for row in progress_df.itertuples():
            pct = min(row.pct_used / 100, 1.0)
            st.markdown(f"**{row.category}** — ₹{row.spent:,.2f} spent of ₹{row.limit_amount:,.2f} "
                        f"({row.pct_used:.1f}%)")
            st.progress(pct)

            if row.pct_used >= 100:
                st.error(f"🚨 Budget exceeded for **{row.category}**! "
                         f"Over by ₹{(row.spent - row.limit_amount):,.2f}.")
            elif row.pct_used >= 80:
                st.warning(f"⚠️ You have used {row.pct_used:.1f}% of your **{row.category}** budget. "
                           "Spend carefully for the rest of the month.")
            else:
                st.success(f"✅ {row.category} spending is on track.")
            st.markdown("---")
