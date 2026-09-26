"use strict";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
let catalog,
  selected,
  values = {},
  slots = {},
  undo = [],
  redo = [],
  timer,
  revision = 0;
let pending = null,
  running = false,
  latest = null,
  drag = null;
const STORAGE = "fillaprint-tuner-v1";
function el(tag, attrs = {}, text) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  return n;
}
function value(id) {
  return values[id] ?? slots[id].value;
}
function session() {
  return { schema: 1, sources: catalog.sources, values: { ...values } };
}
function message(text, error = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", error);
}
function download(name, content, type) {
  const a = document.createElement("a");
  const url = URL.createObjectURL(new Blob([content], { type }));
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function post(path, data) {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tuner-Token": catalog.token,
    },
    body: JSON.stringify(data),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || res.statusText);
  return body;
}
function history() {
  undo.push({ ...values });
  if (undo.length > 100) undo.shift();
  redo = [];
}
function set(id, v) {
  if (v === slots[id].value) delete values[id];
  else values[id] = v;
}
function changed() {
  revision++;
  latest = null;
  $("canvas").classList.add("stale");
  $("validation").textContent =
    "Changes have not been validated across all families.";
  $("affected").replaceChildren();
  try {
    localStorage.setItem(STORAGE, JSON.stringify(session()));
  } catch {}
  $("undo").disabled = !undo.length;
  $("redo").disabled = !redo.length;
  $("export").disabled = !Object.keys(values).length;
  $("edits").textContent =
    `${Object.keys(values).length} edited parameters · source files unchanged`;
}
function schedule(validate = false) {
  clearTimeout(timer);
  timer = setTimeout(() => queue(validate), validate ? 0 : 450);
}
function queue(validate) {
  pending = {
    session: session(),
    family: $("family").value,
    char: $("glyph").value,
    text: $("text").value,
    validate,
    revision,
  };
  drain();
}
async function drain() {
  if (running || !pending) return;
  running = true;
  const req = pending;
  pending = null;
  message(
    req.validate
      ? "Checking changed glyphs in all three families…"
      : "Regenerating source geometry…",
  );
  $("validate").disabled = true;
  try {
    const result = await post("/api/preview", req);
    if (req.revision === revision) {
      latest = result;
      draw(result);
      renderChecks(result);
      $("canvas").classList.remove("stale");
      message(
        result.checks.ok
          ? "Geometry updated. Selected glyph passes the hard geometry checks."
          : "Selected glyph fails geometry checks — inspect the values below.",
        !result.checks.ok,
      );
    }
  } catch (e) {
    if (req.revision === revision) {
      message(e.message, true);
      $("canvas").classList.add("stale");
    }
  } finally {
    running = false;
    $("validate").disabled = false;
    if (pending) drain();
  }
}
function renderTargets() {
  const needle = $("search").value.toLowerCase();
  const list = $("targets");
  list.replaceChildren();
  let count = 0,
    group = "";
  for (const target of catalog.targets) {
    if (
      needle &&
      !(target.char + " " + target.group).toLowerCase().includes(needle)
    )
      continue;
    if (group !== target.group) {
      const h = document.createElement("div");
      h.className = "group";
      h.textContent = target.group;
      list.append(h);
      group = target.group;
    }
    const b = document.createElement("button");
    b.textContent = target.char;
    b.title = `${target.group}: ${target.char} (${target.path}:${target.line})`;
    b.classList.toggle("selected", selected?.id === target.id);
    b.onclick = () => select(target);
    list.append(b);
    count++;
  }
  $("count").textContent = `${count} source constructions`;
}
function select(target) {
  selected = target;
  $("glyph").value = target.char;
  $("family").value = target.family;
  $("title").textContent = target.char + " · " + target.group;
  $("source").textContent = target.path + ":" + target.line;
  $("handle-help").textContent = target.handles.length
    ? "Drag the yellow points or edit exact values. Coincident points are separate source coordinates; use the fields to move each one."
    : "Edit exact values below. This construction is transformed, shared, or composed; its points are not draggable in the finished glyph.";
  renderTargets();
  renderControls();
  revision++;
  $("canvas").classList.add("stale");
  schedule();
}
function renderControls() {
  const panel = $("controls");
  panel.replaceChildren();
  for (const s of selected.slots) {
    const row = document.createElement("div");
    row.className = "control";
    row.classList.toggle("changed", s.id in values);
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.id = "p-" + s.id;
    label.htmlFor = input.id;
    label.textContent = s.label;
    input.type = "number";
    input.step = "0.05";
    input.min = s.kind === "radius" ? "0" : "-32";
    input.max = s.kind === "radius" ? "8" : "32";
    input.value = value(s.id);
    input.onchange = () => {
      const n = input.valueAsNumber;
      if (!input.checkValidity() || !Number.isFinite(n)) {
        input.reportValidity();
        return;
      }
      if (n === value(s.id)) return;
      history();
      set(s.id, n);
      changed();
      row.classList.toggle("changed", s.id in values);
      schedule();
    };
    const reset = document.createElement("button");
    reset.textContent = "↺";
    reset.title = "Reset " + s.label;
    reset.onclick = () => {
      history();
      delete values[s.id];
      changed();
      renderControls();
      schedule();
    };
    row.append(label, input, reset);
    panel.append(row);
  }
}
function draw(result) {
  const svg = $("canvas");
  svg.replaceChildren();
  let [x0, y0, x1, y1] = result.bounds;
  x0 = Math.min(x0 - 2, -2);
  y0 = Math.min(y0 - 2, -7);
  x1 = Math.max(x1 + 2, 12);
  y1 = Math.max(y1 + 2, 16);
  svg.setAttribute("viewBox", [x0, y0, x1 - x0, y1 - y0].join(" "));
  for (let x = Math.ceil(x0); x <= x1; x++)
    svg.append(el("line", { x1: x, y1: y0, x2: x, y2: y1, class: "grid" }));
  for (let y = Math.ceil(y0); y <= y1; y++)
    svg.append(el("line", { x1: x0, y1: y, x2: x1, y2: y, class: "grid" }));
  for (const [y, name] of [
    [-4, "CAP"],
    [0, "X-HEIGHT"],
    [10, "BASELINE"],
    [14, "DESCENDER"],
  ]) {
    svg.append(el("line", { x1: x0, y1: y, x2: x1, y2: y, class: "guide" }));
    svg.append(
      el("text", { x: x0 + 0.2, y: y - 0.15, class: "guide-label" }, name),
    );
  }
  svg.append(
    el("path", { d: result.before, class: "original", "fill-rule": "evenodd" }),
    el("path", { d: result.after, class: "current", "fill-rule": "evenodd" }),
  );
  if (
    $("glyph").value === selected.char &&
    $("family").value === selected.family
  )
    for (const h of selected.handles) {
      const c = el("circle", {
        cx: value(h.x),
        cy: value(h.y),
        r: 0.19,
        class: "handle",
      });
      c.append(el("title", {}, h.label));
      c.onpointerdown = (e) => {
        e.preventDefault();
        history();
        drag = { h, c, pointer: e.pointerId };
        svg.setPointerCapture(e.pointerId);
      };
      svg.append(c);
    }
  const t = $("text-preview");
  t.replaceChildren();
  const [a, b, c, d] = result.text_bounds;
  t.setAttribute(
    "viewBox",
    [a - 1, b - 2, Math.max(10, c - a + 2), d - b + 4].join(" "),
  );
  for (const p of result.text_paths)
    t.append(el("path", { d: p, "fill-rule": "evenodd" }));
  physical();
}
function physical() {
  const w = $("line-width").valueAsNumber;
  if (!Number.isFinite(w) || w <= 0) return;
  $("scale").textContent =
    `At w = ${w.toFixed(2)} mm: cap height ${(14 * w).toFixed(2)} mm · normal stroke ${(2 * w).toFixed(2)} mm${latest ? ` · this glyph ink width ${(latest.width * w).toFixed(2)} mm` : ""}. Screen magnification is arbitrary.`;
}
function renderChecks(r) {
  const c = r.checks;
  const items = [
    ["Ink width", r.width.toFixed(2) + "w", false],
    ["Max thickness", c.thickness.toFixed(2) + "w", false],
    ["Thin regions", c.thin.length, c.thin.length > 0],
    ["Tight holes", c.islands.length, c.islands.length > 0],
    [
      "Piece gap",
      c.piece_gap === null ? "—" : c.piece_gap + "w",
      c.piece_gap !== null && c.piece_gap < 1.98,
    ],
    [
      "Text gap",
      r.text_gap === null ? "—" : r.text_gap + "w",
      r.text_gap !== null && r.text_gap < 1.98,
    ],
  ];
  $("readouts").replaceChildren();
  for (const [name, v, bad] of items) {
    const n = document.createElement("div");
    n.className = "readout" + (bad ? " bad" : "");
    n.textContent = name + " · " + v;
    $("readouts").append(n);
  }
  if (r.validation) {
    $("validation").textContent =
      `${r.changed.length} changed glyphs checked. ${r.failures.length ? r.failures.join(" ") : "Affected geometry passes. Run the full build, tests, and slicer validation after applying the patch."} Thickness above 2.85w is informational; dots and some joins intentionally exceed it.`;
    $("affected").replaceChildren();
    for (const g of r.changed) {
      const n = document.createElement("span");
      n.className = "affected" + (g.checks.ok ? "" : " bad");
      n.textContent = g.family + ":" + g.char;
      $("affected").append(n);
    }
  }
}
$("canvas").onpointermove = (e) => {
  if (!drag) return;
  const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(
    $("canvas").getScreenCTM().inverse(),
  );
  const snap = Number($("snap").value);
  const round = (v) =>
    Math.max(
      -32,
      Math.min(32, Number((Math.round(v / snap) * snap).toFixed(4))),
    );
  set(drag.h.x, round(p.x));
  set(drag.h.y, round(p.y));
  drag.c.setAttribute("cx", value(drag.h.x));
  drag.c.setAttribute("cy", value(drag.h.y));
  renderControls();
};
function endDrag() {
  if (!drag) return;
  drag = null;
  changed();
  schedule();
}
$("canvas").onpointerup = endDrag;
$("canvas").onpointercancel = endDrag;
$("search").oninput = renderTargets;
for (const id of ["glyph", "family", "text"])
  $(id).onchange = () => {
    revision++;
    $("canvas").classList.add("stale");
    $("validation").textContent =
      "Preview changed; revalidate to check the new sample line.";
    schedule();
  };
