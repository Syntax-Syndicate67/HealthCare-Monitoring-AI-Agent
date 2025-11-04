# --- Streamlit Healthcare Monitoring AI Agent (Week 3) ---
import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os
import plotly.express as px
from fpdf import FPDF
import xml.etree.ElementTree as ET

# ---------------- Database Setup ----------------
DB_PATH = "health_data.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def init_db():
    # Week 1/2 tables
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

    # Week 3: Goals table (single row)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY CHECK (id=1),
        weekly_steps_target INTEGER DEFAULT 35000,
        daily_calories_target INTEGER DEFAULT 2200
    )''')
    cur.execute("INSERT OR IGNORE INTO goals(id) VALUES (1)")
    conn.commit()

init_db()

# ---------------- Page Title ----------------
st.set_page_config(page_title="Healthcare Monitoring AI Agent", layout="wide")
st.title("🩺 Healthcare Monitoring AI Agent — Week 3 (Streamlit Edition)")

tabs = st.tabs([
    "💊 Medications",
    "📈 Health Metrics",
    "📊 Upload & Analytics",
    "🎯 Goals",
    "🧠 Insights & Report",
])

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
        st.dataframe(meds, use_container_width=True)

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
            df_int = pd.read_csv("drug_interactions.csv")
            found = df_int[
                ((df_int["drug_a"].str.lower() == drug_a.lower()) & (df_int["drug_b"].str.lower() == drug_b.lower())) |
                ((df_int["drug_a"].str.lower() == drug_b.lower()) & (df_int["drug_b"].str.lower() == drug_a.lower()))
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
        dfm = pd.read_sql("SELECT * FROM health_metrics ORDER BY date DESC", conn)
        if dfm.empty:
            st.warning("No metrics yet.")
        else:
            st.dataframe(dfm, use_container_width=True)
            st.plotly_chart(px.line(dfm, x="date", y="steps", title="Steps over Time"), use_container_width=True)
            st.plotly_chart(px.line(dfm, x="date", y="calories", title="Calories over Time"), use_container_width=True)

# =====================================================
# TAB 3 — UPLOAD & ANALYTICS (CSV + JSON + XML)
# =====================================================
with tabs[2]:
    st.header("Upload Fitness Data for Analysis")

    uploaded = st.file_uploader("Upload a CSV (columns: date, steps, calories)", type=["csv"])
    if uploaded:
        try:
            dfu = pd.read_csv(uploaded, parse_dates=["date"])
            st.write("Preview of Uploaded CSV:")
            st.dataframe(dfu.head(), use_container_width=True)

            st.plotly_chart(px.line(dfu, x="date", y="steps", title="Uploaded Steps Data"), use_container_width=True)
            st.plotly_chart(px.line(dfu, x="date", y="calories", title="Uploaded Calories Data"), use_container_width=True)

            if st.button("Import CSV to DB"):
                for _, r in dfu.iterrows():
                    cur.execute("INSERT INTO health_metrics (date, steps, calories) VALUES (?,?,?)",
                                (r["date"].date().isoformat(), int(r["steps"]), int(r["calories"])))
                conn.commit()
                st.success("CSV data imported successfully!")
        except Exception as e:
            st.error(f"CSV upload failed: {e}")

    st.divider()
    st.subheader("Or import JSON / XML (columns: date, steps, calories)")

    # JSON import
    json_file = st.file_uploader("Upload JSON", type=["json"])
    if json_file:
        try:
            jf = pd.read_json(json_file)
            if not {"date", "steps", "calories"}.issubset(jf.columns):
                st.error("JSON must contain date, steps, calories")
            else:
                st.dataframe(jf.head(), use_container_width=True)
                if st.button("Import JSON to DB"):
                    for _, r in jf.iterrows():
                        cur.execute("INSERT INTO health_metrics(date, steps, calories) VALUES (?,?,?)",
                                    (str(r["date"])[:10], int(r["steps"]), int(r["calories"])))
                    conn.commit()
                    st.success("JSON imported ✅")
        except Exception as e:
            st.error(f"JSON error: {e}")

    # XML import
    xml_file = st.file_uploader("Upload XML", type=["xml"])
    if xml_file:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            rows = []
            for row in root.findall(".//row"):
                rows.append({
                    "date": row.findtext("date"),
                    "steps": int(row.findtext("steps")),
                    "calories": int(row.findtext("calories")),
                })
            xf = pd.DataFrame(rows)
            if xf.empty:
                st.error("XML must have <row><date>..</date><steps>..</steps><calories>..</calories></row>")
            else:
                st.dataframe(xf.head(), use_container_width=True)
                if st.button("Import XML to DB"):
                    for _, r in xf.iterrows():
                        cur.execute("INSERT INTO health_metrics(date, steps, calories) VALUES (?,?,?)",
                                    (r["date"], int(r["steps"]), int(r["calories"])))
                    conn.commit()
                    st.success("XML imported ✅")
        except Exception as e:
            st.error(f"XML error: {e}")

    # --- Export buttons ---
    st.subheader("Export Your Data")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Medications CSV"):
            meds = pd.read_sql("SELECT * FROM medications", conn)
            st.download_button("Download Medications", meds.to_csv(index=False), "medications.csv", "text/csv")
    with col2:
        if st.button("Export Health Metrics CSV"):
            metrics = pd.read_sql("SELECT * FROM health_metrics", conn)
            st.download_button("Download Metrics", metrics.to_csv(index=False), "metrics.csv", "text/csv")

# =====================================================
# TAB 4 — GOALS (DB-backed + progress)
# =====================================================
with tabs[3]:
    st.header("🎯 Goals")
    row = cur.execute("SELECT weekly_steps_target, daily_calories_target FROM goals WHERE id=1").fetchone()
    w_target = st.number_input("Weekly steps target", min_value=0, value=int(row[0]) if row else 35000, step=500)
    d_target = st.number_input("Daily calories target", min_value=0, value=int(row[1]) if row else 2200, step=50)
    if st.button("Save Goals"):
        cur.execute("UPDATE goals SET weekly_steps_target=?, daily_calories_target=? WHERE id=1",
                    (int(w_target), int(d_target)))
        conn.commit()
        st.success("Goals updated ✅")

    # simple weekly progress
    dfm = pd.read_sql("SELECT date, steps, calories FROM health_metrics", conn, parse_dates=["date"])
    if not dfm.empty:
        dfm["week"] = dfm["date"].dt.isocalendar().week
        this_week = dfm[dfm["week"] == dfm["week"].max()]
        wk_steps = int(this_week["steps"].sum()) if not this_week.empty else 0
        st.subheader("This week so far")
        st.progress(min(1.0, wk_steps / max(1, w_target)))
        st.info(f"Steps: {wk_steps} / {w_target}")

# =====================================================
# TAB 5 — INSIGHTS & PDF REPORT
# =====================================================
with tabs[4]:
    st.header("🧠 Insights & 📄 Report")
    df = pd.read_sql("SELECT date, steps, calories FROM health_metrics ORDER BY date", conn)
    if df.empty:
        st.info("Add some metrics to see insights.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        last7 = df[df["date"] >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=6))]
        avg_steps = int(last7["steps"].mean()) if not last7.empty else 0
        avg_cal   = int(last7["calories"].mean()) if not last7.empty else 0

        st.write(f"• 7-day avg steps: **{avg_steps}**")
        st.write(f"• 7-day avg calories: **{avg_cal}**")
        st.plotly_chart(px.line(df, x="date", y="steps", title="Steps trend"), use_container_width=True)
        st.plotly_chart(px.line(df, x="date", y="calories", title="Calories trend"), use_container_width=True)

        def make_pdf() -> bytes:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            pdf.cell(0, 10, "Healthcare Monitoring Report", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, f"7-day Avg Steps: {avg_steps}\n7-day Avg Calories: {avg_cal}")
            pdf.ln(4)
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "Recent Metrics", ln=True)
            pdf.set_font("Arial", size=10)
            for _, r in df.tail(20).iterrows():
                pdf.cell(0, 6, f"{r['date'].date()} | steps={int(r['steps'])} | calories={int(r['calories'])}", ln=True)
            return pdf.output(dest="S").encode("latin-1")

        if st.button("📄 Download PDF Report"):
            st.download_button("Download health_report.pdf", make_pdf(), "health_report.pdf", "application/pdf")

st.markdown("---")
st.caption("Week 3 • Goals + JSON/XML Import + Insights + PDF • Healthcare Monitoring AI Agent")
