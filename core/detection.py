"""Deadlock DETECTION and RECOVERY.

Unlike Banker's Algorithm, detection looks at what processes are *requesting
right now* (not their maximum claim) and asks: is anyone permanently stuck?

Two methods, chosen by the resource model:

* Single-instance resources (every resource type has exactly 1 instance):
  a cycle in the wait-for graph is a necessary AND sufficient condition, so a
  cycle proves deadlock.
* Multiple-instance resources: a cycle in the resource-allocation graph is
  only necessary. It shows a *potential* circular wait, not proof. We run the
  detection algorithm (a Banker's-style reduction using Request instead of Need)
  to confirm.
"""

from copy import deepcopy
from dataclasses import dataclass, field

from core.bankers import add, leq
from core.status import Status

Matrix = list[list[int]]
Vector = list[int]


def total_instances(allocation: Matrix, available: Vector) -> Vector:
    totals = list(available)
    for row in allocation:
        totals = add(totals, row)
    return totals


def is_single_instance(allocation: Matrix, available: Vector) -> bool:
    return all(t == 1 for t in total_instances(allocation, available))


@dataclass
class DetectionStep:
    pass_no: int
    process: int
    request: Vector
    work_before: Vector
    can_finish: bool
    work_after: Vector


@dataclass
class DetectionResult:
    deadlocked: list[int]
    sequence: list[int]
    steps: list[DetectionStep]
    final_work: Vector

    @property
    def status(self) -> Status:
        return Status.DEADLOCK if self.deadlocked else Status.NO_DEADLOCK


def detection_algorithm(allocation: Matrix, request: Matrix, available: Vector) -> DetectionResult:
    """Multiple-instance detection algorithm (Coffman / Silberschatz).

    Work = Available. A process holding nothing can't be part of a deadlock,
    so it starts as finished. Then repeatedly find Pi with Request[i] <= Work,
    assume it completes, and reclaim its allocation. Whoever is left is deadlocked.
    """
    n = len(allocation)
    work = list(available)
    finish = [not any(row) for row in allocation]
    sequence = [i for i in range(n) if finish[i]]
    steps: list[DetectionStep] = []

    pass_no = 0
    progressed = True
    while progressed:
        progressed = False
        pass_no += 1
        for i in range(n):
            if finish[i]:
                continue
            ok = leq(request[i], work)
            before = list(work)
            if ok:
                work = add(work, allocation[i])
                finish[i] = True
                sequence.append(i)
                progressed = True
            steps.append(DetectionStep(pass_no, i, list(request[i]), before, ok, list(work)))

    return DetectionResult([i for i in range(n) if not finish[i]], sequence, steps, work)


# --- Graph view -----------------------------------------------------------------

def rag_edges(allocation: Matrix, request: Matrix) -> list[tuple[str, str, int, str]]:
    """Resource-allocation graph edges as (from, to, count, kind).

    Request edge:    Pi -> Rj  (Pi is waiting for Rj)
    Assignment edge: Rj -> Pi  (an instance of Rj is held by Pi)
    """
    edges = []
    for i, (arow, rrow) in enumerate(zip(allocation, request)):
        for j, (a, r) in enumerate(zip(arow, rrow)):
            if r > 0:
                edges.append((f"P{i}", f"R{j}", r, "request"))
            if a > 0:
                edges.append((f"R{j}", f"P{i}", a, "assignment"))
    return edges


def wait_for_edges(allocation: Matrix, request: Matrix) -> list[tuple[int, int, int]]:
    """Wait-for graph: Pi -> Pk when Pi requests a resource Rj that Pk holds."""
    edges = []
    for i, rrow in enumerate(request):
        for j, r in enumerate(rrow):
            if r <= 0:
                continue
            for k, arow in enumerate(allocation):
                if k != i and arow[j] > 0:
                    edges.append((i, k, j))
    return edges


