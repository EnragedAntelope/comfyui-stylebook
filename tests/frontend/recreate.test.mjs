/**
 * js/stylebook_recreate.js had no frontend test coverage before this
 * revision. This is not exhaustive -- it only proves the module still
 * imports and registers cleanly after stylebook_shared.js was carved out
 * of stylebook_gallery.js and stylebook_recreate.js started importing
 * `warn`/`isStylebookNode` from it instead of defining its own copies.
 */

import { test, before } from "node:test";
import assert from "node:assert/strict";
import { installDom } from "./dom.mjs";
import { makeNode } from "./fake_node.mjs";

installDom();

let app;

before(async () => {
  app = await import("./stubs/app.js");
  if (!app.__getExtension("stylebook.recreate")) {
    await import("../../js/stylebook_recreate.js");
  }
});

test("stylebook.recreate registers and installs a getExtraMenuOptions wrapper on Stylebook nodes", async () => {
  const ext = app.__getExtension("stylebook.recreate");
  assert.ok(ext, "stylebook.recreate never registered");

  const node = makeNode("StylebookStyle");
  await ext.nodeCreated(node);
  assert.equal(typeof node.getExtraMenuOptions, "function");

  const options = [];
  node.getExtraMenuOptions({}, options);
  const entry = options.find((o) => o.content === "Fix node (recreate)");
  assert.ok(entry, "Fix node (recreate) entry was not added");
  assert.equal(typeof entry.callback, "function");
});

test("stylebook.recreate leaves a non-Stylebook node's menu untouched", async () => {
  const ext = app.__getExtension("stylebook.recreate");
  const node = { comfyClass: "SomeOtherPack", widgets: [] };
  await ext.nodeCreated(node);
  assert.equal(node.getExtraMenuOptions, undefined);
});
