"use strict";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const STORAGE = "fillaprint-tuner-v1";
const FAMILY_NAMES = { P: "Proportional", T: "Tab", M: "Mono" };
const UNREACHABLE =
  "Can't reach the tuner server — is `python -m tuner.serve` still running?";
// A busy server is retried after 1, 2, 4 … seconds, for about a minute in total.
const BUSY_LIMIT = 60000;
// Constructor names as they appear in field labels; wording follows beadjoint/geom.py.
const SHAPES = {
  S: "open stroke: a 2w-wide line through its points in order. A corner radius rounds the line at that point (0 is a sharp corner).",
  So: "closed stroke: like S, but the last point joins back to the first, so every point is a rounded corner.",
  D: "disk: a filled circle around point 1. Without a disk radius field it uses the shared dot radius (dots) or 1 (a 2w disk).",
  Rect: "rectangle between corners (x₀, y₀) and (x₁, y₁). Most trim strokes to a band rather than add ink.",
  diagonal:
    "straight 2w-wide stroke from (x₀, y₀) to (x₁, y₁), extended past both ends and cut flat on the clip lines (the cap line and baseline unless clip fields are shown).",
};
let catalog,
  selected,
  values = {},
  slots = {},
  undo = [],
  redo = [],
  timer,
  revision = 0;
let pending = null,
  inflight = null,
  running = false,
  latest = null,
  drag = null;
// The result on screen and the request it answered; resizes and preview changes redraw it.
let drawn = null;
// The last all-family validation, with the edits and sample line it checked, and the last
// attempt that could not run. wantValidation survives previews queued after the request.
let validation = null,
  validationError = null,
  wantValidation = false,
  exportIntent = null;
let previewState = "stale",
  busy = null,
  ticker = null;
let hoverHandle = null,
  focusHandle = null,
  handleOf = {},
  handleEls = new Map(),
  hitRadius = 0.6;
// Another tab changed the autosave; this tab stops writing it until someone decides.
let conflict = false;
// Touch screens have no hover, so help text names what works there.
const HOVER = matchMedia("(hover: hover)").matches;
// Whole-request errors that repeat until the edit changes, and those about the preview inputs.
const UNDO_CODES = ["construction", "invalid_glyph", "disappeared"];
const FAMILY_CODES = ["disappeared", "not_in_family", "text_glyphs"];
// Failures that may pass on a second try: no server, a stuck worker, another tab.
const TRANSIENT_CODES = [
  "offline",
  "timeout",
  "worker_failed",
  "internal",
  "busy",
  "error",
];

function el(tag, attrs = {}, text) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  return n;
}
// Conditional children arrive as false, 0 or null; only nodes and non-empty text are kept.
function kids(...children) {
  return children
    .flat(2)
    .filter((c) => c instanceof Node || (typeof c === "string" && c));
}
function node(tag, props = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (/^(aria-|data-|role$)/.test(k)) n.setAttribute(k, v);
    else n[k] = v;
  }
  n.append(...kids(children));
  return n;
}
function button(label, onclick, className = "") {
  return node("button", { type: "button", className, onclick }, label);
}
// The tuner's own messages mark commands with backticks; show them as code.
function rich(text) {
  return String(text)
    .split("`")
    .map((part, i) => (i % 2 ? node("code", {}, part) : part));
}
function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
function value(id) {
  return values[id] ?? slots[id].value;
}
function session() {
  const s = { schema: 1, sources: catalog.sources };
  if (catalog.commit) s.commit = catalog.commit;
  s.values = { ...values };
  return s;
}
// Only values that differ from the source count as edits.
function edits(v) {
  return Object.fromEntries(
    Object.entries(v || {}).filter(
      ([id, x]) => slots[id] && x !== slots[id].value,
    ),
  );
}
function editsKey(v = values) {
  return JSON.stringify(
    Object.keys(v)
      .sort()
      .map((k) => [k, v[k]]),
  );
}
// Validation checks every changed glyph, but its sample-line check uses this family and text.
function sampleKey() {
  return JSON.stringify([$("family").value, $("text").value]);
}
// A validation that could not run failed on these exact preview inputs.
function inputsKey(body) {
  return JSON.stringify(
    body
      ? [body.family, body.char, body.text]
      : [$("family").value, $("glyph").value, $("text").value],
  );
}
function parseSession(text) {
  let s;
  try {
    s = JSON.parse(text);
  } catch {
    return null;
  }
  const isMap = (m) => m && typeof m === "object" && !Array.isArray(m);
  return isMap(s) && "schema" in s && isMap(s.sources) && isMap(s.values)
    ? s
    : null;
}
// The server names the commit in its own session messages; add it only when it did not.
function commitHint(s, text) {
  return s?.commit &&
    catalog.commit &&
    s.commit !== catalog.commit &&
    !/\bcommit\b/.test(text)
    ? ` It was saved at commit ${s.commit.slice(0, 12)}; this checkout is at ${catalog.commit.slice(0, 12)}.`
    : "";
}

