"""TC1–TC6: the Required Analytical Results Table, produced by running the real code.

Nothing in the "actual" column is typed by hand. Each row calls the same
functions the dashboard uses, so the table always matches the live app.
"""

from copy import deepcopy
from dataclasses import dataclass

from core.bankers import request_resources, safety_algorithm
from core.detection import detection_algorithm, recover
from core.prevention import simulate
from core.scenarios import BANKER_BASE, DETECTION, PREVENTION, REQUESTS
from core.status import Status
from core.validation import validate_system


@dataclass
class TestRow:
    tc: str
    condition: str
    input: str
    expected: str
    actual: str
    passed: bool
    analysis: str


def _seq(ids) -> str:
    return " → ".join(f"P{i}" for i in ids)


def _base():
    b = deepcopy(BANKER_BASE)
    return b["allocation"], b["maximum"], b["available"]


def tc1() -> TestRow:
    alloc, mx, avail = _base()
    r = safety_algorithm(alloc, mx, avail)
    return TestRow(
        "TC1", "Safe state",
        "Scenario A base state, Available = (3, 3, 2)",
        "Safe sequence found",
        f"{r.status.value}: {_seq(r.sequence)}",
        r.safe and len(r.sequence) == len(alloc),
        "P1 (Need 1,2,2 ≤ Work 3,3,2) finishes first and returns its allocation. Work keeps growing, "
        "so P3, P4, P0 and P2 can finish one after another. Because a complete order exists, the state is safe.",
    )


def tc2() -> TestRow:
    alloc, mx, avail = _base()
    q = REQUESTS["waiting"]
    r = request_resources(q["pid"], q["request"], alloc, mx, avail)
    unchanged = r.allocation == alloc and r.available == avail
    return TestRow(
        "TC2", "Request exceeds Available",
        f"P{q['pid']} requests {tuple(q['request'])}",
        "Request not granted immediately",
        f"{r.status.value}; allocation unchanged = {unchanged}",
        r.status is Status.WAITING and unchanged,
        "Request (4,0,0) ≤ Need (6,0,0), so the request is valid. But only 3 × A are free, so P2 has to "
        "wait. It is not marked invalid, and nothing is allocated.",
    )


def tc3() -> TestRow:
    alloc, mx, avail = _base()
    q = REQUESTS["unsafe"]
    r = request_resources(q["pid"], q["request"], alloc, mx, avail)
    restored = r.allocation == alloc and r.available == avail
    return TestRow(
        "TC3", "Request makes state unsafe",
        f"P{q['pid']} requests {tuple(q['request'])}",
        "Request denied; state unchanged",
        f"{r.status.value}; trial safe sequence = {_seq(r.trial_safety.sequence) or 'none'}; "
        f"state restored = {restored}",
        r.status is Status.DENIED and restored and not r.trial_safety.safe,
        "Trial Available = (0,0,2). No process has Need ≤ (0,0,2), so no safe sequence exists. "
        "The trial is rolled back. Unsafe ≠ deadlocked: nobody is blocked yet, but deadlock "
        "could no longer be ruled out.",
    )


def tc4() -> TestRow:
    d = DETECTION["multi_deadlock"]
    det = detection_algorithm(d["allocation"], d["request"], d["available"])
    rec = recover(d["allocation"], d["request"], d["available"])
    v = rec.steps[0] if rec.steps else None
    return TestRow(
        "TC4", "Deadlocked scenario",
        "Multiple-instance detection algorithm (Allocation, Request, Available = 0,0,0)",
        "Deadlock identified by the selected detection method",
        f"{det.status.value}: {', '.join(f'P{i}' for i in det.deadlocked)}. "
        f"Recovery: abort P{v.victim}, release {tuple(v.released)} → "
        f"{'resolved' if rec.resolved else 'still deadlocked'}",
        det.status is Status.DEADLOCK and det.deadlocked == [1, 2, 3, 4] and rec.resolved,
        "Only P0 can finish (it requests nothing), and it frees just one B. No other request ≤ Work, so "
        "P1–P4 are confirmed deadlocked. Aborting P2 frees (3,0,3), which lets P1, P3 and P4 finish.",
    )


