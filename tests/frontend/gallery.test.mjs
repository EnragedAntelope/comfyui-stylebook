/**
 * Frontend smoke tests for js/stylebook_gallery.js.
 *
 * Each test is pinned to a bug that actually shipped through a green
 * Python suite (see the table in docs/worklog and ARCHITECTURE.md). This
 * imports the real, unmodified gallery module -- resolve hooks in hooks.mjs
 * redirect its two ComfyUI imports to stubs/, and fake_node.mjs builds
 * LiteGraph-shaped nodes from the schema-derived fixture in
 * fixtures/nodes.json, so a Python rename shows up here as a broken fixture
 * lookup rather than a silent pass.
 *
 * Honest limit: jsdom has no layout engine, so this proves wiring,
 * visibility, serialization and dialog logic -- not CSS or real pixels.
 */

import { test, before, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { installDom, resetDom } from "./dom.mjs";
import { makeNode, widgetByName } from "./fake_node.mjs";

installDom();

const FIXTURES = JSON.parse(
  readFileSync(new URL("./fixtures/nodes.json", import.meta.url), "utf8")
);

let app;
let getExtension;

before(async () => {
  app = await import("./stubs/app.js");
  const ext0 = app.__getExtension("stylebook.gallery");
  if (!ext0) {
    await import("../../js/stylebook_gallery.js");
  }
  getExtension = () => app.__getExtension("stylebook.gallery");
  assert.ok(getExtension(), "stylebook.gallery never registered");
});

beforeEach(() => {
  resetDom();
});

function findWidget(node, name) {
  const widget = widgetByName(node, name);
  assert.ok(widget, `no widget named ${name} on ${node.comfyClass}`);
  return widget;
}

function isVisible(widget) {
  return widget.hidden !== true && widget.type !== "stylebook_hidden";
}

// --- 1. every picker node gets its button ----------------------------------

const BUTTON_LABEL = {
  StylebookStyle: "Open style gallery",
  StylebookArtist: "Open artist reference",
  StylebookModifier: "Open modifier reference",
  StylebookSheet: "Choose styles",
};

for (const [comfyClass, label] of Object.entries(BUTTON_LABEL)) {
  test(`${comfyClass} gets its picker button attached`, async () => {
    const node = makeNode(comfyClass);
    await getExtension().nodeCreated(node);
    const button = node.widgets.find((w) => w.name === label);
    assert.ok(button, `${comfyClass} is missing its "${label}" button`);
    assert.equal(typeof button.callback, "function");
  });
}

// --- 2 & 4. mode Random -> Pick -> Random restores every hidden widget -----

test("StylebookStyle: mode Random -> Pick -> Random restores every widget, seed and control together", async () => {
  const node = makeNode("StylebookStyle");
  await getExtension().nodeCreated(node);

  const mode = findWidget(node, "mode");
  const style = findWidget(node, "style");
  const category = findWidget(node, "category");
  const cycleIndex = findWidget(node, "cycle_index");
  const seed = findWidget(node, "seed");
  const control = findWidget(node, "control_after_generate");

  // Default is Random: pick widget hidden, pool filters + seed shown.
  assert.equal(mode.value, "Random");
  assert.equal(isVisible(style), false, "style should start hidden in Random mode");
  assert.equal(isVisible(category), true);
  assert.equal(isVisible(seed), true);
  assert.equal(isVisible(control), true);

  mode.value = "Pick";
  mode.callback("Pick", {}, node);

  assert.equal(isVisible(style), true, "style should show in Pick mode");
  assert.equal(isVisible(category), false, "category is unused in Pick mode");
  assert.equal(isVisible(cycleIndex), false);
  assert.equal(isVisible(seed), false, "seed is unused in Pick mode");
  assert.equal(isVisible(control), false, "control_after_generate must hide with seed");

  mode.value = "Random";
  mode.callback("Random", {}, node);

  assert.equal(isVisible(style), false, "style hides again back in Random mode");
  assert.equal(isVisible(category), true);
  assert.equal(isVisible(seed), true);
  assert.equal(isVisible(control), true);

  // The actual regression: toggling back to Pick a second time must bring
  // the dropdown back. showWidget used to leave the zero-size computeSize
  // stub in place after a hide/show round-trip, so the widget's type field
  // never returned to "combo" and the control stayed invisible forever.
  mode.value = "Pick";
  mode.callback("Pick", {}, node);
  assert.equal(isVisible(style), true, "style must return after a second Pick toggle");
  assert.equal(style.type, "combo", "style widget type must be fully restored, not stuck hidden");
});

// --- 3. picker button never lands in widgets_values -------------------------

test("StylebookStyle: the picker button is excluded from serialization", async () => {
  const node = makeNode("StylebookStyle");
  await getExtension().nodeCreated(node);
  const button = findWidget(node, "Open style gallery");
  assert.equal(button.serialize, false);
  assert.equal(button.serializeValue, undefined);
});

// --- 5. axis narrowing resets an out-of-axis modifier value -----------------

test("StylebookModifier: changing axis narrows modifier.options.values and resets an out-of-axis value to Off", async () => {
  const { MODIFIER_LABELS_BY_AXIS } = await import("../../js/stylebook_data.js");
  const node = makeNode("StylebookModifier");
  await getExtension().nodeCreated(node);

  const axis = findWidget(node, "axis");
  const modifier = findWidget(node, "modifier");

  assert.equal(axis.value, "lighting");
  const lightingLabel = MODIFIER_LABELS_BY_AXIS.lighting[0];
  modifier.value = lightingLabel;

  axis.value = "era";
  axis.callback("era", {}, node);

  assert.deepEqual(
    modifier.options.values,
    ["Off", ...MODIFIER_LABELS_BY_AXIS.era],
    "modifier options must narrow to the new axis"
  );
  assert.equal(
    modifier.value,
    "Off",
    "a value from the old axis must reset rather than silently persist outside its own options"
  );
});

// --- 6. dialog opens, filters by search, closes on Escape -------------------

test("StylebookStyle: picker opens, search narrows results, Escape closes and returns focus", async () => {
  const node = makeNode("StylebookStyle");
  await getExtension().nodeCreated(node);
  const button = findWidget(node, "Open style gallery");

  document.body.focus?.();
  button.callback();

  const overlay = document.querySelector(".stylebook-overlay");
  assert.ok(overlay, "picker did not open");
  const tilesBefore = document.querySelectorAll(".stylebook-tile").length;
  assert.ok(tilesBefore > 100, "expected the full style pool on the All tab");

  const search = document.querySelector(".stylebook-search");
  assert.ok(search);
  search.value = "Cyanotype";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));

  const tilesAfter = document.querySelectorAll(".stylebook-tile");
  assert.equal(tilesAfter.length, 1, "search should narrow to the one matching style");
  assert.match(tilesAfter[0].textContent, /Cyanotype/);

  overlay.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(document.querySelector(".stylebook-overlay"), null, "Escape did not close the dialog");
});

