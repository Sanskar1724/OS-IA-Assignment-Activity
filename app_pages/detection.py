from copy import deepcopy

import pandas as pd
import streamlit as st

from core.detection import (detection_algorithm, is_single_instance, name_cycle, pick_victim,
                            process_states, rag_cycle, recover, resource_summary, total_instances,
                            wait_for_edges, wfg_cycle)
from core.scenarios import DETECTION
from core.status import Status
from core.ui import (edit_matrix, edit_vector, footer, graph_legend, rag_dot, resize, resource_names,
                     sequence_chips, show_matrix, status_banner, trace_table, vec, wfg_dot)
from core.validation import validate_detection


def load_det(key: str, state: dict):
    st.session_state.det = deepcopy(state)
    st.session_state.det_key = key
    st.session_state.det_ver = st.session_state.get("det_ver", 0) + 1
    st.session_state.det_recovery = None


if "det" not in st.session_state:
    load_det("multi_deadlock", DETECTION["multi_deadlock"])

st.title(":material/troubleshoot: Detection & recovery")
st.markdown(
    "Detection lets the system allocate freely and checks **afterwards** whether some processes are "
    "permanently stuck. It works with what each process is **requesting right now**, not with maximum "
    "claims. If it finds a deadlock, recovery breaks it."
)
st.caption(":material/info: This is a separate function from Banker's Algorithm. Banker's prevents unsafe "
           "allocations but can't spot a deadlock that already exists. This page can.")

# --- 1. Scenario -------------------------------------------------------------------

st.header("1 · Describe the current allocation", divider="gray")

labels = {k: v["label"] for k, v in DETECTION.items()}
choice = st.segmented_control("Scenario", list(labels), format_func=labels.get,
                              default=st.session_state.det_key, key="det_choice", required=True)
if choice != st.session_state.det_key:
    load_det(choice, DETECTION[choice])
    st.rerun()

det = st.session_state.det
ver = st.session_state.det_ver
st.markdown(f":material/menu_book: {DETECTION[st.session_state.det_key]['story']}")

with st.container(horizontal=True):
    n = st.number_input("Processes", min_value=1, max_value=10, value=len(det["allocation"]), key=f"dn{ver}")
    m = st.number_input("Resource types", min_value=1, max_value=6, value=len(det["available"]), key=f"dm{ver}")
if (n, m) != (len(det["allocation"]), len(det["available"])):
    w = st.session_state.get("det_working", det)
    load_det(st.session_state.det_key, {**DETECTION[st.session_state.det_key],
                                        "resources": resource_names(m, w["resources"]),
                                        "allocation": resize(w["allocation"], n, m),
                                        "request": resize(w["request"], n, m),
                                        "available": resize([w["available"]], 1, m)[0]})
    st.rerun()

res_names = det["resources"]
procs = [f"P{i}" for i in range(n)]
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Allocation**: instances held now")
    allocation = edit_matrix(det["allocation"], procs, res_names, key=f"dalloc{ver}")
with c2:
    st.markdown("**Request**: instances each process is waiting for now")
    request = edit_matrix(det["request"], procs, res_names, key=f"dreq{ver}")
c3, c4 = st.columns(2)
with c3:
    st.markdown("**Available**: free instances")
    available = edit_vector(det["available"], res_names, key=f"davail{ver}", row_label="Free")
st.session_state.det_working = {**det, "allocation": allocation, "request": request, "available": available}

errors = validate_detection(allocation, request, available)
if errors:
    status_banner(Status.INVALID, "This allocation can't be analysed. Fix the cells above.", errors)
    footer()
    st.stop()

totals = total_instances(allocation, available)
single = is_single_instance(allocation, available)
with c4:
    st.markdown("**Resource model**")
    with st.container(border=True):
        if single:
            st.markdown(":violet-badge[:material/looks_one: Single-instance resources]")
            st.caption(f"Every resource type has exactly one instance {vec(totals)}. A cycle in the wait-for "
                       "graph is **necessary and sufficient**: a cycle proves deadlock.")
        else:
            st.markdown(":blue-badge[:material/stacks: Multiple-instance resources]")
            st.caption(f"Total instances {vec(totals)}. A cycle is **necessary but not sufficient**. "
                       "The detection algorithm decides.")

