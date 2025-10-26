# --- Streamlit Healthcare Monitoring AI Agent (Week 2) ---
import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os
import plotly.express as px

# ---------------- Database Setup ----------------
DB_PATH = "health_data.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def init_db():
    cur.execute('''
    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        time TEXT NOT NULL,
        taken INTEGER DEFAULT 0
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS health_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        steps INTEGER DEFAULT 0,
        calories INTEGER DEFAULT 0
    )''')
    conn.commit()

init_db()

# ---------------- Page Title ----------------
st.set_page_config(page_title="Healthcare Monitoring AI Agent", layout="wide")
st.title("🩺 Healthcare Monitoring AI Agent — Week 2 (Streamlit Edition)")

tabs = st.tabs(["💊 Medications", "📈 Health Metrics", "📊 Upload & Analytics"])

# =====================================================
# TAB 1 — MEDICATION MANAGER
# =====================================================
with tabs[0]:
    st.header("Medication Manager")

    name = st.text_input("Medicine Name")
    time = st.text_input("Time (HH:MM)", "08:30")
    if st.button("Add Medication"):
        if name and time:
            cur.execute("INSERT INTO medications (name, time) VALUES (?, ?)", (name.strip(), time.strip()))
            conn.commit()
            st.success(f"✅ Added {name} at {time}")
        else:
            st.error("Please fill in both fields.")

    if st.button("View Schedule"):
        meds = pd.read_sql("SELECT * FROM medications ORDER BY time", conn)
        st.dataframe(meds)

    # --- Mark Taken ---
    med_id = st.number_input("Enter Medication ID to mark as taken", min_value=1, step=1)
    if st.button("Mark as Taken"):
        cur.execute("UPDATE medications SET taken=1 WHERE id=?", (int(med_id),))
        conn.commit()
        st.success(f"Marked ID {int(med_id)} as taken")

    # --- Reset Taken ---
    if st.button("Reset All 'Taken' Flags"):
        cur.execute("UPDATE medications SET taken=0")
        conn.commit()
        st.info("Reset all medications to not taken.")

    # --- Interaction Checker ---
    st.subheader("Check Drug Interaction")
    drug_a = st.text_input("Drug A")
    drug_b = st.text_input("Drug B")
    if st.button("Check Interaction"):
        if not os.path.exists("drug_interactions.csv"):
            st.error("drug_interactions.csv not found. Please add one in your repo.")
        else:
            df = pd.read_csv("drug_interactions.csv")
            found = df[
                ((df["drug_a"].str.lower() == drug_a.lower()) & (df["drug_b"].str.lower() == drug_b.lower())) |
                ((df["drug_a"].str.lower() == drug_b.lower()) & (df["drug_b"].str.lower() == drug_a.lower()))
            ]
            if not found.empty:
                st.warning(found.iloc[0]["interaction"])
            else:
                st.success("✅ No known interactions found in local database.")

# =====================================================
# TAB 2 — HEALTH METRICS
# =====================================================
with tabs[1]:
    st.header("Health Metrics Tracker")

    date = st.date_input("Date", datetime.date.today())
    steps = st.number_input("Steps", min_value=0, value=0)
    calories = st.number_input("Calories", min_value=0, value=0)

    if st.button("Save Metrics"):
        cur.execute("INSERT INTO health_metrics (date, steps, calories) VALUES (?,?,?)",
                    (date.isoformat(), int(steps), int(calories)))
        conn.commit()
        st.success(f"Saved metrics for {date}")

    if st.button("View Metrics"):
        df = pd.read_sql("SELECT * FROM health_metrics ORDER BY date DESC", conn)
        if df.empty:
            st.warning("No metrics yet.")
        else:
            st.dataframe(df)
            st.plotly_chart(px.line(df, x="date", y="steps", title="Steps over Time"), use_container_width=True)
            st.plotly_chart(px.line(df, x="date", y="calories", title="Calories over Time"), use_container_width=True)

    # --- Weekly Summary ---
    st.subheader("Weekly Summary")
    df = pd.read_sql("SELECT date, steps, calories FROM health_metrics", conn, parse_dates=["date"])
    if not df.empty:
        df["week"] = df["date"].dt.isocalendar().week
        weekly = df.groupby("week").agg({"steps": "mean", "calories": "mean"}).reset_index()
        st.dataframe(weekly)
        st.plotly_chart(px.bar(weekly, x="week", y="steps", title="Average Weekly Steps"))

        goal = st.number_input("Weekly Step Goal", min_value=0, value=35000)
        this_week = df[df["week"] == df["week"].max()]
        wk_sum = this_week["steps"].sum()
        st.progress(min(1.0, wk_sum / goal))
        st.info(f"Steps this week: {wk_sum} / {goal}")

# =====================================================
# TAB 3 — UPLOAD & ANALYTICS
# =====================================================
with tabs[2]:
    st.header("Upload Fitness CSV for Analysis")

    uploaded = st.file_uploader("Upload a CSV (columns: date, steps, calories)", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded, parse_dates=["date"])
            st.write("Preview of Uploaded Data:")
            st.dataframe(df.head())

            st.plotly_chart(px.line(df, x="date", y="steps", title="Uploaded Steps Data"), use_container_width=True)
            st.plotly_chart(px.line(df, x="date", y="calories", title="Uploaded Calories Data"), use_container_width=True)

            if st.button("Import Data to DB"):
                for _, r in df.iterrows():
                    cur.execute("INSERT INTO health_metrics (date, steps, calories) VALUES (?,?,?)",
                                (r["date"].date().isoformat(), int(r["steps"]), int(r["calories"])))
                conn.commit()
                st.success("Data imported successfully!")

        except Exception as e:
            st.error(f"Upload failed: {e}")

    # --- Export buttons ---
    st.subheader("Export Your Data")
    if st.button("Export Medications CSV"):
        meds = pd.read_sql("SELECT * FROM medications", conn)
        st.download_button("Download Medications", meds.to_csv(index=False), "medications.csv", "text/csv")

    if st.button("Export Health Metrics CSV"):
        metrics = pd.read_sql("SELECT * FROM health_metrics", conn)
        st.download_button("Download Metrics", metrics.to_csv(index=False), "metrics.csv", "text/csv")

st.markdown("---")
st.caption("Week 2 Project • Healthcare Monitoring AI Agent • Streamlit Version")
