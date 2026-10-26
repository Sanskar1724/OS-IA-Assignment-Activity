"""Shared Streamlit helpers: status banners, matrix editors, graphs and charts.

This is the only module in core/ that imports Streamlit.
"""

import altair as alt
import pandas as pd
import streamlit as st

from core.status import STATUS_STYLE, Status

# Callout used for each state. INVALID and DEADLOCK share st.error's colour but
# always carry different badges and icons, so they are never confused.
_CALLOUT = {
    Status.SAFE: st.success, Status.GRANTED: st.success, Status.NO_DEADLOCK: st.success,
    Status.WAITING: st.info,
    Status.UNSAFE: st.warning, Status.DENIED: st.warning,
    Status.DEADLOCK: st.error, Status.INVALID: st.error,
}

# Chart colours (validated categorical slots from the dataviz reference palette).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
ALLOCATED, FREE = "#2a78d6", "#c9c8c3"


def vec(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")"


def status_badge(status: Status):
    color, icon, _ = STATUS_STYLE[status]
    st.badge(status.value, icon=icon, color=color)


def status_banner(status: Status, headline: str, reasons: list[str] | None = None):
    color, icon, meaning = STATUS_STYLE[status]
    body = f"**{headline}**"
    if reasons:
        body += "\n\n" + "\n".join(f"- {r}" for r in reasons)
    else:
        body += f"\n\n{meaning}"
    with st.container():
        st.badge(status.value, icon=icon, color=color)
        _CALLOUT[status](body, icon=icon)


def status_legend(statuses: list[Status] | None = None):
    statuses = statuses or list(Status)
    lines = []
    for s in statuses:
        color, icon, meaning = STATUS_STYLE[s]
        lines.append(f":{color}-badge[{icon} {s.value}] {meaning}")
    st.markdown("\n\n".join(lines))


def sequence_chips(seq: list[int], prefix: str = "P"):
    if not seq:
        st.markdown(":red-badge[:material/block: No complete sequence]")
        return
    st.markdown(" → ".join(f":green-badge[{prefix}{i}]" for i in seq))


def matrix_df(mat, rows: list[str], cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(mat, index=rows, columns=cols)


def edit_matrix(mat, rows: list[str], cols: list[str], key: str, disabled: bool = False,
                help_text: str | None = None) -> list[list[int]]:
    """An integer grid editor. Negative values are allowed on purpose so the
    validation layer (Scenario F) can catch and explain them."""
    df = matrix_df(mat, rows, cols)
    cfg = {c: st.column_config.NumberColumn(c, step=1, format="%d", help=help_text) for c in cols}
    out = st.data_editor(df, key=key, column_config=cfg, disabled=disabled, width="stretch")
    return out.fillna(0).astype(int).values.tolist()


def edit_vector(v, cols: list[str], key: str, row_label: str) -> list[int]:
    return edit_matrix([v], [row_label], cols, key)[0]


def trace_table(steps, need_label: str = "Need"):
    """Step-by-step trace of the safety / detection algorithm."""
    rows = [{
        "Pass": s.pass_no,
        "Process": f"P{s.process}",
        need_label: vec(getattr(s, "need", None) or getattr(s, "request", [])),
        "Work before": vec(s.work_before),
        f"{need_label} ≤ Work?": "Yes: finishes" if s.can_finish else "No: skip for now",
        "Work after": vec(s.work_after),
    } for s in steps]
    df = pd.DataFrame(rows)

    def tint(row):
        ok = row[f"{need_label} ≤ Work?"].startswith("Yes")
        return ["color: #137a52; font-weight: 600" if ok else "color: #8a8983"] * len(row)

    st.dataframe(df.style.apply(tint, axis=1), hide_index=True, width="stretch")


def show_matrix(mat, rows: list[str], cols: list[str]):
    st.dataframe(matrix_df(mat, rows, cols), width="stretch")


def resize(mat, n: int, m: int) -> list[list[int]]:
    mat = [list(r[:m]) + [0] * max(0, m - len(r)) for r in mat[:n]]
    return mat + [[0] * m for _ in range(n - len(mat))]


def resource_names(m: int, current: list[str]) -> list[str]:
    if len(current) >= m:
        return current[:m]
    pool = [chr(ord("A") + k) for k in range(26)]
    extra = [p for p in pool if p not in current]
    return current + extra[: m - len(current)]


# --- Charts -------------------------------------------------------------------

def allocation_chart(allocation, available, resources: list[str]):
    """Stacked bar per resource type: allocated (by process) vs free instances."""
    rows = []
    for i, row in enumerate(allocation):
        for j, v in enumerate(row):
            if v > 0:
                rows.append({"Resource": resources[j], "Holder": f"P{i}", "Instances": v, "Kind": "Allocated"})
    for j, v in enumerate(available):
        rows.append({"Resource": resources[j], "Holder": "Free", "Instances": v, "Kind": "Free"})
    df = pd.DataFrame(rows)
    if df.empty or df["Instances"].sum() == 0:
        st.caption("Nothing allocated and nothing free.")
        return
    holders = [f"P{i}" for i in range(len(allocation))] + ["Free"]
    palette = (SERIES * 3)[: len(allocation)] + [FREE]
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, stroke="white", strokeWidth=2)
        .encode(
            y=alt.Y("Resource:N", title=None, sort=resources),
            x=alt.X("sum(Instances):Q", title="Instances", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Holder:N", scale=alt.Scale(domain=holders, range=palette),
                            legend=alt.Legend(title="Held by", orient="bottom")),
            order=alt.Order("Holder:N"),
            tooltip=["Resource", "Holder", "Instances"],
        )
        .properties(height=40 * len(resources) + 60)
    )
    st.altair_chart(chart, width="stretch")