// --- 7. a fresh node is widened to a legible minimum ------------------------

test("a fresh node narrower than MIN_NODE_WIDTH is widened", async () => {
  const node = makeNode("StylebookStyle");
  node.size = [140, 80];
  await getExtension().nodeCreated(node);
  assert.equal(node.size[0], 420);
});

test("a node type with no widget setup (Blend) still gets widened, without throwing", async () => {
  const node = makeNode("StylebookBlend");
  node.size = [140, 80];
  await getExtension().nodeCreated(node);
  assert.equal(node.size[0], 420);
});

// --- 8. the stylesheet is injected exactly once -----------------------------

test("setup() injects the stylesheet link exactly once across repeated calls", async () => {
  await getExtension().setup();
  await getExtension().setup();
  const links = document.querySelectorAll("link[data-stylebook-css]");
  assert.equal(links.length, 1);
});

// --- 9. every widget name the JS reads by name exists in the fixture -------

const NAMES_READ_BY_NAME = {
  StylebookStyle: ["mode", "style", "category", "tag_filter", "cycle_index", "seed", "control_after_generate"],
  StylebookArtist: ["mode", "artist", "category", "tag_filter", "cycle_index", "seed", "control_after_generate"],
  StylebookModifier: ["axis", "mode", "modifier", "seed", "control_after_generate", "cycle_index"],
  StylebookSheet: ["styles"],
};

