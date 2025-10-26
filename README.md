# 🩺 Healthcare Monitoring AI Agent

This repo contains Week 1 (Gradio) and Week 2 (Streamlit) work.

## Files
- `Healthcare_Monitoring_AI_Agent.ipynb` — Week 1 Colab notebook (Gradio prototype)
- `streamlit_app.py` — Week 2 Streamlit app (CSV import, analytics, interaction checker)
- `drug_interactions.csv` — sample interaction mapping
- `requirements.txt` — Python dependencies
- `.gitignore` — ignores DB/caches

## Run locally
1. `pip install -r requirements.txt`
2. `streamlit run streamlit_app.py`
3. Open http://localhost:8501

## Quick demo steps (to record)
1. Open deployed app or local URL
2. Add medication and View Schedule
3. Save a metric, View Metrics, show charts
4. Upload CSV → Import to DB → show charts
5. Check drug interaction using example drugs

