import pandas as pd
import streamlit as st

from core.ignorance import (COMPARISON, CONS, FREQUENCIES, IMPACTS, LIMITS, PROS, SCENARIOS, STRATEGIES,
                            check_choice, expected_yearly_cost, recommend)
from core.ui import footer, page_header

page_header(":material/visibility_off:", "Ignorance: the ostrich algorithm",
            "The simplest strategy of all: **do nothing**. The system runs no prevention, avoidance or "
            "detection code and accepts that a deadlock may occasionally happen. When it does, a person "
            "clears it by killing the stuck program, restarting a service or rebooting.",
            kicker="Strategy 4")

st.warning(
    "**Ignoring deadlocks does not make them go away.** Deadlocks still happen exactly as often as before. "
    "The system just doesn't notice them, and stuck processes keep holding their resources until someone "
    "steps in.",
    icon=":material/warning:",
)

st.header("Why would anyone ignore deadlocks?", divider="gray")
st.markdown(
    "Every handling strategy has a price: lower utilization (prevention), a safety check on every request "
    "(avoidance), or periodic scans and aborted work (detection & recovery). If deadlocks are **rare** and "
    "**cheap to clear**, that price can be higher than the cost of the occasional manual restart. The name "
    "comes from the myth of the ostrich hiding its head in the sand."
)
c1, c2, c3 = st.columns(3)
for col, title, icon, items in ((c1, "Advantages", ":material/thumb_up:", PROS),
                                (c2, "Disadvantages", ":material/thumb_down:", CONS),
                                (c3, "Limitations", ":material/block:", LIMITS)):
    with col.container(border=True, height="stretch"):
        st.markdown(f"##### {icon} {title}")
        st.markdown("\n".join(f"- {x}" for x in items))

st.header("How it compares", divider="gray")
st.dataframe(pd.DataFrame(COMPARISON), hide_index=True, width="stretch")

st.header("When is ignoring acceptable?", divider="gray")
st.markdown(
    "- **General-purpose OSes, for user programs.** Silberschatz et al. note that most operating systems, "
    "including Linux and Windows, leave deadlocks among applications to the user or developer. "
    "If two of your programs deadlock, you force-quit one.\n"
    "- **But not inside the kernel.** The same kernels avoid deadlocks in their *own* code by design: "
    "Linux, for example, checks lock acquisition order during development with its `lockdep` validator. "
    "Ignorance is a policy for *some* resources, not a whole-system choice.\n"
    "- **Never where a hang causes harm** (medical devices, flight control, industrial control) or "
    "where it silently loses money or data (payments, databases). Those need prevention, avoidance or "
    "detection & recovery.\n"
    "- **Only with someone watching.** It assumes a user or administrator notices the hang. Unattended "
    "systems usually add at least a watchdog timer that restarts a stuck service, which is a crude form "
    "of detection and recovery, not pure ignorance."
)

st.header("Your turn: pick a strategy", divider="gray")
st.caption("Read each situation and choose the strategy you'd use. Feedback appears as soon as you choose.")

best = 0
for s in SCENARIOS:
    with st.container(border=True):
        st.markdown(f"##### {s.title}")
        st.write(s.situation)
        choice = st.pills("Strategy", STRATEGIES, key=f"ign_{s.sid}", label_visibility="collapsed")
        if choice:
            v = check_choice(s, choice)
            best += v == "best"
            if v == "best":
                st.success(f"**Best choice.** {s.explanation}", icon=":material/check_circle:")
            elif v == "acceptable":
                st.info(f"**Reasonable, but {s.best} fits better.** {s.explanation}", icon=":material/info:")
            else:
                st.error(f"**Not a good fit. Best: {s.best}.** {s.explanation}", icon=":material/close:")
answered = sum(1 for s in SCENARIOS if st.session_state.get(f"ign_{s.sid}"))
st.progress(answered / len(SCENARIOS), text=f"{answered} of {len(SCENARIOS)} answered · {best} best choices")
if st.button("Clear my answers", icon=":material/restart_alt:"):
    for s in SCENARIOS:
        st.session_state.pop(f"ign_{s.sid}", None)
    st.rerun()

st.header("Strategy advisor", divider="gray")
st.caption("A rule of thumb, not a law: describe the system and see which strategy it points to, and why.")
a1, a2 = st.columns([2, 3])
with a1:
    freq = st.segmented_control("How often do deadlocks happen?", FREQUENCIES, default="rare",
                                format_func=str.capitalize, key="adv_freq", required=True)
    impact = st.segmented_control("What does one deadlock cost?", IMPACTS, default="low",
                                  format_func=lambda x: {"low": "Low (restart)", "medium": "Medium (lost work)",
                                                         "high": "High (harm or major loss)"}[x],
                                  key="adv_impact", required=True)
    known = st.toggle("Processes can declare their maximum needs in advance", key="adv_known")
with a2:
    rec = recommend(freq, impact, known)
    with st.container(border=True):
        st.markdown(f"**Suggested strategy:** :blue-badge[{rec.strategy}]")
        st.markdown("\n".join(f"- {r}" for r in rec.reasons))
        if rec.ignoring_acceptable:
            st.caption(":material/info: Ignoring is acceptable here only because deadlocks are rare and cheap. "
                       "It still won't stop them.")

st.header("Expected cost: ignore or handle?", divider="gray")
st.caption("A deliberately simple model for discussion. Use any consistent unit, such as hours of lost work.")
k1, k2, k3, k4 = st.columns(4)
rate = k1.number_input("Deadlocks per year", min_value=0.0, value=2.0, step=1.0)
cost = k2.number_input("Cost of one deadlock", min_value=0.0, value=4.0, step=1.0,
                       help="E.g. hours lost per incident")
overhead = k3.number_input("Yearly cost of handling", min_value=0.0, value=40.0, step=5.0,
                           help="Development, runtime checks, reduced throughput")
share = k4.slider("Share handled", 0, 100, 95, format="%d%%",
                  help="Fraction of deadlocks the mechanism stops or resolves cheaply") / 100
costs = expected_yearly_cost(rate, cost, overhead, share)
with st.container(horizontal=True):
    st.metric("Ignore: expected yearly cost", f"{costs['ignore']:,.1f}", border=True)
    st.metric("Handle: expected yearly cost", f"{costs['handle']:,.1f}", border=True)
if costs["cheaper"] == "ignore":
    st.info("With these numbers ignoring is cheaper. That's the ostrich argument. Check it still holds if one "
            "deadlock costs far more than you assumed.", icon=":material/calculate:")
else:
    st.success("With these numbers handling deadlocks is cheaper than ignoring them.", icon=":material/calculate:")

footer()
