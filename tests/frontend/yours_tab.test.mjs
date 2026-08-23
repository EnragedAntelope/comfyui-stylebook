/**
 * Frontend tests for the "Yours" picker tab (js/stylebook_gallery.js),
 * fed by the /stylebook/user_data route (stylebook_nodes/routes.py).
 *
 * Half the original feature complaint: a custom style added via
 * user_styles.json was selectable in the Pick dropdown but invisible in
 * the gallery. These tests are against the real gallery module; only
 * fetch() is stubbed.
 *
 * Ordering note: gallery.js keeps its fetched user data in one
 * module-level variable, shared by every test in this process. A failed
 * or non-ok fetch deliberately *keeps* whatever was already loaded rather
 * than clearing it -- a transient failure should not wipe previously
 * loaded custom data -- so the tests that expect an empty/no-Yours-tab
 * state must run before any test that successfully populates real data.
 * Declaration order is execution order here (node:test runs a file's
 * top-level tests sequentially), so keep it that way if this file grows.
 */

import { test, before, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { installDom, resetDom, settle, stubFetch } from "./dom.mjs";
import { makeNode, widgetByName } from "./fake_node.mjs";

installDom();

let app;

before(async () => {
  app = await import("./stubs/app.js");
  if (!app.__getExtension("stylebook.gallery")) {
    await import("../../js/stylebook_gallery.js");
  }
});

beforeEach(() => {
  resetDom();
});

function jsonResponse(body, ok = true) {
  return () => Promise.resolve({ ok, json: () => Promise.resolve(body) });
}

async function openStylePicker() {
  const node = makeNode("StylebookStyle");
  await app.__getExtension("stylebook.gallery").nodeCreated(node);
  const button = widgetByName(node, "Open style gallery");
  button.callback();
  await settle();
  return document.querySelector(".stylebook-overlay");
}

// --- state still empty at this point: failure-path tests go first ---------

test("a failed fetch leaves the picker exactly as it is today (built-ins only, no throw)", async () => {
  stubFetch(() => Promise.reject(new Error("network down")));
  await app.__getExtension("stylebook.gallery").setup(); // must not throw

  await openStylePicker();
  const tabs = Array.from(document.querySelectorAll(".stylebook-tab")).map((t) => t.textContent);
  assert.ok(!tabs.includes("Yours"));
  assert.ok(document.querySelectorAll(".stylebook-tile").length > 100, "built-ins must still render");
});

test("a non-ok response is treated the same as no custom data", async () => {
  stubFetch(jsonResponse({ styles: [{ id: "x", label: "X", category: "photography" }] }, false));
  await app.__getExtension("stylebook.gallery").setup();

  await openStylePicker();
  const tabs = Array.from(document.querySelectorAll(".stylebook-tab")).map((t) => t.textContent);
  assert.ok(!tabs.includes("Yours"), "a non-ok response must not populate the Yours tab");
});

test("no user data: the picker has no Yours tab", async () => {
  stubFetch(jsonResponse({ styles: [], artists: [], modifiers: [] }));
  await app.__getExtension("stylebook.gallery").setup();

  await openStylePicker();
  const tabs = Array.from(document.querySelectorAll(".stylebook-tab")).map((t) => t.textContent);
  assert.ok(!tabs.includes("Yours"), "a Yours tab should not appear with no custom data");
});

// --- from here on, real custom data is loaded and stays loaded ------------

test("with custom styles: the picker gains a Yours tab holding exactly the custom entries", async () => {
  stubFetch(jsonResponse({
    styles: [
      { id: "my_style", label: "My Style", category: "photography", detail: "a hand-written look." },
      { id: "another", label: "Another One", category: "illustration", detail: "" },
    ],
    artists: [],
    modifiers: [],
  }));
  await app.__getExtension("stylebook.gallery").setup();

  await openStylePicker();
  const tabs = Array.from(document.querySelectorAll(".stylebook-tab"));
  const yours = tabs.find((t) => t.textContent === "Yours");
  assert.ok(yours, "Yours tab should appear once custom styles exist");

  yours.click();
  const tiles = Array.from(document.querySelectorAll(".stylebook-tile"));
  assert.equal(tiles.length, 2, "Yours tab should show exactly the two custom entries");
  const labels = tiles.map((t) => t.textContent.trim());
  assert.ok(labels.some((l) => l.includes("My Style")));
  assert.ok(labels.some((l) => l.includes("Another One")));
});

test("a custom style also appears under its own real category, not only under Yours", async () => {
  stubFetch(jsonResponse({
    styles: [{ id: "my_style", label: "My Style", category: "photography", detail: "" }],
    artists: [],
    modifiers: [],
  }));
  await app.__getExtension("stylebook.gallery").setup();

  const overlay = await openStylePicker();
  const photographyTab = Array.from(overlay.querySelectorAll(".stylebook-tab"))
    .find((t) => t.textContent === "Photography");
  assert.ok(photographyTab, "Photography tab should exist");
  photographyTab.click();

  const found = Array.from(document.querySelectorAll(".stylebook-tile"))
    .some((tile) => tile.textContent.includes("My Style"));
  assert.ok(found, "a custom style should still be reachable from its real category tab");
});

test("a custom style is filed alphabetically among the built-ins, not appended after them", async () => {
  // The picker sorts the merged list rather than reading the generator's
  // order, precisely so an entry the generator never saw lands in the
  // right place. A custom style tacked onto the end would be as buried
  // as the data-order additions this release stopped producing.
  stubFetch(jsonResponse({
    styles: [{ id: "aaa_custom", label: "Aaa Custom Look", category: "photography", detail: "" }],
    artists: [],
    modifiers: [],
  }));
  await app.__getExtension("stylebook.gallery").setup();

  await openStylePicker();
  const labels = Array.from(document.querySelectorAll(".stylebook-tile-label > span"))
    .map((el) => el.textContent);
  const index = labels.indexOf("Aaa Custom Look");
  assert.ok(index >= 0, "the custom style should be in the All tab");
  assert.ok(
    index < labels.length - 1,
    "a custom style must not be pinned to the end of the list"
  );
  const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });
  assert.deepEqual(labels, labels.slice().sort((a, b) => collator.compare(a, b) || (a < b ? -1 : a > b ? 1 : 0)));
});
