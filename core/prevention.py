"""Deadlock PREVENTION: a small tick-by-tick simulator.

Every resource here has a single instance. Each process has an acquisition plan
(the order in which it grabs resources) and a burst (ticks it needs once it holds
everything). We run the same workload under three policies:

* none        Processes lock resources one at a time, in their own order.
              All four Coffman conditions can hold, so deadlock is possible.
* ordering    Resources get a global rank (R0 < R1 < ...) and every process must
              acquire them in increasing rank. This breaks CIRCULAR WAIT: a cycle
              would need someone to hold a higher rank while waiting for a lower one.
* all_at_once A process gets all of its resources in one atomic step or none of
              them. This breaks HOLD AND WAIT: a waiting process never holds anything.
"""

from dataclasses import dataclass, field

POLICIES = {
    "none": "No prevention (request in any order)",
    "ordering": "Ordered acquisition (prevents circular wait)",
    "all_at_once": "All-at-once allocation (prevents hold and wait)",
}


@dataclass
class TickRecord:
    tick: int
    process: int
    state: str          # acquiring | waiting | running | done | deadlocked
    holding: list[int]
    note: str


@dataclass
class SimulationResult:
    policy: str
    deadlocked: bool
    cycle: list[int]
    ticks: int
    finished: list[int]
    timeline: list[TickRecord] = field(default_factory=list)
    held_idle: int = 0      # resource-ticks a resource was held by a process that wasn't running yet
    held_running: int = 0   # resource-ticks a resource was held by a running process
    n_resources: int = 0
    max_parallel: int = 0   # largest number of processes running in the same tick

    @property
    def utilization(self) -> float:
        """Share of all resource-ticks in which a resource was doing useful work."""
        total = self.n_resources * max(self.ticks, 1)
        return self.held_running / total if total else 0.0


def apply_policy(plans: list[list[int]], policy: str) -> list[list[int]]:
    if policy == "ordering":
        return [sorted(p) for p in plans]
    return [list(p) for p in plans]


def simulate(plans: list[list[int]], n_resources: int, policy: str,
             bursts: list[int] | None = None, max_ticks: int = 60) -> SimulationResult:
    plans = apply_policy(plans, policy)
    n = len(plans)
    bursts = bursts or [2] * n
    holder: list[int | None] = [None] * n_resources
    holding: list[list[int]] = [[] for _ in range(n)]
    acquired = [0] * n
    run_left = list(bursts)
    state = ["acquiring" if plans[i] else "running" for i in range(n)]
    finished: list[int] = []
    timeline: list[TickRecord] = []
    res = SimulationResult(policy, False, [], 0, finished, timeline, n_resources=n_resources)

    tick = 0
    while len(finished) < n and tick < max_ticks:
        tick += 1
        progress = False
        waits_on: dict[int, int] = {}
        running_now = 0

        for i in range(n):
            if state[i] == "done":
                timeline.append(TickRecord(tick, i, "done", [], "finished"))
                continue

            if state[i] == "running":
                running_now += 1
                res.held_running += len(holding[i])
                run_left[i] -= 1
                progress = True
                if run_left[i] <= 0:
                    rel = holding[i]
                    for r in rel:
                        holder[r] = None
                    note = "runs, finishes, releases " + (", ".join(f"R{r}" for r in rel) or "nothing")
                    timeline.append(TickRecord(tick, i, "running", list(rel), note))
                    holding[i] = []
                    state[i] = "done"
                    finished.append(i)
                else:
                    timeline.append(TickRecord(tick, i, "running", list(holding[i]), "runs"))
                continue

            # Not running yet: try to acquire according to policy.
            if policy == "all_at_once":
                busy = [r for r in plans[i] if holder[r] is not None]
                if not busy:
                    for r in plans[i]:
                        holder[r] = i
                    holding[i] = list(plans[i])
                    acquired[i] = len(plans[i])
                    state[i] = "running"
                    progress = True
                    timeline.append(TickRecord(tick, i, "acquiring", list(holding[i]),
                                               "gets all of " + ", ".join(f"R{r}" for r in plans[i]) + " at once"))
                else:
                    waits_on[i] = holder[busy[0]]
                    timeline.append(TickRecord(tick, i, "waiting", [],
                                               f"waits for R{busy[0]} (held by P{holder[busy[0]]}), holding nothing"))
                    # Holding nothing while waiting: no resource-ticks wasted.
                continue

            r = plans[i][acquired[i]]
            if holder[r] is None:
                holder[r] = i
                holding[i].append(r)
                acquired[i] += 1
                progress = True
                if acquired[i] == len(plans[i]):
                    state[i] = "running"
                timeline.append(TickRecord(tick, i, "acquiring", list(holding[i]), f"locks R{r}"))
            else:
                waits_on[i] = holder[r]
                timeline.append(TickRecord(tick, i, "waiting", list(holding[i]),
                                           f"waits for R{r} (held by P{holder[r]})"))
            res.held_idle += len(holding[i])

        res.max_parallel = max(res.max_parallel, running_now)

        if not progress:
            res.deadlocked = True
            res.cycle = _cycle(waits_on)
            for rec in timeline:
                if rec.tick == tick and rec.state == "waiting":
                    rec.state = "deadlocked"
            break

    res.ticks = tick
    return res


def _cycle(waits_on: dict[int, int]) -> list[int]:
    for start in waits_on:
        seen, v = [], start
        while v in waits_on and v not in seen:
            seen.append(v)
            v = waits_on[v]
        if v in seen:
            return seen[seen.index(v):] + [v]
    return []
