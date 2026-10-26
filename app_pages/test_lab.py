from dataclasses import asdict

import pandas as pd
import streamlit as st

from core.testcases import run_all, tc6_cases
from core.ui import footer

st.title(":material/fact_check: Test lab")
st.markdown(
    "The **Required Analytical Results Table** (Section 3 of the brief). Every *Actual result* below is "
    "produced live by running the same functions the dashboard uses. Nothing is typed in by hand."
)

rows = run_all()
subs = tc6_cases()
passed = sum(r.passed for r in rows)

with st.container(horizontal=True):
    st.metric("Test cases passing", f"{passed} / {len(rows)}", border=True)
    st.metric("Boundary & invalid sub-cases", f"{sum(s.passed for s in subs)} / {len(subs)}", border=True)
    st.metric("Scenarios covered", "A – F", border=True,
              help="Safe, waiting, unsafe/denied, deadlock, prevention, boundary/invalid.")

st.header("Required analytical results", divider="gray")


def to_df(items) -> pd.DataFrame:
    df = pd.DataFrame([asdict(r) for r in items])
    df["passed"] = df["passed"].map({True: "✅ Pass", False: "❌ Fail"})
    return df.rename(columns={"tc": "Test case", "condition": "System condition", "input": "Input",
                              "actual": "Actual result", "expected": "Expected result",
                              "passed": "Match?", "analysis": "Analysis / conclusion"})


main = to_df(rows)
cfg = {"Analysis / conclusion": st.column_config.TextColumn(width="large"),
       "Actual result": st.column_config.TextColumn(width="medium")}
st.dataframe(main[["Test case", "System condition", "Actual result", "Expected result", "Match?",
                   "Analysis / conclusion"]], hide_index=True, width="stretch", column_config=cfg)

where = {"TC1": "Avoidance → Load Scenario A",
         "TC2": "Avoidance → Scenario B button",
         "TC3": "Avoidance → Scenario C button",
         "TC4": "Detection → Multiple-instance: deadlock confirmed",
         "TC5": "Prevention → compare policies",
         "TC6": "Avoidance → edit cells / custom request"}
st.subheader("Details and how to reproduce each case")
for r in rows:
    with st.expander(f"{r.tc} · {r.condition}", icon=":material/check_circle:" if r.passed else ":material/cancel:"):
        st.markdown(f"**Input:** {r.input}")
        st.markdown(f"**Expected:** {r.expected}")
        st.markdown(f"**Actual:** {r.actual}")
        st.markdown(f"**Analysis:** {r.analysis}")
        st.caption(f":material/near_me: Reproduce in the dashboard: {where[r.tc]}")

st.header("TC6 · Boundary vs invalid inputs (Scenario F)", divider="gray")
st.markdown(
    "**Boundary** inputs are unusual but legal, so the algorithm runs normally. **Invalid** inputs break "
    "a rule and are rejected *before* the algorithm runs, with a message saying exactly what's wrong. "
    "A request that exceeds Available is **neither**: it's valid and simply waits."
)
sub = to_df(subs)
sub.insert(2, "Kind", ["Boundary" if s.tc in ("TC6a", "TC6b", "TC6c") else "Invalid" for s in subs])
st.dataframe(sub[["Test case", "System condition", "Kind", "Input", "Actual result", "Match?",
                  "Analysis / conclusion"]], hide_index=True, width="stretch", column_config=cfg)

st.header("Export for your report", divider="gray")
full = pd.concat([main, sub.drop(columns=["Kind"])], ignore_index=True)
md = "| Test case | System condition | Actual result | Expected result | Analysis |\n|---|---|---|---|---|\n" + "\n".join(
    f"| {r['Test case']} | {r['System condition']} | {r['Actual result']} | {r['Expected result']} | "
    f"{r['Analysis / conclusion']} |" for _, r in full.iterrows())
with st.container(horizontal=True):
    st.download_button("Download CSV", full.to_csv(index=False).encode("utf-8"), "deadlock_test_results.csv",
                       "text/csv", icon=":material/download:")
    st.download_button("Download Markdown table", md.encode("utf-8"), "deadlock_test_results.md",
                       "text/markdown", icon=":material/description:")
st.caption("Command-line check: `pytest -q` runs the same cases and more in tests/test_core.py.")

footer()