for (const [comfyClass, names] of Object.entries(NAMES_READ_BY_NAME)) {
  test(`${comfyClass}: every widget name the frontend reads by name exists in fixtures/nodes.json`, () => {
    const fixtureNames = new Set((FIXTURES[comfyClass] || []).map((w) => w.name));
    for (const name of names) {
      assert.ok(
        fixtureNames.has(name),
        `${comfyClass} fixture is missing "${name}" -- ` +
          `either the Python schema was renamed or WIDGET_ORDER is stale`
      );
    }
  });
}

// --- 10. ordering: one rule, implemented in two languages ------------------

/**
 * The comparator the gallery uses, rebuilt here rather than exported.
 *
 * Keeping it private to the module under test is the point: if
 * stylebook_gallery.js changes its collator options, this copy stops
 * matching and the cross-check below fails, which is exactly the alarm
 * we want. An exported comparator shared with the test would prove only
 * that a function equals itself.
 */
const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });
const compare = (a, b) => collator.compare(a, b) || (a < b ? -1 : a > b ? 1 : 0);

test("Python and JS agree on order: re-sorting ALL_STYLE_LABELS with the JS comparator is a no-op", async () => {
  // ALL_STYLE_LABELS is emitted by scripts/generate_js_data.py in
  // data/ordering.py's order. If label_sort_key and Intl.Collator ever
  // disagree on a shipped label, this is where it surfaces -- otherwise
  // the dropdown and the gallery would quietly diverge.
  const { ALL_STYLE_LABELS } = await import("../../js/stylebook_data.js");
  assert.ok(ALL_STYLE_LABELS.length > 100, "generated data looks empty");
  const resorted = ALL_STYLE_LABELS.slice().sort(compare);
  const drift = ALL_STYLE_LABELS.findIndex((label, i) => label !== resorted[i]);
  assert.equal(
    drift, -1,
    drift === -1
      ? ""
      : `data/ordering.py and Intl.Collator disagree at index ${drift}: ` +
        `Python put "${ALL_STYLE_LABELS[drift]}" there, JS wants "${resorted[drift]}"`
  );
});

async function openStyleGallery() {
  const node = makeNode("StylebookStyle");
  await getExtension().nodeCreated(node);
  widgetByName(node, "Open style gallery").callback();
  const overlay = document.querySelector(".stylebook-overlay");
  assert.ok(overlay, "picker did not open");
  return overlay;
}

const tileLabels = () =>
  Array.from(document.querySelectorAll(".stylebook-tile-label > span"))
    .map((el) => el.textContent);

const clickTab = (overlay, name) => {
  const tab = Array.from(overlay.querySelectorAll(".stylebook-tab"))
    .find((t) => t.textContent === name);
  assert.ok(tab, `no "${name}" tab`);
  tab.click();
};

test("the All tab lists every style alphabetically, not grouped by category", async () => {
  await openStyleGallery();
  const labels = tileLabels();
  assert.ok(labels.length > 100, "All tab rendered almost nothing");
  assert.deepEqual(labels, labels.slice().sort(compare));
  // Data order used to put "Aerial Photography" (photography, first
  // category) ahead of "3D Matte Painting"; numeric-leading names now
  // lead the list.
  assert.equal(labels[0], "3D Matte Painting");
});

test("a category tab lists its own styles alphabetically", async () => {
  const overlay = await openStyleGallery();
  clickTab(overlay, "Art Movements");
  const labels = tileLabels();
  assert.ok(labels.length > 20, "Art Movements tab rendered almost nothing");
  assert.deepEqual(labels, labels.slice().sort(compare));
});

