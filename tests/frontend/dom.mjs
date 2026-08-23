/**
 * Minimal jsdom bootstrap shared by every frontend test.
 *
 * Honest limits (also documented in ARCHITECTURE.md and the worklog): jsdom
 * has no layout engine, so `clientWidth`/`clientHeight` read 0 and anything
 * that depends on real layout (column-count-from-width, CSS, drag/drop)
 * cannot be exercised here. This catches wiring, visibility, serialization
 * and dialog logic -- the class of bug that has actually shipped -- not
 * painting.
 */

import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

let dom = null;

/**
 * Route fetch() the way a real ComfyUI install would.
 *
 * Two things are fetched. `/stylebook/user_data` is the "Yours" route,
 * which answers empty here so a test that never calls stubFetch()
 * exercises the "nothing to load" path. `stylebook_data.json` is the
 * style corpus, and that one is served from the real generated file --
 * the whole point of these tests is that they run the shipped data, and
 * an empty stub would turn every ordering and search assertion into a
 * check of nothing.
 *
 * Node's built-in fetch would reject the first URL outright (relative,
 * with no base to resolve against) and file-read the second, so neither
 * works unstubbed.
 */
const BULK_JSON = new URL("../../js/stylebook_data.json", import.meta.url);

function defaultFetchStub(input) {
  const url = String(input && input.url ? input.url : input);
  if (url.endsWith("stylebook_data.json")) {
    const text = readFileSync(BULK_JSON, "utf8");
    return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(text)) });
  }
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ styles: [], artists: [], modifiers: [] }),
  });
}

/**
 * Let pending promises run.
 *
 * The picker fetches its corpus when it opens, so the dialog exists one
 * turn before its tiles do. Every test that opens a picker awaits this
 * first. A real user sees the same thing -- an open dialog saying
 * "Loading styles..." -- which is why the fetch is not hidden behind a
 * synchronous import instead.
 */
export function settle(ms = 0) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function installDom() {
  dom = new JSDOM("<!doctype html><html><body></body></html>", {
    url: "http://localhost/",
  });
  const { window } = dom;
  globalThis.window = window;
  globalThis.document = window.document;
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.Node = window.Node;
  globalThis.CustomEvent = window.CustomEvent;
  globalThis.DocumentFragment = window.DocumentFragment;
  // Node itself defines a read-only `navigator` getter (since Node 21), so
  // a plain assignment throws. Redefine the property instead.
  Object.defineProperty(globalThis, "navigator", {
    value: window.navigator,
    configurable: true,
    writable: true,
  });
  globalThis.requestAnimationFrame = (callback) => setTimeout(callback, 0);
  globalThis.fetch = defaultFetchStub;
  return dom;
}

/**
 * Point global fetch() at a one-off handler for the current test.
 *
 * The corpus is deliberately *not* routed to the handler. Every caller of
 * this is testing the `/stylebook/user_data` route -- a failure, a non-ok
 * response, a payload -- and a handler that also answered the corpus
 * request would silently empty the gallery, turning "built-ins must still
 * render" into an assertion about a stub rather than about the pack.
 */
export function stubFetch(handler) {
  globalThis.fetch = (input, init) => {
    const url = String(input && input.url ? input.url : input);
    if (url.endsWith("stylebook_data.json")) return defaultFetchStub(input);
    return handler(input, init);
  };
}

export function resetDom() {
  if (document?.body) document.body.replaceChildren();
  if (document?.head) {
    for (const link of Array.from(document.head.querySelectorAll("link"))) {
      link.remove();
    }
  }
  globalThis.fetch = defaultFetchStub;
}
