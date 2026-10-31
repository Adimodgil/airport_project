"""Airport graph algorithms.   Syllabus: Unit 2 (Dijkstra) and Unit 3 (Floyd, Warshall).

Dijkstra (greedy)            : O(V^2) with a simple scan, space O(V)
Floyd-Warshall (DP)          : O(V^3) time, O(V^2) space - all pairs shortest distance
Warshall (transitive closure): O(V^3) time, O(V^2) space - can I reach B from A?
"""
INF = float("inf")


def build_adjacency(graph):
    """{'RW1': {'J1': 120, ...}, ...} (taxiways work in both directions)."""
    adjacency = {node["id"]: {} for node in graph["nodes"]}
    for a, b, weight in graph["edges"]:
        adjacency[a][b] = weight
        adjacency[b][a] = weight
    return adjacency


def dijkstra(graph, start, end):
    adjacency = build_adjacency(graph)
    if start not in adjacency or end not in adjacency:
        return {"path": [], "distance": None, "steps": ["Unknown node"]}

    distance = {node: INF for node in adjacency}
    previous = {}
    unvisited = set(adjacency)
    distance[start] = 0
    steps = []

    while unvisited:
        current = min(unvisited, key=lambda node: distance[node])   # closest unvisited node
        unvisited.remove(current)
        if distance[current] == INF:
            break
        steps.append(f"Visit {current} (distance {distance[current]})")
        if current == end:
            break
        for neighbour, weight in adjacency[current].items():
            if neighbour in unvisited and distance[current] + weight < distance[neighbour]:
                distance[neighbour] = distance[current] + weight
                previous[neighbour] = current

    if distance[end] == INF:
        return {"path": [], "distance": None, "steps": steps}
    path, node = [end], end
    while node != start:
        node = previous[node]
        path.append(node)
    path.reverse()
    return {"path": path, "distance": distance[end], "steps": steps}


def floyd_warshall(graph):
    ids = [node["id"] for node in graph["nodes"]]
    dist = {a: {b: (0 if a == b else INF) for b in ids} for a in ids}
    for a, b, weight in graph["edges"]:
        dist[a][b] = dist[b][a] = weight
    for k in ids:                                  # allow k as an intermediate stop
        for i in ids:
            for j in ids:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return {"nodes": ids, "distances": dist}


def warshall(graph):
    ids = [node["id"] for node in graph["nodes"]]
    reach = {a: {b: a == b for b in ids} for a in ids}
    for a, b, _ in graph["edges"]:
        reach[a][b] = reach[b][a] = True
    for k in ids:
        for i in ids:
            for j in ids:
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return {"nodes": ids, "reachability": reach}
