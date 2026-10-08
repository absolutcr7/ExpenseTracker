"""
dashboard.py
------------
Main Dashboard: Total Income, Total Expense, Current Balance,
Monthly Summary chart, and Recent Transactions.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import get_connection
from income import get_total_income, get_income_df
from expense import get_total_expense, get_expense_df, get_category_totals


def get_monthly_summary(user_id, months=6):
    """Return a DataFrame with income & expense totals for the last N months."""
    conn = get_connection()
    income_q = pd.read_sql_query(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as income "
        "FROM income WHERE user_id=? GROUP BY month",
        conn, params=(user_id,),
    )
    expense_q = pd.read_sql_query(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as expense "
        "FROM expenses WHERE user_id=? GROUP BY month",
        conn, params=(user_id,),
    )
    conn.close()

    merged = pd.merge(income_q, expense_q, on="month", how="outer").fillna(0)
    merged = merged.sort_values("month").tail(months)
    return merged


def render_dashboard(user_id, username):
    st.markdown(f"## 📊 Welcome back, {username}!")
    st.caption(f"Here's your financial overview as of {datetime.now().strftime('%d %b %Y')}.")

    total_income = get_total_income(user_id)
    total_expense = get_total_expense(user_id)
    balance = total_income - total_expense

    # ---------------- METRIC CARDS ----------------
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Income", f"₹{total_income:,.2f}")
    c2.metric("💸 Total Expense", f"₹{total_expense:,.2f}")
    c3.metric(
        "🏦 Current Balance",
        f"₹{balance:,.2f}",
        delta=f"{'Surplus' if balance >= 0 else 'Deficit'}",
        delta_color="normal" if balance >= 0 else "inverse",
    )

    st.markdown("---")

    # ---------------- MONTHLY SUMMARY ----------------
    st.markdown("### 📅 Monthly Summary (last 6 months)")
    summary_df = get_monthly_summary(user_id)
    if summary_df.empty:
        st.info("No transactions yet. Add income or expenses to see your monthly summary here.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary_df["month"], y=summary_df["income"], name="Income", marker_color="#2E7D32"))
        fig.add_trace(go.Bar(x=summary_df["month"], y=summary_df["expense"], name="Expense", marker_color="#C62828"))
        fig.update_layout(
            barmode="group", height=380, margin=dict(t=30, b=10, l=10, r=10),
            yaxis_title="Amount (₹)", xaxis_title="Month",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    col_pie, col_recent = st.columns([1, 1.3])

    # ---------------- CATEGORY SPLIT ----------------
    with col_pie:
        st.markdown("### 🥧 Spending by Category")
        cat_df = get_category_totals(user_id)
        if cat_df.empty:
            st.info("No expenses recorded yet.")
        else:
            fig2 = px.pie(cat_df, names="category", values="total", hole=0.45,
                           color_discrete_sequence=px.colors.sequential.Teal)
            fig2.update_traces(textinfo="percent+label")
            fig2.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # ---------------- RECENT TRANSACTIONS ----------------
    with col_recent:
        st.markdown("### 🧾 Recent Transactions")
        income_df = get_income_df(user_id).head(5)
        income_df = income_df.assign(type="Income", category=income_df.get("source", "Income"))
        expense_df = get_expense_df(user_id).head(5)
        expense_df = expense_df.assign(type="Expense")

        combined = pd.concat([
            income_df[["date", "type", "category", "amount", "note"]],
            expense_df[["date", "type", "category", "amount", "note"]],
        ])
        if combined.empty:
            st.info("No recent transactions.")
        else:
            combined = combined.sort_values("date", ascending=False).head(8)
            combined["amount"] = combined.apply(
                lambda r: f"+₹{r['amount']:,.2f}" if r["type"] == "Income" else f"-₹{r['amount']:,.2f}", axis=1
            )
            st.dataframe(
                combined.rename(columns={
                    "date": "Date", "type": "Type", "category": "Category/Source",
                    "amount": "Amount", "note": "Note",
                }),
                use_container_width=True, hide_index=True,
            )