// level: "" for success, "progress" while work is pending, "warn" for printable but suspect
// geometry, "error".
function message(text, level = "", actions = []) {
  $("status").replaceChildren(...rich(text), ...actions);
  $("status").className = level;
  if (level !== "progress") $("elapsed").textContent = "";
}
// Outcomes that appear away from the focus (the validation block) are read out from here.
function announce(text) {
  $("announce").textContent = "";
  // Clearing first lets a screen reader repeat news identical to the last.
  setTimeout(() => ($("announce").textContent = text), 50);
}
// Notices stay until dismissed or replaced; every preview rewrites the status line.
// actions: [label, run, primary]; a notice with no dismiss button needs a decision.
function notice(id, level, text, actions = [], dismissible = true) {
  const buttons = actions.map(([label, run, primary]) =>
    button(
      label,
      () => {
        dismiss(id);
        run();
      },
      primary ? "primary" : "",
    ),
  );
  if (dismissible)
    buttons.push(
      node(
        "button",
        {
          type: "button",
          className: "dismiss",
          title: "Dismiss",
          "aria-label": "Dismiss",
          onclick: () => dismiss(id),
        },
        "×",
      ),
    );
  const n = node(
    "div",
    { className: "notice " + level, "data-notice": id },
    node("p", {}, rich(text)),
    node("div", { className: "notice-actions" }, buttons),
  );
  if (level === "error") n.setAttribute("role", "alert");
  const old = document.querySelector(`[data-notice="${id}"]`);
  if (old) old.replaceWith(n);
  else $("notices").append(n);
}
function dismiss(id) {
  document.querySelector(`[data-notice="${id}"]`)?.remove();
}
// Rebuilding a list drops keyboard focus; put it back on the control with the same data-focus
// key, or on the list itself when that control is gone.
function keepFocus(container, rebuild) {
  const active = document.activeElement;
  const inside = container.contains(active) && active !== container;
  const key = inside ? active.dataset.focus : undefined;
  rebuild();
  if (!inside || container.contains(document.activeElement)) return;
  const again =
    key && container.querySelector(`[data-focus="${CSS.escape(key)}"]`);
  (again || container).focus({ preventScroll: true });
}
function focusKey(el, key) {
  el.dataset.focus = key;
  return el;
}
function fillNote(fill) {
  return `Finishing filled ${fill.after.toFixed(2)} w² of gaps narrower than 2w with ink (original ${fill.before.toFixed(2)} w²). Strokes this close print as solid ink; keep them at least 2w apart.`;
}
function download(name, content, type) {
  const a = document.createElement("a");
  const url = URL.createObjectURL(new Blob([content], { type }));
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function apiError(text, status = 0, code = "") {
  const e = new Error(text);
  e.status = status;
  e.code = code;
  return e;
}
async function call(path, init) {
  let res;
  try {
    res = await fetch(path, init);
  } catch {
    throw apiError(UNREACHABLE, 0, "offline");
  }
  let body = null;
  try {
    body = await res.json();
  } catch {}
  if (!res.ok || !body || typeof body !== "object")
    throw apiError(
      body?.error ||
        `The tuner server sent an unexpected reply (HTTP ${res.status}). Check the terminal where it runs.`,
      res.status,
      body?.code || "",
    );
  return body;
}
function post(path, data) {
  return call(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Tuner-Token": catalog.token,
    },
    body: JSON.stringify(data),
  });
}
// Buttons for a failed preview. A 403 means the server restarted with a new token, and
// changed sources need a restart; autosave keeps edits across the reload either way. Errors
// caused by the edit or the preview inputs repeat on retry, so they get Undo or a family switch.
function recovery(e, req) {
  const actions = [];
  const add = (label, run) => actions.push(button(label, run, "inline"));
  if (e.status === 403 || e.code === "sources_changed")
    add("Reload page", () => location.reload());
  if (UNDO_CODES.includes(e.code) && undo.length)
    add("Undo", () => $("undo").click());
  if (FAMILY_CODES.includes(e.code) && req.body.family !== "P")
    add("Preview in Proportional", () => previewGlyph($("glyph").value, "P"));
  if (!e.code || TRANSIENT_CODES.includes(e.code))
    add("Retry", () => {
      if (req.body.validate) wantValidation = true;
      queue();
    });
  return actions;
}

function remember() {
  undo.push({ ...values });
  if (undo.length > 100) undo.shift();
  redo = [];
}
function set(id, v) {
  if (v === slots[id].value) delete values[id];
  else values[id] = v;
}
function autosave() {
  if (conflict) return;
  try {
    localStorage.setItem(STORAGE, JSON.stringify(session()));
  } catch {}
}
function changed() {
  revision++;
  latest = null;
  exportIntent = null;
  wantValidation = false;
  dismiss("export");
  setPreview("stale");
  autosave();
  $("undo").disabled = !undo.length;
  $("redo").disabled = !redo.length;
  $("export").disabled = !Object.keys(values).length;
  renderValidation();
  renderTargets();
}
function editedCount(t) {
  return t.slots.reduce((n, s) => n + (s.id in values), 0);
}
function editedTargets() {
  return catalog.targets.filter(editedCount);
}
function describe(targets) {
  const names = targets.slice(0, 4).map((t) => `${t.char} · ${t.group}`);
  if (targets.length > 4) names.push(`${targets.length - 4} more`);
  return names.join(", ");
}

function schedule(validate = false) {
  if (validate) wantValidation = true;
  clearTimeout(timer);
  timer = setTimeout(
    () => {
      timer = null;
      queue();
    },
    wantValidation ? 0 : 450,
  );
}
// The newest request replaces any waiting one; a wanted validation rides along with it.
function queue() {
  if (busy) {
    clearTimeout(busy.timer);
    busy = null;
  }
  const char = $("glyph").value;
  if ([...char].length !== 1) {
    pending = null;
    setPreview("failed");
    message("Type exactly one character in Preview glyph.", "error");
    // A validation still computing reports for itself when it finishes.
    if (wantValidation && !inflight?.body.validate)
      validationFailed(
        apiError(
          "Preview glyph must hold exactly one character.",
          0,
          "bad_request",
        ),
        editsKey(),
        inputsKey(),
      );
    return;
  }
  pending = {
    body: {
      session: session(),
      family: $("family").value,
      char,
      text: $("text").value,
      validate: wantValidation,
    },
    revision,
    edits: editsKey(),
    sample: sampleKey(),
  };
  drain();
}
async function drain() {
  if (running || !pending || busy?.timer) return;
  running = true;
  const req = (inflight = pending);
  pending = null;
  if (req.revision === revision) progress(req);
  $("validate").disabled = true;
  try {
    const result = await post("/api/preview", req.body);
    busy = null;
    if (req.body.validate) validated(result, req);
    if (req.revision === revision) {
      latest = result;
      draw(result, req.body);
      renderChecks(result);
      setPreview("current");
      previewMessage(result, req.body);
    }
  } catch (e) {
    if (e.code === "busy" || e.status === 409) {
      if (waitForServer(req)) return;
      e.message =
        "The server stayed busy with another preview for a minute (another tuner tab, or this page before a reload). Retry when it has finished.";
    } else busy = null;
    // A newer validation already waiting speaks for these edits instead.
    if (req.body.validate && !pending?.body.validate)
      validationFailed(e, req.edits, inputsKey(req.body));
    if (req.revision === revision) {
      setPreview("failed");
      message(e.message, "error", recovery(e, req));
    }
  } finally {
    running = false;
    inflight = null;
    clearInterval(ticker);
    $("validate").disabled = false;
    if (pending) drain();
    // Something outdated this request without asking for a new one: catch up now.
    else if (req.revision !== revision && !timer && previewState === "stale")
      schedule();
  }
}
// The server computes one preview at a time and answers 409 to everyone else. Returns true
// when the 409 is handled: a retry is waiting, or the request is obsolete and dropped.
function waitForServer(req) {
  const now = Date.now();
  busy ??= { since: now, delay: 1000, timer: null };
  const wait = Math.min(busy.delay, busy.since + BUSY_LIMIT - now);
  if (wait <= 0) {
    busy = null;
    return false;
  }
  if (!pending && req.revision === revision) pending = req;
  if (!pending) {
    busy = null;
    return true;
  }
  busy.delay *= 2;
  message(
    "Another tuner tab is computing (or this page before a reload) — retrying…",
    "progress",
  );
  busy.timer = setTimeout(() => {
    busy.timer = null;
    drain();
  }, wait);
  return true;
}
// The seconds counter sits outside the status live region so it is not read out every second.
function progress(req) {
  const text = req.body.validate
    ? "Checking changed glyphs in all three families…"
    : "Updating preview…";
  if ($("status").textContent !== text) message(text, "progress");
  const started = Date.now();
  const slow = req.body.validate
    ? ""
    : " · the first preview after starting the tuner, or in a new family, takes longer";
  clearInterval(ticker);
  ticker = setInterval(() => {
    const s = Math.round((Date.now() - started) / 1000);
    // A request outdated by a newer edit no longer speaks for the page.
    $("elapsed").textContent =
      inflight === req && req.revision === revision
        ? `${s} s${s >= 4 ? slow : ""}`
        : "";
  }, 1000);
}
function validated(result, req) {
  validation = { result, edits: req.edits, sample: req.sample };
  validationError = null;
  if (req.edits === editsKey()) wantValidation = false;
  // A preview queued meanwhile for the same edits and sample line need not validate again.
  if (pending?.edits === req.edits && pending.sample === req.sample)
    pending.body.validate = false;
  renderValidation();
  const n = failuresOf(result).length;
  announce(
    n
      ? `Validation failed: ${plural(n, "problem")}. The list is under the Validate button.`
      : `Validation passed: ${plural(result.changed.length, "changed glyph")} checked.`,
  );
  if (exportIntent === req.edits) {
    exportIntent = null;
    offerExport();
  }
}
// A validation request fails as a whole when the previewed glyph itself cannot be built.
function validationFailed(e, edits, inputs) {
  wantValidation = false;
  validationError = { message: e.message, code: e.code, edits, inputs };
  renderValidation();
  announce("Validation could not run: " + e.message);
  if (exportIntent === edits) {
    exportIntent = null;
    const fix = validationFix(validationError);
    notice("export", "error", "Validation could not run: " + e.message, [
      ...(fix
        ? [
            [
              fix[0],
              () => {
                exportIntent = editsKey();
                fix[1]();
              },
              true,
            ],
          ]
        : []),
      ["Export anyway", exportPatch],
    ]);
  }
}
// What to offer when validation could not run: [label, action], or null.
function validationFix(err) {
  if (FAMILY_CODES.includes(err.code) && $("family").value !== "P")
    return [
      "Validate with the preview in Proportional",
      () => {
        $("family").value = "P";
        previewChanged();
        schedule(true);
      },
    ];
  if (UNDO_CODES.includes(err.code) && undo.length)
    return ["Undo the last change", () => $("undo").click()];
  if (!err.code || TRANSIENT_CODES.includes(err.code))
    return ["Retry", () => schedule(true)];
  return null;
}
// A validation for the current edits is running, waiting, or about to be queued.
function validating() {
  const key = editsKey();
  return (
    wantValidation ||
    [inflight, pending].some((r) => r?.body.validate && r.edits === key)
  );
}