def work_chart(sequence: list[int], start_work, allocation, resources: list[str]):
    """How the Work vector grows as each process in the safe sequence finishes."""
    rows, work = [], list(start_work)
    rows += [{"Step": "Start", "Resource": r, "Work": w, "order": 0} for r, w in zip(resources, work)]
    for k, pid in enumerate(sequence, start=1):
        work = [a + b for a, b in zip(work, allocation[pid])]
        rows += [{"Step": f"P{pid} done", "Resource": r, "Work": w, "order": k} for r, w in zip(resources, work)]
    df = pd.DataFrame(rows)
    steps = list(dict.fromkeys(df["Step"]))
    chart = (
        alt.Chart(df)
        .mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2)
        .encode(
            x=alt.X("Step:N", sort=steps, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Work:Q", title="Free instances (Work)", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Resource:N", scale=alt.Scale(domain=resources, range=SERIES[: len(resources)]),
                            legend=alt.Legend(orient="bottom")),
            tooltip=["Step", "Resource", "Work"],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, width="stretch")


def timeline_chart(records, n_processes: int):
    """Per-process state at every tick of the prevention simulation."""
    states = ["acquiring", "waiting", "running", "done", "deadlocked"]
    colors = ["#2a78d6", "#eda100", "#1baf7a", "#d9d8d3", "#e34948"]
    df = pd.DataFrame([{"Tick": r.tick, "Process": f"P{r.process}", "State": r.state,
                        "Holding": ", ".join(f"R{x}" for x in r.holding) or "—", "Event": r.note}
                       for r in records])
    chart = (
        alt.Chart(df)
        .mark_rect(cornerRadius=3, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("Tick:O", title="Tick", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Process:N", title=None, sort=[f"P{i}" for i in range(n_processes)]),
            color=alt.Color("State:N", scale=alt.Scale(domain=states, range=colors),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Tick", "Process", "State", "Holding", "Event"],
        )
        .properties(height=46 * n_processes + 50)
    )
    st.altair_chart(chart, width="stretch")


# --- Graphs -------------------------------------------------------------------

def rag_dot(allocation, request, resources: list[str], cycle: list[str] | None = None,
            deadlocked: list[int] | None = None, totals: list[int] | None = None) -> str:
    """Resource-allocation graph as Graphviz DOT. Cycle edges are drawn in red."""
    cycle = cycle or []
    deadlocked = set(deadlocked or [])
    cyc_edges = set(zip(cycle, cycle[1:]))
    out = ['digraph G {', 'rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.9;',
           'node [fontname="Helvetica" fontsize=12]; edge [fontname="Helvetica" fontsize=10];']
    for i in range(len(allocation)):
        fill = "#fde2e1" if i in deadlocked else "#e6f0fb"
        line = "#c62828" if i in deadlocked else "#2a78d6"
        out.append(f'P{i} [label="P{i}" shape=circle style=filled fillcolor="{fill}" color="{line}" penwidth=2 fontcolor="#111"];')
    for j, name in enumerate(resources):
        dots = "●" * min(totals[j], 6) if totals else ""
        label = f"{name}\\n{dots}" if dots else name
        out.append(f'R{j} [label="{label}" shape=box style="rounded,filled" fillcolor="#f4f4f2" color="#77766f" fontcolor="#111"];')
    for i, (arow, rrow) in enumerate(zip(allocation, request)):
        for j, (a, r) in enumerate(zip(arow, rrow)):
            if a > 0:
                hot = (f"R{j}", f"P{i}") in cyc_edges
                c = "#c62828" if hot else "#2a78d6"
                lbl = f' label="{a}"' if a > 1 else ""
                out.append(f'R{j} -> P{i} [color="{c}" penwidth={2.6 if hot else 1.6}{lbl}];')
            if r > 0:
                hot = (f"P{i}", f"R{j}") in cyc_edges
                c = "#c62828" if hot else "#77766f"
                lbl = f' label="{r}"' if r > 1 else ""
                out.append(f'P{i} -> R{j} [color="{c}" style=dashed penwidth={2.6 if hot else 1.4}{lbl}];')
    out.append("}")
    return "\n".join(out)


def wfg_dot(n: int, edges, resources: list[str], cycle: list[str] | None = None,
            deadlocked: list[int] | None = None) -> str:
    cycle = cycle or []
    deadlocked = set(deadlocked or [])
    cyc_edges = set(zip(cycle, cycle[1:]))
    out = ['digraph G {', 'rankdir=LR; bgcolor="transparent";',
           'node [fontname="Helvetica" fontsize=12 shape=circle style=filled]; edge [fontname="Helvetica" fontsize=10];']
    for i in range(n):
        fill = "#fde2e1" if i in deadlocked else "#e6f0fb"
        line = "#c62828" if i in deadlocked else "#2a78d6"
        out.append(f'P{i} [fillcolor="{fill}" color="{line}" penwidth=2 fontcolor="#111"];')
    seen = set()
    for a, b, j in edges:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        hot = (f"P{a}", f"P{b}") in cyc_edges
        out.append(f'P{a} -> P{b} [label="{resources[j]}" color="{"#c62828" if hot else "#77766f"}" penwidth={2.6 if hot else 1.4}];')
    out.append("}")
    return "\n".join(out)


def footer():
    from core.project import PROJECT
    st.caption(
        f"© {PROJECT['year']} {PROJECT['group']} · {PROJECT['course']}, {PROJECT['activity']} · "
        f"{PROJECT['institute']}. Built with Streamlit. Algorithms verified by the test suite in tests/."
    )
