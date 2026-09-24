// Shared helpers for all pages. Plain JS, no libraries.

const CFG = window.PICKEM_CONFIG || {};
const TZ = "America/Los_Angeles";

function isConfigured() {
  return CFG.supabaseUrl && !CFG.supabaseUrl.includes("YOUR-PROJECT");
}

async function api(path, options = {}) {
  const res = await fetch(`${CFG.supabaseUrl}/rest/v1/${path}`, {
    ...options,
    headers: {
      apikey: CFG.supabaseAnonKey,
      Authorization: `Bearer ${CFG.supabaseAnonKey}`,
      "Content-Type": "application/json",
    },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error((body && body.message) || `Request failed (${res.status})`);
  return body;
}

function rpc(name, args) {
  return api(`rpc/${name}`, { method: "POST", body: JSON.stringify(args) });
}

// ---------- Player token (from ?t=, remembered on this device) ----------

function getToken() {
  const fromUrl = new URLSearchParams(location.search).get("t");
  try {
    if (fromUrl) localStorage.setItem("pickem_token", fromUrl);
    return fromUrl || localStorage.getItem("pickem_token");
  } catch {
    return fromUrl;
  }
}

// ---------- Data ----------

async function loadTeams() {
  const rows = await api("teams?select=id,abbreviation,name,full_name");
  return Object.fromEntries(rows.map((t) => [t.id, t]));
}

async function loadWeeks() {
  return api("weeks?select=id,season,week_num,start_date,end_date,is_test&order=start_date.asc,id.asc");
}

async function loadSlateGames(weekId) {
  const links = await api(`slate_games?select=game_id&week_id=eq.${weekId}`);
  if (!links.length) return [];
  const ids = links.map((l) => l.game_id).join(",");
  return api(`games?id=in.(${ids})&order=tipoff_utc.asc,id.asc`);
}

async function loadPlayers() {
  return api("players_public?select=id,display_name&order=display_name.asc");
}

// ---------- Dates & weeks ----------

function todayPT() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date()); // YYYY-MM-DD
}

// Latest week that has started; before any has started, the first one.
function currentWeek(weeks) {
  const today = todayPT();
  const started = weeks.filter((w) => w.start_date <= today);
  return started[started.length - 1] || weeks[0] || null;
}

function weekLabel(w) {
  const fmt = (d) => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${w.is_test ? "Test week" : "Week"} ${w.week_num} · ${fmt(w.start_date)}–${fmt(w.end_date)}`;
}

function tipoffLabel(game) {
  if (!game.tipoff_utc) return "Time TBD";
  return new Date(game.tipoff_utc).toLocaleString("en-US", {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

// ---------- Game state ----------

function isLocked(game) {
  return !game.tipoff_utc || Date.now() >= Date.parse(game.tipoff_utc) || game.status !== "scheduled";
}

function winnerId(game) {
  if (game.status !== "final") return null;
  return game.home_score > game.away_score ? game.home_team_id : game.away_team_id;
}

function statusLabel(game) {
  if (game.status === "final") return "Final";
  if (game.status === "postponed") return "Postponed — no points";
  if (game.status === "in_progress") return "Live · locked";
  return isLocked(game) ? "Locked" : "Open";
}

// ---------- Rendering helpers ----------

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function showNotice(el, html, isError = false) {
  el.innerHTML = `<div class="notice${isError ? " error" : ""}">${html}</div>`;
}

// Returns false (and shows a notice) if the site isn't wired to Supabase yet.
function requireConfig(el) {
  if (isConfigured()) return true;
  showNotice(el, "<strong>Not connected yet.</strong> The database is still being set up. Check back soon.");
  return false;
}

function rankRows(rows) {
  // Standard competition ranking: 1, 2, 2, 4.
  let rank = 0;
  return rows.map((r, i) => {
    if (i === 0 || r.points !== rows[i - 1].points) rank = i + 1;
    return { ...r, rank };
  });
}