function setPreview(state) {
  // The old "passes" message must not sit next to an outline that is out of date.
  if (state === "stale" && previewState !== "stale")
    message(
      drag ? "The preview updates when you release the point." : "Updating preview…",
      "progress",
    );
  previewState = state;
  $("workspace").dataset.preview = state;
  $("canvas").classList.toggle("stale", state !== "current");
  renderTag();
  physical();
}
function renderTag() {
  const tag = $("preview-tag");
  tag.hidden = previewState === "current";
  tag.className = "state-tag " + previewState;
  const paused = !drag && selected?.handles.length && handlesShown();
  tag.textContent =
    (previewState === "failed" ? "Failed" : "Stale") +
    (paused ? " · dragging paused" : "");
  tag.title =
    previewState === "failed"
      ? "The last preview failed. The drawing, readouts and sample line still show an earlier state."
      : "The drawing, readouts and sample line show earlier settings until the new preview arrives.";
}
function handlesShown() {
  return (
    !!selected &&
    $("glyph").value === selected.char &&
    $("family").value === selected.family
  );
}
function previewChanged() {
  revision++;
  setPreview("stale");
  // Take the points off an outline they no longer belong to.
  if (drawn && !drag) draw(drawn.result, drawn.body);
  renderHandleHelp();
  renderValidation();
  schedule();
}
function previewGlyph(char, family) {
  $("glyph").value = char;
  $("family").value = family;
  previewChanged();
}

function hiddenReason(t) {
  if (t.group === "Global dot radius")
    return "This is one radius shared by every dot, so there are no points to drag.";
  if (t.group.startsWith("Accent"))
    return "Points are not shown for accent marks: a mark is drawn in its own coordinates and then moved onto each letter, so its points are not where the drawing shows them.";
  if (t.group === "Mono")
    return "Points are not shown for Mono constructions: several Mono shapes are widened or adjusted for the monospace cell, so raw points would not reliably sit on the drawing.";
  if (t.group === "Shared M / W")
    return "Points are not shown for this shared helper: M and W both use it, turned or shifted, so its points do not line up with any one drawing.";
  return "Points are not shown here: this construction passes its strokes through helper transforms (such as shift, mirror or rotate), so its raw points do not line up with the finished glyph.";
}
function renderHandleHelp() {
  if (!selected) return;
  const help = $("handle-help");
  const own = `${selected.char} in ${FAMILY_NAMES[selected.family]}`;
  const find = HOVER
    ? "Hover a point to find its fields; hover or focus a field to find its point."
    : "Tap a field to find its point.";
  keepFocus(help, () => {
    if (!selected.handles.length)
      help.replaceChildren(
        hiddenReason(selected) +
          " Edit the exact values below; the preview updates the same way.",
      );
    else if (!handlesShown())
      help.replaceChildren(
        `Points are hidden because the preview shows ${$("glyph").value || "nothing"} in ${FAMILY_NAMES[$("family").value]}; they belong to ${own}. The fields still work. `,
        focusKey(
          button(
            `Show ${own}`,
            () => previewGlyph(selected.char, selected.family),
            "inline",
          ),
          "show",
        ),
      );
    else
      help.replaceChildren(
        `Drag the yellow points or edit exact values. ${find} Coincident points are separate source coordinates; use the fields to move each one.`,
      );
  });
  renderTag();
}
function renderLegend() {
  const used = new Set(
    selected.slots.map((s) => /^(So|S|D|Rect|diagonal)\d/.exec(s.label)?.[1]),
  );
  const names = Object.keys(SHAPES).filter((k) => used.has(k));
  const entries = names.map((k) =>
    node("div", {}, node("dt", {}, k), node("dd", {}, SHAPES[k])),
  );
  const numbering = node(
    "p",
    {},
    "The number after the letter counts the shapes in reading order: S1 is the first shape on the source line, D3 the third.",
  );
  $("constructors").hidden = !names.length;
  $("constructors").replaceChildren(node("dl", {}, entries), numbering);
}

