"""Ready-made test data for Scenarios A–F.

Every number here was checked by hand and by tests/test_core.py.
Edit these to create your group's own test cases.
"""

RESOURCES_ABC = ["A", "B", "C"]

# Scenario A: a safe state (5 processes, 3 resource types; totals A=10, B=5, C=7).
BANKER_BASE = {
    "label": "Safe base state (5 processes, A/B/C)",
    "resources": RESOURCES_ABC,
    "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
    "maximum":    [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
    "available":  [3, 3, 2],
}

# Requests made against BANKER_BASE. Each one shows a different outcome.
REQUESTS = {
    "granted": {"pid": 1, "request": [1, 0, 2],
                "title": "P1 asks for (1, 0, 2)",
                "why": "Within Need and Available, and a safe sequence still exists, so it is granted."},
    "waiting": {"pid": 2, "request": [4, 0, 0],
                "title": "Scenario B: P2 asks for (4, 0, 0)",
                "why": "P2 still needs 6 × A, so 4 is allowed, but only 3 × A are free. P2 has to wait."},
    "unsafe":  {"pid": 4, "request": [3, 3, 0],
                "title": "Scenario C: P4 asks for (3, 3, 0)",
                "why": "Fits both Need (4, 3, 1) and Available (3, 3, 2), but leaves Available = (0, 0, 2) "
                       "and nobody could finish. Denied."},
}

# Scenario D: deadlock detection.
DETECTION = {
    "single_deadlock": {
        "label": "Single-instance: circular wait (deadlock)",
        "model": "single",
        "resources": ["R0", "R1", "R2", "R3"],
        "allocation": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        "request":    [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 0]],
        "available":  [0, 0, 0, 0],
        "story": "Every resource has 1 instance. P0 holds R0 and waits for R1, P1 holds R1 and waits for R2, "
                 "P2 holds R2 and waits for R0. P3 holds R3 and isn't waiting for anything.",
    },
    "multi_deadlock": {
        "label": "Multiple-instance: deadlock confirmed",
        "model": "multi",
        "resources": ["A", "B", "C"],
        "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]],
        "request":    [[0, 0, 0], [2, 0, 2], [0, 0, 1], [1, 0, 0], [0, 0, 2]],
        "available":  [0, 0, 0],
        "story": "Totals are A=7, B=2, C=6. Only P0 can finish, and it frees just one B. "
                 "P1–P4 then wait for A or C that only they hold.",
    },
    "multi_cycle_no_deadlock": {
        "label": "Multiple-instance: cycle but NO deadlock",
        "model": "multi",
        "resources": ["R0", "R1"],
        "allocation": [[0, 1], [1, 0], [1, 0], [0, 1]],
        "request":    [[1, 0], [0, 0], [0, 1], [0, 0]],
        "available":  [0, 0],
        "story": "R0 and R1 have 2 instances each. P0 → R0 → P2 → R1 → P0 forms a cycle, "
                 "but P1 and P3 aren't waiting. When they finish, the instances they release break the cycle.",
    },
}

# Scenario E: deadlock prevention workload (single-instance R0..R2).
PREVENTION = {
    "resources": 3,
    "plans": [[0, 1], [1, 2], [2, 0]],   # P2 grabs R2 then R0: that closes the circle
    "bursts": [2, 2, 2],
}
