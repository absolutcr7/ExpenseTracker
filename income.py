"""
income.py
---------
Income Management module: Add / Edit / Delete / View income records.
"""

from datetime import datetime, date

import pandas as pd
import streamlit as st

from database import get_connection, INCOME_SOURCES


# --------------------------------------------------------------------------
# Data access helpers
# --------------------------------------------------------------------------
def add_income(user_id, amount, source, income_date, note):
    if amount is None or amount <= 0:
        return False, "Amount must be greater than ₹0."
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO income (user_id, amount, source, category, date, note, created_at) "
            "VALUES (?, ?, ?, 'Income', ?, ?, ?)",
            (user_id, amount, source, str(income_date), note,
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "Income added successfully."
    except Exception as e:  # pragma: no cover
        return False, f"Error adding income: {e}"
    finally:
        conn.close()


def update_income(income_id, amount, source, income_date, note):
    if amount is None or amount <= 0:
        return False, "Amount must be greater than ₹0."
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE income SET amount=?, source=?, date=?, note=? WHERE id=?",
            (amount, source, str(income_date), note, income_id),
        )
        conn.commit()
        return True, "Income updated successfully."
    except Exception as e:  # pragma: no cover
        return False, f"Error updating income: {e}"
    finally:
        conn.close()


def delete_income(income_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM income WHERE id=?", (income_id,))
        conn.commit()
        return True, "Income record deleted."
    except Exception as e:  # pragma: no cover
        return False, f"Error deleting income: {e}"
    finally:
        conn.close()


def get_income_df(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, amount, source, date, note FROM income WHERE user_id=? ORDER BY date DESC, id DESC",
        conn, params=(user_id,),
    )
    conn.close()
    return df


def get_total_income(user_id, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT COALESCE(SUM(amount),0) as total FROM income WHERE user_id=?"
    params = [user_id]
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [str(start_date), str(end_date)]
    total = conn.execute(query, params).fetchone()["total"]
    conn.close()
    return total or 0


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
def render_income_page(user_id):
    st.markdown("## 💵 Income Management")

    tab_add, tab_history = st.tabs(["➕ Add Income", "📜 View / Edit / Delete History"])

    # ---------------- ADD ----------------
    with tab_add:
        with st.form("add_income_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
                source = st.selectbox("Source", INCOME_SOURCES)
            with c2:
                income_date = st.date_input("Date", value=date.today())
                note = st.text_input("Note (optional)")
            submitted = st.form_submit_button("Add Income", use_container_width=True)
            if submitted:
                success, msg = add_income(user_id, amount, source, income_date, note)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()

    # ---------------- HISTORY ----------------
    with tab_history:
        df = get_income_df(user_id)
        if df.empty:
            st.info("No income records yet. Add your first one from the 'Add Income' tab.")
            return

        display_df = df.copy()
        display_df["amount"] = display_df["amount"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(
            display_df.rename(columns={
                "amount": "Amount", "source": "Source", "date": "Date", "note": "Note"
            })[["Date", "Source", "Amount", "Note"]],
            use_container_width=True, hide_index=True,
        )

        st.markdown("#### ✏️ Edit or 🗑️ Delete a Record")
        options = {
            f"#{row.id} | {row.date} | {row.source} | ₹{row.amount:,.2f}": row.id
            for row in df.itertuples()
        }
        selected_label = st.selectbox("Select a record", list(options.keys()))
        selected_id = options[selected_label]
        selected_row = df[df["id"] == selected_id].iloc[0]

        with st.form("edit_income_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0,
                                              value=float(selected_row["amount"]), format="%.2f")
                new_source = st.selectbox(
                    "Source", INCOME_SOURCES,
                    index=INCOME_SOURCES.index(selected_row["source"]) if selected_row["source"] in INCOME_SOURCES else 0,
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
                success, msg = update_income(selected_id, new_amount, new_source, new_date, new_note)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()
            if delete_clicked:
                success, msg = delete_income(selected_id)
                st.success(msg) if success else st.error(msg)
                if success:
                    st.rerun()