// A shared helper draws the letters its group names: "Shared M / W" draws W as well as M.
function draws(t, ch) {
  return (
    t.char === ch ||
    (t.group.startsWith("Shared ") && t.group.split(/[\s/]+/).includes(ch))
  );
}
function renderTargets() {
  if (!catalog) return;
  const raw = $("search").value.trim();
  const needle = raw.toLowerCase();
  // One typed character means a glyph; matching it inside group names ("n" in "Mono") is noise.
  const single = [...raw].length === 1;
  const hits = catalog.targets.filter(
    (t) =>
      !raw ||
      (single
        ? t.char.toLowerCase() === needle || draws(t, raw)
        : (t.char + " " + t.group).toLowerCase().includes(needle)),
  );
  // Exact character first, then helpers that draw it, then the rest in catalog order.
  const rank = (t) => (!raw ? 0 : t.char === raw ? 0 : draws(t, raw) ? 1 : 2);
  const sorted = hits
    .map((t, i) => [rank(t), i, t])
    .sort((a, b) => a[0] - b[0] || a[1] - b[1])
    .map(([, , t]) => t);
  const exact = sorted.filter((t) => raw && t.char === raw);
  const first = exact.length < hits.length ? exact : [];
  const nodes = [];
  const derived = single && catalog.derived?.[raw];
  if (derived) nodes.push(derivedCard(raw, derived));
  if (first.length) nodes.push(groupHeading("Exact match"));
  nodes.push(...first.map(targetButton));
  let group = "";
  for (const t of sorted) {
    if (first.includes(t)) continue;
    if (group !== t.group) nodes.push(groupHeading((group = t.group)));
    nodes.push(targetButton(t));
  }
  const list = $("targets");
  const scroll = list.scrollTop;
  keepFocus(list, () => list.replaceChildren(...nodes));
  list.scrollTop = scroll;
  const edited = editedTargets().length;
  $("count").textContent =
    (derived && !hits.length
      ? `${raw} has no construction of its own`
      : plural(hits.length, "source construction")) +
    (edited ? ` · ${edited} with edits` : "");
}
function groupHeading(text) {
  return node("div", { className: "group" }, text);
}
function targetButton(t) {
  const k = editedCount(t);
  const what = k ? `, ${plural(k, "edited parameter")}` : "";
  const b = node(
    "button",
    {
      type: "button",
      className:
        (selected?.id === t.id ? "selected" : "") + (k ? " edited" : ""),
      title: `${t.group}: ${t.char} (${t.path}:${t.line})${what}`,
      "aria-label": `${t.char}, ${t.group}${what}`,
      onclick: () => select(t),
    },
    t.char,
  );
  if (k)
    b.append(
      node("span", { className: "badge", "aria-hidden": "true" }, String(k)),
    );
  if (selected?.id === t.id) b.setAttribute("aria-current", "true");
  return focusKey(b, "t:" + t.id);
}
function derivedCard(ch, d) {
  const buttons = catalog.targets
    .filter((t) => draws(t, d.base))
    .map((t) =>
      focusKey(
        button(`${t.char} · ${t.group}`, () => select(t, ch)),
        "d:" + t.id,
      ),
    );
  const missing = [];
  for (const m of d.marks) {
    const t = catalog.targets.find((t) => t.group === "Accent " + m);
    if (t)
      buttons.push(
        focusKey(button(`${m} · accent`, () => select(t, ch)), "d:" + t.id),
      );
    else missing.push(m);
  }
  return node(
    "div",
    { className: "derived" },
    node("p", {}, `${ch} is built from ${[d.base, ...d.marks].join(" + ")}.`),
    buttons.length &&
      node(
        "p",
        { className: "muted" },
        `Edit one of these; the preview shows ${ch}:`,
      ),
    node("div", { className: "derived-actions" }, buttons),
    missing.length &&
      node(
        "p",
        { className: "muted" },
        `The ${missing.join(" and ")} ${missing.length === 1 ? "is" : "are"} drawn by a helper whose numbers are not exposed here.`,
      ),
  );
}
function select(target, previewChar) {
  selected = target;
  $("glyph").value = previewChar || target.char;
  $("family").value = target.family;
  $("title").textContent = target.char + " · " + target.group;
  $("source").textContent = target.path + ":" + target.line;
  hoverHandle = focusHandle = null;
  renderTargets();
  renderControls();
  renderLegend();
  previewChanged();
}

// Named like its fields: "S1 point 3" for "S1 point 3 x" and "y"; a diagonal's end is
// "diagonal3 x₀, y₀" for the fields "diagonal3 x₀" and "diagonal3 y₀".
function pointName(h) {
  const x = slots[h.x].label;
  return x.endsWith(" x")
    ? x.slice(0, -2)
    : `${x}, ${slots[h.y].label.split(" ").pop()}`;
}
// Fields that belong to a point: its x and y, its corner radius, and a disk's radius.
function buildHandleIndex() {
  handleOf = {};
  for (const h of selected.handles) {
    handleOf[h.x] = handleOf[h.y] = h;
    const name = pointName(h);
    const shape = name.split(" ")[0];
    for (const s of selected.slots)
      if (
        s.label === name + " corner radius" ||
        (/^D\d+$/.test(shape) && s.label === shape + " disk radius")
      )
        handleOf[s.id] = h;
  }
}
function renderControls() {
  buildHandleIndex();
  // Rebuilt fields lose focus without a blur event.
  focusHandle = null;
  const panel = $("controls");
  panel.replaceChildren();
  for (const s of selected.slots) {
    const row = document.createElement("div");
    row.className = "control";
    row.dataset.slot = s.id;
    row.classList.toggle("changed", s.id in values);
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.id = "p-" + s.id;
    label.htmlFor = input.id;
    label.textContent = s.label;
    input.type = "number";
    input.step = "any";
    const [lo, hi] = s.kind === "radius" ? [0, 8] : [-32, 32];
    // A few source values (a clip box at x = 40) sit outside the normal range.
    input.min = String(Math.min(lo, s.value));
    input.max = String(Math.max(hi, s.value));
    input.value = value(s.id);
    input.onchange = () => commitField(s, input, row);
    input.onfocus = () => {
      focusHandle = handleOf[s.id] || null;
      renderLink();
    };
    input.onblur = () => {
      focusHandle = null;
      renderLink();
    };
    row.onpointerenter = (e) => {
      if (e.pointerType === "mouse") setHover(handleOf[s.id] || null, false);
    };
    row.onpointerleave = (e) => {
      if (e.pointerType === "mouse") setHover(null, false);
    };
    const reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "↺";
    reset.title = `Reset ${s.label} to ${s.value}`;
    reset.setAttribute("aria-label", reset.title);
    reset.onclick = () => {
      if (!(s.id in values)) return;
      remember();
      delete values[s.id];
      changed();
      renderControls();
      schedule();
    };
    row.append(label, input, reset);
    panel.append(row);
  }
  renderLink();
}
function commitField(s, input, row) {
  const n = input.valueAsNumber;
  if (!Number.isFinite(n) || !input.checkValidity()) {
    const why = input.validity.badInput
      ? "Not a number."
      : input.value === ""
        ? "Empty field."
        : "Out of range.";
    const kept = value(s.id);
    input.value = kept;
    fieldError(
      row,
      input,
      `${why} Use ${input.min} to ${input.max}w; kept ${kept}.`,
    );
    return;
  }
  clearFieldError(row, input);
  if (n === value(s.id)) {
    // Retyping the value after a failed preview is how people ask for it again.
    if (previewState === "failed") schedule();
    return;
  }
  remember();
  set(s.id, n);
  changed();
  row.classList.toggle("changed", s.id in values);
  schedule();
}
function fieldError(row, input, text) {
  let p = row.querySelector(".field-error");
  if (!p) {
    p = node("p", {
      className: "field-error",
      id: input.id + "-error",
      role: "alert",
    });
    row.append(p);
  }
  p.textContent = text;
  input.setAttribute("aria-describedby", p.id);
}
function clearFieldError(row, input) {
  row.querySelector(".field-error")?.remove();
  input.removeAttribute("aria-describedby");
}

