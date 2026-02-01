// web/app.js

// ---------- State ----------
const state = {
    me: null,
    universe: null,
    modules: null,
    myStations: [],

    page: "news",
    selectedStationId: null,
};

// ---------- Build polling ----------
let buildPollTimer = null;

// ---------- Helpers ----------
function setActiveTab(page) {
    document.querySelectorAll(".tab").forEach(t => {
        t.classList.toggle("active", t.dataset.page === page);
    });
}

function fmt(n) {
    if (typeof n !== "number" || Number.isNaN(n)) return String(n);
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
    return state.myStations ?? [];
}

function getSelectedStation() {
    const sts = getStations();
    if (!sts.length) return null;
    if (state.selectedStationId == null) state.selectedStationId = sts[0].id;
    return sts.find(s => s.id === state.selectedStationId) || sts[0];
}

function getSimTime() {
    const u = state.universe?.universe;
    const t = u?.sim_time;
    return (typeof t === "number" && !Number.isNaN(t)) ? t : 0;
}

function computeDerivedFromStation(st) {
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
    const d = computeDerivedFromStation(st);

    const caps = JSON.parse(JSON.stringify(d.caps || {}));
    const usage = JSON.parse(JSON.stringify(d.usage || {}));

    const effects = moduleDef.effects || {};
    for (const [k, v] of Object.entries(effects)) {
        caps[k] = (Number(caps[k] || 0) + Number(v));
    }

    const pd = Number(moduleDef.power_delta || 0);
    if (pd < 0) usage.power_used = Number(usage.power_used || 0) + (-pd);

    usage.crew_used = Number(usage.crew_used || 0) + Number(moduleDef.crew_required || 0);
    usage.slots_used = Number(usage.slots_used || 0) + Number(moduleDef.slot_cost || 0);

    return { caps, usage };
}

