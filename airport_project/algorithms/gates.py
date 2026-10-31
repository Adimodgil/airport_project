"""Gate allocation.   Syllabus: Unit 2 (greedy) and Unit 3 (backtracking / graph colouring).

allocate_gates : greedy interval scheduling - handle flights in order of start time and give
                 each one the first gate that is free.  O(F log F + F*G*F)
find_conflicts : double-booking detector.                 O(F^2)
graph_coloring : backtracking; flights that overlap are neighbours and need different gates.
                 Worst case O(G^F), but first-fit on start-sorted intervals never backtracks.
"""
from .utils import insertion_sort, start_minute

STEP_LIMIT = 20000


def flight_interval(flight):
    start = start_minute(flight)
    return start, start + int(flight.get("duration", 40))


def allocate_gates(flights, gates):
    ordered = insertion_sort(flights, key=start_minute)
    booked = {gate: [] for gate in gates}          # gate -> list of (start, end)
    assignments, unassigned = [], []

    for flight in ordered:
        start, end = flight_interval(flight)
        for gate in gates:
            if all(end <= s or start >= e for s, e in booked[gate]):   # no overlap
                booked[gate].append((start, end))
                assignments.append({"flight_id": flight["id"], "gate": gate, "start": start, "end": end})
                break
        else:
            unassigned.append(flight["id"])
    return {"assignments": assignments, "unassigned": unassigned}


def find_conflicts(assignments):
    """Pairs of flights that use the same gate at overlapping times (should be empty)."""
    conflicts = []
    for i in range(len(assignments)):
        for j in range(i + 1, len(assignments)):
            a, b = assignments[i], assignments[j]
            if a["gate"] == b["gate"] and a["start"] < b["end"] and b["start"] < a["end"]:
                conflicts.append([a["flight_id"], b["flight_id"], a["gate"]])
    return conflicts


def free_gates(gates, assignments, minute):
    busy = {a["gate"] for a in assignments if a["start"] <= minute < a["end"]}
    return [gate for gate in gates if gate not in busy]


def graph_coloring(flights, gates):
    """Colour = gate.  Returns {'colors': {flight: gate}, 'valid': bool, 'gates_used': n}."""
    ordered = insertion_sort(flights, key=start_minute)
    ids = [f["id"] for f in ordered]
    span = {f["id"]: flight_interval(f) for f in ordered}
    neighbours = {i: [j for j in ids if j != i and span[i][0] < span[j][1] and span[j][0] < span[i][1]]
                  for i in ids}
    colors, calls = {}, [0]

    def solve(index):
        if index == len(ids):
            return True
        calls[0] += 1
        if calls[0] > STEP_LIMIT:
            return False
        flight = ids[index]
        for gate in gates:
            if all(colors.get(n) != gate for n in neighbours[flight]):
                colors[flight] = gate
                if solve(index + 1):
                    return True
                del colors[flight]                 # backtrack
        return False

    valid = solve(0)
    return {"colors": colors if valid else {}, "valid": valid,
            "gates_used": len(set(colors.values())), "calls": calls[0]}
