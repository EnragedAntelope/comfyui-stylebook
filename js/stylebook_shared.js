import { app } from "../../scripts/app.js";

/**
 * Frontend helpers shared by every Stylebook extension module
 * (stylebook_gallery.js, stylebook_recreate.js, stylebook_readout.js).
 *
 * Kept in its own file, not because any one of these is large, but
 * because three modules independently defining the same
 * isStylebookNode() and the same by-name widget lookup is exactly how
 * they drift apart -- the class of bug this pack's own test suite exists
 * to catch (see tests/frontend/).
 */

const SHARED_EXT_NAME = "stylebook.shared";

/** Build a warn() bound to one module's own console prefix. */
export function makeWarn(extName) {
  return function warn(message, error) {
    console.warn("[" + extName + "] " + message, error || "");
  };
}

const warn = makeWarn(SHARED_EXT_NAME);

/**
 * Every node reports its resolved output on its own face. At LiteGraph's
 * default width that lands in a two-line sliver you have to scroll, which
 * makes the most useful thing on the node the hardest thing to read. A
 * wider default costs nothing on an empty canvas and is still freely
 * resizable.
 */
export const MIN_NODE_WIDTH = 420;

/** True for any node instance this pack registered, by its comfyClass. */
export function isStylebookNode(node) {
  const type = node && (node.comfyClass || (node.constructor && node.constructor.type));
  return Boolean(type) && String(type).startsWith("Stylebook");
}

/** {name: widget} for a node's current widgets, skipping unnamed ones. */
export function widgetsByName(node) {
  const map = {};
  if (!node || !Array.isArray(node.widgets)) return map;
  for (const widget of node.widgets) {
    if (widget && widget.name) map[widget.name] = widget;
  }
  return map;
}

/** Set a widget's value and run its callback, the same way a user click does. */
export function setWidgetValue(node, widget, value) {
  if (!widget) return;
  widget.value = value;
  if (typeof widget.callback === "function") {
    try {
      widget.callback(value, app.canvas, node);
    } catch (error) {
      warn("widget callback failed", error);
    }
  }
}

/** Widen *node* to fit its content, never below MIN_NODE_WIDTH or its own width. */
export function resizeNode(node) {
  if (!node) return;
  try {
    if (typeof node.computeSize === "function") {
      const computed = node.computeSize();
      const width = (node.size && node.size[0]) || 0;
      // Never shrink below the user's own width, and never below the
      // width the readout needs to be readable.
      node.setSize([
        Math.max(width, computed[0], MIN_NODE_WIDTH),
        computed[1],
      ]);
    }
    if (typeof node.setDirtyCanvas === "function") node.setDirtyCanvas(true, true);
  } catch (error) {
    warn("resize failed", error);
  }
}
