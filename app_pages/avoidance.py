from copy import deepcopy

import pandas as pd
import streamlit as st

from core.bankers import compute_need, leq, request_resources, safety_algorithm
from core.scenarios import BANKER_BASE, REQUESTS
from core.status import Status
from core.ui import (allocation_chart, edit_matrix, edit_vector, footer, resize, resource_names,
                     sequence_chips, show_matrix, status_banner, trace_table, vec, work_chart)
from core.validation import validate_system


# --- State ----------------------------------------------------------------------

def load_state(state: dict, clear_result: bool = True):
    st.session_state.bank = deepcopy(state)
    st.session_state.bank_ver = st.session_state.get("bank_ver", 0) + 1
    if clear_result:
        st.session_state.last_req = None


def base_state() -> dict:
    return {k: BANKER_BASE[k] for k in ("resources", "allocation", "maximum", "available")}


if "bank" not in st.session_state:
    load_state(base_state())
    st.session_state.req_history = []

bank = st.session_state.bank
ver = st.session_state.bank_ver


def run_request(pid, req, state: dict):
    res = request_resources(pid, req, state["allocation"], state["maximum"], state["available"],
                            state["resources"])
    st.session_state.last_req = {"res": res, "before": deepcopy(state)}
    st.session_state.req_history.append({
        "#": len(st.session_state.req_history) + 1, "Process": f"P{pid}", "Request": vec(req),
        "Outcome": res.status.value,
    })
    # Commit the decision. For anything but GRANTED, res holds the untouched original state.
    load_state({**state, "allocation": res.allocation, "available": res.available}, clear_result=False)


# --- Header ---------------------------------------------------------------------

st.title(":material/shield: Avoidance: Banker's Algorithm")
st.markdown(
    "Banker's Algorithm acts **before** resources are handed out. Each process declares its "
    "**maximum** demand up front. A request is granted only if the system can still guarantee that "
    "every process finishes in *some* order, which is called a **safe sequence**."
)

# --- 1. Configure -------------------------------------------------------------------

st.header("1 · Configure the system", divider="gray")

with st.container(horizontal=True, vertical_alignment="bottom"):
    n = st.number_input("Processes", min_value=1, max_value=10, value=len(bank["allocation"]), key=f"n{ver}")
    m = st.number_input("Resource types", min_value=1, max_value=6, value=len(bank["available"]), key=f"m{ver}")
    if st.button("Load Scenario A (safe)", icon=":material/restart_alt:"):
        load_state(base_state())
        st.rerun()
    if st.button("Clear to zeros", icon=":material/clear_all:"):
        rows, cols = len(bank["allocation"]), len(bank["available"])
        load_state({"resources": bank["resources"], "allocation": [[0] * cols for _ in range(rows)],
                    "maximum": [[0] * cols for _ in range(rows)], "available": [0] * cols})
        st.rerun()

if (n, m) != (len(bank["allocation"]), len(bank["available"])):
    work = st.session_state.get("bank_working", bank)
    load_state({"resources": resource_names(m, work["resources"]),
                "allocation": resize(work["allocation"], n, m),
                "maximum": resize(work["maximum"], n, m),
                "available": resize([work["available"]], 1, m)[0]})
    st.rerun()

res_names = bank["resources"]
procs = [f"P{i}" for i in range(n)]

st.caption("Click any cell to edit it. Need is calculated for you. Negative values are allowed so you can "
           "test how invalid input is handled.")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Allocation**: instances each process holds now")
    allocation = edit_matrix(bank["allocation"], procs, res_names, key=f"alloc{ver}")
with c2:
    st.markdown("**Maximum**: most each process may ever hold")
    maximum = edit_matrix(bank["maximum"], procs, res_names, key=f"max{ver}")

c3, c4 = st.columns(2)
with c3:
    st.markdown("**Available**: free instances right now")
    available = edit_vector(bank["available"], res_names, key=f"avail{ver}", row_label="Free")
    totals = [a + sum(r[j] for r in allocation) for j, a in enumerate(available)]
    st.caption(f"Total instances (Allocation + Available): **{vec(totals)}**")
with c4:
    st.markdown("**Need** = Maximum − Allocation (calculated)")
    need = compute_need(allocation, maximum)
    show_matrix(need, procs, res_names)

state = {"resources": res_names, "allocation": allocation, "maximum": maximum, "available": available}
st.session_state.bank_working = state

errors = validate_system(allocation, maximum, available, procs, res_names)
if errors:
    status_banner(Status.INVALID, "This configuration can't be evaluated. Fix the cells below.", errors)
    st.caption("Nothing was run. The safety check only runs on valid input, which keeps “invalid” and "
               "“unsafe” separate.")
    footer()
    st.stop()

# --- 2. Safety check ------------------------------------------------------------------

st.header("2 · Safety check", divider="gray")
safety = safety_algorithm(allocation, maximum, available)

with st.container(horizontal=True):
    st.metric("System state", safety.status.value, border=True)
    st.metric("Processes that can finish", f"{len(safety.sequence)} / {n}", border=True)
    st.metric("Free now (Available)", vec(available), border=True)
    st.metric("Total instances", vec(totals), border=True)

if safety.safe:
    status_banner(Status.SAFE, "The system is in a safe state.", [
        "Every process can finish if they run in the order below.",
        "Each finished process returns its allocation, so Work grows and the next process fits.",
    ])
else:
    stuck = ", ".join(f"P{i}" for i in safety.stuck)
    status_banner(Status.UNSAFE, "The system is in an unsafe state.", [
        f"After {', '.join(f'P{i}' for i in safety.sequence) or 'no process'} finish, Work = "
        f"{vec(safety.final_work)}, and that isn't enough for any of {stuck}.",
        "This is not a deadlock. No one is blocked yet. Processes might release resources early and "
        "everyone could still finish. The system just can't guarantee it.",
        "Go to Detection & recovery to check whether processes are actually stuck right now.",
    ])

