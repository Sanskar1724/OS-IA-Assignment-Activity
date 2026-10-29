"""Tests for the step-through, graph views, ignorance rules, games and resources.

Run with:  pytest -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bankers import (finish_snapshots, move_step, request_resources,  # noqa: E402
                          safety_algorithm)
from core.detection import (detection_algorithm, name_cycle, process_states,  # noqa: E402
                            rag_cycle, resource_summary)
from core.games import (COFFMAN, GRAPHS, PREVENTION, ROUNDS, SAFE_UNSAFE, grade,  # noqa: E402
                        verdict)
from core.ignorance import (SCENARIOS, STRATEGIES, check_choice, expected_yearly_cost,  # noqa: E402
                            recommend)
from core.resources import list_class_materials  # noqa: E402
from core.scenarios import BANKER_BASE as B, DETECTION as D  # noqa: E402
from core.status import Status  # noqa: E402
from core.validation import validate_detection, validate_system  # noqa: E402

ALLOC, MAX, AVAIL = B["allocation"], B["maximum"], B["available"]


# --- Banker's step-through ----------------------------------------------------------

def test_finish_snapshots_follow_safe_sequence():
    r = safety_algorithm(ALLOC, MAX, AVAIL)
    snaps = finish_snapshots(r, 5)
    assert len(snaps) == len(r.steps) == 7
    assert snaps[0] == [False] * 5                       # step 1 checks P0: can't finish
    assert snaps[1] == [False, True, False, False, False]  # step 2: P1 finishes
    assert snaps[-1] == [True] * 5


def test_finish_snapshots_unsafe_leaves_processes_unfinished():
    trial = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [3, 3, 2]]
    r = safety_algorithm(trial, MAX, [0, 0, 2])
    assert finish_snapshots(r, 5)[-1] == [False] * 5
    assert r.status is Status.UNSAFE


@pytest.mark.parametrize("current,total,action,expected", [
    (0, 7, "next", 1), (7, 7, "next", 7), (3, 7, "prev", 2), (0, 7, "prev", 0),
    (4, 7, "reset", 0), (2, 7, "end", 7), (9, 7, "prev", 6), (0, 0, "next", 0),
])
def test_move_step(current, total, action, expected):
    assert move_step(current, total, action) == expected


def test_move_step_rejects_unknown_action():
    with pytest.raises(ValueError):
        move_step(0, 5, "jump")


# --- All request outcomes still behave (regression guard for the new UI) --------------

@pytest.mark.parametrize("pid,req,status", [
    (1, [1, 0, 2], Status.GRANTED),
    (2, [4, 0, 0], Status.WAITING),
    (4, [3, 3, 0], Status.DENIED),
    (1, [2, 0, 0], Status.INVALID),
    (9, [0, 0, 0], Status.INVALID),
    (0, [0, -1, 0], Status.INVALID),
])
def test_request_outcomes(pid, req, status):
    r = request_resources(pid, req, ALLOC, MAX, AVAIL)
    assert r.status is status
    if status is not Status.GRANTED:
        assert r.allocation == ALLOC and r.available == AVAIL


def test_empty_inputs_are_invalid():
    assert validate_system([], [], [])
    assert validate_detection([], [], [])
    assert request_resources(0, [], [], [], []).status is Status.INVALID


# --- Detection views ----------------------------------------------------------------

def test_resource_summary_multi_deadlock():
    d = D["multi_deadlock"]
    rows = resource_summary(d["allocation"], d["request"], d["available"])
    assert [(r["total"], r["allocated"], r["free"], r["requested"]) for r in rows] == \
        [(7, 7, 0, 3), (2, 2, 0, 0), (6, 6, 0, 5)]


def test_process_states_distinguish_waiting_from_deadlocked():
    d = D["multi_cycle_no_deadlock"]
    det = detection_algorithm(d["allocation"], d["request"], d["available"])
    states = {r["process"]: r["state"] for r in process_states(d["allocation"], d["request"], det)}
    assert states == {0: "waiting", 1: "not waiting", 2: "waiting", 3: "not waiting"}

    d = D["multi_deadlock"]
    det = detection_algorithm(d["allocation"], d["request"], d["available"])
    rows = process_states(d["allocation"], d["request"], det)
    assert [r["state"] for r in rows] == ["not waiting"] + ["deadlocked"] * 4
    assert rows[2]["waits_on"] == [3, 4]          # P2 wants C, held by P3 and P4


def test_name_cycle_uses_display_names():
    d = D["multi_deadlock"]
    assert name_cycle(rag_cycle(d["allocation"], d["request"]), d["resources"]) == \
        ["P1", "C", "P2", "C", "P3", "A", "P1"]


# --- Ignorance ------------------------------------------------------------------------

def test_recommend_rules():
    assert recommend("rare", "low", False).strategy == "Ignorance"
    assert recommend("rare", "low", False).ignoring_acceptable
    assert recommend("rare", "high", True).strategy == "Avoidance"
    assert recommend("frequent", "high", False).strategy == "Prevention"
    assert recommend("frequent", "low", True).strategy == "Prevention"
    assert recommend("occasional", "medium", False).strategy == "Detection & recovery"
    with pytest.raises(ValueError):
        recommend("sometimes", "low", False)


def test_ignorance_never_recommended_for_high_impact():
    for f in ("rare", "occasional", "frequent"):
        for known in (True, False):
            rec = recommend(f, "high", known)
            assert rec.strategy != "Ignorance" and not rec.ignoring_acceptable


def test_expected_yearly_cost():
    assert expected_yearly_cost(2, 100, 1000, 0.9) == {"ignore": 200, "handle": 1020.0, "cheaper": "ignore"}
    assert expected_yearly_cost(50, 1000, 5000, 0.9)["cheaper"] == "handle"
    with pytest.raises(ValueError):
        expected_yearly_cost(1, 1, 1, 1.5)


def test_scenario_feedback():
    by_id = {s.sid: s for s in SCENARIOS}
    assert check_choice(by_id["desktop"], "Ignorance") == "best"
    assert check_choice(by_id["pacemaker"], "Ignorance") == "poor"
    assert check_choice(by_id["pacemaker"], "Avoidance") == "acceptable"
    assert check_choice(by_id["database"], "Detection & recovery") == "best"
    assert all(s.best in STRATEGIES for s in SCENARIOS)


# --- Games ----------------------------------------------------------------------------

def test_question_banks_are_well_formed():
    ids = [q.qid for _, qs in ROUNDS.values() for q in qs]
    assert len(ids) == len(set(ids))
    for _, qs in ROUNDS.values():
        for q in qs:
            assert 0 <= q.answer < len(q.options) and q.explanation


def test_computed_answers_match_hand_checks():
    assert [q.options[q.answer] for q in SAFE_UNSAFE] == ["Safe", "Unsafe", "Safe", "Unsafe"]
    assert [q.options[q.answer] for q in GRAPHS] == ["Deadlock", "No deadlock", "No deadlock", "Deadlock"]
    assert COFFMAN[0].options[COFFMAN[0].answer] == "Starvation"
    assert PREVENTION[0].options[PREVENTION[0].answer] == "Circular wait"


def test_grade_counts_correct_wrong_and_unanswered():
    qs = COFFMAN
    perfect = {q.qid: q.answer for q in qs}
    g = grade(qs, perfect)
    assert (g.correct, g.answered, g.total, g.percent, g.complete) == (5, 5, 5, 100, True)
    assert verdict(g) == "Perfect score."

    partial = {qs[0].qid: qs[0].answer, qs[1].qid: (qs[1].answer + 1) % 4}
    g = grade(qs, partial)
    assert (g.correct, g.answered, g.complete) == (1, 2, False)
    assert g.results[qs[2].qid] is None and g.results[qs[1].qid] is False


def test_grade_reset_state_is_empty():
    g = grade(GRAPHS, {})
    assert (g.correct, g.answered, g.percent) == (0, 0, 0)


# --- Class materials --------------------------------------------------------------------

def test_list_class_materials(tmp_path):
    assert list_class_materials(tmp_path / "missing") == []
    for name in ("b.pptx", "A.pdf", "notes.ppt", "photo.jpg", ".hidden.pdf", "readme.md"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub.pdf").mkdir()
    assert [p.name for p in list_class_materials(tmp_path)] == ["A.pdf", "b.pptx", "notes.ppt"]
