# AeroFlow – Smart Airport Operations Manager
College **Design and Analysis of Algorithms (DAA)** mini project.
A web dashboard for airport ground operations: flight schedule, landing queues, runway scheduling,
taxi routes and gate allocation. Every algorithm is written by hand in Python (no built-in `sort`,
`heapq` or `networkx`). Runs fully offline – no database, no internet needed.

## How to run
```
pip install -r requirements.txt
python app.py
```
`python app.py` starts the server **and opens your browser automatically** (http://127.0.0.1:5000).
Stop with `Ctrl+C`. Run the tests with `python -m unittest tests.test_algorithms -v`.

## Pages and the algorithm behind each
| Page | What it does | Algorithm | Complexity | Unit |
|---|---|---|---|---|
| Overview | Status at any time, free gates, next arrival, alerts, airport map | Interval scheduling | O(F·G·F) | 2 |
| Flight schedule | Sort by time / priority / airline, shows comparisons + time | Merge, Quick, Bubble sort | O(n log n) / O(n log n) avg / O(n²) | 1 |
| Flight schedule | Search by ID, airline or exact time. Add new flights (validated) | Linear, Binary search | O(n) / O(log n) | 1 |
| Landing queues | FIFO queue vs priority queue; declare an emergency | Queue, Max-heap, Heap sort | push/pop O(log n), sort O(n log n) | 1, 2 |
| Runway scheduler | 2 runways, emergency flights go first, shows waiting time | Greedy + max-heap | O(F log F) | 2 |
| Taxi route finder | Shortest path runway ↔ gate, animated plane, all-pairs table | Dijkstra, Floyd-Warshall, Warshall | O(V²), O(V³), O(V³) | 2, 3 |
| Gate allocation | Gantt timeline, free gates at a time, delay handling, double-booking detection | Greedy + graph colouring (backtracking) | O(F·G·F), O(G^F) worst | 2, 3 |

## Folder structure
```
airport_project/
├── app.py                 # Flask server + API (opens the browser)
├── requirements.txt
├── data/                  # flights.json, airport_graph.json
├── algorithms/            # sorting, searching, queues, graph, gates, runway, utils
├── templates/index.html
├── static/css/style.css
├── static/js/main.js
└── tests/test_algorithms.py
```

## Viva Q&A
1. **Why Dijkstra for taxi routes?** All taxiway distances are positive, so greedy Dijkstra is correct and faster than Bellman-Ford.
2. **Dijkstra vs Floyd-Warshall?** Dijkstra: one source to all nodes. Floyd: every pair at once (dynamic programming), O(V³).
3. **What does Warshall compute?** Transitive closure – whether node B is reachable from node A.
4. **Why is greedy fine for gate allocation?** Flights are handled in order of start time and each takes the first free gate; for interval scheduling this never needs more gates than necessary.
5. **How does graph colouring relate to gates?** Flights are vertices, overlapping flights are connected, colours are gates. Neighbours must get different colours.
6. **Why backtracking in colouring?** If a flight has no valid gate, we undo the previous choice and try another.
7. **Why a heap for the landing queue?** Push/pop in O(log n) and the highest priority (emergency) is always at the top.
8. **Queue vs priority queue?** Queue = first come first served. Priority queue = most urgent first.
9. **Is heap sort stable? Its space?** Not stable; in-place so O(1) extra space.
10. **Merge vs Quick sort?** Merge: always O(n log n), needs O(n) space. Quick: O(n log n) average, O(n²) worst case, in-place.
11. **Why is Bubble sort slow?** It compares neighbours repeatedly: O(n²). It stops early only if already sorted.
12. **Why must data be sorted for binary search?** It discards half the list each step by comparing with the middle element.
13. **What happens when a flight is delayed?** Its start time shifts, gates are recomputed, and the page shows which flights changed gate.
14. **How are double-bookings detected?** Any two assignments on the same gate whose time ranges overlap are reported (O(F²)).
15. **How does the runway scheduler pick the next flight?** When a runway frees up, all waiting flights are pushed into a max-heap and the highest priority one is popped.
