// Vernetzte Vormoderne — shared helpers, search, person page, map. No build step.
const SRC = { ssrq: "SSRQ", kf: "Königsfelden", sg: "SG Missiven", thun: "Thun Missiven", bullinger: "Bullinger" };
const ORDER = ["ssrq", "kf", "sg", "thun", "bullinger"];
const ID_URL = {
  hls: (v) => `https://hls-dhs-dss.ch/de/articles/${v}/`,
  gnd: (v) => `https://d-nb.info/gnd/${v}`,
  wikidata: (v) => `https://www.wikidata.org/wiki/${v}`,
  ssrq: (v) => `https://www.ssrq-sds-fds.ch/persons-db-edit/?query=${v}`,
  bullinger: (v) => `https://www.bullinger-digital.ch/persons/${v}`,
  dodis: (v) => `https://dodis.ch/${v}`,
  histhub: (v) => `https://data.histhub.ch/person/${v}`,
  viaf: (v) => `https://viaf.org/viaf/${v}`,
  geonames: (v) => `https://www.geonames.org/${v}`,
};
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const years = (y) => (!y ? "" : y[0] === y[1] ? `${y[0]}` : `${y[0]}–${y[1]}`);
const chips = (srcs) => srcs.map((s) => `<span class="chip ${s}" title="${SRC[s] || s}">${esc((SRC[s] || s).split(" ")[0])}</span>`).join("");

// the same folding as vv/common.py fold(): the index files are keyed by its first letter
function fold(s) {
  s = (s || "").replace(/ſ/g, "s").replace(/ß/g, "ss").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  s = s.replace(/[^a-z ]+/g, " ");
  for (const [a, b] of [["tz", "z"], ["th", "t"], ["ck", "k"], ["dt", "t"], ["ph", "f"], ["y", "i"], ["j", "i"], ["v", "u"],
    ["w", "u"], ["z", "s"], ["c", "k"]]) s = s.split(a).join(b);
  return s.replace(/(.)\1+/g, "$1").replace(/\s+/g, " ").trim();
}
async function json(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

// ------------------------------------------------------------------ start page: stats and search
async function startPage() {
  const st = await json("data/stats.json");
  const p = st.persons;
  $("#tiles").innerHTML = [
    [p.joint.toLocaleString("de-CH"), "Personen im gemeinsamen Index"],
    [p.joint_several_sources.toLocaleString("de-CH"), "davon in mehreren Quellen"],
    [st.bios.toLocaleString("de-CH"), "Kurzbiografien"],
    [st.map_places.toLocaleString("de-CH"), "Orte auf der Karte"],
  ].map(([n, t]) => `<div class="tile"><b>${n}</b><span>${t}</span></div>`).join("");
  $("#sources").innerHTML = ORDER.map((k) => {
    const s = st.sources[k];
    return `<li>${chips([k])} <a href="${esc(s.site)}">${esc(s.title)}</a> <span class="small">· ${(st.persons_by_source[k] || 0).toLocaleString("de-CH")} Personen · ${esc(s.license)}</span></li>`;
  }).join("");
  $("#filters").innerHTML = ORDER.map((k) => `<label><input type="checkbox" name="src" value="${k}" checked> ${SRC[k]}</label>`).join("")
    + `<label><input type="checkbox" id="multi"> nur in mehreren Quellen</label><label><input type="checkbox" id="withbio"> mit Biografie</label>`;
  const cache = {};
  const q = $("#q");
  let timer;
  async function search() {
    const term = fold(q.value);
    const out = $("#results");
    if (term.length < 2) { out.innerHTML = ""; $("#count").textContent = ""; return; }
    const letter = /[a-z]/.test(term[0]) ? term[0] : "_";
    cache[letter] ??= await json(`data/index/${letter}.json`).catch(() => []);
    const want = new Set([...document.querySelectorAll("input[name=src]:checked")].map((x) => x.value));
    const multi = $("#multi").checked, bio = $("#withbio").checked;
    const words = term.split(" ");
    const hits = cache[letter].filter((r) => {
      const f = fold(r[1]);
      return words.every((w) => f.includes(w)) && r[3].some((s) => want.has(s)) && (!multi || r[3].length > 1) && (!bio || r[4]);
    });
    hits.sort((a, b) => (fold(a[1]).startsWith(term) ? 0 : 1) - (fold(b[1]).startsWith(term) ? 0 : 1) || b[3].length - a[3].length);
    $("#count").textContent = `${hits.length.toLocaleString("de-CH")} Treffer${hits.length > 300 ? " (die ersten 300)" : ""}`;
    out.innerHTML = hits.slice(0, 300).map((r) => `<li>${chips(r[3])} <a href="person.html#${encodeURIComponent(r[0])}">${esc(r[1])}</a>
      <span class="small">${years(r[2])}${r[4] ? " · Biografie" : ""}${r[5] ? ` · ${r[5]} mögliche Entsprechung${r[5] > 1 ? "en" : ""}` : ""}</span></li>`).join("");
  }
  q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(search, 200); });
  $("#filters").addEventListener("change", search);
  const pre = new URLSearchParams(location.search).get("q");
  if (pre) { q.value = pre; search(); }
}

