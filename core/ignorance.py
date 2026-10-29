"""Deadlock IGNORANCE (the "ostrich algorithm").

Ignoring deadlocks does NOT stop them from happening. The system simply runs no
prevention, avoidance or detection code, and accepts that a deadlock may occur
and be cleared by hand (killing the stuck program, restarting a service or
rebooting). This module holds the teaching content and the small, deterministic
decision rules used by the Ignorance page.
"""

from dataclasses import dataclass

STRATEGIES = ["Ignorance", "Prevention", "Avoidance", "Detection & recovery"]

# One row per strategy for the comparison table.
COMPARISON = [
    {"Strategy": "Ignorance (ostrich)", "Deadlock possible?": "Yes, and it isn't noticed automatically",
     "Runtime cost": "None", "Needs advance knowledge?": "No",
     "Who clears a deadlock": "A user or administrator (kill, restart, reboot)",
     "Typical use": "General-purpose OSes for user programs, where deadlocks are rare"},
    {"Strategy": "Prevention", "Deadlock possible?": "No, one Coffman condition can never hold",
     "Runtime cost": "Low at runtime; paid in lower utilization", "Needs advance knowledge?": "The policy only",
     "Who clears a deadlock": "Nobody needs to",
     "Typical use": "Lock ordering in kernels and multithreaded code"},
    {"Strategy": "Avoidance", "Deadlock possible?": "No, unsafe grants are refused",
     "Runtime cost": "A safety check on every request (O(m·n²))", "Needs advance knowledge?": "Each process's maximum claim",
     "Who clears a deadlock": "Nobody needs to",
     "Typical use": "Systems where jobs declare their maximum demand up front"},
    {"Strategy": "Detection & recovery", "Deadlock possible?": "Yes, but found and broken",
     "Runtime cost": "Periodic detection, plus lost work from aborts", "Needs advance knowledge?": "No",
     "Who clears a deadlock": "The system (abort or preempt a victim)",
     "Typical use": "Database servers aborting a victim transaction"},
]

PROS = [
    "Zero runtime overhead: no safety checks, no periodic detection, no lock-ordering rules.",
    "Simple to build and reason about. No code paths that can themselves have bugs.",
    "No loss of concurrency or utilization from conservative allocation policies.",
]
CONS = [
    "Deadlocks still happen. Ignoring them only means the system doesn't notice.",
    "Stuck processes keep their resources, which can block other, unrelated processes.",
    "Recovery is manual and blunt: killed programs or reboots can lose unsaved work.",
    "Unacceptable where a hang causes harm: medical devices, flight control, payments, industrial control.",
]
LIMITS = [
    "It is a cost decision, not a technique. It only makes sense when deadlocks are rare AND cheap to clear.",
    "It assumes a human is around to notice the hang and restart something.",
    "It gives no guarantee at all, so it can't be used where correctness or availability must be proven.",
]


@dataclass(frozen=True)
class Recommendation:
    strategy: str
    ignoring_acceptable: bool
    reasons: tuple[str, ...]


FREQUENCIES = ("rare", "occasional", "frequent")
IMPACTS = ("low", "medium", "high")


def recommend(frequency: str, impact: str, max_claims_known: bool) -> Recommendation:
    """A deterministic rule of thumb for choosing a strategy.

    frequency         how often deadlock is expected: rare | occasional | frequent
    impact            cost of one deadlock: low | medium | high (high = harm or major loss)
    max_claims_known  can every process declare its maximum demand in advance?
    """
    if frequency not in FREQUENCIES or impact not in IMPACTS:
        raise ValueError("frequency must be rare/occasional/frequent and impact low/medium/high")

    if impact == "high":
        if max_claims_known:
            return Recommendation("Avoidance", False, (
                "A deadlock here is too costly to risk, so it must be ruled out, not ignored or cleaned up later.",
                "Processes can declare their maximum claims, so Banker's Algorithm can refuse unsafe grants "
                "while still allowing more concurrency than a strict prevention rule.",
            ))
        return Recommendation("Prevention", False, (
            "A deadlock here is too costly to risk, so it must be ruled out, not ignored or cleaned up later.",
            "Maximum claims aren't known, so avoidance isn't possible. A design rule such as global lock "
            "ordering removes circular wait instead.",
        ))
    if frequency == "rare" and impact == "low":
        return Recommendation("Ignorance", True, (
            "Deadlocks are rare and cheap to clear (restart the program), so the expected loss is small.",
            "Any handling mechanism would cost more over time than the occasional manual restart.",
            "Deadlocks can still happen. Someone must notice the hang and clear it.",
        ))
    if frequency == "frequent":
        return Recommendation("Prevention", False, (
            "Deadlocks are frequent, so ignoring them or cleaning up after each one is too disruptive.",
            "Removing one Coffman condition by design stops them at the source.",
        ))
    return Recommendation("Detection & recovery", False, (
        "Deadlocks happen often enough, or cost enough, that someone must deal with them, but not so often "
        "that strict prevention or per-request checks are worth their cost.",
        "Periodic detection finds them, and aborting a victim breaks them.",
    ))


