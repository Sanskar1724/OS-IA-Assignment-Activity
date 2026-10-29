"""Deadlock Games: deterministic question banks and scoring.

Questions never use randomness, so a round always shows the same questions in
the same order and can be unit-tested. Answers to the "safe or unsafe" and
"deadlock or not" rounds are COMPUTED with the project's own algorithms, so a
quiz answer can never disagree with what the dashboard shows.
"""

from dataclasses import dataclass, field

from core.bankers import compute_need, safety_algorithm
from core.detection import detection_algorithm, is_single_instance, name_cycle, rag_cycle
from core.scenarios import BANKER_BASE, DETECTION


@dataclass(frozen=True)
class Question:
    qid: str
    prompt: str
    options: tuple[str, ...]
    answer: int                 # index into options
    explanation: str
    figure: dict = field(default_factory=dict, compare=False, hash=False)


def _seq(ids) -> str:
    return " → ".join(f"P{i}" for i in ids) or "none"


def _vec(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")"


# --- Round 1: the four Coffman conditions ---------------------------------------

COFFMAN = [
    Question("c1", "Which of these is NOT one of the four necessary conditions for deadlock?",
             ("Mutual exclusion", "Hold and wait", "Starvation", "Circular wait"), 2,
             "The four Coffman conditions are mutual exclusion, hold and wait, no preemption and circular wait. "
             "Starvation is a different problem: a process waits indefinitely while others keep progressing."),
    Question("c2", "A process keeps the scanner while it waits for the printer. Which condition is this?",
             ("Mutual exclusion", "Hold and wait", "No preemption", "Circular wait"), 1,
             "It holds one resource while waiting for another: hold and wait."),
    Question("c3", "The OS can't take a mutex away from the thread that holds it. Which condition is this?",
             ("No preemption", "Mutual exclusion", "Circular wait", "Hold and wait"), 0,
             "A resource is released only voluntarily by its holder: no preemption."),
    Question("c4", "P0 waits for P1, P1 waits for P2 and P2 waits for P0. Which condition is this?",
             ("Hold and wait", "No preemption", "Mutual exclusion", "Circular wait"), 3,
             "A closed chain of processes, each waiting for the next: circular wait."),
    Question("c5", "Three of the four conditions hold, but there is no circular wait. Can the processes deadlock?",
             ("Yes, three conditions are enough", "No, all four must hold at the same time",
              "Only with multiple-instance resources", "Only if the system is unsafe"), 1,
             "The conditions are jointly necessary. Remove any one of them and deadlock is impossible."),
]


# --- Round 2: safe or unsafe? (Banker's safety algorithm) -------------------------

_STATES = [
    ("s1", "Scenario A base state",
     BANKER_BASE["allocation"], BANKER_BASE["maximum"], BANKER_BASE["available"], ["A", "B", "C"]),
    ("s2", "Scenario A after the trial grant of P4's (3, 3, 0)",
     [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [3, 3, 2]], BANKER_BASE["maximum"], [0, 0, 2], ["A", "B", "C"]),
    ("s3", "Three processes, nothing free",
     [[1, 0], [0, 1], [1, 1]], [[2, 1], [1, 2], [1, 1]], [0, 0], ["R0", "R1"]),
    ("s4", "Two processes, nothing free",
     [[1, 0], [0, 1]], [[2, 1], [1, 2]], [0, 0], ["R0", "R1"]),
]


def _safety_question(qid, title, alloc, mx, avail, names) -> Question:
    r = safety_algorithm(alloc, mx, avail)
    if r.safe:
        why = f"Safe. A safe sequence exists: {_seq(r.sequence)}."
    else:
        stuck = ", ".join(f"P{i}" for i in r.stuck)
        start = f"After {_seq(r.sequence)} finish, " if r.sequence else "No process can finish: "
        why = (f"Unsafe. {start}Work = {_vec(r.final_work)} doesn't cover the Need of {stuck}. "
               "Unsafe is not the same as deadlocked: nobody is blocked yet, but completion can't be guaranteed.")
    return Question(qid, f"{title}: is this state safe or unsafe?", ("Safe", "Unsafe"), 0 if r.safe else 1, why,
                    {"kind": "banker", "allocation": alloc, "maximum": mx, "available": avail,
                     "need": compute_need(alloc, mx), "resources": names})


SAFE_UNSAFE = [_safety_question(*s) for s in _STATES]


# --- Round 3: deadlock or not? (resource-allocation graphs) -------------------------

_GRAPHS = [
    ("g1", "Two processes, two single-instance resources",
     [[1, 0], [0, 1]], [[0, 1], [1, 0]], [0, 0], ["R0", "R1"]),
    ("g2", "A waiting chain without a loop",
     [[1, 0], [0, 1]], [[0, 1], [0, 0]], [0, 0], ["R0", "R1"]),
    ("g3", DETECTION["multi_cycle_no_deadlock"]["label"],
     DETECTION["multi_cycle_no_deadlock"]["allocation"], DETECTION["multi_cycle_no_deadlock"]["request"],
     DETECTION["multi_cycle_no_deadlock"]["available"], DETECTION["multi_cycle_no_deadlock"]["resources"]),
    ("g4", "Multiple-instance resources, five processes",
     DETECTION["multi_deadlock"]["allocation"], DETECTION["multi_deadlock"]["request"],
     DETECTION["multi_deadlock"]["available"], DETECTION["multi_deadlock"]["resources"]),
]


def _graph_question(qid, title, alloc, req, avail, names) -> Question:
    det = detection_algorithm(alloc, req, avail)
    cycle = name_cycle(rag_cycle(alloc, req), names)
    single = is_single_instance(alloc, avail)
    if det.deadlocked:
        why = f"Deadlock: {', '.join(f'P{i}' for i in det.deadlocked)} can never proceed."
        if cycle:
            why += f" Circular wait: {' → '.join(cycle)}."
    elif cycle:
        why = (f"No deadlock, even though there is a cycle ({' → '.join(cycle)}). With multiple instances, "
               f"processes outside the cycle finish and release instances: {_seq(det.sequence)}.")
    else:
        why = f"No deadlock: there is no cycle, and every process can finish ({_seq(det.sequence)})."
    if single and det.deadlocked:
        why += " With single-instance resources, the cycle alone proves it."
    return Question(qid, f"{title}: is there a deadlock?", ("Deadlock", "No deadlock"),
                    0 if det.deadlocked else 1, why,
                    {"kind": "graph", "allocation": alloc, "request": req, "available": avail, "resources": names})


GRAPHS = [_graph_question(*g) for g in _GRAPHS]


# --- Round 4: prevention challenges -----------------------------------------------

_CONDS = ("Mutual exclusion", "Hold and wait", "No preemption", "Circular wait")

PREVENTION = [
    Question("p1", "Policy: every thread must take locks in increasing lock-number order. Which condition does "
             "this remove?", _CONDS, 3,
             "With a global order, a cycle would need someone holding a higher lock while waiting for a lower "
             "one, which the rule forbids. Circular wait is gone."),
    Question("p2", "Policy: a process must request every resource it needs before it starts running. Which "
             "condition does this remove?", _CONDS, 1,
             "A process either holds everything or waits holding nothing. Hold and wait is gone. The cost is "
             "lower utilization and possible starvation."),
    Question("p3", "Policy: if a process holding resources asks for one that isn't free, it must release "
             "everything and ask again later. Which condition does this remove?", _CONDS, 2,
             "Resources are effectively taken back from a blocked holder. No preemption is gone."),
    Question("p4", "Policy: print jobs are spooled to disk and only the spooler talks to the printer. Which "
             "condition does this remove (for the printer)?", _CONDS, 0,
             "Processes never hold the printer directly, so they don't need exclusive access to it. "
             "This works for printers but not for most resources, such as mutexes."),
    Question("p5", "Running Banker's Algorithm on every request is an example of…",
             ("Prevention", "Avoidance", "Detection", "Ignorance"), 1,
             "Banker's doesn't remove any condition. It refuses grants that would leave the system unsafe, "
             "which is avoidance."),
]


ROUNDS = {
    "coffman": ("Coffman conditions", COFFMAN),
    "safe_unsafe": ("Safe or unsafe?", SAFE_UNSAFE),
    "graphs": ("Spot the deadlock", GRAPHS),
    "prevention": ("Prevention challenge", PREVENTION),
}


# --- Scoring ------------------------------------------------------------------------

@dataclass
class Grade:
    correct: int
    answered: int
    total: int
    results: dict[str, bool | None]   # qid -> True / False / None (unanswered)

    @property
    def percent(self) -> int:
        return round(100 * self.correct / self.total) if self.total else 0

    @property
    def complete(self) -> bool:
        return self.answered == self.total


def grade(questions: list[Question], answers: dict[str, int | None]) -> Grade:
    """Score a set of answers. Unknown or out-of-range answers count as wrong;
    missing ones count as unanswered."""
    results: dict[str, bool | None] = {}
    for q in questions:
        a = answers.get(q.qid)
        results[q.qid] = None if a is None else (a == q.answer)
    correct = sum(1 for v in results.values() if v)
    answered = sum(1 for v in results.values() if v is not None)
    return Grade(correct, answered, len(questions), results)


def verdict(g: Grade) -> str:
    """Short feedback line for a finished round."""
    if g.total and g.correct == g.total:
        return "Perfect score."
    if g.percent >= 60:
        return "Good work. Read the explanations for the ones you missed."
    return "Worth another go. Review the explanations, then replay the round."
