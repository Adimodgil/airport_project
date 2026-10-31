"""Run with:  python -m unittest tests.test_algorithms -v"""
import json
import unittest
from pathlib import Path

from algorithms.gates import allocate_gates, find_conflicts, free_gates, graph_coloring
from algorithms.graph import dijkstra, floyd_warshall, warshall
from algorithms.queues import MaxHeap, Queue, heap_sort
from algorithms.runway import schedule_runways
from algorithms.searching import binary_search_by_time, linear_search
from algorithms.sorting import bubble_sort, merge_sort, quick_sort
from algorithms.utils import start_minute

ROOT = Path(__file__).resolve().parents[1]
FLIGHTS = json.loads((ROOT / "data/flights.json").read_text())
GRAPH = json.loads((ROOT / "data/airport_graph.json").read_text())
GATES = ["G1", "G2", "G3", "G4", "G5", "G6"]


class SortingAndSearching(unittest.TestCase):
    def test_all_sorts_give_time_order(self):
        expected = sorted(start_minute(f) for f in FLIGHTS)
        for sorter in (merge_sort, quick_sort, bubble_sort):
            result, stats = sorter(FLIGHTS, "time")
            self.assertEqual([start_minute(f) for f in result], expected)
            self.assertGreater(stats["comparisons"], 0)

    def test_priority_sort_puts_emergency_first(self):
        result, _ = merge_sort(FLIGHTS, "priority")
        self.assertEqual(result[0]["priority"], "emergency")

    def test_linear_search(self):
        self.assertEqual(linear_search(FLIGHTS, "AF101")["item"]["id"], "AF101")
        self.assertIsNone(linear_search(FLIGHTS, "ZZ999")["item"])

    def test_binary_search(self):
        target = FLIGHTS[0]["scheduled_time"]
        self.assertEqual(binary_search_by_time(FLIGHTS, target)["item"]["scheduled_time"], target)
        self.assertIsNone(binary_search_by_time(FLIGHTS, "03:33")["item"])


class QueuesAndHeaps(unittest.TestCase):
    def test_queue_is_fifo(self):
        q = Queue(); q.enqueue(1); q.enqueue(2)
        self.assertEqual((q.dequeue(), q.dequeue(), q.dequeue()), (1, 2, None))

    def test_heap_gives_emergency_first(self):
        heap = MaxHeap()
        for f in FLIGHTS:
            heap.push(f)
        self.assertEqual(heap.pop()["priority"], "emergency")

    def test_heap_sort_orders_by_time(self):
        times = [start_minute(f) for f in heap_sort(FLIGHTS)]
        self.assertEqual(times, sorted(times))


class Graphs(unittest.TestCase):
    def test_dijkstra(self):
        result = dijkstra(GRAPH, "RW1", "G1")
        self.assertEqual(result["path"][0], "RW1")
        self.assertEqual(result["path"][-1], "G1")
        self.assertEqual(result["distance"], floyd_warshall(GRAPH)["distances"]["RW1"]["G1"])

    def test_unknown_node(self):
        self.assertEqual(dijkstra(GRAPH, "RW1", "XX")["path"], [])

    def test_warshall_reachability(self):
        self.assertTrue(warshall(GRAPH)["reachability"]["RW1"]["G6"])


class GatesAndRunways(unittest.TestCase):
    def test_allocation_has_no_conflicts(self):
        result = allocate_gates(FLIGHTS, GATES)
        self.assertEqual(find_conflicts(result["assignments"]), [])
        self.assertEqual(len(result["assignments"]) + len(result["unassigned"]), len(FLIGHTS))

    def test_conflict_detection_works(self):
        fake = [{"flight_id": "A", "gate": "G1", "start": 0, "end": 50},
                {"flight_id": "B", "gate": "G1", "start": 40, "end": 90}]
        self.assertEqual(len(find_conflicts(fake)), 1)

    def test_delay_moves_flight_time(self):
        delayed = [dict(f) for f in FLIGHTS]
        delayed[0]["delay"] = 90
        self.assertEqual(start_minute(delayed[0]), start_minute(FLIGHTS[0]) + 90)

    def test_free_gates(self):
        result = allocate_gates(FLIGHTS, GATES)
        first = result["assignments"][0]
        self.assertNotIn(first["gate"], free_gates(GATES, result["assignments"], first["start"]))

    def test_graph_coloring(self):
        result = graph_coloring(FLIGHTS, GATES)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["colors"]), len(FLIGHTS))

    def test_runway_emergency_goes_first_when_congested(self):
        same_time = [{"id": f"F{i}", "scheduled_time": "10:00", "priority": p, "delay": 0}
                     for i, p in enumerate(["normal", "normal", "emergency"])]
        slots = schedule_runways(same_time, ["RW1"], 10)["slots"]
        self.assertEqual(slots[0]["flight_id"], "F2")
        self.assertEqual(slots[2]["wait"], 20)


if __name__ == "__main__":
    unittest.main()
