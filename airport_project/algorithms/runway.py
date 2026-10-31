"""Runway scheduling.   Syllabus: Unit 2 (greedy + priority queue / heap).

Each take-off or landing blocks a runway for `gap` minutes.  Whenever a runway becomes free,
we push all flights that are already waiting into a max-heap and let the highest priority
flight (emergency > VIP > normal, then earliest) use it.
Time: O(F log F) for the heap work, space O(F).
"""
from .queues import MaxHeap
from .utils import insertion_sort, start_minute


def schedule_runways(flights, runways, gap=10):
    pending = insertion_sort(flights, key=start_minute)
    free_at = {runway: 0 for runway in runways}
    waiting = MaxHeap()
    slots, steps, next_flight, clock = [], [], 0, 0

    while next_flight < len(pending) or len(waiting):
        runway = min(free_at, key=lambda r: free_at[r])          # runway that frees up first
        now = max(free_at[runway], clock)                        # time never goes backwards
        if not len(waiting):
            now = max(now, start_minute(pending[next_flight]))   # nobody waiting: jump ahead
        clock = now
        while next_flight < len(pending) and start_minute(pending[next_flight]) <= now:
            waiting.push(pending[next_flight])
            next_flight += 1
        flight = waiting.pop()
        wanted = start_minute(flight)
        slots.append({"flight_id": flight["id"], "runway": runway, "start": now, "end": now + gap,
                      "wait": now - wanted, "priority": flight["priority"]})
        free_at[runway] = now + gap
        if now > wanted:
            steps.append(f"{flight['id']} waited {now - wanted} min for {runway}")
    return {"slots": slots, "total_wait": sum(s["wait"] for s in slots), "steps": steps}
