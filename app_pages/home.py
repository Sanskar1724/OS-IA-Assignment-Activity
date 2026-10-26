import streamlit as st

from core.project import PROJECT
from core.status import Status
from core.testcases import run_all
from core.ui import footer, status_legend

st.title(":material/sync_lock: Deadlock Lab")
st.markdown(
    "#### See a deadlock coming, catch one that has already happened, and design one out of the system."
)
st.caption(f"{PROJECT['subtitle']} · {PROJECT['course']}, {PROJECT['activity']}")

rows = run_all()
passed = sum(r.passed for r in rows)

with st.container(horizontal=True):
    st.metric("Required test cases passing", f"{passed} / {len(rows)}", border=True,
              help="TC1–TC6, recomputed live from the algorithms every time this page loads.")
    st.metric("Handling strategies", "4", border=True,
              help="Prevention, avoidance, detection and recovery, each on its own page.")
    st.metric("Distinct outcome states", len(Status), border=True,
              help="Safe, unsafe, granted, waiting, denied, deadlock, no deadlock, invalid.")
    st.metric("Resource models", "Single + multi", border=True,
              help="Detection says which model it uses and picks the right method.")

st.subheader("Where do you want to start?")

cards = [
    ("app_pages/avoidance.py", ":material/shield:", "Avoidance: Banker's Algorithm",
     "Set up processes and resources, watch the safety check find a safe sequence step by step, "
     "then test requests that are granted, made to wait, or denied.", "Scenarios A, B, C"),
    ("app_pages/detection.py", ":material/troubleshoot:", "Detection & recovery",
     "Draw the resource-allocation graph, find circular waits, confirm deadlock with the right "
     "method for the resource model, then abort a victim to recover.", "Scenario D"),
    ("app_pages/prevention.py", ":material/rule:", "Prevention",
     "Run the same workload with and without a prevention policy and compare deadlock, "
     "completion time and resource utilization side by side.", "Scenario E"),
    ("app_pages/test_lab.py", ":material/fact_check:", "Test lab",
     "The Required Analytical Results Table, filled from live output, including every boundary "
     "and invalid input case. Download it for your report.", "TC1–TC6, Scenario F"),
]
cols = st.columns(2)
for k, (path, icon, title, text, tag) in enumerate(cards):
    with cols[k % 2].container(border=True, height="stretch"):
        st.markdown(f"##### {icon} {title}")
        st.markdown(f":blue-badge[{tag}]")
        st.write(text)
        st.page_link(path, label="Open", icon=":material/arrow_forward:")

left, right = st.columns([3, 2])
with left:
    st.subheader("The one idea to get right")
    with st.container(border=True):
        st.markdown(
            "**Avoidance and detection answer different questions.**\n\n"
            "- **Banker's Algorithm (avoidance)** asks *before* allocating: *“If I grant this, can every "
            "process still finish?”* It works with each process's declared **maximum** demand.\n"
            "- **The detection algorithm** asks *after the fact*: *“Is anyone stuck right now?”* It works with "
            "what processes are **currently requesting**.\n\n"
            "Banker's never finds an existing deadlock, and detection never stops one from forming. "
            "That's why they live on separate pages."
        )
    with st.container(border=True):
        st.markdown(
            "**Unsafe ≠ deadlocked.** An unsafe state means the system *can't guarantee* that everyone "
            "finishes. Processes may still release resources early and finish fine. A deadlock means some "
            "processes *are already* blocked on each other, permanently. Every deadlocked state is unsafe, "
            "but most unsafe states never become a deadlock."
        )
with right:
    st.subheader("Every outcome has its own label")
    with st.container(border=True):
        status_legend()

st.subheader("Six-minute demo script")
with st.container(border=True):
    st.markdown(
        """
| Time | Show | Page | What to say |
|---|---|---|---|
| 0:00 | Safe state | Avoidance | “Need = Max − Allocation. Work starts at Available. P1 fits first, returns its resources, and the sequence P1 → P3 → P4 → P0 → P2 completes.” |
| 1:15 | Request that waits | Avoidance | “P2 asks for (4,0,0). It's within Need, so it's **valid**, but only 3 A are free. It **waits**, and nothing changes.” |
| 2:00 | Request that's denied | Avoidance | “P4's (3,3,0) fits Need and Available, but the trial state has no safe sequence. **Denied** and rolled back. That's unsafe, not deadlock.” |
| 3:00 | Deadlock detected | Detection | “Multiple-instance model, so we confirm with the detection algorithm, not just the cycle. P1–P4 are deadlocked.” |
| 4:00 | Recovery | Detection | “Abort P2. It releases (3,0,3) and everyone else finishes.” |
| 4:45 | Cycle ≠ deadlock | Detection | “Here's a cycle with 2-instance resources and no deadlock. A cycle is necessary, not sufficient.” |
| 5:15 | Prevention | Prevention | “Ordered acquisition removes circular wait. The price is idle holding and longer completion time.” |
"""
    )

footer()