function checkBudget(preview) {
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

/**
 * Find an active/pending build event for a station by scanning /api/universe events.
 *
 * Supports both shapes:
 *  - Option A (recommended): { id, time, type:"build_module_complete", data:{station_id,module_id} }
 *  - Older variant:          { id, fires_at, type:"build_module", data:{station_id,module_id} }
 */
function findPendingBuildForStation(stationId) {
    const events = state.universe?.universe?.events;
    if (!Array.isArray(events) || !stationId) return null;

    const candidates = [];
    for (const ev of events) {
        if (!ev || typeof ev !== "object") continue;

        const type = String(ev.type || "");
        const data = ev.data && typeof ev.data === "object" ? ev.data : {};
        const sid = Number(data.station_id ?? data.stationId ?? -1);

        if (sid !== Number(stationId)) continue;

        const isBuild =
            type === "build_module_complete" || // Option A
            type === "build_module";            // older

        if (!isBuild) continue;

        const finishesAt =
            (typeof ev.time === "number" ? ev.time : null) ??
            (typeof ev.fires_at === "number" ? ev.fires_at : null) ??
            (typeof ev.firesAt === "number" ? ev.firesAt : null);

        if (typeof finishesAt !== "number") continue;

        candidates.push({
            event_id: Number(ev.id ?? 0),
            type,
            module_id: String(data.module_id ?? data.moduleId ?? ""),
            finishes_at: finishesAt,
        });
    }

    if (!candidates.length) return null;

    // Choose the soonest finishing build (in case old data exists)
    candidates.sort((a, b) => a.finishes_at - b.finishes_at);
    return candidates[0];
}

function startBuildPolling() {
    if (buildPollTimer) return;
    buildPollTimer = setInterval(async () => {
        // Only poll while user is on Modules page (keeps noise down)
        if (state.page !== "modules") return;
        try {
            await refreshAll();
        } catch {
            // ignore polling errors
        }
    }, 2000);
}

function stopBuildPolling() {
    if (buildPollTimer) {
        clearInterval(buildPollTimer);
        buildPollTimer = null;
    }
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
        { title: "Patch v0.1", body: "Build queue now supported (one build at a time)." },
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

    const stationCount = getStations().length;
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
      <div class="muted">Tip: go to <strong>Modules</strong> and queue a build to test the build timer + install completion.</div>
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
    document.getElementById("sideSub").textContent = "Build modules (queue-based)";

    const stations = getStations();
    const st = getSelectedStation();

    // Side panel: pick a station
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

    // Main panel
    document.getElementById("mainTitle").textContent = "Module Browser";
    document.getElementById("mainSub").textContent = st
        ? `Selected Station: ${st.name}`
        : "Create/select a station to queue builds";

    const mods = state.modules?.modules ?? [];
    if (!mods.length) {
        document.getElementById("mainBody").innerHTML = `<div class="muted">No module definitions loaded.</div>`;
        stopBuildPolling();
        return;
    }

    // Budget pills
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

    // Pending build banner
    const simTime = getSimTime();
    const pending = st ? findPendingBuildForStation(st.id) : null;
    const busy = !!pending;

    let buildBanner = "";
    if (st && pending) {
        const remaining = Math.max(0, pending.finishes_at - simTime);
        const mm = Math.floor(remaining / 60);
        const ss = Math.floor(remaining % 60);
        const remText = `${mm}:${String(ss).padStart(2, "0")}`;

        // Find module display name
        const def = mods.find(x => x.id === pending.module_id);
        const modName = def ? def.name : pending.module_id;

        buildBanner = `
          <div class="row" style="margin-bottom:10px;">
            <span class="pill">
              🏗️ Build in progress:
              <strong style="color:var(--text)">${modName}</strong>
              <span class="muted">• completes in</span>
              <strong style="color:var(--text)">${remText}</strong>
            </span>
            <span class="pill muted">event_id: ${pending.event_id}</span>
          </div>
          <div class="muted" style="margin-bottom:10px;">
            One build at a time. Build buttons are disabled until the current build completes.
          </div>
        `;
    }

    if (busy && state.page === "modules") startBuildPolling();
    if (!busy) stopBuildPolling();

    // Installed lookup
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
                : `<button class="btn btn-primary" data-action="build" data-mid="${m.id}" ${busy ? "disabled" : ""}>Build</button>`;

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
      ${buildBanner}
      <div class="muted" style="margin-bottom:10px;">
        Queue builds using <strong>Build</strong>. When the timer finishes, the module installs automatically (server-side).
        <br/>
        <span class="muted">Remove is still “debug” for now.</span>
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

    // Click handling
    const table = document.getElementById("modulesTable");
    table.onclick = async (ev) => {
        const btn = ev.target.closest("button[data-action]");
        if (!btn) return;
        if (!st) return;

        const action = btn.dataset.action;
        const mid = btn.dataset.mid;

        try {
            if (action === "build") {
                if (busy) {
                    alert("Build already in progress for this station.");
                    return;
                }

                const moduleDef = (mods || []).find(x => x.id === mid);
                if (!moduleDef) {
                    alert("Unknown module: " + mid);
                    return;
                }

                // Local preview check (server will enforce too)
                const preview = previewInstall(st, moduleDef);
                const check = checkBudget(preview);
                if (!check.ok) {
                    alert(
                        "Cannot build module (over budget after install):\n\n" +
                        check.problems.map(p => "• " + p).join("\n")
                    );
                    return;
                }

                await apiPost(`/api/stations/${st.id}/build/module`, { module_id: mid });
            }
            else if (action === "remove") {
                await apiPost(`/api/debug/stations/${st.id}/modules/remove`, { module_id: mid });
            }

            await refreshAll();
            state.page = "modules";
            render();
        } catch (e) {
            // Map common server errors to nicer messages
            const msg = (e && e.message) ? e.message : String(e);

            if (msg === "station_busy" || msg === "build_in_progress") {
                alert("That station is already building something (one build at a time).");
                return;
            }
            if (msg.startsWith("over_budget")) {
                alert("Cannot build: would exceed station limits.\n\n" + msg);
                return;
            }
            if (msg === "insufficient_materials") {
                alert("Not enough materials to pay the module cost.");
                return;
            }

            alert("Action failed: " + msg);
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

    state.myStations = [];

    if (state.me && state.me.user_id) {
        // Optional: auto-ensure station on load
        try { await apiPost("/api/universe/ensure_player_station", {}); }
        catch { /* ignore */ }

        try {
            const r = await apiGet("/api/my/stations");
            state.myStations = r.stations || [];
        } catch {
            state.myStations = [];
        }
    }

    // Keep selected station valid after refresh
    const stations = getStations();
    if (stations.length && state.selectedStationId == null) {
        state.selectedStationId = stations[0].id;
    }
    if (stations.length && state.selectedStationId != null) {
        const exists = stations.some(s => s.id === state.selectedStationId);
        if (!exists) state.selectedStationId = stations[0].id;
    }

    // If we are NOT on modules page, stop polling (keeps things quiet)
    if (state.page !== "modules") stopBuildPolling();

    render();
}

// ---------- Events ----------
document.getElementById("tabs").onclick = (ev) => {
    const t = ev.target.closest(".tab");
    if (!t) return;
    state.page = t.dataset.page;

    // Stop polling when leaving modules
    if (state.page !== "modules") stopBuildPolling();

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
