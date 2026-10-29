"""Deadlock AVOIDANCE: Banker's Algorithm.

Three pieces, each kept small so it can be explained line by line:

1. compute_need      Need = Maximum - Allocation
2. safety_algorithm  Is there an order in which every process can finish?
3. request_resources Can this request be granted without leaving the safe zone?

Banker's Algorithm only decides whether a *future* allocation keeps the system
safe. It does not detect a deadlock that already exists. That job belongs to
core/detection.py.
"""

from copy import deepcopy
from dataclasses import dataclass, field

from core.status import Status
from core.validation import validate_request, validate_system

Matrix = list[list[int]]
Vector = list[int]


def compute_need(allocation: Matrix, maximum: Matrix) -> Matrix:
    return [[mx - al for mx, al in zip(max_row, alloc_row)]
            for max_row, alloc_row in zip(maximum, allocation)]


def leq(a: Vector, b: Vector) -> bool:
    """Element-wise a <= b."""
    return all(x <= y for x, y in zip(a, b))


def add(a: Vector, b: Vector) -> Vector:
    return [x + y for x, y in zip(a, b)]


def sub(a: Vector, b: Vector) -> Vector:
    return [x - y for x, y in zip(a, b)]


@dataclass
class SafetyStep:
    """One check made by the safety algorithm, kept for the step-by-step trace."""
    pass_no: int
    process: int
    need: Vector
    work_before: Vector
    can_finish: bool
    work_after: Vector


@dataclass
class SafetyResult:
    safe: bool
    sequence: list[int]
    steps: list[SafetyStep]
    finish: list[bool]
    final_work: Vector

    @property
    def status(self) -> Status:
        return Status.SAFE if self.safe else Status.UNSAFE

    @property
    def stuck(self) -> list[int]:
        return [i for i, done in enumerate(self.finish) if not done]


def safety_algorithm(allocation: Matrix, maximum: Matrix, available: Vector) -> SafetyResult:
    """Banker's safety algorithm.

    Work = Available; Finish[i] = False.
    Repeat passes over P0..Pn-1: whenever Need[i] <= Work and Finish[i] is False,
    pretend Pi runs to completion and returns its allocation (Work += Allocation[i]).
    Stop when a full pass makes no progress. Safe if and only if every Finish[i] is True.
    """
    n = len(allocation)
    need = compute_need(allocation, maximum)
    work = list(available)
    finish = [False] * n
    sequence: list[int] = []
    steps: list[SafetyStep] = []

    pass_no = 0
    progressed = True
    while progressed and len(sequence) < n:
        progressed = False
        pass_no += 1
        for i in range(n):
            if finish[i]:
                continue
            ok = leq(need[i], work)
            before = list(work)
            if ok:
                work = add(work, allocation[i])
                finish[i] = True
                sequence.append(i)
                progressed = True
            steps.append(SafetyStep(pass_no, i, list(need[i]), before, ok, list(work)))

    return SafetyResult(all(finish), sequence, steps, finish, work)


def finish_snapshots(result: SafetyResult, n: int) -> list[list[bool]]:
    """Finish vector after each recorded step, for the step-through view.

    Entry k is the Finish vector once step k has been applied, so the list has
    one entry per step in result.steps.
    """
    finish = [False] * n
    snaps = []
    for s in result.steps:
        if s.can_finish:
            finish[s.process] = True
        snaps.append(list(finish))
    return snaps


STEP_ACTIONS = ("reset", "prev", "next", "end")


def move_step(current: int, total: int, action: str) -> int:
    """Stepper position after a button press.

    Position 0 is the initial state (Work = Available, nothing finished);
    position k (1..total) means steps 1..k have been applied.
    """
    if action not in STEP_ACTIONS:
        raise ValueError(f"Unknown step action: {action!r}")
    if total <= 0 or action == "reset":
        return 0
    if action == "end":
        return total
    current = min(max(current, 0), total)
    return min(current + 1, total) if action == "next" else max(current - 1, 0)


@dataclass
class RequestResult:
    status: Status
    pid: int | None
    request: Vector
    reasons: list[str] = field(default_factory=list)
    # The state after the decision. Equal to the original unless status is GRANTED.
    allocation: Matrix = field(default_factory=list)
    available: Vector = field(default_factory=list)
    # The tentative state the safety check ran on (only for GRANTED / DENIED).
    trial_allocation: Matrix | None = None
    trial_available: Vector | None = None
    trial_safety: SafetyResult | None = None
    state_unchanged: bool = True


def request_resources(pid, request, allocation: Matrix, maximum: Matrix,
                      available: Vector, resources: list[str] | None = None) -> RequestResult:
    """Banker's resource-request algorithm.

    Step 1  Request <= Need?       No  -> INVALID (exceeds the maximum claim)
    Step 2  Request <= Available?  No  -> WAITING (valid, but must wait)
    Step 3  Pretend to allocate, then run the safety algorithm on that trial state.
            Safe   -> GRANTED (commit the trial state)
            Unsafe -> DENIED  (throw the trial state away, keep the original)
    The caller's matrices are never mutated.
    """
    allocation = deepcopy(allocation)
    available = list(available)

    sys_errors = validate_system(allocation, maximum, available, resources=resources)
    if sys_errors:
        return RequestResult(Status.INVALID, None, list(request), sys_errors, allocation, available)

    need = compute_need(allocation, maximum)
    errors = validate_request(pid, list(request), need, len(allocation), resources)
    if errors:
        return RequestResult(Status.INVALID, pid if isinstance(pid, int) else None,
                             list(request), errors, allocation, available)

    rname = (lambda j: resources[j]) if resources else (lambda j: f"R{j}")

    if not leq(request, available):
        short = [f"{rname(j)}: asks {r}, only {a} free"
                 for j, (r, a) in enumerate(zip(request, available)) if r > a]
        return RequestResult(
            Status.WAITING, pid, list(request),
            ["The request is within P%d's remaining Need, so it is valid." % pid,
             "But it exceeds what is free right now (" + "; ".join(short) + ").",
             "P%d must wait until other processes release resources. "
             "Nothing was allocated and the state is unchanged." % pid],
            allocation, available,
        )

    # Step 3: tentative allocation on a copy.
    trial_alloc = deepcopy(allocation)
    trial_alloc[pid] = add(trial_alloc[pid], request)
    trial_avail = sub(available, request)
    safety = safety_algorithm(trial_alloc, maximum, trial_avail)

    if safety.safe:
        seq = " → ".join(f"P{i}" for i in safety.sequence)
        return RequestResult(
            Status.GRANTED, pid, list(request),
            ["The request is within both Need and Available.",
             f"After the trial allocation a safe sequence still exists: {seq}.",
             "The allocation has been committed."],
            trial_alloc, trial_avail, trial_alloc, trial_avail, safety, state_unchanged=False,
        )

    stuck = ", ".join(f"P{i}" for i in safety.stuck)
    return RequestResult(
        Status.DENIED, pid, list(request),
        ["The request is within both Need and Available, so it could be granted physically.",
         f"But after the trial allocation no safe sequence exists ({stuck} could never be guaranteed to finish).",
         "The request is denied, the trial allocation is rolled back, and the original state is kept.",
         "The system was never deadlocked: the unsafe state was only simulated and then discarded."],
        allocation, available, trial_alloc, trial_avail, safety, state_unchanged=True,
    )
