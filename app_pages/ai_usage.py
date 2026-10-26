import pandas as pd
import streamlit as st

from core.ui import footer

st.title(":material/smart_toy: AI usage record")
st.markdown(
    "The brief asks every group to record which AI tools they used, what each produced, and **how the "
    "group verified it**. Edit the table below, then download it for your submission."
)

DEFAULT = pd.DataFrame([
    {"AI tool used": "Claude (Anthropic) via Claude Code", "Purpose": "Dashboard design",
     "Output generated": "Streamlit page layout, navigation, status banners, charts and the explanatory copy",
     "Student verification": "✎ e.g. Checked every page against the brief's minimum requirements; "
                             "rewrote explanations in our own words"},
    {"AI tool used": "Claude (Anthropic) via Claude Code", "Purpose": "Algorithm/code assistance",
     "Output generated": "Banker's safety and request algorithms, detection algorithm, recovery, prevention simulator",
     "Student verification": "✎ e.g. Hand-traced Scenario A: Need matrix and safe sequence P1 → P3 → P4 → P0 → P2 "
                             "match the dashboard"},
    {"AI tool used": "Claude (Anthropic) via Claude Code", "Purpose": "Test-case generation or debugging",
     "Output generated": "Scenario data for TC1–TC6 and the pytest suite in tests/test_core.py",
     "Student verification": "✎ e.g. Recomputed TC3's trial state (Available = 0,0,2) by hand and confirmed "
                             "no process can finish"},
])

if "ai_record" not in st.session_state:
    st.session_state.ai_record = DEFAULT

record = st.data_editor(
    st.session_state.ai_record, key="ai_editor", num_rows="dynamic", hide_index=True, width="stretch",
    column_config={c: st.column_config.TextColumn(width="large" if c != "Purpose" else "medium")
                   for c in DEFAULT.columns},
)
st.caption("Rows marked ✎ are prompts. Replace them with what your group actually did. "
           "Add a row for every other tool you used (ChatGPT, Gemini, Copilot, Canva, …).")

with st.container(horizontal=True):
    st.download_button("Download CSV", record.to_csv(index=False).encode("utf-8"), "ai_usage_record.csv",
                       "text/csv", icon=":material/download:")
    md = "| " + " | ".join(record.columns) + " |\n|" + "---|" * len(record.columns) + "\n" + "\n".join(
        "| " + " | ".join(str(v) for v in row) + " |" for row in record.itertuples(index=False))
    st.download_button("Download Markdown", md.encode("utf-8"), "ai_usage_record.md", "text/markdown",
                       icon=":material/description:")
    if st.button("Reset to template", icon=":material/restart_alt:"):
        st.session_state.ai_record = DEFAULT
        st.session_state.pop("ai_editor", None)
        st.rerun()

st.header("Responsible AI checklist", divider="gray")
st.caption("From Section 1 of the brief. Tick each one when your whole group can honestly say yes.")
checks = [
    "We reviewed, tested and changed AI-generated code where needed.",
    "We checked the Banker's Algorithm, safe sequences and request decisions independently (by hand or with our own tests).",
    "We didn't assume any AI explanation or output was correct without testing it.",
    "We listed every AI tool used and what it contributed.",
    "Every member can explain and modify any part of the code without AI help.",
    "We didn't upload confidential institutional information, credentials or sensitive data to AI tools.",
]
done = sum(st.checkbox(c, key=f"ai_chk_{i}") for i, c in enumerate(checks))
st.progress(done / len(checks), text=f"{done} of {len(checks)} confirmed")

st.header("Where to look when verifying", divider="gray")
st.markdown(
    """
| To verify… | Read this file | Key function |
|---|---|---|
| Need = Max − Allocation | `core/bankers.py` | `compute_need` |
| Safety algorithm and Work updates | `core/bankers.py` | `safety_algorithm` |
| Request: invalid / waiting / denied / granted | `core/bankers.py` | `request_resources` |
| Input validation (Scenario F) | `core/validation.py` | `validate_system`, `validate_request` |
| Deadlock detection (multi-instance) | `core/detection.py` | `detection_algorithm` |
| Cycle in RAG / wait-for graph | `core/detection.py` | `rag_cycle`, `wfg_cycle` |
| Recovery by process termination | `core/detection.py` | `recover`, `pick_victim` |
| Prevention policies | `core/prevention.py` | `simulate` |
| TC1–TC6 table | `core/testcases.py` | `run_all` |
"""
)

footer()
