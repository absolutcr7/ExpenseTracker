"""
expense.py
----------
Expense Management module: Add / Edit / Delete / Filter / View expenses.
"""

from datetime import datetime, date

import pandas as pd
import streamlit as st

from database import get_connection, CATEGORIES


# --------------------------------------------------------------------------
# Data access helpers
# --------------------------------------------------------------------------
def add_expense(user_id, amount, category, expense_date, note):
    if amount is None or amount <= 0:
        return False, "Amount must be greater than ₹0."
    if category not in CATEGORIES:
        return False, "Please select a valid category."
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, amount, category, str(expense_date), note,
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "Expense added successfully."
    except Exception as e:  # pragma: no cover
        return False, f"Error adding expense: {e}"
    finally:
        conn.close()


def update_expense(expense_id, amount, category, expense_date, note):
    if amount is None or amount <= 0:
        return False, "Amount must be greater than ₹0."
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE expenses SET amount=?, category=?, date=?, note=? WHERE id=?",
            (amount, category, str(expense_date), note, expense_id),
        )
        conn.commit()
        return True, "Expense updated successfully."
    except Exception as e:  # pragma: no cover
        return False, f"Error updating expense: {e}"
    finally:
        conn.close()


def delete_expense(expense_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()
        return True, "Expense record deleted."
    except Exception as e:  # pragma: no cover
        return False, f"Error deleting expense: {e}"
    finally:
        conn.close()


def get_expense_df(user_id, category_filter=None, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT id, amount, category, date, note FROM expenses WHERE user_id=?"
    params = [user_id]
    if category_filter and category_filter != "All":
        query += " AND category=?"
        params.append(category_filter)
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [str(start_date), str(end_date)]
    query += " ORDER BY date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_total_expense(user_id, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE user_id=?"
    params = [user_id]
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [str(start_date), str(end_date)]
    total = conn.execute(query, params).fetchone()["total"]
    conn.close()
    return total or 0


def get_category_totals(user_id, start_date=None, end_date=None):
    """Return a DataFrame of category -> total spent (for charts)."""
    conn = get_connection()
    query = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id=?"
    params = [user_id]
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [str(start_date), str(end_date)]
    query += " GROUP BY category ORDER BY total DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
def render_expense_page(user_id):
    st.markdown("## 🧾 Expense Management")

    tab_add, tab_history = st.tabs(["➕ Add Expense", "📜 View / Filter / Edit / Delete"])

    # ---------------- ADD ----------------
    with tab_add:
        with st.form("add_expense_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%.2f")
                category = st.selectbox("Category", CATEGORIES)
            with c2:
                expense_date = st.date_input("Date", value=date.today())
                note = st.text_input("Note (optional)")
            submitted = st.form_submit_button("Add Expense", use_container_width=True)
            if submitted:
                success, msg = add_expense(user_id, amount, category, expense_date, note)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

    # ---------------- HISTORY + FILTER ----------------
    with tab_history:
        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            category_filter = st.selectbox("Filter by Category", ["All"] + CATEGORIES)

        df = get_expense_df(user_id, category_filter)
        if df.empty:
            st.info("No expense records found for this filter.")
            return

        display_df = df.copy()
        display_df["amount"] = display_df["amount"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(
            display_df.rename(columns={
                "amount": "Amount", "category": "Category", "date": "Date", "note": "Note"
            })[["Date", "Category", "Amount", "Note"]],
            use_container_width=True, hide_index=True,
        )

        st.markdown("#### ✏️ Edit or 🗑️ Delete a Record")
        options = {
            f"#{row.id} | {row.date} | {row.category} | ₹{row.amount:,.2f}": row.id
            for row in df.itertuples()
        }
        selected_label = st.selectbox("Select a record", list(options.keys()))
        selected_id = options[selected_label]
        selected_row = df[df["id"] == selected_id].iloc[0]

        with st.form("edit_expense_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0,
                                              value=float(selected_row["amount"]), format="%.2f")
                new_category = st.selectbox(
                    "Category", CATEGORIES,
                    index=CATEGORIES.index(selected_row["category"]) if selected_row["category"] in CATEGORIES else 0,
                )
            with c2:
                new_date = st.date_input(
                    "Date",
                    value=datetime.strptime(selected_row["date"], "%Y-%m-%d").date(),
                )
                new_note = st.text_input("Note", value=selected_row["note"] or "")

            bcol1, bcol2 = st.columns(2)
            update_clicked = bcol1.form_submit_button("💾 Update", use_container_width=True)
            delete_clicked = bcol2.form_submit_button("🗑️ Delete", use_container_width=True)

            if update_clicked:
                success, msg = update_expense(selected_id, new_amount, new_category, new_date, new_note)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()
            if delete_clicked:
                success, msg = delete_expense(selected_id)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()
