"use strict";
(async function () {
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("beadjoint:" + k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("beadjoint:" + k, v); } catch (e) { /* storage blocked */ } },
  };
  const [glyphs, summary] = await Promise.all([
    fetch("data/glyphs.json").then((r) => r.json()),
    fetch("data/summary.json").then((r) => r.json()),
  ]);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const fmt = (v, d = 2) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));

  $("build-line").textContent = `v${summary.version} · ${summary.count} glyphs · built ${summary.built} · demo slice: ${summary.demo.pass} of ${summary.demo.total} glyph faces pass`;

  // ---- size calculator ---------------------------------------------------------------------
  const PT = 25.4 / 72;
  const presets = [0.25, 0.32, 0.4, 0.42, 0.45, 0.62];
  const wIn = $("w-input"), sIn = $("scale-input");
  wIn.value = store.get("w", "0.32");
  sIn.value = store.get("scale", "1");
  $("w-presets").innerHTML = presets.map((p) => `<button type="button" class="chip" data-w="${p}">${p.toFixed(2)} mm</button>`).join("");
  $("w-presets").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { wIn.value = b.dataset.w; calc(); } });
  function calc() {
    const w = Math.max(0.05, parseFloat(wIn.value) || 0.32);
    const k = Math.max(1, parseFloat(sIn.value) || 1);
    const u = w * k;
    store.set("w", String(w)); store.set("scale", String(k));
    [...$("w-presets").children].forEach((b) => b.setAttribute("aria-pressed", String(Math.abs(+b.dataset.w - w) < 1e-9)));
    $("scale-hint").textContent = k === 1 ? "1× is the two-bead size: every stroke exactly 2 line widths."
      : `${k}× : strokes ${(2 * k).toFixed(2)} line widths; wider joints get extra beads or infill.`;
    const rows = [
      ["Fusion text Height", 14 * u, "mm", "Fusion sizes text by cap height; figures and capitals are 14 w", true],
      ["Font size (em)", 20 * u, "mm", "for programs that size by em (CadQuery, Inkscape, most slicers)", true],
      ["Font size", 20 * u / PT, "pt", "same em in points", false],
      ["Stroke", 2 * u, "mm", "two beads", false],
      ["x-height", 10 * u, "mm", "lowercase body", false],
      ["Line pitch", 20 * u, "mm", "baseline to baseline", false],
    ];
    $("calc-out").innerHTML = rows.map(([t, v, unit, s, key]) =>
      `<div class="${key ? "key" : ""}"><dt>${t}</dt><dd>${v.toFixed(unit === "pt" ? 1 : 2)} ${unit}<small>${s}</small></dd></div>`).join("");
  }
  wIn.addEventListener("input", calc); sIn.addEventListener("input", calc); calc();

  // ---- type tester ---------------------------------------------------------------------------
  const tText = $("tester-text"), tFont = $("tester-font"), tSize = $("tester-size"), tOut = $("tester-out");
  tText.value = store.get("tester", tText.value);
  function tester() {
    tOut.textContent = tText.value;
    tOut.style.fontFamily = `"${tFont.value}", monospace`;
    tOut.style.fontSize = tSize.value + "px";
    store.set("tester", tText.value);
  }
  [tText, tFont, tSize].forEach((el) => el.addEventListener("input", tester)); tester();

  // ---- glyph grid ----------------------------------------------------------------------------
  const groups = [["all", "All"], ["letters", "Letters"], ["accented", "Accented"], ["figures", "Figures"], ["punct", "Punctuation"], ["symbols", "Symbols"], ["fails", "Needs attention"]];
  let filter = store.get("filter", "all"), query = "";
  $("glyph-filters").innerHTML = groups.map(([k, t]) => `<button type="button" class="chip" data-f="${k}">${t}</button>`).join("");
  $("glyph-filters").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { filter = b.dataset.f; store.set("filter", filter); render(); } });
  $("glyph-search").addEventListener("input", (e) => { query = e.target.value.trim().toLowerCase(); render(); });
  const status = (g) => (!g.checks.ok ? "bad" : g.demo && !g.demo.pass ? "warn" : "ok");
  const svg = (g, big) => {
    const [x, y, w, h] = g.vb;
    const guides = big ? [-4, 0, 10].map((gy) => `<line x1="${x}" x2="${x + w}" y1="${gy}" y2="${gy}"/>`).join("") : "";
    return `<svg viewBox="${x} ${y} ${w} ${h}" role="img" aria-label="${esc(g.name)}">${guides}<path class="ink" fill-rule="evenodd" d="${g.d}"/></svg>`;
  };
  let shown = [];
  function render() {
    [...$("glyph-filters").children].forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f === filter)));
    shown = glyphs.filter((g) => {
      if (filter === "fails" && status(g) === "ok") return false;
      if (filter !== "all" && filter !== "fails" && g.group !== filter) return false;
      if (!query) return true;
      return g.c === query || g.name.toLowerCase().includes(query) || ("u+" + g.cp.toLowerCase()) === query || g.cp.toLowerCase() === query.replace("u+", "");
    });
    $("glyph-count").textContent = `${shown.length} of ${glyphs.length} shown. Dot: green passes every check and the demo slice, amber passes the design checks but not every demo-slice threshold, red fails a design check.`;
    $("grid").innerHTML = shown.map((g, i) =>
      `<button type="button" class="tile" data-i="${i}" title="${esc(g.c)} U+${g.cp} ${esc(g.name)}">${svg(g, false)}<span class="cp">${esc(g.c)} ${g.cp}</span><span class="dot ${status(g)}"></span></button>`).join("");
  }
  $("grid").addEventListener("click", (e) => { const t = e.target.closest(".tile"); if (t) open(+t.dataset.i); });
  render();

  // ---- detail --------------------------------------------------------------------------------
  const dlg = $("detail");
  let cur = 0;
  function row(k, v) { return `<tr><th>${k}</th><td>${v}</td></tr>`; }
  function face(f) {
    if (!f) return "–";
    const cls = f.pass ? "ok" : "warn";
    return `<span class="pill ${cls}">${f.pass ? "pass" : "check"}</span> covered ${fmt(f.covered, 1)} %, void ${fmt(f.void, 3)} mm², bleed ${fmt(f.bleed, 1)} %, beads ${fmt(f.w_min)}–${fmt(f.w_max)} mm${f.fat > 0 ? `, single-bead run ${fmt(f.fat)} mm` : ""}`;
  }
  function open(i) {
    cur = (i + shown.length) % shown.length;
    const g = shown[cur];
    $("detail-title").textContent = `${g.c}  U+${g.cp}  ${g.name}`;
    $("detail-svg").innerHTML = svg(g, true);
    $("detail-thick").src = g.thick; $("detail-thick").alt = `Local stroke width of ${g.name}`;
    const c = g.checks;
    $("detail-facts").innerHTML = `<table>${
      row("Design checks", `<span class="pill ${c.ok ? "ok" : "bad"}">${c.ok ? "pass" : "fail"}</span>`) +
      row("Thickest point", `${fmt(c.thickness)} w ${c.thickness > 2.85 ? "(infill)" : "(two beads)"}`) +
      row("Thin ink", c.thin.length ? c.thin.join(", ") + " w²" : "none") +
      row("Thin enclosed holes", c.islands.length ? c.islands.join(", ") + " w²" : "none") +
      row("Gap between pieces", c.piece_gap >= 99 ? "one piece" : fmt(c.piece_gap) + " w") +
      row("Advance", `${fmt(g.width, 2)} w ink${g.mono ? "" : " · not in Mono (wider than a 12 w cell)"}`) +
      row("Demo slice, top", face(g.demo && g.demo.top)) +
      row("Demo slice, bed", face(g.demo && g.demo.bottom)) +
      (g.note ? row("Design note", esc(g.note)) : "")}</table>`;
    $("crop-top").src = g.crops.top; $("crop-top").alt = `Top-face toolpaths of ${g.name}`;
    $("crop-bottom").src = g.crops.bottom; $("crop-bottom").alt = `Bed-face toolpaths of ${g.name}`;
    if (!dlg.open) dlg.showModal();
  }
  $("prev").addEventListener("click", () => open(cur - 1));
  $("next").addEventListener("click", () => open(cur + 1));
  $("close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  document.addEventListener("keydown", (e) => {
    if (!dlg.open) return;
    if (e.key === "ArrowLeft") open(cur - 1);
    if (e.key === "ArrowRight") open(cur + 1);
  });

  // ---- checks, log, files --------------------------------------------------------------------
  $("checks-body").innerHTML = summary.checks.map((c) =>
    `<div class="check ${c.state}"><h4>${esc(c.title)}</h4><div class="num">${esc(c.value)}</div><p>${esc(c.text)}</p>${
      c.items && c.items.length ? `<ul>${c.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}</div>`).join("");
  $("log-body").innerHTML = summary.log.length ? summary.log.map((r) =>
    `<article><h4>${esc(r.title)}</h4><ul>${r.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul></article>`).join("")
    : `<p class="note">No review rounds yet.</p>`;
  $("files-body").innerHTML = summary.files.map((f) => `<li><a href="${esc(f.href)}">${esc(f.name)}</a> — ${esc(f.text)}</li>`).join("");
})();
