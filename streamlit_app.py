# --- Healthcare Monitoring AI Agent (Weeks 1–7, Track A / Option A2) ---
import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os
import plotly.express as px
from fpdf import FPDF
import xml.etree.ElementTree as ET

# ==========================================================
#                DATABASE INITIALISATION
# ==========================================================
DB_PATH = "health_data.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def init_db():
    # Medications – now supports family members + dates + caregiver email
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT DEFAULT 'Self',
            name TEXT NOT NULL,
            date TEXT NOT NULL,           -- YYYY-MM-DD
            time TEXT NOT NULL,           -- HH:MM
            taken INTEGER DEFAULT 0,
            caregiver_email TEXT
        )
        """
    )

    # Health metrics – also per person
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS health_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT DEFAULT 'Self',
            date TEXT NOT NULL,           -- YYYY-MM-DD
            steps INTEGER DEFAULT 0,
            calories INTEGER DEFAULT 0
        )
        """
    )

    # Goals table – single row, global goals
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY CHECK (id=1),
            weekly_steps_target INTEGER DEFAULT 35000,
            daily_calories_target INTEGER DEFAULT 2200
        )
        """
    )
    cur.execute("INSERT OR IGNORE INTO goals(id) VALUES (1)")

    conn.commit()


init_db()


# ==========================================================
#          SMALL HELPERS (DB ACCESS & INSIGHTS)
# ==========================================================
def get_people():
    """Return list of distinct persons from DB, ensure 'Self' exists."""
    people = set(["Self"])
    cur.execute("SELECT DISTINCT person FROM medications")
    people.update([r[0] for r in cur.fetchall()])
    cur.execute("SELECT DISTINCT person FROM health_metrics")
    people.update([r[0] for r in cur.fetchall()])
    return sorted(list(people))


def get_goals():
    row = cur.execute(
        "SELECT weekly_steps_target, daily_calories_target FROM goals WHERE id=1"
    ).fetchone()
    if row:
        return int(row[0]), int(row[1])
    return 35000, 2200


def medication_adherence(person: str | None = None) -> tuple[int, int, float]:
    """Return (taken_count, total_count, adherence_percent)."""
    if person:
        df = pd.read_sql(
            "SELECT taken FROM medications WHERE person=?",
            conn,
            params=(person,),
        )
    else:
        df = pd.read_sql("SELECT taken FROM medications", conn)

    if df.empty:
        return 0, 0, 0.0
    total = len(df)
    taken = int(df["taken"].sum())
    pct = (taken / total) * 100 if total > 0 else 0.0
    return taken, total, pct


def load_metrics(person: str | None = None):
    if person:
        return pd.read_sql(
            "SELECT * FROM health_metrics WHERE person=? ORDER BY date",
            conn,
            params=(person,),
        )
    return pd.read_sql("SELECT * FROM health_metrics ORDER BY date", conn)


def generate_recommendations(person: str) -> list[str]:
    """Simple rule-based health advice – no external API / key."""
    recs: list[str] = []

    # Goals
    weekly_goal, daily_cal_goal = get_goals()

    # Steps & calories (recent 7 days)
    df = load_metrics(person)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        last7 = df[df["date"] >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=6))]
        avg_steps = int(last7["steps"].mean()) if not last7.empty else 0
        avg_cals = int(last7["calories"].mean()) if not last7.empty else 0

        if avg_steps < (weekly_goal / 7) * 0.8:
            recs.append(
                f"Average daily steps for {person} are below the weekly target. "
                "Consider adding a short walk or light activity to the routine."
            )
        else:
            recs.append(
                f"{person} is close to or meeting the step goal. Maintain regular activity to keep this trend."
            )

        if avg_cals > daily_cal_goal * 1.1:
            recs.append(
                f"Average daily calories for {person} exceed the target. "
                "Review diet, reduce sugary drinks and high-fat snacks."
            )
        else:
            recs.append(
                f"Calorie intake for {person} is within the expected range. Continue balanced meals."
            )

    # Medication adherence
    taken, total, pct = medication_adherence(person)
    if total == 0:
        recs.append(
            f"No medication schedule found for {person}. If medications are prescribed, please add them to the tracker."
        )
    elif pct < 80:
        recs.append(
            f"Medication adherence for {person} is around {pct:.1f}%. "
            "Set reminders and keep medicines in a visible place to avoid missing doses."
        )
    else:
        recs.append(
            f"{person} has good medication adherence (~{pct:.1f}%). Continue the current reminder strategy."
        )

    if not recs:
        recs.append("Not enough data yet. Please add health metrics and medications.")
    return recs


def make_pdf_report(person: str) -> bytes:
    df = load_metrics(person)
    weekly_goal, daily_cal_goal = get_goals()
    taken, total, pct = medication_adherence(person)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, f"Healthcare Report – {person}", ln=True)

    pdf.set_font("Arial", size=11)
    pdf.multi_cell(
        0,
        6,
        f"Generated on: {datetime.date.today().isoformat()}\n"
        f"Weekly Steps Goal: {weekly_goal}\n"
        f"Daily Calories Goal: {daily_cal_goal}\n"
        f"Medication adherence: {pct:.1f}% ({taken}/{total})",
    )
    pdf.ln(4)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Recent Health Metrics", ln=True)
    pdf.set_font("Arial", size=10)
    if not df.empty:
        for _, r in df.tail(20).iterrows():
            pdf.cell(
                0,
                6,
                f"{r['date']} | steps={int(r['steps'])} | calories={int(r['calories'])}",
                ln=True,
            )
    else:
        pdf.cell(0, 6, "No metrics recorded yet.", ln=True)

    recs = generate_recommendations(person)
    pdf.ln(4)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Health Insights", ln=True)
    pdf.set_font("Arial", size=10)
    for r in recs:
        pdf.multi_cell(0, 5, f"- {r}")
        pdf.ln(1)

    return pdf.output(dest="S").encode("latin-1")


# ==========================================================
#                      STREAMLIT LAYOUT
# ==========================================================
st.set_page_config(
    page_title="Healthcare Monitoring AI Agent", layout="wide", page_icon="🩺"
)

st.title("🩺 Healthcare Monitoring AI Agent – Weeks 1–7")
st.caption(
    "Educational prototype – not a substitute for professional medical advice."
)

# ---------- SIDEBAR: FAMILY MEMBERS  -----------------------
st.sidebar.header("Family / Profiles")

people = get_people()
active_person = st.sidebar.selectbox("Active person", people, index=people.index("Self"))

new_person = st.sidebar.text_input("Add family member name")
if st.sidebar.button("Add person") and new_person.strip():
    # we simply insert via a dummy row in metrics so that person appears
    cur.execute(
        "INSERT INTO health_metrics(person, date, steps, calories) VALUES (?,?,?,?)",
        (new_person.strip(), datetime.date.today().isoformat(), 0, 0),
    )
    conn.commit()
    st.sidebar.success(f"Added profile for {new_person.strip()}. Refresh list from sidebar.")

st.sidebar.markdown("---")
st.sidebar.write(f"Currently managing data for: **{active_person}**")

# Tabs: Dashboard + previous functionality
tabs = st.tabs(
    [
        "🏠 Dashboard",
        "💊 Medications",
        "📈 Health Metrics",
        "📊 Upload & Analytics",
        "🎯 Goals",
        "🧠 Insights & Report",
    ]
)

# ==========================================================
# TAB 0 – DASHBOARD (Week 7 polish)
# ==========================================================
with tabs[0]:
    st.header(f"Overall Dashboard – {active_person}")

    col_a, col_b, col_c = st.columns(3)
    taken, total, pct = medication_adherence(active_person)
    df_person = load_metrics(active_person)

    with col_a:
        st.subheader("Medication Adherence")
        st.metric(
            "Adherence %",
            f"{pct:.1f}%",
            help="Taken / total medications for this person (all time).",
        )
        st.progress(min(1.0, pct / 100) if total else 0)

    with col_b:
        st.subheader("Steps (last 7 days)")
        if not df_person.empty:
            df_person["date"] = pd.to_datetime(df_person["date"])
            last7 = df_person[
                df_person["date"]
                >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=6))
            ]
            avg_steps = int(last7["steps"].mean()) if not last7.empty else 0
        else:
            avg_steps = 0
        weekly_goal, daily_cal_goal = get_goals()
        st.metric("Avg daily steps (7d)", f"{avg_steps:,}")
        if weekly_goal > 0:
            st.progress(min(1.0, (avg_steps * 7) / weekly_goal))
        else:
            st.progress(0)

    with col_c:
        st.subheader("Calories (last 7 days)")
        if not df_person.empty:
            last7 = df_person[
                df_person["date"]
                >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=6))
            ]
            avg_cal = int(last7["calories"].mean()) if not last7.empty else 0
        else:
            avg_cal = 0
        st.metric("Avg daily calories (7d)", f"{avg_cal:,}")
        if daily_cal_goal > 0:
            st.progress(min(1.0, avg_cal / daily_cal_goal))
        else:
            st.progress(0)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Recent Metrics")
        if not df_person.empty:
            st.dataframe(df_person.tail(10), use_container_width=True)
            st.plotly_chart(
                px.line(df_person, x="date", y="steps", title="Steps trend"),
                use_container_width=True,
            )
        else:
            st.info("No metrics yet for this person.")

    with col2:
        st.subheader("Medication Overview")
        meds_df = pd.read_sql(
            "SELECT * FROM medications WHERE person=? ORDER BY date, time",
            conn,
            params=(active_person,),
        )
        if meds_df.empty:
            st.info("No medications recorded yet.")
        else:
            st.dataframe(meds_df, use_container_width=True)
            by_person = pd.read_sql(
                "SELECT person, SUM(taken) as taken, COUNT(*) as total FROM medications GROUP BY person",
                conn,
            )
            by_person["adherence"] = (by_person["taken"] / by_person["total"]) * 100
            st.plotly_chart(
                px.bar(
                    by_person,
                    x="person",
                    y="adherence",
                    title="Adherence by family member",
                    labels={"adherence": "Adherence %"},
                    range_y=[0, 100],
                ),
                use_container_width=True,
            )

# ==========================================================
# TAB 1 – MEDICATION MANAGER (Week 5–6 enhancements)
# ==========================================================
with tabs[1]:
    st.header("Medication Manager")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Medicine Name")
        med_date = st.date_input("Date", datetime.date.today())
        time_str = st.text_input("Time (HH:MM)", "08:30")
    with col2:
        med_person = st.text_input("Person (leave blank for active)", value=active_person)
        caregiver_email = st.text_input(
            "Caregiver Email (optional)", help="For reference; app does not send emails."
        )

    if st.button("Add Medication"):
        person_use = med_person.strip() or active_person
        if name and time_str:
            cur.execute(
                "INSERT INTO medications (person, name, date, time, taken, caregiver_email) "
                "VALUES (?,?,?,?,?,?)",
                (
                    person_use,
                    name.strip(),
                    med_date.isoformat(),
                    time_str.strip(),
                    0,
                    caregiver_email.strip() or None,
                ),
            )
            conn.commit()
            st.success(f"✅ Added {name} for {person_use} at {time_str} on {med_date}.")
        else:
            st.error("Please fill in at least medicine name and time.")

    st.markdown("### Current Schedule")
    meds_df = pd.read_sql(
        "SELECT * FROM medications WHERE person=? ORDER BY date, time",
        conn,
        params=(active_person,),
    )
    if meds_df.empty:
        st.info(f"No medications saved yet for {active_person}.")
    else:
        st.dataframe(meds_df, use_container_width=True)

    st.markdown("### Mark Medication as Taken")
    med_id = st.number_input(
        "Enter Medication ID to mark as taken", min_value=1, step=1, value=1
    )
    if st.button("Mark as Taken"):
        cur.execute(
            "UPDATE medications SET taken=1 WHERE id=?", (int(med_id),)
        )
        conn.commit()
        st.success(f"Marked medication ID {int(med_id)} as taken.")

    if st.button("Reset All 'Taken' Flags for Active Person"):
        cur.execute(
            "UPDATE medications SET taken=0 WHERE person=?", (active_person,)
        )
        conn.commit()
        st.info(f"Reset all medications to not taken for {active_person}.")

# ==========================================================
# TAB 2 – HEALTH METRICS
# ==========================================================
with tabs[2]:
    st.header("Health Metrics Tracker")

    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("Date", datetime.date.today(), key="metrics_date")
    with col2:
        steps = st.number_input("Steps", min_value=0, value=0)
    with col3:
        calories = st.number_input("Calories", min_value=0, value=0)

    person_for_metrics = st.text_input(
        "Person (leave blank for active profile)", value=active_person
    )

    if st.button("Save Metrics"):
        person_use = person_for_metrics.strip() or active_person
        cur.execute(
            "INSERT INTO health_metrics (person, date, steps, calories) VALUES (?,?,?,?)",
            (person_use, date.isoformat(), int(steps), int(calories)),
        )
        conn.commit()
        st.success(f"Saved metrics for {person_use} on {date}.")

    if st.button("View Metrics for Active Person"):
        dfm = load_metrics(active_person)
        if dfm.empty:
            st.warning("No metrics yet.")
        else:
            st.dataframe(dfm, use_container_width=True)
            st.plotly_chart(
                px.line(dfm, x="date", y="steps", title="Steps over time"),
                use_container_width=True,
            )
            st.plotly_chart(
                px.line(dfm, x="date", y="calories", title="Calories over time"),
                use_container_width=True,
            )

# ==========================================================
# TAB 3 – UPLOAD & ANALYTICS (CSV + JSON + XML)
# ==========================================================
with tabs[3]:
    st.header("Upload Fitness Data for Analysis")

    st.markdown("#### Upload CSV (columns: date, steps, calories)")
    uploaded = st.file_uploader("CSV file", type=["csv"])
    if uploaded:
        try:
            dfu = pd.read_csv(uploaded, parse_dates=["date"])
            st.write("Preview of Uploaded CSV:")
            st.dataframe(dfu.head(), use_container_width=True)

            st.plotly_chart(
                px.line(dfu, x="date", y="steps", title="Uploaded Steps Data"),
                use_container_width=True,
            )
            st.plotly_chart(
                px.line(dfu, x="date", y="calories", title="Uploaded Calories Data"),
                use_container_width=True,
            )

            if st.button("Import CSV to DB"):
                for _, r in dfu.iterrows():
                    cur.execute(
                        "INSERT INTO health_metrics (person, date, steps, calories) "
                        "VALUES (?,?,?,?)",
                        (
                            active_person,
                            r["date"].date().isoformat(),
                            int(r["steps"]),
                            int(r["calories"]),
                        ),
                    )
                conn.commit()
                st.success("CSV data imported successfully!")
        except Exception as e:
            st.error(f"CSV upload failed: {e}")

    st.divider()
    st.subheader("Or import JSON / XML (date, steps, calories)")

    json_file = st.file_uploader("Upload JSON", type=["json"])
    if json_file:
        try:
            jf = pd.read_json(json_file)
            if not {"date", "steps", "calories"}.issubset(jf.columns):
                st.error("JSON must contain date, steps, calories.")
            else:
                st.dataframe(jf.head(), use_container_width=True)
                if st.button("Import JSON to DB"):
                    for _, r in jf.iterrows():
                        cur.execute(
                            "INSERT INTO health_metrics (person, date, steps, calories) VALUES (?,?,?,?)",
                            (
                                active_person,
                                str(r["date"])[:10],
                                int(r["steps"]),
                                int(r["calories"]),
                            ),
                        )
                    conn.commit()
                    st.success("JSON imported ✅")
        except Exception as e:
            st.error(f"JSON error: {e}")

    xml_file = st.file_uploader("Upload XML", type=["xml"])
    if xml_file:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            rows = []
            for row in root.findall(".//row"):
                rows.append(
                    {
                        "date": row.findtext("date"),
                        "steps": int(row.findtext("steps")),
                        "calories": int(row.findtext("calories")),
                    }
                )
            xf = pd.DataFrame(rows)
            if xf.empty:
                st.error(
                    "XML must have <row><date>..</date><steps>..</steps><calories>..</calories></row>"
                )
            else:
                st.dataframe(xf.head(), use_container_width=True)
                if st.button("Import XML to DB"):
                    for _, r in xf.iterrows():
                        cur.execute(
                            "INSERT INTO health_metrics (person, date, steps, calories) VALUES (?,?,?,?)",
                            (
                                active_person,
                                r["date"],
                                int(r["steps"]),
                                int(r["calories"]),
                            ),
                        )
                    conn.commit()
                    st.success("XML imported ✅")
        except Exception as e:
            st.error(f"XML error: {e}")

    st.subheader("Export Your Data")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Medications CSV"):
            meds = pd.read_sql("SELECT * FROM medications", conn)
            st.download_button(
                "Download Medications",
                meds.to_csv(index=False),
                "medications.csv",
                "text/csv",
            )
    with col2:
        if st.button("Export Health Metrics CSV"):
            metrics = pd.read_sql("SELECT * FROM health_metrics", conn)
            st.download_button(
                "Download Metrics",
                metrics.to_csv(index=False),
                "metrics.csv",
                "text/csv",
            )

# ==========================================================
# TAB 4 – GOALS
# ==========================================================
with tabs[4]:
    st.header("🎯 Wellness Goals")

    weekly_target, daily_cal_target = get_goals()
    w_target = st.number_input(
        "Weekly steps target", min_value=0, value=int(weekly_target), step=500
    )
    d_target = st.number_input(
        "Daily calories target", min_value=0, value=int(daily_cal_target), step=50
    )
    if st.button("Save Goals"):
        cur.execute(
            "UPDATE goals SET weekly_steps_target=?, daily_calories_target=? WHERE id=1",
            (int(w_target), int(d_target)),
        )
        conn.commit()
        st.success("Goals updated ✅")

    st.markdown("### Goal Progress (for active person)")
    dfm = load_metrics(active_person)
    if dfm.empty:
        st.info("Add some health metrics to see progress.")
    else:
        dfm["date"] = pd.to_datetime(dfm["date"])
        dfm["week"] = dfm["date"].dt.isocalendar().week
        this_week = dfm[dfm["week"] == dfm["week"].max()]
        wk_steps = int(this_week["steps"].sum()) if not this_week.empty else 0

        st.write(f"Steps this week for {active_person}: **{wk_steps} / {w_target}**")
        st.progress(min(1.0, wk_steps / max(1, w_target)))

        st.plotly_chart(
            px.bar(
                dfm.groupby("week")["steps"].sum().reset_index(),
                x="week",
                y="steps",
                title=f"Weekly steps for {active_person}",
            ),
            use_container_width=True,
        )

# ==========================================================
# TAB 5 – INSIGHTS & PDF REPORT
# ==========================================================
with tabs[5]:
    st.header(f"🧠 Insights & 📄 Report – {active_person}")

    df = load_metrics(active_person)
    if df.empty:
        st.info("Add some metrics to see insights.")
    else:
        df["date"] = pd.to_datetime(df["date"])
        st.plotly_chart(
            px.line(df, x="date", y="steps", title="Steps trend"),
            use_container_width=True,
        )
        st.plotly_chart(
            px.line(df, x="date", y="calories", title="Calories trend"),
            use_container_width=True,
        )

        st.subheader("Text Insights")
        recs = generate_recommendations(active_person)
        for r in recs:
            st.write("• " + r)

        st.subheader("PDF Report")
        if st.button("Generate PDF for Active Person"):
            pdf_bytes = make_pdf_report(active_person)
            st.download_button(
                "Download health_report.pdf",
                pdf_bytes,
                "health_report.pdf",
                "application/pdf",
            )

st.markdown("---")
st.caption(
    "Week 7 Milestone • Multi-person medication & wellness tracker with analytics, goals, and PDF reporting."
)
