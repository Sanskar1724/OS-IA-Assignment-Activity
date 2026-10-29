"""Shared Streamlit helpers: status banners, matrix editors, graphs and charts.

This is the only module in core/ that imports Streamlit. Every colour used by a
chart or graph comes from palette(), which follows the light/dark theme the
viewer picked in the app menu.
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

# Categorical slots from the dataviz reference palette, stepped for each surface.
_LIGHT = {
    "bg": "#FFFFFF", "ink": "#0F172A", "muted": "#5B6472", "edge": "#77766F", "grid": "#D9D8D3",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "free": "#C9C8C3", "ok": "#137A52",
    "proc_fill": "#E6F0FB", "proc_line": "#2A78D6",
    "wait_fill": "#FFF3DC", "wait_line": "#B87800",
    "dead_fill": "#FDE2E1", "dead_line": "#C62828",
    "res_fill": "#F4F4F2", "res_line": "#77766F",
    "assign": "#2A78D6", "request": "#D95926", "cycle": "#C62828",
    "states": ["#2a78d6", "#eda100", "#1baf7a", "#D9D8D3", "#e34948"],
}
_DARK = {
    "bg": "#0F141B", "ink": "#E6EAF0", "muted": "#9AA4B2", "edge": "#8B95A3", "grid": "#2A3441",
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
    "free": "#4A5361", "ok": "#4FD19B",
    "proc_fill": "#16263D", "proc_line": "#5B9BF0",
    "wait_fill": "#3A2C10", "wait_line": "#E0A526",
    "dead_fill": "#3A1A1C", "dead_line": "#FF6B6B",
    "res_fill": "#1C2531", "res_line": "#8B95A3",
    "assign": "#5B9BF0", "request": "#E07A45", "cycle": "#FF6B6B",
    "states": ["#3987e5", "#c98500", "#199e70", "#3A4452", "#e66767"],
}


def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def palette() -> dict:
    return _DARK if is_dark() else _LIGHT


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


def trace_table(steps, need_label: str = "Need", current: int | None = None):
    """Step-by-step trace of the safety / detection algorithm.

    current (1-based) marks the step the step-through view is on.
    """
    p = palette()
    rows = [{
        "Step": k,
        "Pass": s.pass_no,
        "Process": f"P{s.process}",
        need_label: vec(getattr(s, "need", None) or getattr(s, "request", [])),
        "Work before": vec(s.work_before),
        f"{need_label} ≤ Work?": "Yes: finishes" if s.can_finish else "No: skip for now",
        "Work after": vec(s.work_after),
    } for k, s in enumerate(steps, start=1)]
    df = pd.DataFrame(rows)

    def tint(row):
        ok = row[f"{need_label} ≤ Work?"].startswith("Yes")
        style = f"color: {p['ok']}; font-weight: 600" if ok else f"color: {p['muted']}"
        if current is not None and row["Step"] == current:
            style += f"; background-color: {p['wait_fill']}"
        return [style] * len(row)

    st.dataframe(df.style.apply(tint, axis=1), hide_index=True, width="stretch")


def show_matrix(mat, rows: list[str], cols: list[str]):
    st.dataframe(matrix_df(mat, rows, cols), width="stretch")


def banker_matrices(allocation, maximum, need, resources: list[str], finished: list[bool],
                    current: int | None = None):
    """Allocation | Maximum | Need side by side, one row per process.

    Finished processes are greyed out; the process being checked is highlighted.
    """
    p = palette()
    data = {}
    for label, mat in (("Alloc", allocation), ("Max", maximum), ("Need", need)):
        for j, r in enumerate(resources):
            data[f"{label} {r}"] = [row[j] for row in mat]
    df = pd.DataFrame(data, index=[f"P{i}" for i in range(len(allocation))])
    df.insert(0, "Finish", ["true" if f else "false" for f in finished])

    def tint(row):
        i = int(row.name[1:])
        if current is not None and i == current:
            return [f"background-color: {p['wait_fill']}; font-weight: 700"] * len(row)
        if finished[i]:
            return [f"color: {p['muted']}"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(tint, axis=1), width="stretch")


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
    p = palette()
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
    colors = (p["series"] * 3)[: len(allocation)] + [p["free"]]
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, stroke=p["bg"], strokeWidth=2)
        .encode(
            y=alt.Y("Resource:N", title=None, sort=resources),
            x=alt.X("sum(Instances):Q", title="Instances", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Holder:N", scale=alt.Scale(domain=holders, range=colors),
                            legend=alt.Legend(title="Held by", orient="bottom")),
            order=alt.Order("Holder:N"),
            tooltip=["Resource", "Holder", "Instances"],
        )
        .properties(height=40 * len(resources) + 60)
    )
    st.altair_chart(chart, width="stretch")


def work_chart(sequence: list[int], start_work, allocation, resources: list[str]):
    """How the Work vector grows as each process in the safe sequence finishes."""
    p = palette()
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
            color=alt.Color("Resource:N", scale=alt.Scale(domain=resources, range=p["series"][: len(resources)]),
                            legend=alt.Legend(orient="bottom")),
            tooltip=["Step", "Resource", "Work"],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, width="stretch")


def timeline_chart(records, n_processes: int):
    """Per-process state at every tick of the prevention simulation."""
    p = palette()
    states = ["acquiring", "waiting", "running", "done", "deadlocked"]
    df = pd.DataFrame([{"Tick": r.tick, "Process": f"P{r.process}", "State": r.state,
                        "Holding": ", ".join(f"R{x}" for x in r.holding) or "—", "Event": r.note}
                       for r in records])
    chart = (
        alt.Chart(df)
        .mark_rect(cornerRadius=3, stroke=p["bg"], strokeWidth=2)
        .encode(
            x=alt.X("Tick:O", title="Tick", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Process:N", title=None, sort=[f"P{i}" for i in range(n_processes)]),
            color=alt.Color("State:N", scale=alt.Scale(domain=states, range=p["states"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Tick", "Process", "State", "Holding", "Event"],
        )
        .properties(height=46 * n_processes + 50)
    )
    st.altair_chart(chart, width="stretch")


# --- Graphs -------------------------------------------------------------------

def _dot_header(p: dict, extra: str = "") -> list[str]:
    return ['digraph G {', f'rankdir=LR; bgcolor="transparent"; {extra}',
            f'node [fontname="Helvetica" fontsize=12 fontcolor="{p["ink"]}"]; '
            f'edge [fontname="Helvetica" fontsize=10 fontcolor="{p["muted"]}"];']


def _instances(allocated: int, free: int) -> str:
    """● for each allocated instance, ○ for each free one (compact for large counts)."""
    if allocated + free <= 8:
        return "●" * allocated + "○" * free
    return f"{allocated} held · {free} free"


def rag_dot(allocation, request, resources: list[str], cycle: list[str] | None = None,
            deadlocked: list[int] | None = None, available: list[int] | None = None,
            show_states: bool = True) -> str:
    """Resource-allocation graph as Graphviz DOT.

    Assignment edges (R → P, held) are solid; request edges (P → R, waiting) are
    dashed and in a second colour. Cycle edges are thick and red. Processes are
    shaded by state: deadlocked, waiting, or not waiting. Processes on a cycle
    that is NOT a confirmed deadlock get a dashed red outline (potential only).
    """
    p = palette()
    cycle = cycle or []
    deadlocked = set(deadlocked or [])
    cyc_edges = set(zip(cycle, cycle[1:]))
    on_cycle = {v for v in cycle if v.startswith("P")}
    out = _dot_header(p, "nodesep=0.4; ranksep=1.0;")
    for i in range(len(allocation)):
        waiting = any(request[i])
        if i in deadlocked:
            fill, line, state = p["dead_fill"], p["dead_line"], "deadlocked"
        elif waiting:
            fill, line, state = p["wait_fill"], p["wait_line"], "waiting"
        else:
            fill, line, state = p["proc_fill"], p["proc_line"], "not waiting"
        style = "filled,dashed" if f"P{i}" in on_cycle and i not in deadlocked else "filled"
        if style.endswith("dashed"):
            line = p["cycle"]
        label = f"P{i}\\n{state}" if show_states else f"P{i}"
        out.append(f'P{i} [label="{label}" shape=circle style="{style}" fillcolor="{fill}" color="{line}" '
                   f'penwidth=2 fontsize=11];')
    for j, name in enumerate(resources):
        held = sum(row[j] for row in allocation)
        if available is not None:
            free = available[j]
            label = f"{name}\\n{_instances(held, free)}\\nfree {free}/{held + free}"
        else:
            label = name
        out.append(f'R{j} [label="{label}" shape=box style="rounded,filled" fillcolor="{p["res_fill"]}" '
                   f'color="{p["res_line"]}"];')
    for i, (arow, rrow) in enumerate(zip(allocation, request)):
        for j, (a, r) in enumerate(zip(arow, rrow)):
            if a > 0:
                hot = (f"R{j}", f"P{i}") in cyc_edges
                c = p["cycle"] if hot else p["assign"]
                lbl = f' label="holds {a}"' if a > 1 else ""
                out.append(f'R{j} -> P{i} [color="{c}" penwidth={3 if hot else 1.6}{lbl}];')
            if r > 0:
                hot = (f"P{i}", f"R{j}") in cyc_edges
                c = p["cycle"] if hot else p["request"]
                lbl = f' label="wants {r}"' if r > 1 else ""
                out.append(f'P{i} -> R{j} [color="{c}" style=dashed penwidth={3 if hot else 1.6}{lbl}];')
    out.append("}")
    return "\n".join(out)


def wfg_dot(n: int, edges, resources: list[str], cycle: list[str] | None = None,
            deadlocked: list[int] | None = None) -> str:
    p = palette()
    cycle = cycle or []
    deadlocked = set(deadlocked or [])
    cyc_edges = set(zip(cycle, cycle[1:]))
    waiting = {a for a, _, _ in edges}
    out = _dot_header(p)
    for i in range(n):
        if i in deadlocked:
            fill, line = p["dead_fill"], p["dead_line"]
        elif i in waiting:
            fill, line = p["wait_fill"], p["wait_line"]
        else:
            fill, line = p["proc_fill"], p["proc_line"]
        out.append(f'P{i} [shape=circle style=filled fillcolor="{fill}" color="{line}" penwidth=2];')
    labels: dict[tuple[int, int], list[str]] = {}
    for a, b, j in edges:
        labels.setdefault((a, b), []).append(resources[j])
    for (a, b), names in labels.items():
        hot = (f"P{a}", f"P{b}") in cyc_edges
        out.append(f'P{a} -> P{b} [label="{", ".join(names)}" color="{p["cycle"] if hot else p["edge"]}" '
                   f'penwidth={3 if hot else 1.4}];')
    out.append("}")
    return "\n".join(out)


def graph_legend():
    """Markdown legend matching rag_dot's encoding (theme colours via named colours)."""
    st.markdown(
        "- :blue[**Solid arrow R → P**]: an instance of R is **held** by P\n"
        "- :orange[**Dashed arrow P → R**]: P is **waiting** for R\n"
        "- ● held instance, ○ free instance\n"
        "- :red[**Thick red edges**]: a cycle (circular wait)\n"
        "- :red-badge[deadlocked] confirmed by the detection algorithm · "
        ":orange-badge[waiting] outstanding request · :blue-badge[not waiting]\n"
        "- **Dashed red outline**: on a cycle, but *not* deadlocked (potential only)"
    )


