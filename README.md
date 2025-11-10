# 🩺 Healthcare Monitoring AI Agent

This project is developed as part of a **2-month AI & Software Engineering internship**.  
It showcases how AI can assist in personal health monitoring — from medication scheduling to fitness tracking, goals, and insights.

---

## 📆 Project Progress Overview

| Week | Focus Area | Key Technologies |
|------|-------------|------------------|
| **Week 1** | Gradio prototype for health & medication tracking | Python • Gradio • SQLite |
| **Week 2** | Streamlit migration + Database integration + Data visualization | Streamlit • Plotly • SQLite |
| **Week 3** | Goals + CSV/JSON/XML import + Insights + PDF report | Streamlit • FPDF • Pandas |
| **Week 4** | Local Medication Info + Quick DB Summary + UI polishing | Streamlit • CSV lookup • Data analytics |

---

## 🧠 Features Summary

### 🏥 Week 1 — Gradio Prototype
- Simple interactive Gradio UI for entering medication & health metrics.  
- Data stored in SQLite (`health_data.db`).  
- Basic analytics for steps and calories.  

**File:** `Healthcare_Monitoring_AI_Agent.ipynb`

---

### 💻 Week 2 — Streamlit App
- Rebuilt the Gradio app in Streamlit.  
- Three tabs:
  1. **Medications:** Add, view, and mark medications as taken.  
  2. **Health Metrics:** Record steps/calories + visualize with Plotly.  
  3. **Upload & Analytics:** Import/export CSV data.  
- Added **Drug Interaction Checker** using `drug_interactions.csv`.

**File:** `streamlit_app.py`  
**Data file:** `drug_interactions.csv`

---

### 📊 Week 3 — Goals, Imports, Insights & PDF
- Added **Goals** tab (weekly steps & daily calories targets stored in DB).  
- Support for **CSV, JSON, and XML** imports of health data.  
- **Weekly summary**, 7-day insights, and progress bars.  
- **PDF Report** generation using FPDF (downloadable health summary).  

---

### 🧩 Week 4 — Local Medication Info + Quick Summary
- Added **Agent Tools – Local Medication Info**:  
  Searches a new file `med_info.csv` for uses, side effects, and precautions.  
  *(No API key required — fully offline.)*
- Added **Quick DB Summary** button in Upload & Analytics:  
  Displays total records, date range, and averages.
- Updated interface text & captions.

**New file:** `med_info.csv` (see below)

Example `med_info.csv` content:
```csv
drug_name,uses,side_effects,precautions
Paracetamol,Pain relief; Fever relief,Nausea; Liver damage in overdose,Do not exceed recommended dose; Avoid with heavy alcohol use
Ibuprofen,Anti-inflammatory; Pain relief,Stomach upset; Increased bleeding risk,Avoid if stomach ulcer or on blood thinners
Aspirin,Blood thinner; Pain relief,Stomach irritation; Reye's syndrome risk,Not for children with viral illness
Amoxicillin,Antibiotic; Treat bacterial infections,Diarrhea; Allergic reactions,Complete full course; Inform if allergic to penicillin
Metformin,Blood sugar control in type 2 diabetes,Nausea; Gastrointestinal upset,Take with food; Monitor kidney function
