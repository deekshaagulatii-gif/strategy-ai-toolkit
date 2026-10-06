"""Web version of the toolkit. Run locally with:  streamlit run app.py

On Streamlit Community Cloud, add ANTHROPIC_API_KEY (and optionally APP_PASSWORD) under Settings > Secrets,
never in the code. Every AI call uses the key owner's credits.
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from toolkit import consultation, outcomes, tender
from toolkit.llm import get_llm

load_dotenv()
try:  # Streamlit Cloud stores keys in st.secrets; copy them into the environment for toolkit.llm
    for key, value in st.secrets.items():
        os.environ.setdefault(key, str(value))
except Exception:
    pass  # running locally with a .env file instead

st.set_page_config(page_title="Strategy AI Toolkit", page_icon="🧭", layout="wide")
st.title("Strategy AI Toolkit")
st.caption("Three working models of AI for a strategy consultancy: win the work, research it, track the results. "
           "Public documents and fictional sample data only. Every output is a first draft for a consultant to review.")

password = os.getenv("APP_PASSWORD")
if password and st.text_input("Password", type="password") != password:
    st.stop()


@st.cache_resource
def llm():
    return get_llm()


tab1, tab2, tab3 = st.tabs(["1. Tender Fit Checker", "2. Consultation Analyser", "3. Outcome Tracker"])

with tab1:
    st.write("Checks a draft tender response against the tender's own scored criteria and lists gaps by marks at risk.")
    col1, col2 = st.columns(2)
    tender_text = col1.text_area("Tender: requirements and award criteria", Path("data/sample_tender.txt").read_text(), height=360)
    draft_text = col2.text_area("Draft response", Path("data/sample_draft.txt").read_text(), height=360)
    if st.button("Check the draft", type="primary"):
        with st.spinner("Reviewing the draft against each criterion..."):
            md = tender.to_markdown(tender.check(tender_text, draft_text, llm()))
        st.markdown(md)
        st.download_button("Download as Markdown", md, "tender_fit_check.md")

with tab2:
    st.write("Groups responses into themes and checks every quote word for word against its source.")
    question = st.text_input("Consultation question", "What should a national health and social care regulator prioritise over the next three years?")
    uploaded = st.file_uploader("Or upload your own CSV with a 'response' column", type="csv")
    df = pd.read_csv(uploaded) if uploaded else pd.read_csv("data/sample_responses.csv")
    responses = [str(r).strip() for r in df["response"].dropna() if str(r).strip()]
    with st.expander(f"{len(responses)} responses"):
        st.dataframe(pd.DataFrame({"ID": [f"R{i}" for i in range(1, len(responses) + 1)], "Response": responses}), hide_index=True)
    if st.button("Find themes", type="primary"):
        with st.spinner("Reading responses..."):
            result = consultation.analyse(responses, llm(), question)
        for t in result["themes"]:
            q = t["quote"]
            st.subheader(f"{t['name']} ({t['count']} of {result['total_responses']})")
            st.write(t.get("description", ""))
            st.markdown(f"> “{q.get('text', '')}” (R{q.get('response_id')})")
            (st.success if q.get("verified") else st.error)("Quote verified" if q.get("verified") else "Quote not found in source")
            st.caption("Responses: " + ", ".join(f"R{i}" for i in t["response_ids"]))
        if result.get("less_common"):
            st.warning("Less common points to read by hand:\n\n" + "\n".join(f"- {p['point']} (R{p['response_id']})" for p in result["less_common"]))
        if result["unassigned"]:
            st.info("Not placed in any theme: " + ", ".join(f"R{i}" for i in result["unassigned"]))
        st.download_button("Download as Markdown", consultation.to_markdown(result, question), "consultation_analysis.md")

with tab3:
    st.write("After a strategy launches: separates outputs (work done) from outcomes (change for people), proposes "
             "indicators, then drafts the progress update. Example: HIQA's public Corporate Plan 2025–2027.")
    plan = outcomes.load_outcomes()
    choice = st.selectbox("Outcome", range(len(plan)), format_func=lambda i: f"{i + 1}. {plan[i]['name']}")
    outcome = plan[choice]
    st.markdown("**Step 1: Outputs or outcomes?**")
    if st.button("Analyse this outcome", type="primary"):
        with st.spinner("Classifying actions and proposing indicators..."):
            st.markdown(outcomes.to_markdown(outcomes.analyse(outcome, llm())))
    st.markdown("**Step 2: Draft the progress update** (statuses are illustrative, not HIQA's real progress)")
    statuses = {a: st.selectbox(a, outcomes.STATUSES, key=f"s{choice}-{i}") for i, a in enumerate(outcome["actions"])}
    audience = st.radio("Audience", list(outcomes.AUDIENCES), horizontal=True, format_func=str.capitalize)
    note = st.text_input("Anything else to note (optional)")
    if st.button("Draft the update"):
        with st.spinner("Drafting..."):
            res = outcomes.draft_update(outcome, statuses, audience, llm(), note)
        st.text(res["text"])
        if res["unsupported_numbers"]:
            st.warning("Check these numbers, they are not in the inputs: " + ", ".join(res["unsupported_numbers"]))
