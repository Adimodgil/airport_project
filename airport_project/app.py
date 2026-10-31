"""AeroFlow - Smart Airport Operations Manager (DAA mini project).

Run with:  python app.py   (your browser opens automatically)
"""
import copy
import json
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from algorithms.gates import allocate_gates, find_conflicts, free_gates, graph_coloring
from algorithms.graph import dijkstra, floyd_warshall, warshall
from algorithms.queues import MaxHeap, Queue, heap_sort
from algorithms.runway import schedule_runways
from algorithms.searching import binary_search_by_time, linear_search
from algorithms.sorting import bubble_sort, merge_sort, quick_sort
from algorithms.utils import to_minutes, to_time, start_minute

BASE = Path(__file__).parent
HOST, PORT = "127.0.0.1", 5000

app = Flask(__name__)


def load_json(name):
    with (BASE / "data" / name).open(encoding="utf-8") as file:
        return json.load(file)


ORIGINAL_FLIGHTS = load_json("flights.json")
FLIGHTS = copy.deepcopy(ORIGINAL_FLIGHTS)          # changes (delays, new flights) live in memory
GRAPH = load_json("airport_graph.json")
GATES = ["G1", "G2", "G3", "G4", "G5", "G6"]
RUNWAYS = ["RW1", "RW2"]
DEFAULT_RUNWAY_GAP = 10


# ---------------------------------------------------------------- helpers
def error(message, code=400):
    return jsonify({"error": message}), code


def annotated_flights():
    """Copies of all flights plus the values the screens need (gate, runway, status ...)."""
    gate_of = {a["flight_id"]: a["gate"] for a in allocate_gates(FLIGHTS, GATES)["assignments"]}
    runway_of = {s["flight_id"]: s["runway"]
                 for s in schedule_runways(FLIGHTS, RUNWAYS, DEFAULT_RUNWAY_GAP)["slots"]}
    result = []
    for flight in FLIGHTS:
        item = dict(flight)
        item["gate"] = gate_of.get(flight["id"], "-")
        item["runway"] = runway_of.get(flight["id"], "-")
        item["expected"] = to_time(start_minute(flight))
        if flight["priority"] == "emergency":
            item["status"] = "Emergency"
        elif flight.get("delay", 0) > 0:
            item["status"] = "Delayed"
        else:
            item["status"] = "On time"
        result.append(item)
    return result


def parse_minute(text, default="12:00"):
    try:
        return to_minutes(text or default)
    except (ValueError, AttributeError):
        return to_minutes(default)


def find_flight(flight_id):
    return next((f for f in FLIGHTS if f["id"] == flight_id), None)


# ---------------------------------------------------------------- pages / overview
@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/overview")
def overview():
    time_text = request.args.get("time", "12:00")
    minute = parse_minute(time_text)
    allocation = allocate_gates(FLIGHTS, GATES)
    free = free_gates(GATES, allocation["assignments"], minute)

    next_arrival = None                                   # earliest arrival not yet landed
    for flight in annotated_flights():
        if flight["type"] == "arrival" and start_minute(flight) >= minute:
            if next_arrival is None or start_minute(flight) < start_minute(next_arrival):
                next_arrival = flight

    return jsonify({
        "time": time_text,
        "flights": annotated_flights(),
        "graph": GRAPH,
        "gates": GATES,
        "free_gates": free,
        "total_flights": len(FLIGHTS),
        "emergency": sum(f["priority"] == "emergency" for f in FLIGHTS),
        "delayed": sum(f.get("delay", 0) > 0 for f in FLIGHTS),
        "next_arrival": next_arrival,
        "conflicts": len(find_conflicts(allocation["assignments"])),
        "unassigned": allocation["unassigned"],
    })


# ---------------------------------------------------------------- flights: add / sort / search
@app.post("/api/flights")
def add_flight():
    data = request.get_json(silent=True) or {}
    flight_id = str(data.get("id", "")).strip().upper()
    airline = str(data.get("airline", "")).strip()
    try:
        to_minutes(data.get("scheduled_time", ""))
        duration, passengers = int(data.get("duration", 0)), int(data.get("passengers", 0))
    except (ValueError, AttributeError):
        return error("Please enter a valid time (HH:MM) and numbers.")

    if not flight_id or not airline:
        return error("Flight ID and airline are required.")
    if len(flight_id) > 8 or len(airline) > 25:
        return error("Flight ID (max 8) or airline name (max 25) is too long.")
    if find_flight(flight_id):
        return error(f"Flight {flight_id} already exists.")
    if data.get("type") not in ("arrival", "departure"):
        return error("Type must be arrival or departure.")
    if data.get("priority") not in ("normal", "VIP", "emergency"):
        return error("Priority must be normal, VIP or emergency.")
    if not 10 <= duration <= 180:
        return error("Gate duration must be between 10 and 180 minutes.")
    if not 1 <= passengers <= 600:
        return error("Passengers must be between 1 and 600.")

    FLIGHTS.append({"id": flight_id, "airline": airline, "type": data["type"],
                    "scheduled_time": data["scheduled_time"], "duration": duration,
                    "priority": data["priority"], "passengers": passengers, "delay": 0})
    return jsonify({"message": f"Flight {flight_id} added."})


