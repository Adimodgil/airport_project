/* AeroFlow front-end. Each "render..." function draws one page of the dashboard. */

const $ = (selector) => document.querySelector(selector);

const PAGE_TITLES = {
  overview: "Operations overview",
  schedule: "Flight schedule & search",
  queues: "Landing and take-off queues",
  runways: "Runway scheduler",
  routes: "Taxi route finder",
  gates: "Gate allocation",
};
const TIMELINE_START = 360;   // 06:00 in minutes
const TIMELINE_SPAN = 1020;   // timeline covers 06:00 - 23:00

const state = { time: "12:00", path: [], graph: null };

/* ------------------------------------------------------------ small helpers */
async function api(url, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function toast(message, isError = false) {
  const box = $("#toast");
  box.textContent = message;
  box.style.borderColor = isError ? "#8a3a46" : "#317c70";
  box.style.background = isError ? "#3b1d26" : "#183e3a";
  box.classList.add("show");
  setTimeout(() => box.classList.remove("show"), 3000);
}

/* Run a button action; show any error as a toast instead of breaking the page. */
async function attempt(action) {
  try { await action(); } catch (e) { toast(e.message, true); }
}

function esc(text) {   // stops user-typed text from being treated as HTML
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function minutesToTime(m) {
  m = m % 1440;
  return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
}

function tag(text, color) { return `<span class="tag ${color}">${esc(text)}</span>`; }
function priorityTag(p) { return tag(p, p === "emergency" ? "red" : p === "VIP" ? "amber" : "green"); }
function statusTag(s) { return tag(s, s === "Emergency" ? "red" : s === "Delayed" ? "amber" : "green"); }

function info(algorithm, complexity, unit) {
  return `<div class="info"><strong>Algorithm used:</strong> ${algorithm}
          <div><b>Complexity:</b> ${complexity} &nbsp;·&nbsp; <b>Syllabus:</b> ${unit}</div></div>`;
}

function card(title, body, extra = "") {
  return `<section class="card"><div class="card-head"><h2>${title}</h2>${extra}</div>${body}</section>`;
}

function stat(label, value, icon, sub) {
  return `<div class="card"><span class="metric-icon">${icon}</span>
          <div class="metric-label">${label}</div><div class="metric">${value}</div>
          <div class="metric-label">${sub}</div></div>`;
}

function table(headers, rows) {
  const head = headers.map((h) => `<th>${h}</th>`).join("");
  const body = rows.length ? rows.join("") : `<tr><td colspan="${headers.length}" class="empty">No results</td></tr>`;
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function stepList(items) {
  if (!items || !items.length) return '<div class="muted">No steps to show.</div>';
  return `<div class="step-list">${items.map((s) => `<div class="step">${esc(s)}</div>`).join("")}</div>`;
}

function flightTable(flights) {
  const rows = flights.map((f) => `<tr>
      <td><b>${esc(f.id)}</b></td><td>${esc(f.airline)}</td><td>${f.type}</td>
      <td>${f.scheduled_time}</td><td>${f.expected}</td><td>${statusTag(f.status)}</td>
      <td>${priorityTag(f.priority)}</td><td>${tag(f.gate, "blue")}</td><td>${f.runway}</td><td>${f.passengers}</td></tr>`);
  return table(["FLIGHT", "AIRLINE", "TYPE", "SCHEDULED", "EXPECTED", "STATUS", "PRIORITY", "GATE", "RUNWAY", "PAX"], rows);
}

/* ------------------------------------------------------------ airport map */
function drawMap(graph, highlight = []) {
  const nodeById = Object.fromEntries(graph.nodes.map((n) => [n.id, n]));
  const onPath = (a, b) => highlight.some((x, i) => i < highlight.length - 1 &&
      ((x === a && highlight[i + 1] === b) || (x === b && highlight[i + 1] === a)));

  const edges = graph.edges.map(([a, b, weight]) => {
    const p = nodeById[a], q = nodeById[b];
    return `<line x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}" class="map-edge ${onPath(a, b) ? "highlight" : ""}"/>
            <text x="${(p.x + q.x) / 2}" y="${(p.y + q.y) / 2 - 5}" class="map-edge-label">${weight}m</text>`;
  }).join("");

  const nodes = graph.nodes.map((n) => {
    const radius = n.kind === "runway" ? 17 : n.kind === "gate" ? 13 : 15;
    return `<g class="map-node ${n.kind}" transform="translate(${n.x},${n.y})">
              <circle r="${radius}"/><text text-anchor="middle" y="4">${n.id}</text>
              <text text-anchor="middle" y="${n.kind === "gate" ? 27 : 30}" style="font-size:9px;fill:#8395b2">${esc(n.label)}</text>
            </g>`;
  }).join("");

  return `<div class="map-wrap"><svg viewBox="0 0 740 470" aria-label="Airport taxiway map">
            ${edges}${nodes}<text id="plane" font-size="22" x="-100" y="-100">✈</text></svg></div>
          <div class="map-legend"><span><i class="legend-dot" style="background:var(--cyan)"></i>Shortest path</span>
          <span><i class="legend-dot" style="background:var(--green)"></i>Gates</span>
          <span><i class="legend-dot" style="background:var(--amber)"></i>Services</span></div>`;
}

/* Slide the plane smoothly from node to node along the path. */
function animatePlane(graph, path) {
  const plane = $("#plane");
  if (!plane || path.length < 2) return;
  const points = path.map((id) => graph.nodes.find((n) => n.id === id));
  let segment = 0, progress = 0;
  function frame() {
    const a = points[segment], b = points[segment + 1];
    const x = a.x + (b.x - a.x) * progress, y = a.y + (b.y - a.y) * progress;
    plane.setAttribute("x", x - 10);
    plane.setAttribute("y", y + 7);
    progress += 0.03;
    if (progress >= 1) { segment++; progress = 0; }
    if (segment < points.length - 1) requestAnimationFrame(frame);
  }
  frame();
}

/* ------------------------------------------------------------ navigation */
async function render(page) {
  $("#page-title").textContent = PAGE_TITLES[page];
  document.querySelectorAll(".nav").forEach((n) => n.classList.toggle("active", n.dataset.page === page));
  $("#content").innerHTML = '<div class="loading">Running algorithm…</div>';
  const renderers = { overview: renderOverview, schedule: renderSchedule, queues: renderQueues,
                      runways: renderRunways, routes: renderRoutes, gates: renderGates };
  try {
    await renderers[page]();
  } catch (e) {
    $("#content").innerHTML = card("Something went wrong", `<p class="muted">${esc(e.message)}</p>`);
  }
}
document.querySelectorAll(".nav").forEach((n) => n.addEventListener("click", () => render(n.dataset.page)));

/* ------------------------------------------------------------ 1. overview */
async function renderOverview() {
  const d = await api("/api/overview?time=" + state.time);
  state.graph = d.graph;
  const arrivals = d.flights.filter((f) => f.type === "arrival").length;
  const alerts = [];
  if (d.conflicts) alerts.push(`<div class="alert">⚠ ${d.conflicts} gate double-booking(s) detected!</div>`);
  if (d.unassigned.length) alerts.push(`<div class="alert">⚠ No gate available for: ${d.unassigned.join(", ")}</div>`);
  if (!alerts.length) alerts.push('<div class="alert ok">✔ No gate conflicts. All flights have a gate.</div>');

  $("#content").innerHTML = `
    <div class="controls"><div class="field"><label>Airport status at</label>
      <input id="statusTime" type="time" value="${state.time}"></div></div>
    <div class="grid stats">
      ${stat("Total flights", d.total_flights, "✈", `${arrivals} arrivals · ${d.total_flights - arrivals} departures`)}
      ${stat("Free gates", `${d.free_gates.length}/${d.gates.length}`, "▣", d.free_gates.join(", ") || "None free")}
      ${stat("Emergency flights", d.emergency, "!", `${d.delayed} delayed flight(s)`)}
      ${stat("Next arrival", d.next_arrival ? d.next_arrival.expected : "—", "◷", d.next_arrival ? d.next_arrival.id : "No more arrivals")}
    </div>
    <div class="grid two">
      ${card("Airport surface map", drawMap(d.graph), tag("14 NODES · 24 TAXIWAYS", "green"))}
      ${card("Alerts", alerts.join("") + `<p class="muted">Delays and emergencies are handled on the Gate allocation and Landing queues pages.</p>`)}
    </div>
    <div class="section-gap"></div>
    ${card("All flight movements", flightTable(d.flights))}`;

  $("#statusTime").onchange = (event) => { state.time = event.target.value || "12:00"; renderOverview(); };
}

/* ------------------------------------------------------------ 2. schedule: sort, search, add */
async function renderSchedule() {
  const d = await api("/api/overview");
  $("#content").innerHTML = `
    ${info("Merge / Quick / Bubble sort · Linear / Binary search", "Merge &amp; Quick O(n log n), Bubble O(n²) · Linear O(n), Binary O(log n)", "Unit 1")}
    <div class="controls">
      <div class="field"><label>Sort algorithm</label><select id="sortAlgo">
        <option value="merge">Merge Sort</option><option value="quick">Quick Sort</option><option value="bubble">Bubble Sort</option></select></div>
      <div class="field"><label>Sort by</label><select id="sortBy">
        <option value="time">Time</option><option value="priority">Priority</option><option value="airline">Airline</option></select></div>
      <button class="btn" id="sortBtn">Run sort</button>
      <div class="field"><label>Search value</label><input id="query" placeholder="AF101 / 09:30"></div>
      <div class="field"><label>Search method</label><select id="searchKind">
        <option value="linear">Linear · flight ID</option><option value="airline">Linear · airline</option><option value="binary">Binary · exact time</option></select></div>
      <button class="btn secondary" id="searchBtn">Search</button>
    </div>
    <div id="sortStats"></div><div id="searchResult"></div>
    <div id="flightTable">${card("Flight schedule", flightTable(d.flights))}</div>
    <div class="section-gap"></div>
    ${card("Add a new flight", `
      <div class="form-grid">
        <div class="field"><label>Flight ID</label><input id="nId" placeholder="AF201" maxlength="8"></div>
        <div class="field"><label>Airline</label><input id="nAirline" placeholder="IndiGo" maxlength="25"></div>
        <div class="field"><label>Type</label><select id="nType"><option value="arrival">Arrival</option><option value="departure">Departure</option></select></div>
        <div class="field"><label>Time</label><input id="nTime" type="time" value="12:00"></div>
        <div class="field"><label>Gate time (min)</label><input id="nDuration" type="number" value="45" min="10" max="180"></div>
        <div class="field"><label>Passengers</label><input id="nPax" type="number" value="100" min="1" max="600"></div>
        <div class="field"><label>Priority</label><select id="nPriority"><option>normal</option><option>VIP</option><option>emergency</option></select></div>
        <div class="field"><label>&nbsp;</label><button class="btn" id="addBtn">Add flight</button></div>
      </div>`)}`;

  $("#sortBtn").onclick = () => attempt(async () => {
    const r = await api("/api/sort", { algorithm: $("#sortAlgo").value, by: $("#sortBy").value });
    $("#sortStats").innerHTML = card(r.algorithm.toUpperCase() + " SORT",
      `<div class="result-row"><span>Comparisons / time</span><b>${r.stats.comparisons} comparisons · ${r.stats.elapsed_ms.toFixed(3)} ms</b></div>${stepList(r.stats.steps)}`);
    $("#flightTable").innerHTML = card("Sorted schedule", flightTable(r.flights));
    toast("Flights sorted");
  });

  $("#searchBtn").onclick = () => attempt(async () => {
    const kind = $("#searchKind").value, query = $("#query").value.trim();
    if (!query) return toast("Enter a search value", true);
    const r = await api("/api/search", { kind: kind === "binary" ? "binary" : "linear", field: kind === "airline" ? "airline" : "id", query });
    const found = r.item ? `Found <b>${esc(r.item.id)}</b> · ${esc(r.item.airline)} · ${r.item.expected}` : "No matching flight found.";
    $("#searchResult").innerHTML = card("Search trace", `<p>${found} ${tag(r.checks + " checks", "blue")}</p>${stepList(r.steps)}`);
  });

  $("#addBtn").onclick = () => attempt(async () => {
    const r = await api("/api/flights", {
      id: $("#nId").value, airline: $("#nAirline").value, type: $("#nType").value,
      scheduled_time: $("#nTime").value, duration: $("#nDuration").value,
      passengers: $("#nPax").value, priority: $("#nPriority").value });
    toast(r.message);
    renderSchedule();
  });
}

/* ------------------------------------------------------------ 3. queues + emergency */
async function renderQueues() {
  const [q, o] = await Promise.all([api("/api/queues"), api("/api/overview")]);
  const rows = (list) => list.map((f, i) => `<tr><td>${i + 1}</td><td><b>${esc(f.id)}</b></td><td>${f.expected}</td><td>${priorityTag(f.priority)}</td></tr>`);
  const head = ["ORDER", "FLIGHT", "TIME", "PRIORITY"];

  $("#content").innerHTML = `
    ${info("FIFO queue + max-heap priority queue + Heap Sort", "Heap push/pop O(log n), Heap sort O(n log n)", "Unit 1 &amp; 2")}
    <div class="controls">
      <div class="field"><label>Declare emergency for</label><select id="emFlight">${o.flights.filter((f) => f.priority !== "emergency").map((f) => `<option>${f.id}</option>`).join("")}</select></div>
      <button class="btn warn" id="emBtn">Declare emergency</button></div>
    <div class="grid two">
      ${card("Landing queue · first come first served", table(head, rows(q.landing_fifo)))}
      ${card("Landing queue · priority (heap)", table(head, rows(q.landing_priority)))}
    </div>
    <div class="section-gap"></div>
    <div class="grid two">
      ${card("Take-off queue · priority (heap)", table(head, rows(q.takeoff_priority)))}
      ${card("Heap Sort · schedule by time", table(head, rows(q.heap_sorted.slice(0, 10))), tag("first 10", "blue"))}
    </div>`;

  $("#emBtn").onclick = () => attempt(async () => {
    const r = await api("/api/emergency", { flight_id: $("#emFlight").value });
    toast(r.message);
    renderQueues();
  });
}

/* ------------------------------------------------------------ 4. runway scheduler */
async function renderRunways() {
  $("#content").innerHTML = `
    ${info("Greedy scheduling with a priority queue (max-heap)", "O(F log F)", "Unit 2")}
    <div class="controls">
      <div class="field"><label>Runway busy time per movement (min)</label><input id="gap" type="number" value="10" min="1" max="180"></div>
      <button class="btn" id="gapBtn">Schedule runways</button></div>
    <div id="runwayResult"></div>`;

  const run = () => attempt(async () => {
    const r = await api("/api/runways", { gap: Number($("#gap").value) });
    const bars = (runway) => r.slots.filter((s) => s.runway === runway).map((s) => {
      const left = Math.max(0, (s.start - TIMELINE_START) / TIMELINE_SPAN * 100);
      const width = Math.max(2, (s.end - s.start) / TIMELINE_SPAN * 100);
      const cls = s.priority === "emergency" ? "emergency" : s.priority === "VIP" ? "vip" : "";
      return `<div class="bar ${cls}" style="left:${left}%;width:${width}%" title="${s.flight_id}"></div>`;
    }).join("");
    const lanes = r.runways.map((rw) => `<div class="time-row"><span class="time-label">${rw}</span><div class="track">${bars(rw)}</div></div>`).join("");
    const rows = r.slots.map((s) => `<tr><td><b>${s.flight_id}</b></td><td>${tag(s.runway, "blue")}</td>
        <td>${minutesToTime(s.start)}</td><td>${s.wait} min</td><td>${priorityTag(s.priority)}</td></tr>`);
    $("#runwayResult").innerHTML = `
      <div class="grid stats">${stat("Movements", r.slots.length, "✈", "all flights scheduled")}
        ${stat("Total waiting", r.total_wait + " min", "◷", "sum over all flights")}</div>
      ${card("Runway timeline (06:00 – 23:00)", `<div class="timeline">${lanes}</div>
        <p class="muted">Amber = VIP, red = emergency. Increase the busy time to create congestion and watch normal flights wait.</p>`)}
      <div class="section-gap"></div>
      ${card("Delays caused by runway congestion", stepList(r.steps.length ? r.steps : ["No flight had to wait."]))}
      <div class="section-gap"></div>
      ${card("Runway slots", table(["FLIGHT", "RUNWAY", "STARTS", "WAITED", "PRIORITY"], rows))}`;
  });
  $("#gapBtn").onclick = run;
  run();
}

/* ------------------------------------------------------------ 5. taxi routes */
async function renderRoutes() {
  const d = await api("/api/overview");
  state.graph = d.graph;
  const nodeOptions = (selected) => d.graph.nodes.map((n) => `<option ${n.id === selected ? "selected" : ""}>${n.id}</option>`).join("");

  $("#content").innerHTML = `
    ${info("Dijkstra shortest path · Floyd-Warshall · Warshall", "Dijkstra O(V²) · Floyd &amp; Warshall O(V³)", "Unit 2 &amp; 3")}
    <div class="grid two">
      ${card("Taxiway map", `<div id="mapBox">${drawMap(d.graph, state.path)}</div>`)}
      ${card("Find shortest taxi route", `
        <div class="controls"><div class="field"><label>Or pick a flight</label><select id="routeFlight"><option value="">— choose —</option>
          ${d.flights.map((f) => `<option value="${f.id}">${f.id} (${f.type})</option>`).join("")}</select></div></div>
        <div class="controls">
          <div class="field"><label>From</label><select id="routeStart">${nodeOptions("RW1")}</select></div>
          <div class="field"><label>To</label><select id="routeEnd">${nodeOptions("G1")}</select></div>
          <button class="btn" id="routeBtn">Calculate route</button></div>
        <div id="routeResult" class="result-list"></div>
        <div style="margin-top:14px"><button class="btn secondary" id="matrixBtn">Show all-pairs distances</button></div>
        <div id="matrixResult"></div>`)}
    </div>`;

  // Choosing a flight fills From/To: arrivals go runway -> gate, departures gate -> runway.
  $("#routeFlight").onchange = (event) => {
    const f = d.flights.find((x) => x.id === event.target.value);
    if (!f) return;
    $("#routeStart").value = f.type === "arrival" ? f.runway : f.gate;
    $("#routeEnd").value = f.type === "arrival" ? f.gate : f.runway;
  };

  $("#routeBtn").onclick = () => attempt(async () => {
    const r = await api("/api/route", { start: $("#routeStart").value, end: $("#routeEnd").value });
    state.path = r.path;
    $("#mapBox").innerHTML = drawMap(d.graph, r.path);
    animatePlane(d.graph, r.path);
    $("#routeResult").innerHTML = `
      <div class="result-row"><span>Shortest path</span><b>${r.path.join(" → ") || "No path"}</b></div>
      <div class="result-row"><span>Total taxi distance</span><b class="big-number">${r.distance ?? "—"} m</b></div>${stepList(r.steps)}`;
  });

  $("#matrixBtn").onclick = () => attempt(async () => {
    const m = await api("/api/matrices");
    const ids = m.floyd.nodes;
    const rows = ids.map((i) => `<tr><td><b>${i}</b></td>${ids.map((j) => `<td>${m.floyd.distances[i][j]}</td>`).join("")}</tr>`);
    const unreachable = ids.filter((i) => ids.some((j) => !m.warshall.reachability[i][j])).length;
    $("#matrixResult").innerHTML = `<h3 style="margin:16px 0 8px">Floyd-Warshall distances (m)</h3>
      ${table(["", ...ids], rows)}<p class="muted">Warshall reachability: ${unreachable === 0 ? "every node can reach every other node." : unreachable + " node(s) cannot reach everything."}</p>`;
  });
}

/* ------------------------------------------------------------ 6. gate allocation */
async function renderGates() {
  const [o, g] = await Promise.all([api("/api/overview"), api("/api/gates?time=12:00")]);
  const priorityOf = Object.fromEntries(o.flights.map((f) => [f.id, f.priority]));

  const lanes = g.gates.map((gate) => {
    const bars = g.assignments.filter((a) => a.gate === gate).map((a) => {
      const left = Math.max(0, (a.start - TIMELINE_START) / TIMELINE_SPAN * 100);
      const width = Math.max(4, (a.end - a.start) / TIMELINE_SPAN * 100);
      const cls = priorityOf[a.flight_id] === "emergency" ? "emergency" : priorityOf[a.flight_id] === "VIP" ? "vip" : "";
      return `<div class="bar ${cls}" style="left:${left}%;width:${width}%" title="${a.flight_id} ${minutesToTime(a.start)}-${minutesToTime(a.end)}">${a.flight_id}</div>`;
    }).join("");
    return `<div class="time-row"><span class="time-label">${gate}</span><div class="track">${bars}</div></div>`;
  }).join("");

  const status = g.conflicts.length
    ? `<div class="alert">⚠ Double-booking: ${g.conflicts.map((c) => c.join(" & ") + " at " + c[2]).join("; ")}</div>`
    : '<div class="alert ok">✔ No double-booking detected.</div>';
  const unassigned = g.unassigned.length ? `<div class="alert">No gate free for: ${g.unassigned.join(", ")}</div>` : "";
  const colorText = g.coloring.valid
    ? `All flights can be placed using only <b>${g.coloring.gates_used}</b> gate(s) (graph colouring with backtracking).`
    : "Graph colouring found no valid assignment with the available gates.";

  $("#content").innerHTML = `
    ${info("Greedy interval scheduling + graph colouring (backtracking)", "Greedy O(F log F + F·G·F) · Colouring O(G^F) worst case", "Unit 2 &amp; 3")}
    ${status}${unassigned}
    ${card("Gate occupancy timeline (06:00 – 23:00)", `<div class="timeline">${lanes}</div>
        <p class="muted">Amber = VIP, red = emergency. ${colorText}</p>`)}
    <div class="section-gap"></div>
    <div class="grid two">
      ${card("Free gates at a chosen time", `
        <div class="controls"><div class="field"><label>Time</label><input id="checkTime" type="time" value="12:00"></div>
        <button class="btn secondary" id="freeBtn">Check</button></div>
        <div class="result-row"><span>Free gates</span><b id="freeList">${g.free_now.join(", ") || "None"}</b></div>`)}
      ${card("Delay a flight", `
        <div class="controls">
          <div class="field"><label>Flight</label><select id="delayFlight">${o.flights.map((f) => `<option>${f.id}</option>`).join("")}</select></div>
          <div class="field"><label>Minutes</label><input id="delayMins" type="number" value="30" min="1" max="720"></div>
          <button class="btn" id="delayBtn">Apply delay</button>
          <button class="btn warn" id="resetBtn">Reset all</button></div>
        <div id="delayResult"></div>`)}
    </div>
    <div class="section-gap"></div>
    ${card("Current gate assignments", table(["FLIGHT", "GATE", "FROM", "UNTIL"],
        g.assignments.map((a) => `<tr><td><b>${a.flight_id}</b></td><td>${tag(a.gate, "blue")}</td><td>${minutesToTime(a.start)}</td><td>${minutesToTime(a.end)}</td></tr>`)))}`;

  $("#freeBtn").onclick = () => attempt(async () => {
    const r = await api("/api/gates?time=" + $("#checkTime").value);
    $("#freeList").textContent = r.free_now.join(", ") || "None";
  });

  $("#delayBtn").onclick = () => attempt(async () => {
    const r = await api("/api/delay", { flight_id: $("#delayFlight").value, minutes: Number($("#delayMins").value) });
    toast(r.message);
    await renderGates();
    $("#delayResult").innerHTML = `<div class="info"><strong>${esc(r.message)}</strong>
      <div>Gate changes: ${r.changes.length ? r.changes.join(" · ") : "none, every flight kept its gate"}</div></div>`;
  });

  $("#resetBtn").onclick = () => attempt(async () => {
    toast((await api("/api/reset", {})).message);
    renderGates();
  });
}

/* ------------------------------------------------------------ start */
setInterval(() => { $("#clock").textContent = new Date().toLocaleTimeString(); }, 1000);
render("overview");