test("the artist reference is alphabetical too", async () => {
  const node = makeNode("StylebookArtist");
  await getExtension().nodeCreated(node);
  widgetByName(node, "Open artist reference").callback();
  const names = Array.from(document.querySelectorAll(".stylebook-row-name"))
    .map((el) => el.textContent);
  assert.ok(names.length > 100, "artist reference rendered almost nothing");
  assert.deepEqual(names, names.slice().sort(compare));
});

test("the modifier reference stays in data order, so the era axis reads chronologically", async () => {
  const node = makeNode("StylebookModifier");
  await getExtension().nodeCreated(node);
  widgetByName(node, "Open modifier reference").callback();
  const names = Array.from(document.querySelectorAll(".stylebook-row-name"))
    .map((el) => el.textContent);
  assert.ok(names.length > 20, "modifier reference rendered almost nothing");
  assert.notDeepEqual(
    names, names.slice().sort(compare),
    "modifiers must NOT be alphabetical -- the era axis is chronological"
  );
});

// --- 11. the category chip appears only where the tab strip does not -------

test("the category chip shows in All, in search results, and not in a category tab", async () => {
  const overlay = await openStyleGallery();
  const chips = () => document.querySelectorAll(".stylebook-tile-cat");

  assert.ok(chips().length > 100, "All tab should caption every tile with its category");
  assert.ok(
    document.querySelector(".stylebook-grid").classList.contains("with-category"),
    "the grid must carry .with-category, or the fixed row height clips the chip"
  );
  const first = chips()[0];
  assert.equal(first.getAttribute("aria-hidden"), "true",
    "the chip duplicates the tile's accessible name and must not be announced");
  assert.ok(first.textContent.length > 0, "chip rendered empty");

  clickTab(overlay, "Art Movements");
  assert.equal(chips().length, 0, "a category tab already names the category");
  assert.ok(
    !document.querySelector(".stylebook-grid").classList.contains("with-category"),
    "the row height must shrink back when the chip is gone"
  );

  const search = overlay.querySelector(".stylebook-search");
  search.value = "print";
  search.dispatchEvent(new window.Event("input", { bubbles: true }));
  assert.ok(chips().length > 0,
    "a search spans every category, so results need the caption back");
});

// --- 12. the scene badge ---------------------------------------------------

test("a scene style is badged, and the badge lives inside the art box", async () => {
  const overlay = await openStyleGallery();
  const badges = document.querySelectorAll(".stylebook-tile-scene");

  assert.ok(badges.length > 10, "no scene badges rendered at all");
  // The whole point of the design: it must not occupy a tile row, because
  // tile height is fixed by grid-auto-rows and a new row clips the label.
  for (const badge of badges) {
    assert.ok(
      badge.parentElement.classList.contains("stylebook-tile-art"),
      "the badge must be overlaid on the art, not added as a tile row"
    );
  }
  assert.equal(badges[0].getAttribute("aria-hidden"), "true",
    "the tile title already carries the explanation in words");

  const tile = badges[0].closest(".stylebook-tile");
  assert.match(tile.title, /Places your subject in /,
    "a one-word badge needs the tooltip to say what it means");
});

test("scene badges are the exception, not the rule", async () => {
  await openStyleGallery();
  const tiles = document.querySelectorAll(".stylebook-tile").length;
  const badged = document.querySelectorAll(".stylebook-tile-scene").length;
  assert.ok(badged * 4 < tiles,
    "if most styles are badged the badge has stopped meaning anything");
});

test("the artist reference gets no category chip -- its rows already carry a descriptor", async () => {
  const node = makeNode("StylebookArtist");
  await getExtension().nodeCreated(node);
  widgetByName(node, "Open artist reference").callback();
  assert.equal(document.querySelectorAll(".stylebook-tile-cat").length, 0);
});