@app.post("/api/sort")
def sort_flights():
    data = request.get_json(silent=True) or {}
    algorithm = data.get("algorithm", "merge")
    sorter = {"merge": merge_sort, "quick": quick_sort, "bubble": bubble_sort}.get(algorithm, merge_sort)
    result, stats = sorter(annotated_flights(), data.get("by", "time"))
    return jsonify({"flights": result, "stats": stats, "algorithm": algorithm})


@app.post("/api/search")
def search_flights():
    data = request.get_json(silent=True) or {}
    query = str(data.get("query", ""))
    flights = annotated_flights()
    if data.get("kind") == "binary":
        return jsonify(binary_search_by_time(flights, query))
    return jsonify(linear_search(flights, query, data.get("field", "id")))


# ---------------------------------------------------------------- queues, emergency, runways
@app.get("/api/queues")
def queues():
    landing_fifo, takeoff_fifo = Queue(), Queue()
    landing_heap, takeoff_heap = MaxHeap(), MaxHeap()
    for flight in annotated_flights():
        if flight["type"] == "arrival":
            landing_fifo.enqueue(flight)
            landing_heap.push(flight)
        else:
            takeoff_fifo.enqueue(flight)
            takeoff_heap.push(flight)

    def drain(structure):
        out = []
        while len(structure):
            out.append(structure.dequeue() if isinstance(structure, Queue) else structure.pop())
        return out

    return jsonify({"landing_fifo": drain(landing_fifo), "landing_priority": drain(landing_heap),
                    "takeoff_priority": drain(takeoff_heap), "heap_sorted": heap_sort(annotated_flights())})


@app.post("/api/emergency")
def declare_emergency():
    flight = find_flight((request.get_json(silent=True) or {}).get("flight_id"))
    if not flight:
        return error("Flight not found.", 404)
    flight["priority"] = "emergency"
    return jsonify({"message": f"{flight['id']} declared EMERGENCY - it now goes first in the queue."})


@app.post("/api/runways")
def runways():
    try:
        gap = int((request.get_json(silent=True) or {}).get("gap", DEFAULT_RUNWAY_GAP))
    except (TypeError, ValueError):
        return error("Gap must be a number.")
    if not 1 <= gap <= 180:
        return error("Runway busy time must be 1 to 180 minutes.")
    return jsonify(schedule_runways(FLIGHTS, RUNWAYS, gap) | {"gap": gap, "runways": RUNWAYS})


# ---------------------------------------------------------------- taxi routes
@app.post("/api/route")
def route():
    data = request.get_json(silent=True) or {}
    return jsonify(dijkstra(GRAPH, data.get("start"), data.get("end")))


@app.get("/api/matrices")
def matrices():
    return jsonify({"floyd": floyd_warshall(GRAPH), "warshall": warshall(GRAPH)})


# ---------------------------------------------------------------- gates, delays
@app.get("/api/gates")
def gates():
    minute = parse_minute(request.args.get("time"))
    allocation = allocate_gates(FLIGHTS, GATES)
    return jsonify({
        "assignments": allocation["assignments"],
        "unassigned": allocation["unassigned"],
        "conflicts": find_conflicts(allocation["assignments"]),
        "free_now": free_gates(GATES, allocation["assignments"], minute),
        "coloring": graph_coloring(FLIGHTS, GATES),
        "gates": GATES,
    })


@app.post("/api/delay")
def delay():
    data = request.get_json(silent=True) or {}
    flight = find_flight(data.get("flight_id"))
    if not flight:
        return error("Flight not found.", 404)
    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        return error("Delay must be a number.")
    if not 1 <= minutes <= 720:
        return error("Delay must be between 1 and 720 minutes.")

    before = {a["flight_id"]: a["gate"] for a in allocate_gates(FLIGHTS, GATES)["assignments"]}
    flight["delay"] = flight.get("delay", 0) + minutes
    after = {a["flight_id"]: a["gate"] for a in allocate_gates(FLIGHTS, GATES)["assignments"]}
    moved = [f"{fid}: {before.get(fid, '-')} -> {after.get(fid, '-')}"
             for fid in after if before.get(fid) != after[fid]]
    return jsonify({"message": f"{flight['id']} delayed by {minutes} min (total {flight['delay']} min).",
                    "changes": moved})


@app.post("/api/reset")
def reset():
    FLIGHTS[:] = copy.deepcopy(ORIGINAL_FLIGHTS)
    return jsonify({"message": "Original schedule restored."})


# ---------------------------------------------------------------- start
if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()   # open the browser for you
    print(f"AeroFlow running at {url}  (press Ctrl+C to stop)")
    app.run(host=HOST, port=PORT, debug=False)
