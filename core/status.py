"""The distinct outcome states the dashboard reports.

The assignment insists these are never treated as interchangeable:
an unsafe state is not a deadlock, and a request that must wait is not invalid.
"""

from enum import Enum


class Status(str, Enum):
    SAFE = "Safe"
    UNSAFE = "Unsafe"
    GRANTED = "Granted"
    WAITING = "Waiting (deferred)"
    DENIED = "Denied (would be unsafe)"
    DEADLOCK = "Deadlock detected"
    NO_DEADLOCK = "No deadlock"
    INVALID = "Invalid input"


# Colour, icon and one-line meaning for each state. Used by the UI legend and banners.
STATUS_STYLE = {
    Status.SAFE: ("green", ":material/verified_user:",
                  "A safe sequence exists, so every process can finish."),
    Status.UNSAFE: ("orange", ":material/warning:",
                    "No safe sequence exists. Deadlock is possible, but has not happened yet."),
    Status.GRANTED: ("green", ":material/check_circle:",
                     "The request was allocated and the system is still safe."),
    Status.WAITING: ("blue", ":material/hourglass_top:",
                     "The request is valid, but there aren't enough free resources yet. The process waits."),
    Status.DENIED: ("orange", ":material/block:",
                    "Granting would make the system unsafe, so the request is refused and the state is rolled back."),
    Status.DEADLOCK: ("red", ":material/sync_lock:",
                      "Processes are blocked on each other right now and none of them can proceed."),
    Status.NO_DEADLOCK: ("green", ":material/lock_open:",
                         "Every process can eventually finish, so there is no deadlock."),
    Status.INVALID: ("gray", ":material/error:",
                     "The input breaks a rule (e.g. negative values, unknown process, more than the declared maximum)."),
}
