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

import { JSDOM } from "jsdom";

let dom = null;

/** Empty-but-successful response, so a test that never calls stubFetch()
 * still exercises the "nothing to load" path instead of hitting the
 * network (Node's built-in fetch also rejects a relative URL like
 * "/stylebook/user_data" outright with no base to resolve it against). */
function defaultFetchStub() {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ styles: [], artists: [], modifiers: [] }),
  });
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

/** Point global fetch() at a one-off handler for the current test. */
export function stubFetch(handler) {
  globalThis.fetch = handler;
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
