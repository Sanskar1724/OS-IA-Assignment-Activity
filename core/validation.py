"""Input validation (Scenario F).

Each check returns a list of human-readable problems. An empty list means the
input is valid. Boundary cases that are *valid* (zero Available, a process whose
remaining Need is zero, an all-zero request) are deliberately not flagged here.
"""

from numbers import Integral

Matrix = list[list[int]]
Vector = list[int]


def _is_int(x) -> bool:
    return isinstance(x, Integral) and not isinstance(x, bool)


def validate_system(allocation: Matrix, maximum: Matrix, available: Vector,
                    processes: list[str] | None = None,
                    resources: list[str] | None = None) -> list[str]:
    """Check that a Banker's Algorithm state is well formed."""
    errors: list[str] = []
    n, m = len(allocation), len(available)
    pname = (lambda i: processes[i]) if processes else (lambda i: f"P{i}")
    rname = (lambda j: resources[j]) if resources else (lambda j: f"R{j}")

    if n == 0 or m == 0:
        return ["There must be at least one process and one resource type."]
    if len(maximum) != n:
        errors.append(f"Allocation has {n} rows but Maximum has {len(maximum)}.")
        return errors

    for j, a in enumerate(available):
        if not _is_int(a):
            errors.append(f"Available[{rname(j)}] must be a whole number (got {a!r}).")
        elif a < 0:
            errors.append(f"Available[{rname(j)}] is negative ({a}). Free instances can't be below zero.")

    for i in range(n):
        if len(allocation[i]) != m or len(maximum[i]) != m:
            errors.append(f"{pname(i)} must have exactly {m} values in every matrix.")
            continue
        for j in range(m):
            al, mx = allocation[i][j], maximum[i][j]
            if not _is_int(al) or not _is_int(mx):
                errors.append(f"{pname(i)}/{rname(j)}: values must be whole numbers.")
                continue
            if al < 0:
                errors.append(f"Allocation[{pname(i)}][{rname(j)}] is negative ({al}).")
            if mx < 0:
                errors.append(f"Maximum[{pname(i)}][{rname(j)}] is negative ({mx}).")
            if al > mx:
                errors.append(
                    f"{pname(i)} holds {al} × {rname(j)} but declared a maximum of only {mx}. "
                    "Allocation can never exceed the declared maximum demand."
                )
    return errors


def validate_request(pid, request, need: Matrix, n_processes: int,
                     resources: list[str] | None = None) -> list[str]:
    """Check a resource request *before* the Banker's Algorithm looks at Available.

    Exceeding Available is NOT an error here: that request is valid and simply
    has to wait. Only malformed or over-claiming requests are invalid.
    """
    rname = (lambda j: resources[j]) if resources else (lambda j: f"R{j}")
    if not _is_int(pid) or not (0 <= pid < n_processes):
        return [f"Process '{pid}' doesn't exist. Valid processes are P0 to P{n_processes - 1}."]

    m = len(need[pid])
    if len(request) != m:
        return [f"The request must contain exactly {m} values, one per resource type."]

    errors: list[str] = []
    for j, r in enumerate(request):
        if not _is_int(r):
            errors.append(f"Request[{rname(j)}] must be a whole number (got {r!r}).")
        elif r < 0:
            errors.append(f"Request[{rname(j)}] is negative ({r}). A process can't request a negative amount.")
        elif r > need[pid][j]:
            errors.append(
                f"P{pid} asks for {r} × {rname(j)} but its remaining Need is only {need[pid][j]}. "
                "That would exceed its declared maximum claim."
            )
    return errors


def validate_detection(allocation: Matrix, request: Matrix, available: Vector) -> list[str]:
    """Check a deadlock-detection state (Allocation, Request, Available)."""
    errors: list[str] = []
    m = len(available)
    if not allocation or m == 0:
        return ["There must be at least one process and one resource type."]
    for name, mat in (("Allocation", allocation), ("Request", request)):
        for i, row in enumerate(mat):
            if len(row) != m:
                errors.append(f"{name} row P{i} must have {m} values.")
            elif any(not _is_int(v) or v < 0 for v in row):
                errors.append(f"{name} row P{i} must contain whole numbers ≥ 0.")
    if any(not _is_int(v) or v < 0 for v in available):
        errors.append("Available must contain whole numbers ≥ 0.")
    return errors
