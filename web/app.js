// web/app.js

// ---------- State ----------
const state = {
    me: null,
    universe: null,
    modules: null,

    page: "news",
    selectedStationId: null,
};

// ---------- Helpers ----------
function setActiveTab(page) {
    document.querySelectorAll(".tab").forEach(t => {
        t.classList.toggle("active", t.dataset.page === page);
    });
}

function fmt(n) {
    if (typeof n !== "number") return String(n);
    return n.toFixed(2);
}

function el(html) {
    const d = document.createElement("div");
    d.innerHTML = html.trim();
    return d.firstChild;
}

async function apiGet(path) {
    const r = await fetch(path);
    const data = await r.json().catch(() => null);
    if (!r.ok) throw new Error((data && data.detail) ? data.detail : `HTTP ${r.status}`);
    return data;
}

async function apiPost(path, body) {
    const r = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body ?? {}),
    });
    const data = await r.json().catch(() => null);
    if (!r.ok) throw new Error((data && data.detail) ? data.detail : `HTTP ${r.status}`);
    return data;
}

function getStations() {
    return state.universe?.universe?.stations ?? [];
}

function getSelectedStation() {
    const sts = getStations();
    if (!sts.length) return null;
    if (state.selectedStationId == null) state.selectedStationId = sts[0].id;
    return sts.find(s => s.id === state.selectedStationId) || sts[0];
}

function computeDerivedFromStation(st) {
    // Uses station.derived if server already provided it.
    // If missing (shouldn't be), returns a safe default.
    const d = st?.derived;
    if (!d) {
        return {
            caps: { slot_cap: 0, power_cap: 0, crew_cap: 0 },
            usage: { slots_used: 0, power_used: 0, crew_used: 0 },
        };
    }
    return d;
}

function previewInstall(st, moduleDef) {
    // Returns a "preview" of caps/usage AFTER adding moduleDef,
    // without changing anything.
    const d = computeDerivedFromStation(st);

    // Clone caps + usage so we can modify them
    const caps = JSON.parse(JSON.stringify(d.caps || {}));
    const usage = JSON.parse(JSON.stringify(d.usage || {}));

    // Effects add to caps
    const effects = moduleDef.effects || {};
    for (const [k, v] of Object.entries(effects)) {
        caps[k] = (Number(caps[k] || 0) + Number(v));
    }

    // Usage changes
    // power_used is increased by negative power_delta (consumption)
    const pd = Number(moduleDef.power_delta || 0);
    if (pd < 0) usage.power_used = Number(usage.power_used || 0) + (-pd);

    usage.crew_used = Number(usage.crew_used || 0) + Number(moduleDef.crew_required || 0);
    usage.slots_used = Number(usage.slots_used || 0) + Number(moduleDef.slot_cost || 0);

    return { caps, usage };
}

function checkBudget(preview) {
    // Returns { ok: boolean, problems: string[] }
    const caps = preview.caps || {};
    const usage = preview.usage || {};

    const problems = [];

    const slotsUsed = Number(usage.slots_used || 0);
    const slotsCap = Number(caps.slot_cap || 0);
    if (slotsUsed > slotsCap + 1e-9) problems.push(`Slots: ${fmt(slotsUsed)} / ${fmt(slotsCap)}`);

    const crewUsed = Number(usage.crew_used || 0);
    const crewCap = Number(caps.crew_cap || 0);
    if (crewUsed > crewCap + 1e-9) problems.push(`Crew: ${fmt(crewUsed)} / ${fmt(crewCap)}`);

    const powerUsed = Number(usage.power_used || 0);
    const powerCap = Number(caps.power_cap || 0);
    if (powerUsed > powerCap + 1e-9) problems.push(`Power: ${fmt(powerUsed)} / ${fmt(powerCap)}`);

    return { ok: problems.length === 0, problems };
}

// ---------- Account UI ----------
function renderAccount() {
    const area = document.getElementById("accountArea");
    area.innerHTML = "";

    if (!state.me || !state.me.user_id) {
        area.appendChild(el(`<a class="btn" href="/login">Login</a>`));
        area.appendChild(el(`<a class="btn btn-primary" href="/register">Register</a>`));
        return;
    }

    area.appendChild(el(`<div class="muted">Welcome, <strong style="color:var(--text)">${state.me.username}</strong></div>`));
    const logout = el(`<button class="btn btn-danger">Logout</button>`);
    logout.onclick = async () => {
        await fetch("/api/logout", { method: "POST" });
        location.href = "/login";
    };
    area.appendChild(logout);
}

