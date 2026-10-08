"""
reports.py
----------
Reports & Analytics module:
    - Monthly report
    - Weekly report
    - Category-wise report
    - CSV download
    - Pie / Bar / Line charts & spending trends
"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_connection
from expense import get_expense_df, get_category_totals
from income import get_income_df


def _date_range_df(user_id, start_date, end_date):
    """Return combined income & expense rows for a date range."""
    conn = get_connection()
    income = pd.read_sql_query(
        "SELECT date, amount, 'Income' as type, source as category FROM income "
        "WHERE user_id=? AND date BETWEEN ? AND ?",
        conn, params=(user_id, str(start_date), str(end_date)),
    )
    expense = pd.read_sql_query(
        "SELECT date, amount, 'Expense' as type, category FROM expenses "
        "WHERE user_id=? AND date BETWEEN ? AND ?",
        conn, params=(user_id, str(start_date), str(end_date)),
    )
    conn.close()
    return pd.concat([income, expense], ignore_index=True)


def render_reports_page(user_id):
    st.markdown("## 📑 Reports & Analytics")

    tab_monthly, tab_weekly, tab_category, tab_analytics = st.tabs(
        ["📆 Monthly Report", "🗓️ Weekly Report", "🏷️ Category-wise Report", "📈 Analytics"]
    )

    # ---------------- MONTHLY REPORT ----------------
    with tab_monthly:
        month = st.text_input("Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"), key="monthly_rep")
        year, mon = map(int, month.split("-"))
        start_date = f"{month}-01"
        end_date = (pd.to_datetime(f"{year}-{mon:02d}-01") + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")

        df = _date_range_df(user_id, start_date, end_date)
        if df.empty:
            st.info("No transactions found for this month.")
        else:
            total_income = df[df["type"] == "Income"]["amount"].sum()
            total_expense = df[df["type"] == "Expense"]["amount"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Income", f"₹{total_income:,.2f}")
            c2.metric("Expense", f"₹{total_expense:,.2f}")
            c3.metric("Net Savings", f"₹{total_income - total_expense:,.2f}")

            display = df.sort_values("date", ascending=False).copy()
            display["amount"] = display["amount"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display.rename(columns={
                "date": "Date", "amount": "Amount", "type": "Type", "category": "Category/Source"
            }), use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ Download Monthly Report (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"monthly_report_{month}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ---------------- WEEKLY REPORT ----------------
    with tab_weekly:
        week_end = st.date_input("Week ending on", value=datetime.now().date(), key="weekly_rep")
        week_start = week_end - timedelta(days=6)
        st.caption(f"Showing transactions from **{week_start}** to **{week_end}**")

        df = _date_range_df(user_id, week_start, week_end)
        if df.empty:
            st.info("No transactions found for this week.")
        else:
            total_income = df[df["type"] == "Income"]["amount"].sum()
            total_expense = df[df["type"] == "Expense"]["amount"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Income", f"₹{total_income:,.2f}")
            c2.metric("Expense", f"₹{total_expense:,.2f}")
            c3.metric("Net Savings", f"₹{total_income - total_expense:,.2f}")

            display = df.sort_values("date", ascending=False).copy()
            display["amount"] = display["amount"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(display.rename(columns={
                "date": "Date", "amount": "Amount", "type": "Type", "category": "Category/Source"
            }), use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ Download Weekly Report (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"weekly_report_{week_start}_to_{week_end}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ---------------- CATEGORY-WISE REPORT ----------------
    with tab_category:
        cat_df = get_category_totals(user_id)
        if cat_df.empty:
            st.info("No expense data available yet.")
        else:
            cat_df_display = cat_df.copy()
            cat_df_display["total"] = cat_df_display["total"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(cat_df_display.rename(columns={"category": "Category", "total": "Total Spent"}),
                         use_container_width=True, hide_index=True)

            fig = px.bar(cat_df, x="category", y="total", color="category", text_auto=".2s",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=False, height=380, yaxis_title="Amount (₹)", xaxis_title="Category")
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                "⬇️ Download Category-wise Report (CSV)",
                data=cat_df.to_csv(index=False).encode("utf-8"),
                file_name="category_wise_report.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ---------------- ANALYTICS ----------------
    with tab_analytics:
        st.markdown("#### 📈 Spending Trends & Visual Analytics")
        expense_df = get_expense_df(user_id)
        income_df = get_income_df(user_id)

        if expense_df.empty and income_df.empty:
            st.info("Add some transactions to unlock analytics.")
            return

        # Pie chart - category split
        cat_df = get_category_totals(user_id)
        if not cat_df.empty:
            colp, colb = st.columns(2)
            with colp:
                st.caption("Pie Chart — Category Split")
                fig_pie = px.pie(cat_df, names="category", values="total", hole=0.4)
                fig_pie.update_layout(height=340, margin=dict(t=10, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)
            with colb:
                st.caption("Bar Chart — Category Comparison")
                fig_bar = px.bar(cat_df, x="category", y="total", color="category")
                fig_bar.update_layout(height=340, showlegend=False, margin=dict(t=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

        # Line chart - daily spending trend
        if not expense_df.empty:
            st.caption("Line Chart — Daily Spending Trend")
            trend = expense_df.groupby("date", as_index=False)["amount"].sum().sort_values("date")
            fig_line = px.line(trend, x="date", y="amount", markers=True)
            fig_line.update_layout(height=360, yaxis_title="Amount (₹)", xaxis_title="Date")
            st.plotly_chart(fig_line, use_container_width=True)

        # Income vs Expense over time
        if not expense_df.empty or not income_df.empty:
            st.caption("Line Chart — Income vs Expense Over Time")
            inc_trend = income_df.groupby("date", as_index=False)["amount"].sum().rename(columns={"amount": "Income"})
            exp_trend = expense_df.groupby("date", as_index=False)["amount"].sum().rename(columns={"amount": "Expense"})
            merged = pd.merge(inc_trend, exp_trend, on="date", how="outer").fillna(0).sort_values("date")
            fig_cmp = px.line(merged, x="date", y=["Income", "Expense"], markers=True)
            fig_cmp.update_layout(height=360, yaxis_title="Amount (₹)", xaxis_title="Date")
            st.plotly_chart(fig_cmp, use_container_width=True)
