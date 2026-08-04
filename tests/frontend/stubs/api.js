/**
 * Stand-in for ComfyUI's scripts/api.js, redirected to by resolve_hook.mjs.
 *
 * Real code does `api.addEventListener("some.event", (e) => use(e.detail))`.
 * `__dispatch` lets a test fire that same shape without a live ComfyUI
 * server behind it.
 */

const listeners = new Map();

export const api = {
  addEventListener(type, handler) {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type).add(handler);
  },
  removeEventListener(type, handler) {
    listeners.get(type)?.delete(handler);
  },
};

export function __dispatch(type, detail) {
  for (const handler of listeners.get(type) || []) {
    handler({ detail });
  }
}

export function __reset() {
  listeners.clear();
}