$("line-width").oninput = physical;
$("validate").onclick = () => schedule(true);
$("reset").onclick = () => {
  history();
  for (const s of selected.slots) delete values[s.id];
  changed();
  renderControls();
  schedule();
};
$("undo").onclick = () => {
  if (!undo.length) return;
  redo.push({ ...values });
  values = undo.pop();
  changed();
  renderControls();
  schedule();
};
$("redo").onclick = () => {
  if (!redo.length) return;
  undo.push({ ...values });
  values = redo.pop();
  changed();
  renderControls();
  schedule();
};
$("session").onclick = () =>
  download(
    "fillaprint-tuning.json",
    JSON.stringify(session(), null, 2) + "\n",
    "application/json",
  );
$("export").onclick = async () => {
  try {
    const r = await post("/api/export", { session: session() });
    if (!r.patch) throw new Error("There are no source changes to export.");
    download("fillaprint-glyphs.patch", r.patch, "text/x-diff");
    message(
      "Patch exported. Apply with git apply --check, then git apply, and run the full build.",
    );
  } catch (e) {
    message(e.message, true);
  }
};
$("import").onclick = () => $("file").click();
$("file").onchange = async () => {
  try {
    const file = $("file").files[0];
    if (!file) return;
    clearTimeout(timer);
    pending = null;
    const importRevision = ++revision;
    $("canvas").classList.add("stale");
    message("Checking session against the current source files…");
    if (file.size > 262144) throw new Error("Session is too large.");
    const s = JSON.parse(await file.text());
    await post("/api/export", { session: s });
    if (revision !== importRevision)
      throw new Error(
        "Another edit occurred while opening the session. Open it again to replace those edits.",
      );
    history();
    values = s.values;
    changed();
    renderControls();
    schedule();
  } catch (e) {
    message(e.message, true);
  } finally {
    $("file").value = "";
  }
};
window.addEventListener("beforeunload", (e) => {
  if (Object.keys(values).length) {
    e.preventDefault();
    e.returnValue = "";
  }
});
async function start() {
  try {
    catalog = await (await fetch("/api/catalog")).json();
    for (const t of catalog.targets) for (const s of t.slots) slots[s.id] = s;
    let restored = null;
    try {
      restored = JSON.parse(localStorage.getItem(STORAGE));
    } catch {}
    if (restored) {
      try {
        await post("/api/export", { session: restored });
        values = restored.values;
      } catch {
        if (Object.keys(restored.values || {}).length) {
          download(
            "fillaprint-previous-session.json",
            JSON.stringify(restored, null, 2),
            "application/json",
          );
          alert(
            "Your saved session uses different source files. It was downloaded for recovery; this checkout starts a new session.",
          );
        }
      }
    }
    changed();
    select(
      catalog.targets.find((t) => t.char === "a" && t.group === "Base") ||
        catalog.targets[0],
    );
  } catch (e) {
    message("Could not start tuner: " + e.message, true);
  }
}
start();
