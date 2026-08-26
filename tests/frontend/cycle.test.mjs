/**
 * js/stylebook_cycle.js: proves the auto-advance toggle installs cleanly and
 * actually advances cycle_index on a resolved Cycle-mode run, wrapping at the
 * pool size the backend reports. Also proves a non-Cycle run (or the toggle
 * off) leaves the index alone, and that the toggle is a node property -- not a
 * schema change -- so it defaults to off on a fresh node.
 */

import { test, before } from "node:test";
import assert from "node:assert/strict";
import { installDom } from "./dom.mjs";
import { makeNode } from "./fake_node.mjs";
import { api, __dispatch } from "./stubs/api.js";
import { widgetsByName } from "../../js/stylebook_shared.js";

installDom();

const EVENT_NAME = "stylebook.resolved";

let app;

before(async () => {
  app = await import("./stubs/app.js");
  if (!app.__getExtension("stylebook.cycle")) {
    await import("../../js/stylebook_cycle.js");
  }
});

test("stylebook.cycle registers and adds an Auto-advance menu toggle on Stylebook nodes", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  assert.ok(ext, "stylebook.cycle never registered");

  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);
  assert.equal(typeof node.getExtraMenuOptions, "function");

  const options = [];
  node.getExtraMenuOptions({}, options);
  const entry = options.find((o) => o.content.startsWith("Auto-advance cycle:"));
  assert.ok(entry, "Auto-advance cycle entry was not added");
  assert.equal(entry.content, "Auto-advance cycle: OFF");
  assert.equal(typeof entry.callback, "function");
});

test("the toggle flips the stylebook_auto_advance node property", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);

  const options = [];
  node.getExtraMenuOptions({}, options);
  const entry = options.find((o) => o.content.startsWith("Auto-advance cycle:"));

  entry.callback();
  assert.equal(node.properties["stylebook_auto_advance"], true);
  const options2 = [];
  node.getExtraMenuOptions({}, options2);
  assert.equal(
    options2.find((o) => o.content.startsWith("Auto-advance cycle:")).content,
    "Auto-advance cycle: ON"
  );

  // Toggle back off.
  options2.find((o) => o.content.startsWith("Auto-advance cycle:")).callback();
  assert.equal(node.properties["stylebook_auto_advance"], false);
});

test("auto-advance steps cycle_index by one and wraps at the pool size", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);
  node.properties = { stylebook_auto_advance: true };

  const widgets = widgetsByName(node);
  const modeWidget = widgets["mode"];
  const cycleWidget = widgets["cycle_index"];
  modeWidget.value = "Cycle";
  cycleWidget.value = 0;

  // Pool of 3: 0 -> 1 -> 2 -> 0 (wrap).
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 3 });
  assert.equal(cycleWidget.value, 1);
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 3 });
  assert.equal(cycleWidget.value, 2);
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 3 });
  assert.equal(cycleWidget.value, 0);
});

test("auto-advance does nothing when the toggle is off or mode is not Cycle", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);
  // Toggle off by default.
  const widgets = widgetsByName(node);
  const cycleWidget = widgets["cycle_index"];
  widgets["mode"].value = "Cycle";
  cycleWidget.value = 0;

  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 5 });
  assert.equal(cycleWidget.value, 0, "off toggle must not advance");

  // Turn on but switch out of Cycle mode.
  node.properties = { stylebook_auto_advance: true };
  widgets["mode"].value = "Random";
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 5 });
  assert.equal(cycleWidget.value, 0, "non-Cycle mode must not advance");
});

test("auto-advance ignores events for other nodes and a pool size of 1", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);
  node.properties = { stylebook_auto_advance: true };
  const widgets = widgetsByName(node);
  widgets["mode"].value = "Cycle";
  widgets["cycle_index"].value = 0;

  __dispatch(EVENT_NAME, { node_id: "other-node", cycle_pool_size: 4 });
  assert.equal(widgets["cycle_index"].value, 0, "other node's event ignored");

  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 1 });
  assert.equal(widgets["cycle_index"].value, 0, "pool of 1 never advances");
});

test("stylebook.cycle leaves a non-Stylebook node's menu untouched", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = { comfyClass: "SomeOtherPack", widgets: [] };
  await ext.nodeCreated(node);
  assert.equal(node.getExtraMenuOptions, undefined);
});
