"""Independent checks of the algorithms. Run with:  pytest -q

Expected values were worked out by hand, so they don't depend on the code under test.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bankers import compute_need, request_resources, safety_algorithm  # noqa: E402
from core.detection import (detection_algorithm, is_single_instance, rag_cycle, recover,  # noqa: E402
                            wfg_cycle)
from core.prevention import simulate  # noqa: E402
from core.scenarios import BANKER_BASE as B, DETECTION as D, PREVENTION as P  # noqa: E402
from core.status import Status  # noqa: E402
from core.testcases import run_all, tc6_cases  # noqa: E402
from core.validation import validate_system  # noqa: E402

ALLOC, MAX, AVAIL = B["allocation"], B["maximum"], B["available"]


# --- Scenario A -------------------------------------------------------------------

def test_need_matrix():
    assert compute_need(ALLOC, MAX) == [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]


def test_safe_sequence_and_work_updates():
    r = safety_algorithm(ALLOC, MAX, AVAIL)
    assert r.safe and r.status is Status.SAFE
    assert r.sequence == [1, 3, 4, 0, 2]
    finished = [s.work_after for s in r.steps if s.can_finish]
    assert finished == [[5, 3, 2], [7, 4, 3], [7, 4, 5], [7, 5, 5], [10, 5, 7]]


# --- Scenarios B and C ----------------------------------------------------------------

def test_request_granted():
    r = request_resources(1, [1, 0, 2], ALLOC, MAX, AVAIL)
    assert r.status is Status.GRANTED
    assert r.available == [2, 3, 0] and r.allocation[1] == [3, 0, 2]


def test_request_waits_and_state_unchanged():
    r = request_resources(2, [4, 0, 0], ALLOC, MAX, AVAIL)
    assert r.status is Status.WAITING
    assert r.allocation == ALLOC and r.available == AVAIL


def test_request_unsafe_denied_and_restored():
    r = request_resources(4, [3, 3, 0], ALLOC, MAX, AVAIL)
    assert r.status is Status.DENIED
    assert r.trial_available == [0, 0, 2]
    assert not r.trial_safety.safe and r.trial_safety.sequence == []
    assert r.allocation == ALLOC and r.available == AVAIL


def test_inputs_never_mutated():
    alloc = [row[:] for row in ALLOC]
    request_resources(1, [1, 0, 2], alloc, MAX, AVAIL)
    assert alloc == ALLOC


# --- Scenario D -----------------------------------------------------------------------

def test_single_instance_cycle_is_deadlock():
    d = D["single_deadlock"]
    assert is_single_instance(d["allocation"], d["available"])
    assert wfg_cycle(d["allocation"], d["request"]) == ["P0", "P1", "P2", "P0"]
    assert detection_algorithm(d["allocation"], d["request"], d["available"]).deadlocked == [0, 1, 2]


def test_multi_instance_deadlock_and_recovery():
    d = D["multi_deadlock"]
    det = detection_algorithm(d["allocation"], d["request"], d["available"])
    assert det.status is Status.DEADLOCK and det.deadlocked == [1, 2, 3, 4]
    rec = recover(d["allocation"], d["request"], d["available"])
    assert rec.resolved and [s.victim for s in rec.steps] == [2]
    assert rec.steps[0].released == [3, 0, 3]


def test_cycle_without_deadlock():
    d = D["multi_cycle_no_deadlock"]
    assert rag_cycle(d["allocation"], d["request"])        # potential circular wait...
    det = detection_algorithm(d["allocation"], d["request"], d["available"])
    assert det.status is Status.NO_DEADLOCK                # ...but not a deadlock


def test_no_self_cycle_for_same_resource():
    # P0 holds 1 A and asks for 1 more A: not a circular wait.
    assert rag_cycle([[1]], [[1]]) == []


# --- Scenario E -----------------------------------------------------------------------

def test_prevention_policies():
    none = simulate(P["plans"], P["resources"], "none", P["bursts"])
    ordered = simulate(P["plans"], P["resources"], "ordering", P["bursts"])
    atomic = simulate(P["plans"], P["resources"], "all_at_once", P["bursts"])
    assert none.deadlocked and none.cycle[0] == none.cycle[-1]
    assert not ordered.deadlocked and sorted(ordered.finished) == [0, 1, 2]
    assert not atomic.deadlocked and atomic.held_idle == 0


# --- Scenario F -----------------------------------------------------------------------

def test_allocation_over_max_is_invalid():
    bad = [row[:] for row in ALLOC]
    bad[1] = [4, 0, 0]
    assert validate_system(bad, MAX, AVAIL)


def test_negative_available_is_invalid():
    assert validate_system(ALLOC, MAX, [-1, 3, 2])


def test_all_boundary_and_invalid_cases():
    assert all(c.passed for c in tc6_cases())


def test_required_table_all_pass():
    rows = run_all()
    assert [r.tc for r in rows] == ["TC1", "TC2", "TC3", "TC4", "TC5", "TC6"]
    assert all(r.passed for r in rows), [r.tc for r in rows if not r.passed]