// ---------- Rendering ----------
function render() {
    setActiveTab(state.page);

    // top-right button in main header
    const ensureBtn = document.getElementById("ensureStationBtn");
    ensureBtn.style.display = (state.me && state.me.user_id) ? "inline-flex" : "none";

    if (state.page === "news") renderNews();
    else if (state.page === "universe") renderUniverse();
    else if (state.page === "stations") renderStations();
    else if (state.page === "modules") renderModules();
    else renderPlaceholder(state.page);
}

function renderPlaceholder(page) {
    const title = page[0].toUpperCase() + page.slice(1);

    document.getElementById("sideTitle").textContent = title;
    document.getElementById("sideSub").textContent = "Coming soon";
    document.getElementById("sideBody").innerHTML = `<div class="muted">No data yet.</div>`;

    document.getElementById("mainTitle").textContent = title;
    document.getElementById("mainSub").textContent = "Placeholder";
    document.getElementById("mainBody").innerHTML = `<div class="muted">We’ll build this panel later.</div>`;
}

function renderNews() {
    document.getElementById("sideTitle").textContent = "News Feed";
    document.getElementById("sideSub").textContent = "Patch notes & universe headlines";

    const items = [
        { title: "Patch v0.1", body: "Modules + derived station stats now visible in UI." },
        { title: "Universe", body: "Sol belts discovered: Inner Belt, Outer Belt." },
        { title: "Rumor", body: "Trader factions will arrive later (AI placeholder)." },
    ];

    const side = document.getElementById("sideBody");
    side.innerHTML = "";
    const list = document.createElement("div");
    list.className = "list";
    items.forEach(it => {
        list.appendChild(el(`
      <div class="list-item">
        <div class="name">${it.title}</div>
        <div class="meta">${it.body}</div>
      </div>
    `));
    });
    side.appendChild(list);

    const u = state.universe?.universe;
    document.getElementById("mainTitle").textContent = "Welcome";
    document.getElementById("mainSub").textContent = "Universe-first station game (dev)";

    const stationCount = u?.stations?.length ?? 0;
    const bodyCount = u?.bodies?.length ?? 0;
    const moduleCount = state.modules?.modules?.length ?? 0;

    document.getElementById("mainBody").innerHTML = `
    <div class="kvs">
      <div class="kv"><div class="k">Sim Time</div><div class="v">${u ? fmt(u.sim_time) : "—"}</div></div>
      <div class="kv"><div class="k">Stations</div><div class="v">${stationCount}</div></div>
      <div class="kv"><div class="k">Bodies</div><div class="v">${bodyCount}</div></div>
      <div class="kv"><div class="k">Modules Defined</div><div class="v">${moduleCount}</div></div>
    </div>
    <div style="height:12px"></div>
    <div class="muted">Tip: go to <strong>Modules</strong> and install modules (debug) to test station stats.</div>
  `;
}

function renderUniverse() {
    document.getElementById("sideTitle").textContent = "Universe";
    document.getElementById("sideSub").textContent = "Systems, bodies, and global state";

    const bodies = state.universe?.universe?.bodies ?? [];
    const side = document.getElementById("sideBody");
    side.innerHTML = "";

    if (!bodies.length) {
        side.innerHTML = `<div class="muted">No bodies found.</div>`;
    } else {
        const list = document.createElement("div");
        list.className = "list";
        bodies.forEach(b => {
            list.appendChild(el(`
        <div class="list-item">
          <div class="name">${b.name}</div>
          <div class="meta">${b.system} • ${b.type}</div>
        </div>
      `));
        });
        side.appendChild(list);
    }

    document.getElementById("mainTitle").textContent = "Universe Snapshot";
    document.getElementById("mainSub").textContent = "Debug view";
    document.getElementById("mainBody").innerHTML = `<pre>${JSON.stringify(state.universe, null, 2)}</pre>`;
}

