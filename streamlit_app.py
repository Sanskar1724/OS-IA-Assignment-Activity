"""Deadlock Lab: entry point.

Run locally:   streamlit run streamlit_app.py
"""

import streamlit as st

from core.project import PROJECT

st.set_page_config(
    page_title=PROJECT["title"],
    page_icon=":material/sync_lock:",
    layout="wide",
)

page = st.navigation(
    {
        "Start here": [
            st.Page("app_pages/home.py", title="Overview", icon=":material/home:", default=True),
            st.Page("app_pages/concepts.py", title="Deadlock concepts", icon=":material/school:"),
        ],
        "Handle deadlocks": [
            st.Page("app_pages/avoidance.py", title="Avoidance: Banker's", icon=":material/shield:"),
            st.Page("app_pages/detection.py", title="Detection & recovery", icon=":material/troubleshoot:"),
            st.Page("app_pages/prevention.py", title="Prevention", icon=":material/rule:"),
        ],
        "Evaluate": [
            st.Page("app_pages/test_lab.py", title="Test lab (TC1–TC6)", icon=":material/fact_check:"),
            st.Page("app_pages/ai_usage.py", title="AI usage record", icon=":material/smart_toy:"),
        ],
    }
)

with st.sidebar:
    st.markdown(f"### :material/sync_lock: {PROJECT['title']}")
    st.caption(f"{PROJECT['course']} · {PROJECT['activity']}")
    with st.expander("Team", icon=":material/group:"):
        st.markdown(f"**{PROJECT['group']}**, {PROJECT['institute']}")
        for name, roll, role in PROJECT["members"]:
            st.markdown(f"**{name}** · {roll}  \n:gray[{role}]")

page.run()
