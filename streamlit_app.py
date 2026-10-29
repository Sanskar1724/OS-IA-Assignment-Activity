"""Deadlock Lab: entry point.

Run locally:   streamlit run streamlit_app.py
"""

import streamlit as st

from core.project import PROJECT
from core.ui import is_dark

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
            st.Page("app_pages/prevention.py", title="Prevention", icon=":material/rule:"),
            st.Page("app_pages/avoidance.py", title="Avoidance: Banker's", icon=":material/shield:"),
            st.Page("app_pages/detection.py", title="Detection & recovery", icon=":material/troubleshoot:"),
            st.Page("app_pages/ignorance.py", title="Ignorance (ostrich)", icon=":material/visibility_off:"),
        ],
        "Practise": [
            st.Page("app_pages/games.py", title="Deadlock games", icon=":material/sports_esports:"),
        ],
        "Evaluate": [
            st.Page("app_pages/test_lab.py", title="Test lab (TC1–TC6)", icon=":material/fact_check:"),
            st.Page("app_pages/ai_usage.py", title="AI usage record", icon=":material/smart_toy:"),
        ],
        "About": [
            st.Page("app_pages/resources.py", title="Team & resources", icon=":material/groups:"),
        ],
    }
)

with st.sidebar:
    st.markdown(f"### :material/sync_lock: {PROJECT['title']}")
    st.caption(f"{PROJECT['course']} · {PROJECT['activity']}")
    with st.expander("Team", icon=":material/group:"):
        st.caption(PROJECT["institute"])
        for name, prn in PROJECT["members"]:
            st.markdown(f"**{name}**  \n:gray[PRN {prn}]")
    mode = "Dark" if is_dark() else "Light"
    st.caption(f":material/contrast: {mode} mode. To switch, open the **⋮** menu (top right) → "
               "**Settings** → **Theme**. Graphs and charts follow your choice.")

page.run()