def expected_yearly_cost(deadlocks_per_year: float, cost_per_deadlock: float,
                         handling_cost_per_year: float, share_prevented: float) -> dict:
    """Compare the expected yearly cost of ignoring deadlocks with handling them.

    share_prevented is the fraction (0–1) of deadlocks the chosen mechanism stops
    or resolves without the full cost. The model is deliberately simple and is
    meant for discussion, not for real capacity planning.
    """
    if min(deadlocks_per_year, cost_per_deadlock, handling_cost_per_year) < 0:
        raise ValueError("Rates and costs can't be negative.")
    if not 0 <= share_prevented <= 1:
        raise ValueError("share_prevented must be between 0 and 1.")
    ignore = deadlocks_per_year * cost_per_deadlock
    handle = handling_cost_per_year + deadlocks_per_year * (1 - share_prevented) * cost_per_deadlock
    return {"ignore": ignore, "handle": handle, "cheaper": "ignore" if ignore <= handle else "handle"}


@dataclass(frozen=True)
class Scenario:
    sid: str
    title: str
    situation: str
    best: str
    acceptable: tuple[str, ...]
    explanation: str


SCENARIOS = [
    Scenario("desktop", "Desktop photo editor",
             "A single-user photo editor occasionally hangs when two plug-ins lock the same files in opposite "
             "orders. It happens a few times a year, and the user can force-quit and reopen the app.",
             "Ignorance", ("Prevention",),
             "Rare and cheap to clear, so most general-purpose OSes leave this to the user. Fixing the plug-in "
             "lock order (prevention) would be even better if you control the code."),
    Scenario("pacemaker", "Pacemaker firmware",
             "Two tasks in a pacemaker share a sensor bus and a log buffer. A hang of even a second could harm "
             "the patient.",
             "Prevention", ("Avoidance",),
             "Ignoring is never acceptable when a hang causes harm, and detecting a deadlock afterwards is too "
             "late. A static rule (fixed lock order or all-at-once acquisition) rules deadlock out by design."),
    Scenario("database", "Online shop database",
             "Thousands of transactions lock rows in unpredictable orders. Deadlocks happen several times an "
             "hour, and a transaction can be rolled back and retried safely.",
             "Detection & recovery", (),
             "Lock orders can't be fixed in advance and maximum claims are unknown, so real DBMSs detect "
             "deadlocks with a wait-for graph and abort a victim transaction, which the client retries."),
    Scenario("batch", "Tape-drive batch system",
             "Every batch job declares up front how many tape drives and printers it may need. Jobs must not "
             "be killed half-way.",
             "Avoidance", ("Prevention",),
             "Maximum claims are known, so Banker's Algorithm can grant requests only while a safe sequence "
             "exists. No job ever has to be aborted."),
    Scenario("mutex", "Two mutexes in a web server",
             "A web server's request handlers sometimes lock the cache mutex then the stats mutex, and "
             "sometimes the other way round. It deadlocks under load.",
             "Prevention", (),
             "This is a textbook circular wait. Making every handler take the mutexes in one fixed order "
             "removes the condition entirely at almost no cost."),
]


def check_choice(scenario: Scenario, choice: str) -> str:
    """'best', 'acceptable' or 'poor' for a learner's chosen strategy."""
    if choice not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {choice!r}")
    if choice == scenario.best:
        return "best"
    return "acceptable" if choice in scenario.acceptable else "poor"
