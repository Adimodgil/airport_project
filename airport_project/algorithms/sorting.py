"""Sorting the flight schedule.   Syllabus: Unit 1.

Algorithm   Paradigm            Best        Average     Worst       Space
Merge sort  divide & conquer    O(n log n)  O(n log n)  O(n log n)  O(n)
Quick sort  divide & conquer    O(n log n)  O(n log n)  O(n^2)      O(log n)
Bubble sort brute force         O(n)        O(n^2)      O(n^2)      O(1)

Every function returns (sorted_list, stats) where stats has the number of
comparisons and the time taken, so the UI can display them.
"""
from time import perf_counter

from .utils import priority_rank, start_minute


def sort_key(flight, by):
    """What we compare when sorting: time, priority (emergency first) or airline."""
    if by == "priority":
        return (-priority_rank(flight), start_minute(flight))
    if by == "airline":
        return (flight["airline"].lower(), start_minute(flight))
    return (start_minute(flight), -priority_rank(flight))


def merge_sort(flights, by="time"):
    stats = {"comparisons": 0}
    begin = perf_counter()

    def divide(items):
        if len(items) <= 1:
            return items
        middle = len(items) // 2
        left, right = divide(items[:middle]), divide(items[middle:])
        merged, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            stats["comparisons"] += 1
            if sort_key(left[i], by) <= sort_key(right[j], by):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        return merged + left[i:] + right[j:]

    result = divide(list(flights))
    stats["elapsed_ms"] = (perf_counter() - begin) * 1000
    stats["steps"] = [f"Split the list in halves, sorted each half, merged them ({len(result)} flights)."]
    return result, stats


def quick_sort(flights, by="time"):
    items = list(flights)
    stats = {"comparisons": 0}
    begin = perf_counter()

    def sort_range(low, high):
        if low >= high:
            return
        pivot = sort_key(items[high], by)          # last element is the pivot
        boundary = low
        for j in range(low, high):
            stats["comparisons"] += 1
            if sort_key(items[j], by) <= pivot:
                items[boundary], items[j] = items[j], items[boundary]
                boundary += 1
        items[boundary], items[high] = items[high], items[boundary]
        sort_range(low, boundary - 1)
        sort_range(boundary + 1, high)

    sort_range(0, len(items) - 1)
    stats["elapsed_ms"] = (perf_counter() - begin) * 1000
    stats["steps"] = [f"Partitioned around a pivot again and again ({len(items)} flights)."]
    return items, stats


def bubble_sort(flights, by="time"):
    items = list(flights)
    stats = {"comparisons": 0}
    begin = perf_counter()
    for end in range(len(items) - 1, 0, -1):
        swapped = False
        for i in range(end):
            stats["comparisons"] += 1
            if sort_key(items[i], by) > sort_key(items[i + 1], by):
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True
        if not swapped:                            # already sorted -> stop early
            break
    stats["elapsed_ms"] = (perf_counter() - begin) * 1000
    stats["steps"] = ["Swapped neighbouring flights until no swap was needed."]
    return items, stats
