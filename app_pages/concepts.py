import streamlit as st

from core.status import Status
from core.ui import footer, status_legend

st.title(":material/school: Deadlock concepts")
st.markdown(
    "A **deadlock** happens when a set of processes are each waiting for a resource that another "
    "process in the same set is holding. None of them can move, so none of them will ever release "
    "what they hold."
)

st.subheader("The four conditions (Coffman, 1971)")
st.caption("A deadlock can only happen if all four hold at the same time. Break any one and deadlock is impossible.")
conds = [
    (":material/lock:", "Mutual exclusion", "At least one resource can be used by only one process at a time.",
     "Make resources shareable (read-only files, spooling). Often impossible: a printer can't print two jobs at once."),
    (":material/back_hand:", "Hold and wait", "A process holds at least one resource while waiting for more.",
     "Request everything up front, or release everything before asking again. Costs utilization."),
    (":material/do_not_touch:", "No preemption", "A resource can't be taken away; the holder must release it.",
     "Let the OS take resources back (CPU registers, memory pages). Hard for locks and devices."),
    (":material/cycle:", "Circular wait", "P0 waits for P1, P1 waits for P2, …, Pn waits for P0.",
     "Number all resource types and only acquire in increasing order. The most practical fix."),
]
cols = st.columns(4)
for col, (icon, name, what, fix) in zip(cols, conds):
    with col.container(border=True, height="stretch"):
        st.markdown(f"##### {icon} {name}")
        st.write(what)
        st.caption(f"**To break it:** {fix}")

st.subheader("Four ways to handle deadlock")
st.markdown(
    """
| Strategy | When it acts | What it needs to know | Cost | In this dashboard |
|---|---|---|---|---|
| **Prevention** | At design time | Nothing at runtime: a policy makes one condition impossible | Lower utilization, less concurrency | Prevention page |
| **Avoidance** | Before every allocation | Each process's **maximum** demand, declared in advance | Safety check on every request; requests may be denied | Avoidance: Banker's |
| **Detection** | Periodically, or when the CPU idles | What each process is **currently requesting** | Running the algorithm; deadlocks exist until found | Detection & recovery |
| **Recovery** | After a deadlock is detected | Which processes are deadlocked and what they hold | Lost work from aborted or rolled-back processes | Detection & recovery |
"""
)

left, right = st.columns(2)
with left:
    st.subheader("Safe, unsafe, deadlocked")
    st.graphviz_chart(
        """
digraph G {
  bgcolor="transparent"; compound=true; node [fontname="Helvetica" fontsize=12 shape=box style="rounded,filled"];
  subgraph cluster_all { label="All possible states"; fontname="Helvetica"; style="rounded"; color="#77766f";
    safe [label="SAFE\\na safe sequence exists" fillcolor="#e3f4ea" color="#1baf7a"];
    subgraph cluster_unsafe { label="UNSAFE: no safe sequence"; style="rounded,filled"; fillcolor="#fff3dc"; color="#eda100";
      maybe [label="may still finish\\n(processes release early)" fillcolor="#fff8ea" color="#eda100"];
      dead [label="DEADLOCK\\nprocesses already blocked" fillcolor="#fde2e1" color="#c62828"];
    }
  }
  safe -> maybe [label=" risky grant" style=dashed color="#77766f" fontname="Helvetica" fontsize=10];
  maybe -> dead [label=" bad luck" style=dashed color="#77766f" fontname="Helvetica" fontsize=10];
}
""",
        width="stretch",
    )
    st.caption(
        "Deadlock sits *inside* the unsafe region. Banker's Algorithm keeps the system in the green box, "
        "so it can never reach the red one."
    )
with right:
    st.subheader("Avoidance vs detection")
    st.markdown(
        """
| | Banker's (avoidance) | Detection algorithm |
|---|---|---|
| Question | *Will granting this keep everyone able to finish?* | *Is anyone stuck right now?* |
| Uses | **Need** = Max − Allocation | **Request** = what's asked for now |
| Runs | On every request, before allocating | Periodically or on demand |
| Unsafe/deadlock result | Denies the request, state unchanged | Reports deadlocked set; recovery needed |
| Finds an existing deadlock? | **No** | **Yes** |
"""
    )
    st.info(
        "A cycle in the resource-allocation graph **proves** deadlock only when every resource has one "
        "instance. With multiple instances, a cycle shows a *potential* circular wait, and the detection "
        "algorithm decides.",
        icon=":material/info:",
    )

st.subheader("Banker's Algorithm in pseudocode")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Safety algorithm**")
    st.code(
        """Need  = Max - Allocation
Work  = Available
Finish[i] = false for all i

repeat:
    find i with Finish[i] == false and Need[i] <= Work
    if found:
        Work = Work + Allocation[i]   # Pi finishes, returns resources
        Finish[i] = true
        append Pi to safe sequence
until no such i

SAFE  if all Finish[i] are true
UNSAFE otherwise""",
        language="text",
    )
with c2:
    st.markdown("**Resource-request algorithm** (Pi asks for Request)")
    st.code(
        """if Request > Need[i]:        -> INVALID   (exceeds max claim)
if Request > Available:      -> WAITING   (valid, but must wait)

# pretend to allocate
Available  -= Request
Allocation[i] += Request
Need[i]    -= Request

if safety algorithm says SAFE:  -> GRANTED  (keep the change)
else:                           -> DENIED   (roll back to the old state)""",
        language="text",
    )

st.subheader("Glossary of outcome states")
with st.container(border=True):
    status_legend(list(Status))

footer()