function draw(result, body) {
  drawn = { result, body };
  const svg = $("canvas");
  svg.replaceChildren();
  let [x0, y0, x1, y1] = result.bounds;
  x0 = Math.min(x0 - 2, -2);
  y0 = Math.min(y0 - 2, -7);
  x1 = Math.max(x1 + 2, 12);
  y1 = Math.max(y1 + 2, 16);
  const box = svg.getBoundingClientRect();
  if (box.width && box.height) {
    // Fill the pane so the grid, guide names and tick numbers get the margins, not the ink.
    const want = box.width / box.height;
    const extra = (want * (y1 - y0) - (x1 - x0)) / 2;
    if (extra > 0) [x0, x1] = [x0 - extra, x1 + extra];
    else [y0, y1] = [y0 + extra / want, y1 - extra / want];
  }
  svg.setAttribute("viewBox", [x0, y0, x1 - x0, y1 - y0].join(" "));
  // Size text and hit areas in screen pixels: the scale changes with the glyph and window.
  const px = box.width / (x1 - x0) || 30;
  const font = 11 / px;
  const label = (x, y, cls, anchor, text) =>
    el(
      "text",
      {
        x,
        y,
        class: cls,
        "font-size": font,
        "stroke-width": font * 0.3,
        "text-anchor": anchor,
      },
      text,
    );
  for (let x = Math.ceil(x0); x <= x1; x++)
    svg.append(
      el("line", {
        x1: x,
        y1: y0,
        x2: x,
        y2: y1,
        class: x % 2 ? "grid" : "grid major",
      }),
    );
  for (let y = Math.ceil(y0); y <= y1; y++)
    svg.append(
      el("line", {
        x1: x0,
        y1: y,
        x2: x1,
        y2: y,
        class: y % 2 ? "grid" : "grid major",
      }),
    );
  // Coordinates every 2w: x along the bottom, y along the right (guide names use the left).
  for (let x = Math.ceil(x0 / 2) * 2; x <= x1 - 2.5 * font; x += 2)
    if (x >= x0 + font)
      svg.append(label(x, y1 - font * 0.5, "tick", "middle", String(x)));
  for (let y = Math.ceil(y0 / 2) * 2; y <= y1 - 1.6 * font; y += 2)
    svg.append(
      label(x1 - font * 0.4, y + font * 0.35, "tick", "end", String(y)),
    );
  for (const [y, name] of [
    [-4, "CAP"],
    [0, "X-HEIGHT"],
    [10, "BASELINE"],
    [14, "DESCENDER"],
  ]) {
    svg.append(el("line", { x1: x0, y1: y, x2: x1, y2: y, class: "guide" }));
    svg.append(
      label(x0 + font * 0.4, y - font * 0.35, "guide-label", "start", name),
    );
  }
  svg.append(
    el("path", { d: result.before, class: "original", "fill-rule": "evenodd" }),
    el("path", { d: result.after, class: "current", "fill-rule": "evenodd" }),
  );
  handleEls = new Map();
  // A generous invisible hit area keeps small dots easy to grab with a finger.
  hitRadius = Math.max(0.6, 18 / px);
  const dot = Math.max(0.2, 5 / px);
  const own =
    handlesShown() &&
    body.char === selected.char &&
    body.family === selected.family;
  if (own)
    for (const h of selected.handles) {
      const cx = value(h.x),
        cy = value(h.y);
      const g = el("g", { class: "handle-group" });
      g.append(
        el("circle", { cx, cy, r: hitRadius, class: "handle-hit" }),
        el("circle", { cx, cy, r: dot * 2, class: "handle-halo" }),
        el("circle", { cx, cy, r: dot * 2, class: "handle-ring" }),
        el("circle", { cx, cy, r: dot, class: "handle" }),
      );
      svg.append(g);
      handleEls.set(h, g);
    }
  const tip = el("g", { class: "handle-tip", visibility: "hidden" });
  tip.append(
    el("rect", { "stroke-width": font * 0.1 }),
    el("text", { "font-size": font * 1.1 }),
  );
  svg.append(tip);
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
  renderLink();
}
// Highlight one point and its fields: the dragged one, else the hovered, else the focused.
function renderLink() {
  const h = drag?.h || hoverHandle || focusHandle;
  const tip = $("canvas").querySelector(".handle-tip");
  for (const [k, g] of handleEls) {
    g.classList.toggle("linked", k === h);
    // Keep the highlighted point above its neighbours.
    if (k === h && tip) tip.before(g);
  }
  if (tip) {
    const shown = h && handleEls.has(h);
    tip.setAttribute("visibility", shown ? "visible" : "hidden");
    if (shown) placeTip(tip, h);
  }
  for (const row of $("controls").children)
    row.classList.toggle("linked", !!h && handleOf[row.dataset.slot] === h);
}
// The name matches the field labels, so "S1 point 3" here is "S1 point 3 x" and "y" there.
function placeTip(tip, h) {
  const [rect, label] = tip.children;
  const x = value(h.x),
    y = value(h.y);
  const [vx, , vw] = $("canvas")
    .getAttribute("viewBox")
    .split(" ")
    .map(Number);
  const right = x > vx + vw * 0.6;
  label.textContent = `${pointName(h)} (${x}, ${y})`;
  label.setAttribute("x", right ? x - hitRadius : x + hitRadius);
  label.setAttribute("y", y - hitRadius * 0.6);
  label.setAttribute("text-anchor", right ? "end" : "start");
  const b = label.getBBox();
  const pad = b.height * 0.2;
  rect.setAttribute("x", b.x - pad);
  rect.setAttribute("y", b.y - pad / 2);
  rect.setAttribute("width", b.width + 2 * pad);
  rect.setAttribute("height", b.height + pad);
}
function setHover(h, reveal) {
  if (h === hoverHandle) return;
  hoverHandle = h;
  renderLink();
  if (h && reveal) revealRow(h);
}
// Scroll the fields list (not the page) so a hovered point's fields are visible.
function revealRow(h) {
  const box = $("controls");
  if (box.scrollHeight <= box.clientHeight) return;
  const row = [...box.children].find((r) => handleOf[r.dataset.slot] === h);
  if (
    row &&
    (row.offsetTop < box.scrollTop ||
      row.offsetTop + row.offsetHeight > box.scrollTop + box.clientHeight)
  )
    box.scrollTop = row.offsetTop - box.clientHeight / 3;
}
function physical() {
  const w = $("line-width").valueAsNumber;
  if (!Number.isFinite(w) || w <= 0) return;
  $("scale").textContent =
    `At w = ${w.toFixed(2)} mm: cap height ${(14 * w).toFixed(2)} mm · normal stroke ${(2 * w).toFixed(2)} mm${latest && previewState === "current" ? ` · this glyph ink width ${(latest.width * w).toFixed(2)} mm` : ""}. Screen magnification is arbitrary.`;
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
}
// Worst first, matching the chips: a glyph missing from a family outranks a thin stroke.
const FAILURE_ORDER = ["disappeared", "text_gap", "tabular_width", "checks"];
// Older servers sent failures as sentences; current ones send objects with a message.
function failuresOf(r) {
  const rank = (f) => {
    const i = FAILURE_ORDER.indexOf(f.code);
    return i < 0 ? FAILURE_ORDER.length : i;
  };
  return (r?.failures || [])
    .map((f) =>
      typeof f === "string"
        ? { family: null, char: null, code: "error", message: f }
        : f,
    )
    .sort((a, b) => rank(a) - rank(b));
}
function previewMessage(result, body) {
  // A validation result lists every failure; the status line is about this glyph and line.
  const fails = failuresOf(result).filter(
    (f) =>
      !result.validation ||
      f.code === "text_gap" ||
      (f.char === body.char && f.family === body.family),
  );
  if (!result.checks.ok && !fails.some((f) => f.char === body.char))
    fails.unshift({
      message:
        "Selected glyph fails geometry checks — inspect the values below.",
    });
  const fill = result.fill.warn ? fillNote(result.fill) : "";
  if (fails.length)
    message(
      fails.map((f) => f.message).join(" ") + (fill && " " + fill),
      "error",
    );
  else if (fill) message(fill, "warn");
  else
    message(
      "Geometry updated. Selected glyph passes the hard geometry checks.",
    );
}
function renderEditCount() {
  const n = Object.keys(values).length;
  const v = validation?.edits === editsKey() ? validation : null;
  const k = v ? failuresOf(v.result).length : 0;
  const state = !n
    ? ""
    : !v
      ? " · not validated"
      : k
        ? ` · validation found ${plural(k, "problem")}`
        : " · validation passed";
  $("edits").textContent =
    plural(n, "edited parameter") +
    state +
    (conflict
      ? " · autosave paused (another tab)"
      : " · source files unchanged");
  $("edits").classList.toggle("bad", k > 0);
}
function renderValidation() {
  renderEditCount();
  const box = $("validation");
  keepFocus(box, () => fillValidation(box));
  if (validation)
    keepFocus($("affected"), () =>
      renderChips(
        validation.result,
        failuresOf(validation.result),
        validation.edits !== editsKey(),
      ),
    );
  else $("affected").replaceChildren();
}
// Why validation could not run for the current edits, and what to do about it.
function couldNotRun(err) {
  const fix = validationFix(err);
  const hint = FAMILY_CODES.includes(err.code)
    ? "Validation builds the previewed glyph first. Proportional has every character, so validating with the preview in Proportional still checks Tab and Mono."
    : UNDO_CODES.includes(err.code)
      ? "Undo or fix the value first: validation needs the previewed glyph to build."
      : "";
  return node(
    "div",
    { className: "could-not-run" },
    node("p", { className: "summary-title" }, "Validation could not run."),
    node("p", {}, err.message),
    hint && node("p", {}, hint),
    fix && focusKey(button(fix[0], fix[1], "inline"), "fix"),
  );
}
function fillValidation(box) {
  const error =
    validationError?.edits === editsKey() &&
    validationError.inputs === inputsKey()
      ? validationError
      : null;
  if (!validation) {
    box.className = "validation-summary" + (error ? " failed" : "");
    box.replaceChildren(
      error
        ? couldNotRun(error)
        : node(
            "p",
            { className: "muted" },
            Object.keys(values).length
              ? "These edits have not been validated across all families yet. The preview checks one glyph and the sample line; validation checks every changed outline and derived accent in all three families."
              : "Preview checks one glyph and the sample line. Full validation checks all changed outlines and derived accents across the three families.",
          ),
    );
    return;
  }
  const r = validation.result;
  const fails = failuresOf(r);
  const oldEdits = validation.edits !== editsKey();
  const oldSample = validation.sample !== sampleKey();
  const [family, text] = JSON.parse(validation.sample);
  const staleNote =
    (oldEdits || oldSample) &&
    node(
      "p",
      { className: "stale-note" },
      oldEdits
        ? "Results for earlier edits — revalidate. "
        : `Results for earlier settings — revalidate. The sample-line check used “${text}” in ${FAMILY_NAMES[family]}. `,
      focusKey(button("Revalidate", () => schedule(true), "inline"), "revalidate"),
    );
  const glyphs = plural(r.changed.length, "changed glyph");
  const outcome = fails.length
    ? [
        node(
          "p",
          { className: "summary-title" },
          `Validation failed: ${plural(fails.length, "problem")} across ${glyphs}.`,
        ),
        failureList(fails),
      ]
    : [
        node(
          "p",
          { className: "summary-title" },
          `Validation passed: ${glyphs} checked in all three families.`,
        ),
        node(
          "p",
          {},
          "Affected geometry passes. Run the full build, tests, and slicer validation after applying the patch.",
        ),
      ];
  const w = r.warnings;
  const fillWarning =
    w.length &&
    node(
      "p",
      { className: "fill-note" },
      `Finishing filled new gaps narrower than 2w with ink in ${plural(w.length, "glyph")} (${w.slice(0, 6).join(", ")}${w.length > 6 ? ", …" : ""}); those strokes print as solid ink.`,
    );
  const thickness = node(
    "p",
    { className: "muted" },
    "Thickness above 2.85w is informational; dots and some joins intentionally exceed it.",
  );
  box.className =
    "validation-summary " +
    (fails.length || error ? "failed" : "passed") +
    (staleNote ? " stale" : "");
  box.replaceChildren(
    ...kids(error && couldNotRun(error), staleNote, outcome, fillWarning, thickness),
  );
}
// Long lists fold after the first few so the block stays readable.
function failureList(fails, shown = 8) {
  const items = (list) => list.map((f) => node("li", {}, f.message));
  if (fails.length <= shown + 1) return node("ul", {}, items(fails));
  return [
    node("ul", {}, items(fails.slice(0, shown))),
    node(
      "details",
      {},
      node("summary", {}, `Show ${fails.length - shown} more problems`),
      node("ul", {}, items(fails.slice(shown))),
    ),
  ];
}
function renderChips(r, fails, old) {
  const chips = $("affected");
  const why = (g) =>
    fails
      .filter((f) => f.family === g.family && f.char === g.char)
      .map((f) => f.message);
  const items = r.changed.map((g) => ({ ...g }));
  // A failure naming a glyph missing from the changed list still gets a chip.
  for (const f of fails)
    if (
      f.char &&
      f.family &&
      !items.some((g) => g.family === f.family && g.char === f.char)
    )
      items.push({
        family: f.family,
        char: f.char,
        failed: true,
        disappeared: f.code === "disappeared",
      });
  const rank = (g) =>
    g.disappeared
      ? 0
      : g.failed || why(g).length || (g.checks && !g.checks.ok)
        ? 1
        : g.fill_warn
          ? 2
          : 3;
  items.sort((a, b) => rank(a) - rank(b));
  const title = node(
    "p",
    { className: "chips-title" },
    "Changed glyphs · select one to preview it",
  );
  chips.className = old ? "stale" : "";
  chips.replaceChildren(...kids(items.length && title, items.map(chip)));

  function chip(g) {
    const kind = ["gone", "bad", "warn", "ok"][rank(g)];
    const name = `${g.family}:${g.char}`;
    const reason =
      why(g).join(" ") ||
      {
        gone: `Dropped from ${FAMILY_NAMES[g.family]}.`,
        bad: "Fails the geometry checks.",
        warn: "Finishing fills a new narrow gap with ink.",
        ok: "Passes.",
      }[kind];
    return node(
      "button",
      {
        type: "button",
        className: "affected " + kind,
        title: `${reason} Select to preview ${name}.`,
        "aria-label": `${name}: ${reason}`,
        "data-focus": "c:" + name,
        onclick: () => previewGlyph(g.char, g.family),
      },
      kind === "gone"
        ? `${name} dropped from ${FAMILY_NAMES[g.family]}`
        : name,
    );
  }
}