def state_regions_dot() -> str:
    """Safe / unsafe / deadlock regions: deadlock sits inside unsafe."""
    p = palette()
    return f"""
digraph G {{
  bgcolor="transparent"; compound=true;
  node [fontname="Helvetica" fontsize=12 shape=box style="rounded,filled" fontcolor="{p['ink']}"];
  edge [fontname="Helvetica" fontsize=10 fontcolor="{p['muted']}" color="{p['edge']}" style=dashed];
  subgraph cluster_all {{ label="All possible states"; fontname="Helvetica"; fontcolor="{p['ink']}"; style="rounded"; color="{p['edge']}";
    safe [label="SAFE\\na safe sequence exists" fillcolor="{p['proc_fill']}" color="{p['ok']}"];
    subgraph cluster_unsafe {{ label="UNSAFE: no safe sequence"; fontcolor="{p['ink']}"; style="rounded,filled"; fillcolor="{p['wait_fill']}"; color="{p['wait_line']}";
      maybe [label="may still finish\\n(processes release early)" fillcolor="{p['bg']}" color="{p['wait_line']}"];
      dead [label="DEADLOCK\\nprocesses already blocked" fillcolor="{p['dead_fill']}" color="{p['dead_line']}"];
    }}
  }}
  safe -> maybe [label=" risky grant"];
  maybe -> dead [label=" bad luck"];
}}
"""


def page_header(icon: str, title: str, lead: str, kicker: str | None = None):
    """Consistent page heading: optional kicker badge, title and one-line lead."""
    if kicker:
        st.markdown(f":blue-badge[{kicker}]")
    st.title(f"{icon} {title}")
    st.markdown(lead)


def footer():
    from core.project import PROJECT
    st.caption(
        f"© {PROJECT['year']} {', '.join(name for name, _ in PROJECT['members'])} · "
        f"{PROJECT['course']}, {PROJECT['activity']} · "
        f"{PROJECT['institute']}. Built with Streamlit. Algorithms verified by the test suite in tests/."
    )