def tc5() -> TestRow:
    p = PREVENTION
    before = simulate(p["plans"], p["resources"], "none", p["bursts"])
    after = simulate(p["plans"], p["resources"], "ordering", p["bursts"])
    return TestRow(
        "TC5", "Prevention policy applied",
        "Plans P0: R0→R1, P1: R1→R2, P2: R2→R0. Policy: ordered acquisition",
        "Selected deadlock condition eliminated",
        f"Without policy: deadlock (cycle {_seq(before.cycle)}) at tick {before.ticks}. "
        f"With ordering: all finish in {after.ticks} ticks, no deadlock",
        before.deadlocked and not after.deadlocked,
        "Forcing every process to lock in R0 < R1 < R2 order rewrites P2's plan to R0→R2, so the circle can't "
        "close. Circular wait is eliminated. The cost: P0 holds R0 idle while waiting, so throughput drops.",
    )


def tc6_cases() -> list[TestRow]:
    rows: list[TestRow] = []
    alloc, mx, avail = _base()

    zero = [0, 0, 0]
    r = request_resources(1, [1, 0, 0], alloc, mx, zero)
    rows.append(TestRow("TC6a", "Zero Available (boundary)", "Available = (0,0,0); P1 requests (1,0,0)",
                        "Valid; request waits", r.status.value, r.status is Status.WAITING,
                        "Zero free instances is a legal state. The request is valid but has to wait."))

    mx0 = deepcopy(mx)
    mx0[3] = list(alloc[3])  # P3 now needs nothing more
    s = safety_algorithm(alloc, mx0, avail)
    r = request_resources(3, [1, 0, 0], alloc, mx0, avail)
    rows.append(TestRow("TC6b", "Process with zero remaining Need (boundary)",
                        "Max[P3] = Allocation[P3] → Need[P3] = (0,0,0); P3 requests (1,0,0)",
                        "State valid; extra request rejected", f"State {s.status.value}; request {r.status.value}",
                        s.safe and r.status is Status.INVALID,
                        "A zero-Need process can always finish, so it helps the safety check. "
                        "Any further request exceeds its maximum claim and is invalid."))

    r = request_resources(0, [0, 0, 0], alloc, mx, avail)
    rows.append(TestRow("TC6c", "All-zero request (boundary)", "P0 requests (0,0,0)",
                        "Valid; trivially granted", r.status.value, r.status is Status.GRANTED,
                        "Asking for nothing changes nothing and keeps the state safe."))

    r = request_resources(7, [1, 0, 0], alloc, mx, avail)
    rows.append(TestRow("TC6d", "Invalid process identifier", "P7 requests (1,0,0) (only P0–P4 exist)",
                        "Validation message", r.status.value, r.status is Status.INVALID,
                        "; ".join(r.reasons)))

    r = request_resources(1, [-1, 0, 0], alloc, mx, avail)
    rows.append(TestRow("TC6e", "Negative request", "P1 requests (-1,0,0)",
                        "Validation message", r.status.value, r.status is Status.INVALID,
                        "; ".join(r.reasons)))

    bad = deepcopy(alloc)
    bad[1] = [4, 0, 0]  # Max[P1] is (3,2,2)
    errs = validate_system(bad, mx, avail)
    rows.append(TestRow("TC6f", "Allocation exceeds declared Maximum", "Allocation[P1] = (4,0,0), Max[P1] = (3,2,2)",
                        "Validation message", Status.INVALID.value if errs else "Accepted", bool(errs),
                        "; ".join(errs)))

    r = request_resources(1, [2, 0, 0], alloc, mx, avail)
    rows.append(TestRow("TC6g", "Request exceeds Need", "P1 requests (2,0,0), Need[P1] = (1,2,2)",
                        "Validation message", r.status.value, r.status is Status.INVALID,
                        "; ".join(r.reasons)))
    return rows


def tc6() -> TestRow:
    cases = tc6_cases()
    ok = sum(c.passed for c in cases)
    return TestRow(
        "TC6", "Boundary and invalid inputs", f"{len(cases)} sub-cases (TC6a–TC6{chr(ord('a') + len(cases) - 1)})",
        "Correct handling or validation message",
        f"{ok}/{len(cases)} handled correctly",
        ok == len(cases),
        "Boundary inputs (zero Available, zero Need, zero request) are valid and evaluated normally. "
        "Malformed inputs (unknown process, negative values, Allocation > Max, Request > Need) are "
        "rejected with a specific message before the algorithm runs.",
    )


def run_all() -> list[TestRow]:
    return [tc1(), tc2(), tc3(), tc4(), tc5(), tc6()]
