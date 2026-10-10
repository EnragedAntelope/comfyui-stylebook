/**
 * Frontend tests for js/stylebook_readout.js: the "Copy resolved prompt"
 * and "Pin this pick" context-menu items driven by the backend's
 * `stylebook.resolved` event.
 */

import { test, before, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { installDom, resetDom } from "./dom.mjs";
import { makeGraphTree, makeNode } from "./fake_node.mjs";

installDom();

let app;
let apiStub;

before(async () => {
  app = await import("./stubs/app.js");
  apiStub = await import("./stubs/api.js");
  if (!app.__getExtension("stylebook.readout")) {
    await import("../../js/stylebook_readout.js");
  }
});

beforeEach(() => {
  resetDom();
  apiStub.__reset();
});

async function setUp(comfyClass, id = "1") {
  const node = makeNode(comfyClass, id);
  await app.__getExtension("stylebook.readout").nodeCreated(node);
  return node;
}

function menuFor(node) {
  const options = [];
  node.getExtraMenuOptions({}, options);
  return options;
}

function find(options, contentStart) {
  return options.find((o) => o.content.startsWith(contentStart));
}

// --- Copy present everywhere, Pin only where there is a real pick ----------

const ALL_NODES = ["StylebookStyle", "StylebookArtist", "StylebookModifier", "StylebookSheet", "StylebookBlend"];
const PIN_NODES = new Set(["StylebookStyle", "StylebookArtist", "StylebookModifier"]);

for (const comfyClass of ALL_NODES) {
  test(`${comfyClass}: Copy resolved prompt is always present`, async () => {
    const node = await setUp(comfyClass);
    const copy = find(menuFor(node), "Copy resolved prompt");
    assert.ok(copy, "Copy resolved prompt is missing");
  });

  test(`${comfyClass}: Pin this pick is ${PIN_NODES.has(comfyClass) ? "present" : "absent"}`, async () => {
    const node = await setUp(comfyClass);
    const pin = find(menuFor(node), "Pin this pick");
    if (PIN_NODES.has(comfyClass)) {
      assert.ok(pin, "Pin this pick should be present on this node type");
    } else {
      assert.equal(pin, undefined, "Pin this pick must not appear on this node type");
    }
  });
}

// --- disabled before any event arrives --------------------------------------

test("before any event, Copy and Pin are both disabled with a clear label", async () => {
  const node = await setUp("StylebookStyle");
  const options = menuFor(node);
  const copy = find(options, "Copy resolved prompt");
  const pin = find(options, "Pin this pick");
  assert.equal(copy.disabled, true);
  assert.match(copy.content, /not run yet/);
  assert.equal(pin.disabled, true);
  assert.match(pin.content, /not run yet/);
});

// --- event routing by node id ------------------------------------------------

test("an event for a different node id does not update this node", async () => {
  const node = await setUp("StylebookStyle", "42");
  apiStub.__dispatch("stylebook.resolved", {
    node_id: "99",
    prompt: "a prompt that belongs to node 99",
    style: "Cyanotype",
  });
  const copy = find(menuFor(node), "Copy resolved prompt");
  assert.equal(copy.disabled, true, "an event for another node must not enable this one");
});

test("an event matching this node's id enables Copy and Pin", async () => {
  const node = await setUp("StylebookStyle", "7");
  apiStub.__dispatch("stylebook.resolved", {
    node_id: "7",
    prompt: "Rendered as a cyanotype print in Prussian blue.",
    style: "Cyanotype",
  });
  const options = menuFor(node);
  const copy = find(options, "Copy resolved prompt");
  const pin = find(options, "Pin this pick");
  assert.equal(copy.disabled, false);
  assert.equal(copy.content, "Copy resolved prompt");
  assert.equal(pin.disabled, false);
  assert.equal(pin.content, "Pin this pick");
});

// --- subgraph execution ids ("12:5") ----------------------------------------

function copyEnabled(node) {
  return !find(menuFor(node), "Copy resolved prompt").disabled;
}

test("a node inside a subgraph is reached by its execution id", async () => {
  const tree = makeGraphTree(["12"]);
  const node = tree.place(await setUp("StylebookStyle", "5"), tree.subgraphs["12"]);
  apiStub.__dispatch("stylebook.resolved", { node_id: "12:5", prompt: "...", style: "Cyanotype" });
  assert.equal(copyEnabled(node), true, "the inner node never matched its execution id");
});

test("an execution id reaches only the node at that path, not a same-numbered node elsewhere", async () => {
  const tree = makeGraphTree(["12", "14"]);
  const otherSubgraph = tree.place(await setUp("StylebookStyle", "5"), tree.subgraphs["14"]);
  const topLevel = tree.place(await setUp("StylebookStyle", "5"), tree.root);
  apiStub.__dispatch("stylebook.resolved", { node_id: "12:5", prompt: "...", style: "Cyanotype" });
  assert.equal(copyEnabled(otherSubgraph), false, "node 5 in subgraph 14 took subgraph 12's event");
  assert.equal(copyEnabled(topLevel), false, "top-level node 5 took subgraph 12's event");
});

test("a node inside a subgraph ignores a top-level node's plain id", async () => {
  const tree = makeGraphTree(["12"]);
  const inner = tree.place(await setUp("StylebookStyle", "5"), tree.subgraphs["12"]);
  const topLevel = tree.place(await setUp("StylebookStyle", "5"), tree.root);
  apiStub.__dispatch("stylebook.resolved", { node_id: "5", prompt: "...", style: "Cyanotype" });
  assert.equal(copyEnabled(topLevel), true);
  assert.equal(copyEnabled(inner), false, "the inner node took the top-level node's event");
});

test("an execution id through a host that is not a subgraph matches nothing", async () => {
  const tree = makeGraphTree(["12"]);
  const node = tree.place(await setUp("StylebookStyle", "5"), tree.subgraphs["12"]);
  apiStub.__dispatch("stylebook.resolved", { node_id: "99:5", prompt: "...", style: "Cyanotype" });
  assert.equal(copyEnabled(node), false);
});

// --- Copy puts the full untruncated prompt on the clipboard -----------------

test("Copy resolved prompt writes the full prompt from the event, not the truncated node-face readout", async () => {
  const node = await setUp("StylebookStyle", "3");
  const fullPrompt = "x".repeat(500); // longer than the 300-char node-face cap
  apiStub.__dispatch("stylebook.resolved", { node_id: "3", prompt: fullPrompt, style: "Cyanotype" });

  const written = [];
  Object.defineProperty(globalThis, "navigator", {
    value: { clipboard: { writeText: (text) => { written.push(text); return Promise.resolve(); } } },
    configurable: true,
  });

  const copy = find(menuFor(node), "Copy resolved prompt");
  await copy.callback();
  assert.equal(written.length, 1);
  assert.equal(written[0], fullPrompt);
  assert.equal(written[0].length, 500);
});

// --- Pin writes the resolved label back into this node's own widget --------

test("StylebookStyle: Pin this pick sets mode to Pick and writes the resolved style label", async () => {
  const node = await setUp("StylebookStyle", "5");
  apiStub.__dispatch("stylebook.resolved", { node_id: "5", prompt: "...", style: "Ligne Claire" });

  const pin = find(menuFor(node), "Pin this pick");
  pin.callback();

  const mode = node.widgets.find((w) => w.name === "mode");
  const style = node.widgets.find((w) => w.name === "style");
  assert.equal(mode.value, "Pick");
  assert.equal(style.value, "Ligne Claire");
});

test("StylebookModifier: Pin this pick sets axis before writing the modifier value", async () => {
  const node = await setUp("StylebookModifier", "6");
  apiStub.__dispatch("stylebook.resolved", {
    node_id: "6",
    prompt: "...",
    modifier: "Blue Hour",
    axis: "lighting",
  });

  const pin = find(menuFor(node), "Pin this pick");
  pin.callback();

  const axis = node.widgets.find((w) => w.name === "axis");
  const modifier = node.widgets.find((w) => w.name === "modifier");
  const mode = node.widgets.find((w) => w.name === "mode");
  assert.equal(axis.value, "lighting");
  assert.equal(modifier.value, "Blue Hour");
  assert.equal(mode.value, "Pick");
});

// --- onRemoved unsubscribes, closing the listener leak ----------------------

test("onRemoved unsubscribes: an event after removal no longer reaches this node", async () => {
  const node = await setUp("StylebookStyle", "8");
  node.onRemoved();

  apiStub.__dispatch("stylebook.resolved", { node_id: "8", prompt: "should be ignored", style: "X" });
  const copy = find(menuFor(node), "Copy resolved prompt");
  assert.equal(copy.disabled, true, "a removed node must not still be listening");
});

// --- composes with stylebook_recreate.js's own getExtraMenuOptions wrap ----

test("readout menu items appear alongside stylebook_recreate.js's Fix node entry", async () => {
  if (!app.__getExtension("stylebook.recreate")) {
    await import("../../js/stylebook_recreate.js");
  }
  const node = makeNode("StylebookStyle", "9");
  await app.__getExtension("stylebook.recreate").nodeCreated(node);
  await app.__getExtension("stylebook.readout").nodeCreated(node);

  const options = menuFor(node);
  assert.ok(find(options, "Fix node (recreate)"), "recreate's menu entry is missing");
  assert.ok(find(options, "Copy resolved prompt"), "readout's menu entry is missing");
});
