/**
 * js/stylebook_cycle.js: proves the auto-advance toggle installs cleanly and
 * actually advances cycle_index once per queued item (afterQueued), wrapping at the
 * pool size the backend reports. Also proves a non-Cycle run (or the toggle
 * off) leaves the index alone, and that the toggle is a node property -- not a
 * schema change -- so it defaults to ON (advances) on a fresh Cycle-capable
 * node; the menu toggle turns it off to hold a fixed index.
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
  assert.equal(entry.content, "Auto-advance cycle: ON");
  assert.equal(typeof entry.callback, "function");
});

test("the toggle flips the stylebook_auto_advance node property", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);

  const options = [];
  node.getExtraMenuOptions({}, options);
  const entry = options.find((o) => o.content.startsWith("Auto-advance cycle:"));

  // Defaults to ON: Cycle mode is expected to advance.
  assert.equal(entry.content, "Auto-advance cycle: ON");

  // First click turns it OFF.
  entry.callback();
  assert.equal(node.properties["stylebook_auto_advance"], false);
  const options2 = [];
  node.getExtraMenuOptions({}, options2);
  assert.equal(
    options2.find((o) => o.content.startsWith("Auto-advance cycle:")).content,
    "Auto-advance cycle: OFF"
  );

  // Second click turns it back ON.
  options2.find((o) => o.content.startsWith("Auto-advance cycle:")).callback();
  assert.equal(node.properties["stylebook_auto_advance"], true);
});

function cycleNode(ext, properties = { stylebook_auto_advance: true }) {
  const node = makeNode("StylebookStyle");
  node.properties = properties;
  const widgets = widgetsByName(node);
  widgets["mode"].value = "Cycle";
  widgets["cycle_index"].value = 0;
  return ext.nodeCreated(node).then(() => ({ node, widgets }));
}

test("a queued run steps cycle_index by one and wraps at the reported pool size", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const { node, widgets } = await cycleNode(ext);
  const cycleWidget = widgets["cycle_index"];

  // The backend reports the pool once, on the first run.
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 3 });
  assert.equal(cycleWidget.value, 0, "the event alone must not advance");

  // Pool of 3: 0 -> 1 -> 2 -> 0 (wrap).
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 1);
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 2);
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 0);
});

test("a batch of N queued items walks N consecutive entries", async () => {
  // ComfyUI serialises every batch item before any executes, so the advance
  // has to happen per queued item, not per execution event.
  const ext = app.__getExtension("stylebook.cycle");
  const { widgets } = await cycleNode(ext);
  const cycleWidget = widgets["cycle_index"];
  const sent = [];
  for (let i = 0; i < 4; i += 1) {
    sent.push(cycleWidget.value); // what graphToPrompt would serialise
    cycleWidget.afterQueued();
  }
  assert.deepEqual(sent, [0, 1, 2, 3]);
  assert.equal(cycleWidget.value, 4);
});

test("before any event the index counts up and wraps at the widget ceiling", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const { widgets } = await cycleNode(ext);
  const cycleWidget = widgets["cycle_index"];
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 1);
  cycleWidget.options.max = 5;
  cycleWidget.value = 5;
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 0);
});

test("the advance does nothing when the toggle is off, the mode is not Cycle, or the node is muted", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const off = await cycleNode(ext, { stylebook_auto_advance: false });
  off.widgets["cycle_index"].afterQueued();
  assert.equal(off.widgets["cycle_index"].value, 0, "off toggle must not advance");

  const random = await cycleNode(ext);
  random.widgets["mode"].value = "Random";
  random.widgets["cycle_index"].afterQueued();
  assert.equal(random.widgets["cycle_index"].value, 0, "non-Cycle mode must not advance");

  const muted = await cycleNode(ext);
  muted.node.mode = 2;
  muted.widgets["cycle_index"].afterQueued();
  assert.equal(muted.widgets["cycle_index"].value, 0, "a muted node must not advance");
});

test("pool events for other nodes are ignored, and a pool of 1 never advances", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const { node, widgets } = await cycleNode(ext);
  const cycleWidget = widgets["cycle_index"];

  // Another node's pool of 1 must not freeze this one.
  __dispatch(EVENT_NAME, { node_id: "other-node", cycle_pool_size: 1 });
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 1, "other node's event ignored");

  cycleWidget.value = 0;
  __dispatch(EVENT_NAME, { node_id: node.id, cycle_pool_size: 1 });
  cycleWidget.afterQueued();
  assert.equal(cycleWidget.value, 0, "pool of 1 never advances");
});

test("a numeric node id matches the event's string id", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle", 7);
  node.properties = { stylebook_auto_advance: true };
  const widgets = widgetsByName(node);
  widgets["mode"].value = "Cycle";
  await ext.nodeCreated(node);
  __dispatch(EVENT_NAME, { node_id: "7", cycle_pool_size: 2 });
  widgets["cycle_index"].afterQueued();
  widgets["cycle_index"].afterQueued();
  assert.equal(widgets["cycle_index"].value, 0, "pool of 2 wraps after two steps");
});

test("an existing afterQueued on the widget still runs", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = makeNode("StylebookStyle");
  node.properties = { stylebook_auto_advance: true };
  const widgets = widgetsByName(node);
  widgets["mode"].value = "Cycle";
  let inherited = 0;
  widgets["cycle_index"].afterQueued = () => { inherited += 1; };
  await ext.nodeCreated(node);
  widgets["cycle_index"].afterQueued();
  assert.equal(inherited, 1);
  assert.equal(widgets["cycle_index"].value, 1);
});

test("stylebook.cycle leaves a non-Stylebook node's menu untouched", async () => {
  const ext = app.__getExtension("stylebook.cycle");
  const node = { comfyClass: "SomeOtherPack", widgets: [] };
  await ext.nodeCreated(node);
  assert.equal(node.getExtraMenuOptions, undefined);
});
