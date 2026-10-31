"""Small helpers shared by all algorithms."""


def to_minutes(time_text):
    """'09:30' -> 570. Raises ValueError for a bad time."""
    hours, minutes = time_text.split(":")
    hours, minutes = int(hours), int(minutes)
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError("time out of range")
    return hours * 60 + minutes


def to_time(minutes):
    """570 -> '09:30' (wraps after midnight)."""
    minutes = minutes % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def start_minute(flight):
    """Real time a flight needs its gate/runway = scheduled time + delay."""
    return to_minutes(flight["scheduled_time"]) + int(flight.get("delay", 0))


def priority_rank(flight):
    """emergency (3) > VIP (2) > normal (1)."""
    return {"emergency": 3, "VIP": 2}.get(flight.get("priority"), 1)


def insertion_sort(items, key):
    """Simple stable sort used inside other algorithms.  O(n^2) worst, O(n) best."""
    items = list(items)
    for i in range(1, len(items)):
        current = items[i]
        j = i - 1
        while j >= 0 and key(items[j]) > key(current):
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current
    return items