# --- 2. Graph -------------------------------------------------------------------------

st.header("2 · Look for circular wait", divider="gray")
result = detection_algorithm(allocation, request, available)
r_cycle = rag_cycle(allocation, request)
w_cycle = wfg_cycle(allocation, request)

g1, g2 = st.columns([3, 2])
with g1:
    view = st.segmented_control("Graph", ["Resource-allocation graph", "Wait-for graph"],
                                default="Resource-allocation graph", key="det_view", required=True)
    if view == "Wait-for graph":
        st.graphviz_chart(wfg_dot(n, wait_for_edges(allocation, request), res_names, w_cycle, result.deadlocked),
                          width="stretch")
        st.caption("The wait-for graph collapses resources: P → Q means P waits for something Q holds. "
                   "The edge label names the resource.")
    else:
        st.graphviz_chart(rag_dot(allocation, request, res_names, r_cycle, result.deadlocked, available),
                          width="stretch")
with g2:
    st.markdown("**How to read it**")
    graph_legend()

r1, r2 = st.columns(2)
with r1:
    st.markdown("**Resource availability**")
    st.dataframe(pd.DataFrame([{
        "Resource": res_names[r["resource"]], "Total": r["total"], "Held": r["allocated"], "Free": r["free"],
        "Requested": r["requested"], "Short by": r["shortfall"],
    } for r in resource_summary(allocation, request, available)]), hide_index=True, width="stretch",
        column_config={"Short by": st.column_config.NumberColumn(
            help="Outstanding requests minus free instances. Above 0 means some requests can't be met now.")})
with r2:
    st.markdown("**Process states**")
    label = {"deadlocked": "🔴 Deadlocked", "waiting": "🟠 Waiting", "not waiting": "🔵 Not waiting"}
    st.dataframe(pd.DataFrame([{
        "Process": f"P{r['process']}", "Holds": vec(allocation[r["process"]]),
        "Requests": vec(request[r["process"]]), "State": label[r["state"]],
        "Waits on": ", ".join(f"P{k}" for k in r["waits_on"]) or "—",
        "Finishes": f"#{r['finish_order']}" if r["finish_order"] else "never",
    } for r in process_states(allocation, request, result)]), hide_index=True, width="stretch")

with st.expander("Why a cycle isn't always a deadlock", icon=":material/help:"):
    st.markdown(
        "- With **single-instance** resources, every request edge points at the one holder. If the waits "
        "form a cycle, nobody in it can ever be served: the cycle **proves** deadlock.\n"
        "- With **multiple instances**, a process on the cycle can be served by *another* instance, held by "
        "a process **outside** the cycle. When that process finishes and releases it, the cycle breaks.\n"
        "- So for multiple instances a cycle is only a **potential** circular wait. The detection algorithm "
        "(Work/Finish reduction on current requests) gives the confirmed answer.\n"
        "- Try the *cycle but NO deadlock* scenario: P0 → R0 → P2 → R1 → P0 is a cycle, yet P1 and P3 free "
        "the instances that P0 and P2 need."
    )

# --- 3. Verdict ---------------------------------------------------------------------------

st.header("3 · Is there a deadlock?", divider="gray")
v1, v2 = st.columns(2)
with v1.container(border=True, height="stretch"):
    st.markdown("**Graph check: circular wait**")
    if r_cycle:
        st.markdown(":orange-badge[:material/cycle: Cycle found]")
        st.markdown(" → ".join(name_cycle(r_cycle, res_names)))
        st.caption("Proof of deadlock for single-instance resources." if single else
                   "Only a *potential* circular wait, because resources have several instances.")
    else:
        st.markdown(":green-badge[:material/check: No cycle]")
        st.caption("Without a cycle there can't be a deadlock, whatever the resource model.")
with v2.container(border=True, height="stretch"):
    st.markdown("**Detection algorithm: confirmed result**")
    if result.deadlocked:
        st.markdown(":red-badge[:material/sync_lock: Deadlock]")
        st.markdown("Deadlocked: " + ", ".join(f"**P{i}**" for i in result.deadlocked))
    else:
        st.markdown(":green-badge[:material/lock_open: No deadlock]")
        st.markdown("Every process can finish in this order:")
        sequence_chips(result.sequence)