def find_cycle(nodes: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Return one directed cycle as a list of nodes (first == last), or [] if none."""
    graph: dict[str, list[str]] = {v: [] for v in nodes}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, [])

    WHITE, GREY, BLACK = 0, 1, 2
    color = {v: WHITE for v in graph}
    stack: list[str] = []

    def dfs(v: str) -> list[str]:
        color[v] = GREY
        stack.append(v)
        for w in graph[v]:
            if color[w] == GREY:
                return stack[stack.index(w):] + [w]
            if color[w] == WHITE:
                found = dfs(w)
                if found:
                    return found
        stack.pop()
        color[v] = BLACK
        return []

    for v in graph:
        if color[v] == WHITE:
            cycle = dfs(v)
            if cycle:
                return cycle
    return []


def wfg_cycle(allocation: Matrix, request: Matrix) -> list[str]:
    nodes = [f"P{i}" for i in range(len(allocation))]
    return find_cycle(nodes, [(f"P{a}", f"P{b}") for a, b, _ in wait_for_edges(allocation, request)])


def rag_cycle(allocation: Matrix, request: Matrix) -> list[str]:
    """A cycle between different processes, written out with the resources in between.

    A process asking for more of a resource it already holds (P1 -> A -> P1) isn't
    a circular wait, so we build the cycle from the wait-for graph and expand
    each Pi -> Pk hop into Pi -> Rj -> Pk.
    """
    procs = wfg_cycle(allocation, request)
    if not procs:
        return []
    via = {(a, b): j for a, b, j in wait_for_edges(allocation, request)}
    path: list[str] = []
    for a, b in zip(procs, procs[1:]):
        path += [a, f"R{via[(int(a[1:]), int(b[1:]))]}"]
    return path + [procs[-1]]


def name_cycle(cycle: list[str], resources: list[str]) -> list[str]:
    """Replace internal resource ids (R0, R1, …) in a cycle with display names."""
    return [resources[int(v[1:])] if v.startswith("R") else v for v in cycle]


# --- Tabular views of the current state ------------------------------------------

def resource_summary(allocation: Matrix, request: Matrix, available: Vector) -> list[dict]:
    """Per resource type: total, allocated, free and outstanding requests."""
    totals = total_instances(allocation, available)
    rows = []
    for j, total in enumerate(totals):
        allocated = sum(row[j] for row in allocation)
        requested = sum(row[j] for row in request)
        rows.append({"resource": j, "total": total, "allocated": allocated, "free": available[j],
                     "requested": requested, "shortfall": max(0, requested - available[j])})
    return rows


def process_states(allocation: Matrix, request: Matrix, result: DetectionResult) -> list[dict]:
    """Per process: whether it is waiting, who it waits on, and the detection verdict.

    state is one of:
      "deadlocked"  confirmed by the detection algorithm
      "waiting"     has an outstanding request, but will eventually be satisfied
      "not waiting" requests nothing right now
    """
    waits = wait_for_edges(allocation, request)
    order = {pid: k for k, pid in enumerate(result.sequence, start=1)}
    rows = []
    for i in range(len(allocation)):
        if i in result.deadlocked:
            state = "deadlocked"
        elif any(request[i]):
            state = "waiting"
        else:
            state = "not waiting"
        rows.append({
            "process": i,
            "state": state,
            "waits_on": sorted({k for a, k, _ in waits if a == i}),
            "finish_order": order.get(i),
        })
    return rows


# --- Recovery -------------------------------------------------------------------

@dataclass
class RecoveryStep:
    victim: int
    released: Vector
    available_after: Vector
    detection: DetectionResult


@dataclass
class RecoveryResult:
    steps: list[RecoveryStep] = field(default_factory=list)
    allocation: Matrix = field(default_factory=list)
    request: Matrix = field(default_factory=list)
    available: Vector = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return not self.steps or not self.steps[-1].detection.deadlocked


def terminate_process(victim: int, allocation: Matrix, request: Matrix, available: Vector):
    """Abort one process: its held resources go back to Available and its request is dropped."""
    allocation, request = deepcopy(allocation), deepcopy(request)
    released = list(allocation[victim])
    available = add(available, released)
    allocation[victim] = [0] * len(released)
    request[victim] = [0] * len(released)
    return allocation, request, available, released


def pick_victim(deadlocked: list[int], allocation: Matrix) -> int:
    """Default policy: abort the deadlocked process holding the most instances.

    Freeing the most resources tends to break the deadlock with the fewest aborts.
    Ties go to the higher process number (treated as the most recently started).
    """
    return max(deadlocked, key=lambda i: (sum(allocation[i]), i))


def recover(allocation: Matrix, request: Matrix, available: Vector,
            first_victim: int | None = None, max_rounds: int = 50) -> RecoveryResult:
    """Abort processes one at a time until the detection algorithm reports no deadlock."""
    result = RecoveryResult(allocation=deepcopy(allocation), request=deepcopy(request),
                            available=list(available))
    det = detection_algorithm(allocation, request, available)
    victim = first_victim
    for _ in range(max_rounds):
        if not det.deadlocked:
            break
        if victim is None or victim not in det.deadlocked:
            victim = pick_victim(det.deadlocked, result.allocation)
        result.allocation, result.request, result.available, released = terminate_process(
            victim, result.allocation, result.request, result.available)
        det = detection_algorithm(result.allocation, result.request, result.available)
        result.steps.append(RecoveryStep(victim, released, list(result.available), det))
        victim = None
    return result