st.markdown("**Safe sequence**")
sequence_chips(safety.sequence)

t1, t2 = st.columns([3, 2])
with t1:
    st.markdown("**Step-by-step trace**")
    st.caption("Each pass checks the unfinished processes in order. A process finishes when its Need fits in Work.")
    trace_table(safety.steps)
with t2:
    st.markdown("**How Work grows**")
    work_chart(safety.sequence, available, allocation, res_names)

st.markdown("**Who holds what**")
allocation_chart(allocation, available, res_names)

# --- 3. Request ------------------------------------------------------------------------

st.header("3 · Make a resource request", divider="gray")
st.markdown(
    "A request goes through three checks in order: **Request ≤ Need?** (otherwise invalid), "
    "**Request ≤ Available?** (otherwise wait), then a **trial allocation and safety check** "
    "(otherwise deny and roll back)."
)

st.markdown("**Try a ready-made scenario.** Each one reloads the Scenario A state first.")
with st.container(horizontal=True):
    for key, icon in (("granted", ":material/check_circle:"), ("waiting", ":material/hourglass_top:"),
                      ("unsafe", ":material/block:")):
        q = REQUESTS[key]
        if st.button(q["title"], icon=icon, help=q["why"], key=f"preset_{key}"):
            base = base_state()
            load_state(base)
            run_request(q["pid"], q["request"], base)
            st.rerun()

with st.form("request_form", border=True):
    st.markdown("**Or build your own request** against the current state")
    with st.container(horizontal=True):
        pid = st.number_input("Process number (P…)", value=0, step=1,
                              help="Try a number that doesn't exist to see validation.")
        req = [st.number_input(f"{r}", value=0, step=1, key=f"req_{r}") for r in res_names]
    submitted = st.form_submit_button("Check request", icon=":material/play_arrow:", type="primary")

if submitted:
    run_request(int(pid), [int(x) for x in req], state)
    st.rerun()

last = st.session_state.get("last_req")
if last:
    res, before = last["res"], last["before"]
    p = f"P{res.pid}" if res.pid is not None else "The process"
    headline = {
        Status.GRANTED: f"{p}'s request {vec(res.request)} is granted.",
        Status.WAITING: f"{p} must wait. {vec(res.request)} is more than is free right now.",
        Status.DENIED: f"{p}'s request {vec(res.request)} is denied. Granting it would make the system unsafe.",
        Status.INVALID: f"Request {vec(res.request)} rejected: invalid input.",
    }[res.status]

    st.subheader("Result")
    status_banner(res.status, headline, res.reasons)

    if res.status is not Status.INVALID:
        b_need = compute_need(before["allocation"], before["maximum"])[res.pid]
        b_avail = before["available"]
        s1, s2, s3 = st.columns(3)
        with s1.container(border=True, height="stretch"):
            st.markdown("**Step 1 · Request ≤ Need?**")
            st.markdown(f":green[:material/check: Yes]: {vec(res.request)} ≤ {vec(b_need)}")
        with s2.container(border=True, height="stretch"):
            st.markdown("**Step 2 · Request ≤ Available?**")
            if leq(res.request, b_avail):
                st.markdown(f":green[:material/check: Yes]: {vec(res.request)} ≤ {vec(b_avail)}")
            else:
                st.markdown(f":blue[:material/hourglass_top: No]: {vec(res.request)} ≰ {vec(b_avail)}. Wait.")
        with s3.container(border=True, height="stretch"):
            st.markdown("**Step 3 · Trial allocation safe?**")
            if res.trial_safety is None:
                st.markdown(":gray[Not reached]")
            elif res.trial_safety.safe:
                st.markdown(":green[:material/check: Yes]: safe sequence found")
            else:
                st.markdown(":orange[:material/close: No]: no safe sequence")

    if res.trial_safety is not None:
        with st.expander("Trial allocation and its safety check", icon=":material/science:",
                         expanded=res.status is Status.DENIED):
            st.caption(f"Trial Available = Available − Request = {vec(res.trial_available)}")
            tc1, tc2 = st.columns(2)
            with tc1:
                st.markdown("**Trial Allocation**")
                show_matrix(res.trial_allocation, [f"P{i}" for i in range(len(res.trial_allocation))],
                            before["resources"])
            with tc2:
                st.markdown("**Trial Need**")
                show_matrix(compute_need(res.trial_allocation, before["maximum"]),
                            [f"P{i}" for i in range(len(res.trial_allocation))], before["resources"])
            sequence_chips(res.trial_safety.sequence)
            trace_table(res.trial_safety.steps)

    if res.status in (Status.WAITING, Status.DENIED, Status.INVALID):
        same = (before["allocation"] == st.session_state.bank["allocation"]
                and before["available"] == st.session_state.bank["available"])
        if same:
            st.success("**State check passed:** Allocation and Available are exactly as they were before "
                       "the request.", icon=":material/verified:")
        else:
            st.error("State check failed: the state changed.", icon=":material/error:")
    if res.status is Status.DENIED:
        st.info(
            "**Why “unsafe” isn't “deadlocked”:** the trial state was only simulated. No process was "
            "blocked, and the real system is still safe. Banker's denies the request because it can't "
            "*guarantee* completion, not because a deadlock exists.",
            icon=":material/lightbulb:",
        )

if st.session_state.req_history:
    with st.expander("Request log for this session", icon=":material/history:"):
        st.dataframe(pd.DataFrame(st.session_state.req_history), hide_index=True, width="stretch")

footer()
