/**
 * Stand-in for ComfyUI's scripts/app.js, redirected to by resolve_hook.mjs.
 *
 * Real ComfyUI extensions call `app.registerExtension({...})` once at
 * import time as a side effect; ComfyUI later calls the lifecycle methods
 * on that object (`setup()`, `nodeCreated(node)`) itself. This stub keeps
 * every registered extension object in `__extensions` so a test can import
 * the real js/stylebook_gallery.js, retrieve the extension it registered,
 * and drive its lifecycle by hand against a fake node.
 */

export const __extensions = [];

export const app = {
  canvas: {
    setDirty() {},
  },
  registerExtension(extension) {
    __extensions.push(extension);
  },
};

export function __getExtension(name) {
  return __extensions.find((ext) => ext.name === name);
}

export function __reset() {
  __extensions.length = 0;
}