// ------------------------------------------------------------------ person page
async function sha1hex2(s) {
  const buf = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].slice(0, 1).map((b) => b.toString(16).padStart(2, "0")).join("");
}
function bioHtml(text) {
  return esc(text).replace(/\[(HLS|HBLS|SSRQ|KF|SG|Thun|Bullinger|Graph)\]/g, '<span class="tag">[$1]</span>');
}
async function personPage() {
  const jid = decodeURIComponent(location.hash.slice(1));
  if (!jid) { $("#person").innerHTML = "<p>Keine Person angegeben.</p>"; return; }
  const pages = await json(`data/p/${await sha1hex2(jid)}.json`);
  const p = pages[jid];
  if (!p) { $("#person").innerHTML = `<p>Person ${esc(jid)} nicht gefunden.</p>`; return; }
  document.title = `${p.label} · Vernetzte Vormoderne`;
  const ids = Object.entries(p.ids).map(([k, v]) => ID_URL[k] ? `<a href="${ID_URL[k](v)}">${k.toUpperCase()} ${esc(v)}</a>` : `${k} ${esc(v)}`).join(" · ");
  let h = `<h2>${esc(p.label)} <span class="muted">${years(p.years)}</span></h2><p>${chips(p.sources)}</p><p class="small sans">${ids}</p>`;
  if (p.bio && p.bio.bio) {
    const hlsNote = p.bio.hls ? ` Grundlage u. a.: <a href="${esc(p.bio.hls.url)}">HLS-Artikel</a> von ${esc(p.bio.hls.author || "?")} (Version ${esc(p.bio.hls.version || "?")}), ${esc(p.bio.hls.licence)}.` : "";
    h += `<div class="card"><div class="bio">${bioHtml(p.bio.bio)}</div>
      ${(p.bio.unsicher || []).length ? `<p class="note">Unsicher: ${p.bio.unsicher.map(esc).join("; ")}</p>` : ""}
      <p class="small">Maschinell erstellt (${esc(p.bio.model)}, ${esc(p.bio.generated)}) aus den unten aufgeführten Belegen; nicht redigiert.${hlsNote}</p></div>`;
  } else if (p.steckbrief) {
    h += `<div class="card"><p>${esc(p.steckbrief)}</p><p class="small">Steckbrief, automatisch aus den Belegen zusammengestellt.</p></div>`;
  }
  h += `<h3>Belege in den Quellen</h3><table><thead><tr><th>Quelle</th><th>Name</th><th>Jahre</th><th>Angaben</th></tr></thead><tbody>`;
  for (const m of p.members) {
    const extra = [m.occupation, m.birth && `* ${m.birth}`, m.death && `† ${m.death}`, (m.roles || []).join(", "),
      m.docs ? `${m.docs} Dok.` : "", m.note && `<span class="muted">${esc(m.note.slice(0, 200))}</span>`,
      Object.keys(m.via || {}).length ? `<span class="small">Ids über ${esc([...new Set(Object.values(m.via))].join(", "))}</span>` : ""].filter(Boolean).join(" · ");
    const forms = (m.forms || []).filter((f) => f !== m.name).slice(0, 6);
    h += `<tr><td>${chips([m.source])}</td><td>${m.url ? `<a href="${esc(m.url)}">${esc(m.name)}</a>` : esc(m.name)}${forms.length ? `<br><span class="small">${forms.map(esc).join(", ")}</span>` : ""}</td>
      <td>${years(m.years)}</td><td>${extra}</td></tr>`;
  }
  h += "</tbody></table>";
  if (p.edges.length) {
    h += `<h3>Möglicherweise dieselbe Person</h3><p class="small">Nicht zusammengeführt: die Übereinstimmung ist nicht sicher (docs/verknuepfung.md).</p><ul>`;
    for (const [o, lab, g, why] of p.edges) {
      h += `<li><a href="person.html#${encodeURIComponent(o)}">${esc(lab)}</a> <span class="grade ${esc(g)}">${esc(g)}</span> <span class="small">${esc(why)}</span></li>`;
    }
    h += "</ul>";
  }
  $("#person").innerHTML = h;
}

// ------------------------------------------------------------------ map
async function mapPage() {
  const css = getComputedStyle(document.documentElement);
  const color = (srcs) => css.getPropertyValue(srcs.length > 1 ? "--multi" : `--${srcs[0]}`).trim();
  const places = await json("data/places.json");
  const map = L.map("map", { preferCanvas: true }).setView([46.9, 8.2], 8);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  const layer = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 40 });
  map.addLayer(layer);
  $("#legend").innerHTML = ORDER.map((k) => `<label><input type="checkbox" name="src" value="${k}" checked> <span class="dot" style="background:${color([k])}"></span>${SRC[k]}</label>`).join("")
    + `<span><span class="dot" style="background:${color(["a", "b"])}"></span>in mehreren Quellen</span>
       <label><input type="checkbox" id="multi"> nur in mehreren Quellen</label>`;
  function draw() {
    const want = new Set([...document.querySelectorAll("#legend input[name=src]:checked")].map((x) => x.value));
    const multi = $("#multi").checked;
    layer.clearLayers();
    const ms = [];
    for (const [jid, label, lat, lon, srcs, docs, members] of places) {
      if (!srcs.some((s) => want.has(s)) || (multi && srcs.length < 2)) continue;
      const m = L.circleMarker([lat, lon], { radius: Math.min(4 + Math.log2(1 + docs), 12), color: color(srcs), weight: 1, fillOpacity: 0.7 });
      m.bindPopup(() => `<b>${esc(label)}</b><br>${chips(srcs)}<br>${members.map(([s, n, u]) => `${SRC[s] || s}: ${u ? `<a href="${esc(u)}">${esc(n)}</a>` : esc(n)}`).join("<br>")}`);
      ms.push(m);
    }
    layer.addLayers(ms);
    $("#mapcount").textContent = `${ms.length.toLocaleString("de-CH")} Orte`;
  }
  $("#legend").addEventListener("change", draw);
  draw();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  ({ start: startPage, person: personPage, map: mapPage })[page]?.().catch((e) => {
    document.querySelector("main").insertAdjacentHTML("beforeend", `<p class="note">Fehler: ${esc(e.message)}</p>`);
  });
  if (document.body.dataset.page === "person") window.addEventListener("hashchange", personPage);
});
