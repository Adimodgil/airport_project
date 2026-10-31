"""Landing / take-off queues.   Syllabus: Unit 1 (queue) and Unit 2 (heap, heap sort).

Queue (FIFO): enqueue O(1), dequeue O(n) here because we use list.pop(0).
MaxHeap     : push O(log n), pop O(log n), peek O(1).  Emergency flights come out first.
Heap sort   : O(n log n) time, O(1) extra space.
"""
from .utils import priority_rank, start_minute


class Queue:
    """First come, first served."""

    def __init__(self):
        self.items = []

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        return self.items.pop(0) if self.items else None

    def __len__(self):
        return len(self.items)


class MaxHeap:
    """Priority queue: highest priority first; if equal, the earlier flight first."""

    def __init__(self):
        self.data = []

    @staticmethod
    def score(flight):
        return (priority_rank(flight), -start_minute(flight))

    def push(self, flight):
        self.data.append(flight)
        child = len(self.data) - 1
        while child > 0:                           # bubble up
            parent = (child - 1) // 2
            if self.score(self.data[parent]) >= self.score(self.data[child]):
                break
            self.data[parent], self.data[child] = self.data[child], self.data[parent]
            child = parent

    def pop(self):
        if not self.data:
            return None
        top = self.data[0]
        last = self.data.pop()
        if self.data:
            self.data[0] = last
            self._sift_down(0)
        return top

    def _sift_down(self, i):
        size = len(self.data)
        while True:
            left, right, largest = 2 * i + 1, 2 * i + 2, i
            if left < size and self.score(self.data[left]) > self.score(self.data[largest]):
                largest = left
            if right < size and self.score(self.data[right]) > self.score(self.data[largest]):
                largest = right
            if largest == i:
                return
            self.data[i], self.data[largest] = self.data[largest], self.data[i]
            i = largest

    def __len__(self):
        return len(self.data)


def heap_sort(flights):
    """Sort flights by expected time (earliest first) using a max-heap built in place."""
    items = list(flights)

    def sift_down(i, size):
        while True:
            left, right, largest = 2 * i + 1, 2 * i + 2, i
            if left < size and start_minute(items[left]) > start_minute(items[largest]):
                largest = left
            if right < size and start_minute(items[right]) > start_minute(items[largest]):
                largest = right
            if largest == i:
                return
            items[i], items[largest] = items[largest], items[i]
            i = largest

    for i in range(len(items) // 2 - 1, -1, -1):   # 1) build max-heap
        sift_down(i, len(items))
    for end in range(len(items) - 1, 0, -1):       # 2) move the biggest to the end
        items[0], items[end] = items[end], items[0]
        sift_down(0, end)
    return items
