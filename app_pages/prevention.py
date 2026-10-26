import pandas as pd
import streamlit as st

from core.prevention import POLICIES, simulate
from core.scenarios import PREVENTION
from core.status import Status
from core.ui import footer, status_banner, timeline_chart

st.title(":material/rule: Prevention")
st.markdown(
    "Prevention changes the **rules of allocation** so that one of the four deadlock conditions can "
    "never hold. No runtime check is needed, because deadlock is impossible by design. Here the same "
    "workload runs under three policies so you can compare them."
)

st.header("1 · Define the workload", divider="gray")
st.caption("Every resource has one instance. Each process locks its resources one by one in the order "
           "listed, runs for its burst, then releases everything. Processes take turns, one action per tick.")

if "prev_plans" not in st.session_state:
    st.session_state.prev_plans = pd.DataFrame({
        "Process": [f"P{i}" for i in range(len(PREVENTION["plans"]))],
        "Acquisition order": [", ".join(f"R{r}" for r in p) for p in PREVENTION["plans"]],
        "Burst (ticks)": PREVENTION["bursts"],
    })

e1, e2 = st.columns([3, 1])
with e2:
    n_res = st.number_input("Resources (R0…)", min_value=1, max_value=8, value=PREVENTION["resources"])
    if st.button("Reset workload", icon=":material/restart_alt:"):
        del st.session_state.prev_plans
        st.session_state.pop("prev_editor", None)
        st.rerun()
with e1:
    table = st.data_editor(
        st.session_state.prev_plans, key="prev_editor", num_rows="dynamic", hide_index=True, width="stretch",
        column_config={
            "Process": st.column_config.TextColumn(disabled=True),
            "Acquisition order": st.column_config.TextColumn(help="Comma-separated, e.g. R2, R0"),
            "Burst (ticks)": st.column_config.NumberColumn(min_value=1, max_value=10, step=1, default=2),
        },
    )

plans, bursts, errors = [], [], []
for k, row in enumerate(table.itertuples(index=False)):
    raw = str(row[1] or "").replace(" ", "")
    ids = []
    for tok in filter(None, raw.split(",")):
        t = tok.upper().lstrip("R")
        if not t.isdigit() or int(t) >= n_res:
            errors.append(f"P{k}: '{tok}' isn't a resource. Use R0 to R{n_res - 1}.")
        elif int(t) in ids:
            errors.append(f"P{k}: R{t} is listed twice.")
        else:
            ids.append(int(t))
    plans.append(ids)
    bursts.append(int(row[2]) if pd.notna(row[2]) and int(row[2]) > 0 else 1)

if errors:
    status_banner(Status.INVALID, "The workload has errors.", errors)
    footer()
    st.stop()

results = {p: simulate(plans, n_res, p, bursts) for p in POLICIES}

st.header("2 · Compare the policies", divider="gray")
cols = st.columns(3)
breaks = {"none": "Nothing: all four conditions can hold",
          "ordering": "Circular wait",
          "all_at_once": "Hold and wait"}
for col, (key, res) in zip(cols, results.items()):
    with col.container(border=True, height="stretch"):
        st.markdown(f"**{POLICIES[key]}**")
        st.caption(f"Breaks: {breaks[key]}")
        if res.deadlocked:
            st.markdown(":red-badge[:material/sync_lock: Deadlock]")
            st.markdown(f"Stuck at tick {res.ticks}: " + " → ".join(f"P{i}" for i in res.cycle))
        else:
            st.markdown(":green-badge[:material/check: No deadlock]")
            st.markdown(f"All {len(res.finished)} processes done in **{res.ticks} ticks**")

summary = pd.DataFrame([{
    "Policy": POLICIES[k],
    "Deadlock?": "Yes" if r.deadlocked else "No",
    "Processes finished": f"{len(r.finished)} / {len(plans)}",
    "Ticks": r.ticks,
    "Idle holding (resource-ticks)": r.held_idle,
    "Useful utilization": r.utilization,
} for k, r in results.items()])
st.dataframe(summary, hide_index=True, width="stretch", column_config={
    "Useful utilization": st.column_config.ProgressColumn(
        format="percent", min_value=0, max_value=1,
        help="Share of resource-ticks in which a resource was held by a process that was actually running."),
    "Idle holding (resource-ticks)": st.column_config.NumberColumn(
        help="Ticks a resource sat locked by a process that was still waiting for something else. Wasted capacity."),
})

st.header("3 · Watch it tick by tick", divider="gray")
pick = st.segmented_control("Policy", list(POLICIES), format_func=POLICIES.get, default="none",
                            key="prev_pick", required=True)
sim = results[pick]
timeline_chart(sim.timeline, len(plans))
if pick == "ordering":
    st.caption("Rewritten plans under ordering: " +
               "; ".join(f"P{i}: " + " → ".join(f"R{r}" for r in sorted(p)) for i, p in enumerate(plans)))
with st.expander("Event log", icon=":material/list_alt:"):
    st.dataframe(pd.DataFrame([{"Tick": r.tick, "Process": f"P{r.process}", "State": r.state,
                                "Holding": ", ".join(f"R{x}" for x in r.holding) or "—", "Event": r.note}
                               for r in sim.timeline]), hide_index=True, width="stretch")

st.header("4 · Trade-offs", divider="gray")
base, ordr, aao = results["none"], results["ordering"], results["all_at_once"]
t1, t2 = st.columns(2)
with t1.container(border=True, height="stretch"):
    st.markdown("##### :material/sort: Ordered acquisition")
    st.markdown(
        "**Why it works:** to wait for Rj you must already hold only resources ranked below j. A cycle would "
        "need someone to hold a higher-ranked resource while waiting for a lower one, which the rule forbids.\n\n"
        f"**What it costs here:** {ordr.held_idle} resource-ticks of idle holding. A process must lock "
        "low-numbered resources first, even when it needs them last, so it holds them while it waits. "
        "Programmers also have to know every resource's rank ahead of time."
    )
with t2.container(border=True, height="stretch"):
    st.markdown("##### :material/inventory_2: All-at-once allocation")
    st.markdown(
        "**Why it works:** a waiting process holds nothing, so it can't block anyone. Hold-and-wait is gone.\n\n"
        f"**What it costs here:** finished in {aao.ticks} ticks with {aao.held_idle} idle resource-ticks, "
        "but a process must know its full need up front and claims everything for its whole run. "
        "A process that needs a popular resource can **starve**, waiting for the moment when *all* its "
        "resources are free together."
    )
if base.deadlocked:
    st.info(
        f"Without a policy, this workload deadlocks at tick {base.ticks}. Both policies remove the deadlock, "
        "and both pay for it with lower concurrency or utilization. Prevention is cheap to run but "
        "conservative. Avoidance (Banker's) allows more concurrency, but it needs maximum claims and a check "
        "on every request.",
        icon=":material/balance:",
    )
else:
    st.info("This workload happens to finish without a policy. Try making two processes lock the same "
            "resources in opposite order (e.g. P0: R0, R1 and P1: R1, R0) to create a deadlock.",
            icon=":material/lightbulb:")

footer()