function svgPoint(e) {
  return new DOMPoint(e.clientX, e.clientY).matrixTransform(
    $("canvas").getScreenCTM().inverse(),
  );
}
// The nearest visible point within its hit area, so overlapping hit areas pick sensibly.
function nearest(p) {
  let best = null,
    dist = hitRadius;
  for (const h of handleEls.keys()) {
    const d = Math.hypot(value(h.x) - p.x, value(h.y) - p.y);
    if (d <= dist) [best, dist] = [h, d];
  }
  return best;
}
$("canvas").onpointerdown = (e) => {
  const p = svgPoint(e);
  const h = nearest(p);
  if (!h) return;
  e.preventDefault();
  // The outline under a stale or failed preview no longer matches the fields; the tag says why.
  if (previewState !== "current") return;
  const start = { x: value(h.x), y: value(h.y) };
  // Keep the pointer's offset from the point so an off-centre grab does not jump.
  drag = {
    h,
    start,
    grab: { x: p.x - start.x, y: p.y - start.y },
    moved: false,
  };
  $("canvas").setPointerCapture(e.pointerId);
  $("canvas").classList.add("dragging");
  renderLink();
};
$("canvas").onpointermove = (e) => {
  const p = svgPoint(e);
  if (!drag) {
    if (e.pointerType === "mouse") setHover(nearest(p), true);
    return;
  }
  const snap = Number($("snap").value);
  const next = {};
  for (const axis of ["x", "y"]) {
    const start = drag.start[axis];
    const round = (v) =>
      Math.max(
        Math.min(-32, start),
        Math.min(
          Math.max(32, start),
          Number((Math.round(v / snap) * snap).toFixed(4)),
        ),
      );
    // An axis changes only once the pointer reaches another grid step, so a horizontal
    // drag or a jittery click leaves the other coordinate exactly as written in the source.
    const moved = round(p[axis] - drag.grab[axis]);
    next[axis] = moved === round(start) ? start : moved;
  }
  if (next.x === value(drag.h.x) && next.y === value(drag.h.y)) return;
  if (!drag.moved) {
    drag.moved = true;
    remember();
    // Discard any preview already running: it shows the values from before the drag.
    revision++;
    setPreview("stale");
  }
  for (const axis of ["x", "y"]) {
    const id = drag.h[axis];
    set(id, next[axis]);
    const input = $("p-" + id);
    if (input) {
      input.value = value(id);
      input.closest(".control").classList.toggle("changed", id in values);
    }
  }
  for (const c of handleEls.get(drag.h).children) {
    c.setAttribute("cx", value(drag.h.x));
    c.setAttribute("cy", value(drag.h.y));
  }
  renderLink();
};
$("canvas").onpointerleave = (e) => {
  if (!drag && e.pointerType === "mouse") setHover(null, false);
};
function endDrag() {
  if (!drag) return;
  const moved = drag.moved;
  drag = null;
  $("canvas").classList.remove("dragging");
  renderLink();
  renderTag();
  if (!moved) return;
  message("Updating preview…", "progress");
  changed();
  schedule();
}
$("canvas").onpointerup = endDrag;
$("canvas").onpointercancel = endDrag;
$("search").oninput = renderTargets;
for (const id of ["glyph", "family", "text"]) $(id).onchange = previewChanged;
$("line-width").oninput = physical;
$("validate").onclick = () => schedule(true);
let resizeTimer;
// Tick numbers and hit areas are sized in screen pixels, so redraw after a resize.
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(
    () => drawn && !drag && draw(drawn.result, drawn.body),
    150,
  );
});
$("reset").onclick = () => {
  if (!selected.slots.some((s) => s.id in values)) return;
  remember();
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

function showProblems() {
  $("validation").scrollIntoView({ block: "center" });
  $("validation").focus({ preventScroll: true });
}
function validateForExport() {
  exportIntent = editsKey();
  schedule(true);
  notice(
    "export",
    "info",
    "Validating these edits in all three families; this usually takes 5 to 20 seconds. The result appears here.",
  );
}
// "M:n, M:ñ and 3 more"; the validation block lists the full messages.
function where(fails) {
  const names = [
    ...new Set(
      fails.map((f) =>
        f.char
          ? `${f.family}:${f.char}`
          : f.code === "text_gap"
            ? "the sample line"
            : f.message,
      ),
    ),
  ];
  return (
    names.slice(0, 6).join(", ") +
    (names.length > 6 ? ` and ${names.length - 6} more` : "")
  );
}
function offerExport() {
  const v = validation?.edits === editsKey() ? validation : null;
  const fails = v ? failuresOf(v.result) : [];
  if (!v)
    notice(
      "export",
      "warn",
      "These edits have not been validated across all three families yet. Validation checks every changed glyph, including derived accents and Mono, and takes a few seconds.",
      [
        ["Validate now", validateForExport, true],
        ["Export anyway", exportPatch],
      ],
    );
  else if (fails.length)
    notice(
      "export",
      "error",
      `Validation found ${plural(fails.length, "problem")} with these edits (${where(fails)}). Exporting now would put ${fails.length === 1 ? "it" : "them"} in the patch.`,
      [
        ["Show the problems", showProblems, true],
        ["Export anyway", exportPatch],
      ],
    );
  else
    notice("export", "info", "Validation passed for these edits.", [
      ["Export Git patch", exportPatch, true],
    ]);
}
$("export").onclick = () => {
  if (!Object.keys(values).length) return;
  if (
    validation?.edits === editsKey() &&
    !failuresOf(validation.result).length
  )
    return exportPatch();
  if (validating()) {
    exportIntent = editsKey();
    notice(
      "export",
      "info",
      "Validation of these edits is still running; the result appears here when it finishes.",
      [["Export anyway", exportPatch]],
    );
    return;
  }
  offerExport();
};
async function exportPatch() {
  dismiss("export");
  try {
    const r = await post("/api/export", { session: session() });
    if (!r.patch) throw new Error("There are no source changes to export.");
    download("fillaprint-glyphs.patch", r.patch, "text/x-diff");
    notice(
      "exported",
      "info",
      "Your browser saved fillaprint-glyphs.patch (usually in Downloads). Stop the tuner, then in the repository run `git apply --check <path to the patch>` and `git apply <path to the patch>`, rebuild and test. docs/TUNER.md lists every step.",
    );
  } catch (e) {
    notice("export", "error", "Patch not exported. " + e.message);
  }
}

$("import").onclick = () => $("file").click();
$("file").onchange = async () => {
  const file = $("file").files[0];
  $("file").value = "";
  if (!file) return;
  // Opening a session must not disturb the current preview or edits until it is accepted.
  const before = revision;
  notice(
    "import",
    "info",
    `Checking ${file.name} against the current source files…`,
    [],
    false,
  );
  let s = null;
  try {
    if (file.size <= 262144) s = parseSession(await file.text());
    if (!s) throw new Error("That file is not a tuner session.");
    try {
      await post("/api/export", { session: s });
    } catch (e) {
      e.message += commitHint(s, e.message);
      throw e;
    }
    if (revision !== before)
      throw new Error(
        "You made another edit while the session was being checked. Open it again to replace those edits.",
      );
  } catch (e) {
    notice(
      "import",
      "error",
      `Session not opened. ${e.message} Your current edits are unchanged.`,
    );
    return;
  }
  remember();
  values = edits(s.values);
  changed();
  const n = Object.keys(values).length;
  const first = editedTargets()[0];
  if (first && !editedCount(selected)) select(first);
  else {
    renderControls();
    schedule();
  }
  notice(
    "import",
    "info",
    `Opened ${file.name}: ${plural(n, "edit")}${n ? ` (${describe(editedTargets())})` : ""}. Undo returns to the edits you had before.`,
  );
};

// Another tab writing the autosave would otherwise be overwritten by this tab's next edit.
window.addEventListener("storage", (e) => {
  if (!catalog || (e.key !== STORAGE && e.key !== null)) return;
  const other = e.key === null ? null : parseSession(e.newValue);
  if (editsKey(edits(other?.values)) === editsKey()) return;
  conflict = true;
  renderEditCount();
  notice(
    "conflict",
    "warn",
    "Another tuner tab changed the autosaved edits. This tab has stopped autosaving so the two tabs do not overwrite each other.",
    [
      ["Load the other tab's edits", loadOtherTab, true],
      ["Keep this tab's edits", keepThisTab],
    ],
    false,
  );
});
// Autosave keeps edits across a reload, except while paused by a conflict: then edits made
// here exist only in this page, and leaving it should ask first.
window.addEventListener("beforeunload", (e) => {
  if (!conflict) return;
  const saved = parseSession(localStorage.getItem(STORAGE));
  if (editsKey(edits(saved?.values)) === editsKey()) return;
  e.preventDefault();
  e.returnValue = "";
});
async function loadOtherTab() {
  const s = parseSession(localStorage.getItem(STORAGE));
  try {
    if (s) await post("/api/export", { session: s });
  } catch (e) {
    notice(
      "conflict",
      "error",
      `The other tab's edits could not be loaded: ${e.message}`,
      [["Keep this tab's edits", keepThisTab, true]],
      false,
    );
    return;
  }
  conflict = false;
  remember();
  values = edits(s?.values);
  changed();
  renderControls();
  schedule();
  notice(
    "conflict",
    "info",
    `Loaded ${plural(Object.keys(values).length, "edit")} from the other tab. Undo returns to this tab's edits.`,
  );
}
function keepThisTab() {
  conflict = false;
  autosave();
  renderEditCount();
}

// Returns the number of autosaved edits restored.
async function restore() {
  let saved = null;
  try {
    saved = parseSession(localStorage.getItem(STORAGE));
  } catch {}
  if (!Object.keys(saved?.values || {}).length) return 0;
  try {
    await post("/api/export", { session: saved });
  } catch (e) {
    // Without a server the autosave cannot be checked; keep it rather than overwrite it.
    if (e.code === "offline") throw e;
    download(
      "fillaprint-previous-session.json",
      JSON.stringify(saved, null, 2) + "\n",
      "application/json",
    );
    notice(
      "restore",
      "warn",
      `Your autosaved edits could not be loaded: ${e.message}${commitHint(saved, e.message)} They were downloaded as fillaprint-previous-session.json, so nothing is lost; this checkout starts without them.`,
    );
    return 0;
  }
  values = edits(saved.values);
  return Object.keys(values).length;
}
function discardRestored() {
  remember();
  values = {};
  changed();
  renderControls();
  schedule();
  notice(
    "restored",
    "info",
    "Discarded the restored edits. Undo brings them back.",
  );
}
async function start() {
  try {
    catalog = await call("/api/catalog");
    for (const t of catalog.targets) for (const s of t.slots) slots[s.id] = s;
    const restored = await restore();
    changed();
    select(
      editedTargets()[0] ||
        catalog.targets.find((t) => t.char === "a" && t.group === "Base") ||
        catalog.targets[0],
    );
    if (restored)
      notice(
        "restored",
        "info",
        `Restored ${plural(restored, "edit")} from this browser's autosave (${describe(editedTargets())}). Edited constructions are marked in the left rail.`,
        [["Discard these edits", discardRestored]],
      );
  } catch (e) {
    catalog = null;
    setPreview("failed");
    $("count").textContent = "Source parameters not loaded.";
    message(
      e.code === "offline"
        ? e.message
        : "Could not start the tuner: " + e.message,
      "error",
      [button("Reload page", () => location.reload(), "inline")],
    );
  }
}
start();