function renderStations() {
    document.getElementById("sideTitle").textContent = "Stations";
    document.getElementById("sideSub").textContent = "Select a station to view details";

    const stations = getStations();
    const side = document.getElementById("sideBody");
    side.innerHTML = "";

    if (!stations.length) {
        side.innerHTML = `
      <div class="muted">No stations yet.</div>
      <div style="height:10px"></div>
      <div class="muted">Use “Ensure Player Station” to create your first station.</div>
    `;
        document.getElementById("mainTitle").textContent = "Stations";
        document.getElementById("mainSub").textContent = "You don’t own any stations yet.";
        document.getElementById("mainBody").innerHTML = `<div class="muted">Create a station to begin.</div>`;
        return;
    }

    if (state.selectedStationId == null) state.selectedStationId = stations[0].id;

    const list = document.createElement("div");
    list.className = "list";
    stations.forEach(s => {
        const active = (s.id === state.selectedStationId);
        const li = el(`
      <div class="list-item ${active ? "active" : ""}">
        <div class="name">${s.name}</div>
        <div class="meta">System: ${s.system} • Modules: ${(s.modules || []).length}</div>
      </div>
    `);
        li.onclick = () => { state.selectedStationId = s.id; renderStations(); };
        list.appendChild(li);
    });
    side.appendChild(list);

    const st = getSelectedStation();
    const d = st?.derived;
    const caps = d?.caps ?? {};
    const usage = d?.usage ?? {};

    document.getElementById("mainTitle").textContent = st.name;
    document.getElementById("mainSub").textContent = `System: ${st.system} • Credits: ${fmt(st.credits)}`;

    document.getElementById("mainBody").innerHTML = `
    <div class="kvs">
      <div class="kv"><div class="k">Power</div><div class="v">${fmt(usage.power_used)} / ${fmt(caps.power_cap)}</div></div>
      <div class="kv"><div class="k">Crew</div><div class="v">${fmt(usage.crew_used)} / ${fmt(caps.crew_cap)}</div></div>
      <div class="kv"><div class="k">Slots</div><div class="v">${fmt(usage.slots_used)} / ${fmt(caps.slot_cap)}</div></div>
      <div class="kv"><div class="k">Cargo Cap</div><div class="v">${fmt(caps.cargo_cap)}</div></div>
      <div class="kv"><div class="k">Dock Cap</div><div class="v">${fmt(caps.dock_cap)}</div></div>
      <div class="kv"><div class="k">Defense</div><div class="v">${fmt(caps.defense)}</div></div>
      <div class="kv"><div class="k">Scan Level</div><div class="v">${fmt(caps.scan_level)}</div></div>
    </div>

    <div style="height:12px"></div>
    <div class="row">
      <span class="pill">Installed Modules: <strong style="color:var(--text)">${(st.modules || []).length}</strong></span>
    </div>

    <div style="height:10px"></div>
    <pre>${JSON.stringify(st.modules || [], null, 2)}</pre>
  `;
}