if result.deadlocked:
    reasons = [f"The detection algorithm finished {', '.join(f'P{i}' for i in result.sequence) or 'no process'} "
               f"and then got stuck with Work = {vec(result.final_work)}."]
    reasons += [f"P{i} requests {vec(request[i])}, which doesn't fit in {vec(result.final_work)}, and the only "
                "processes that could free more are also stuck." for i in result.deadlocked]
    reasons.append("Single-instance model: the cycle alone already proved this." if single else
                   "Multiple-instance model: confirmed by the detection algorithm, not just the cycle.")
    status_banner(Status.DEADLOCK, f"{len(result.deadlocked)} processes are deadlocked.", reasons)
elif r_cycle:
    status_banner(Status.NO_DEADLOCK, "There's a cycle, but no deadlock.", [
        "The graph shows a circular wait, so a deadlock was possible.",
        "But processes outside the cycle aren't blocked. When they finish they release instances, and "
        "the processes in the cycle can then go on.",
        "So with multiple instances, a cycle alone doesn't prove deadlock.",
    ])
else:
    status_banner(Status.NO_DEADLOCK, "No deadlock. Every process can finish.")

with st.expander("Detection algorithm trace", icon=":material/list_alt:", expanded=bool(result.deadlocked)):
    st.caption("Same idea as Banker's safety check, but it compares each process's current Request with "
               "Work, not its Need. Processes holding nothing start as finished.")
    trace_table(result.steps, need_label="Request")

# --- 4. Recovery -------------------------------------------------------------------------

if result.deadlocked:
    st.header("4 · Recover by aborting a process", divider="gray")
    st.markdown(
        "Abort a deadlocked process (the **victim**). Its resources go back to Available and the "
        "detection algorithm runs again. If processes are still stuck, the next victim is chosen "
        "automatically."
    )
    default = pick_victim(result.deadlocked, allocation)
    with st.container(horizontal=True, vertical_alignment="bottom"):
        victim = st.selectbox(
            "Victim", result.deadlocked, index=result.deadlocked.index(default),
            format_func=lambda i: f"P{i}: holds {vec(allocation[i])}" + ("  (suggested)" if i == default else ""),
            help="Suggested victim: the deadlocked process holding the most instances. Freeing the most "
                 "resources tends to end the deadlock with the fewest aborts.",
        )
        go = st.button("Abort and release resources", icon=":material/cancel:", type="primary")

    sig = repr((allocation, request, available))
    if go:
        st.session_state.det_recovery = {"sig": sig, "rec": recover(allocation, request, available, victim)}
    saved = st.session_state.get("det_recovery")
    if saved and saved["sig"] == sig:
        rec = saved["rec"]
        for k, s in enumerate(rec.steps, start=1):
            with st.container(border=True):
                st.markdown(f"**Step {k} · Abort P{s.victim}**")
                st.markdown(
                    f"P{s.victim} is terminated and releases {vec(s.released)}. "
                    f"Available becomes {vec(s.available_after)}."
                )
                if s.detection.deadlocked:
                    st.markdown(":red-badge[Still deadlocked] " +
                                ", ".join(f"P{i}" for i in s.detection.deadlocked))
                else:
                    st.markdown(":green-badge[Deadlock resolved]. Remaining processes now finish in this order:")
                    aborted = {x.victim for x in rec.steps}
                    sequence_chips([i for i in s.detection.sequence if i not in aborted])
        if rec.resolved:
            victims = ", ".join(f"P{s.victim}" for s in rec.steps)
            status_banner(Status.NO_DEADLOCK, f"Recovered by aborting {victims}.", [
                f"Released resources raised Available to {vec(rec.steps[-1].available_after)}.",
                "With those free instances, the remaining requests fit one after another, so every surviving "
                "process can finish.",
                f"Cost: {victims} lost its work and must restart from scratch.",
            ])
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**Allocation after recovery**")
            show_matrix(rec.allocation, procs, res_names)
        with a2:
            st.markdown("**Graph after recovery**")
            st.graphviz_chart(rag_dot(rec.allocation, rec.request, res_names, [], [], rec.available), width="stretch")

footer()
