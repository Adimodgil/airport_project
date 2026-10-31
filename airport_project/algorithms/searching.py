"""Searching flights.   Syllabus: Unit 1.

Linear search: best O(1), average/worst O(n), space O(1)  (works on unsorted data)
Binary search: best O(1), average/worst O(log n), space O(1) (needs sorted data)
"""
from .sorting import merge_sort
from .utils import to_minutes, to_time, start_minute


def linear_search(flights, query, field="id"):
    """Check flights one by one; match if the field contains the query text."""
    query = str(query).lower().strip()
    steps = []
    for index, flight in enumerate(flights):
        steps.append(f"Step {index + 1}: checked {flight[field]}")
        if query in str(flight[field]).lower():
            return {"item": flight, "steps": steps, "checks": index + 1}
    return {"item": None, "steps": steps, "checks": len(flights)}


def binary_search_by_time(flights, query):
    """Find a flight by its exact expected time ('HH:MM'). Sorts first, then halves the range."""
    try:
        target = to_minutes(query)
    except ValueError:
        return {"item": None, "steps": ["Time must look like HH:MM"], "checks": 0}
    ordered, _ = merge_sort(flights, "time")
    low, high, steps = 0, len(ordered) - 1, []
    while low <= high:
        middle = (low + high) // 2
        value = start_minute(ordered[middle])
        steps.append(f"Looked at middle flight {ordered[middle]['id']} ({to_time(value)})")
        if value == target:
            return {"item": ordered[middle], "steps": steps, "checks": len(steps)}
        if value < target:
            low = middle + 1
        else:
            high = middle - 1
    return {"item": None, "steps": steps, "checks": len(steps)}