function renderModules() {
    document.getElementById("sideTitle").textContent = "Modules";
    document.getElementById("sideSub").textContent = "Browse module definitions (data-only)";

    const stations = getStations();
    const st = getSelectedStation();

    // Side panel: pick a station (so installs know where to go)
    const side = document.getElementById("sideBody");
    side.innerHTML = "";

    if (!stations.length) {
        side.innerHTML = `
      <div class="muted">No stations available.</div>
      <div style="height:10px"></div>
      <div class="muted">Create a station first using “Ensure Player Station”.</div>
    `;
    } else {
        const list = document.createElement("div");
        list.className = "list";
        stations.forEach(s => {
            const active = (s.id === state.selectedStationId);
            const li = el(`
        <div class="list-item ${active ? "active" : ""}">
          <div class="name">${s.name}</div>
          <div class="meta">Modules: ${(s.modules || []).length}</div>
        </div>
      `);
            li.onclick = () => { state.selectedStationId = s.id; renderModules(); };
            list.appendChild(li);
        });
        side.appendChild(list);
    }

    // Main panel: module table
    document.getElementById("mainTitle").textContent = "Module Browser";
    document.getElementById("mainSub").textContent = st
        ? `Selected Station: ${st.name}`
        : "Create/select a station to install modules (debug)";

    let budgetHtml = `<div class="muted" style="margin-bottom:10px;">Select a station to see budgets.</div>`;
    if (st && st.derived) {
        const caps = st.derived.caps;
        const usage = st.derived.usage;

        const powerOk = usage.power_used <= caps.power_cap + 1e-9;
        const crewOk = usage.crew_used <= caps.crew_cap + 1e-9;
        const slotsOk = usage.slots_used <= caps.slot_cap + 1e-9;

        budgetHtml = `
    <div class="row" style="margin-bottom:10px;">
      <span class="pill">Power: <strong style="color:${powerOk ? "var(--text)" : "var(--danger)"}">${fmt(usage.power_used)} / ${fmt(caps.power_cap)}</strong></span>
      <span class="pill">Crew: <strong style="color:${crewOk ? "var(--text)" : "var(--danger)"}">${fmt(usage.crew_used)} / ${fmt(caps.crew_cap)}</strong></span>
      <span class="pill">Slots: <strong style="color:${slotsOk ? "var(--text)" : "var(--danger)"}">${fmt(usage.slots_used)} / ${fmt(caps.slot_cap)}</strong></span>
    </div>
  `;
    }


    const mods = state.modules?.modules ?? [];

    if (!mods.length) {
        document.getElementById("mainBody").innerHTML = `<div class="muted">No module definitions loaded.</div>`;
        return;
    }

    // Build a fast lookup of installed modules for the selected station
    const installed = new Set((st?.modules ?? []).map(String));

    const rows = mods.map(m => {
        const isInstalled = installed.has(m.id);
        const costEntries = Object.entries(m.cost || {});
        const costText = costEntries.length
            ? costEntries.map(([k, v]) => `${k} x${v}`).join(", ")
            : "—";

        const effectsEntries = Object.entries(m.effects || {});
        const effectsText = effectsEntries.length
            ? effectsEntries.map(([k, v]) => `${k} ${v >= 0 ? "+" : ""}${v}`).join(", ")
            : "—";

        const actionBtn = (!st)
            ? `<span class="muted">—</span>`
            : isInstalled
                ? `<button class="btn btn-danger" data-action="remove" data-mid="${m.id}">Remove</button>`
                : `<button class="btn btn-primary" data-action="add" data-mid="${m.id}">Install (debug)</button>`;

        return `
      <tr>
        <td><strong>${m.name}</strong><div class="muted" style="font-size:12px;">${m.id}</div></td>
        <td><span class="pill">${m.category}</span></td>
        <td>${m.power_delta >= 0 ? `+${m.power_delta}` : `${m.power_delta}`}</td>
        <td>${m.crew_required}</td>
        <td>${m.slot_cost}</td>
        <td>${m.build_time}s</td>
        <td class="muted">${costText}</td>
        <td class="muted">${effectsText}</td>
        <td>${actionBtn}</td>
      </tr>
    `;
    }).join("");

    document.getElementById("mainBody").innerHTML = `
    ${budgetHtml}
    <div class="muted" style="margin-bottom:10px;">
      This page is for testing. “Install (debug)” directly adds the module to your station (no build queue yet).
    </div>
    <table class="table" id="modulesTable">
      <thead>
        <tr>
          <th>Module</th>
          <th>Category</th>
          <th>Power Δ</th>
          <th>Crew</th>
          <th>Slots</th>
          <th>Build</th>
          <th>Cost</th>
          <th>Effects</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

    // Wire up button clicks (event delegation)
    const table = document.getElementById("modulesTable");
    table.onclick = async (ev) => {
        const btn = ev.target.closest("button[data-action]");
        if (!btn) return;
        if (!st) return;

        const action = btn.dataset.action;
        const mid = btn.dataset.mid;

        try {
            if (action === "add") {
                // Find module definition for mid
                const moduleDef = (mods || []).find(x => x.id === mid);
                if (!moduleDef) {
                    alert("Unknown module: " + mid);
                    return;
                }

                // Preview install
                const preview = previewInstall(st, moduleDef);
                const check = checkBudget(preview);

                if (!check.ok) {
                    alert(
                        "Cannot install module (over budget):\n\n" +
                        check.problems.map(p => "• " + p).join("\n")
                    );
                    return;
                }

                await apiPost(`/api/debug/stations/${st.id}/modules/add`, { module_id: mid });
            } else {
                await apiPost(`/api/debug/stations/${st.id}/modules/remove`, { module_id: mid });
            }
            await refreshAll();
            state.page = "modules";
            render();
        } catch (e) {
            alert("Module action failed: " + e.message);
        }
    };
}

// ---------- Data Loading ----------
async function refreshAll() {
    document.getElementById("sideBody").innerHTML = `<div class="muted">Loading…</div>`;
    document.getElementById("mainBody").innerHTML = `<div class="muted">Loading…</div>`;

    try { state.me = await apiGet("/api/me"); }
    catch { state.me = { ok: true, user_id: null, username: null }; }

    renderAccount();

    try { state.universe = await apiGet("/api/universe"); }
    catch { state.universe = null; }

    try { state.modules = await apiGet("/api/modules"); }
    catch { state.modules = null; }

    // Keep selected station valid after refresh
    const stations = getStations();
    if (stations.length && state.selectedStationId == null) {
        state.selectedStationId = stations[0].id;
    }
    if (stations.length && state.selectedStationId != null) {
        const exists = stations.some(s => s.id === state.selectedStationId);
        if (!exists) state.selectedStationId = stations[0].id;
    }

    render();
}

// ---------- Events ----------
document.getElementById("tabs").onclick = (ev) => {
    const t = ev.target.closest(".tab");
    if (!t) return;
    state.page = t.dataset.page;
    render();
};

document.getElementById("refreshBtn").onclick = refreshAll;

document.getElementById("ensureStationBtn").onclick = async () => {
    try {
        await apiPost("/api/universe/ensure_player_station", {});
        await refreshAll();
        state.page = "stations";
        render();
    } catch (e) {
        alert("Ensure station failed: " + e.message);
    }
};

// ---------- Boot ----------
refreshAll();
