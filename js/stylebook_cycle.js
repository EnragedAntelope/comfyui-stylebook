import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import {
  isStylebookNode,
  makeWarn,
  setWidgetValue,
  widgetsByName,
} from "./stylebook_shared.js";

/**
 * Auto-advance for Cycle mode.
 *
 * Cycle mode steps through a pool by `cycle_index`, but the index only moves
 * when the user edits it by hand. That makes a category sweep a manual chore:
 * queue, read the result, bump the index, queue again. This extension adds a
 * per-node toggle ("Auto-advance cycle") that advances `cycle_index` by one on
 * every resolved run while the node is in Cycle mode, wrapping at the pool
 * size the backend reports in the `stylebook.resolved` event.
 *
 * It is a node *property*, not a widget, so it changes nothing about the saved
 * graph schema: old workflows load and run exactly as before. The toggle
 * defaults to ON for any node that has a cycle index (Style / Artist /
 * Modifier), because "Cycle" is expected to actually step through the pool --
 * that is the fix for the "every run stays the same" report. Turn it off from
 * the same menu entry to hold a fixed index. Blend and Sheet have no cycle
 * index, so they never show the toggle.
 */

const EXT_NAME = "stylebook.cycle";
const PROP = "stylebook_auto_advance";
const EVENT_NAME = "stylebook.resolved";
const warn = makeWarn(EXT_NAME);

function autoAdvanceOn(node) {
  const props = node.properties || {};
  // Default ON: Cycle mode is expected to step through the pool. An explicit
  // false (set via the menu toggle) is honored; absence means "advance".
  return props[PROP] === undefined ? true : Boolean(props[PROP]);
}

function hasCycleWidget(node) {
  return Boolean(widgetsByName(node)["cycle_index"]);
}

function setupCycleNode(node) {
  const originalMenu = node.getExtraMenuOptions;
  node.getExtraMenuOptions = function (ctx, options) {
    const result = options || [];
    if (typeof originalMenu === "function") {
      originalMenu.call(node, ctx, result);
    }
    if (!hasCycleWidget(node)) return result;
    const on = autoAdvanceOn(node);
    result.push({
      content: on ? "Auto-advance cycle: ON" : "Auto-advance cycle: OFF",
      callback: () => {
        if (!node.properties) node.properties = {};
        node.properties[PROP] = !on;
        if (app.graph && typeof app.graph.setDirtyCanvas === "function") {
          app.graph.setDirtyCanvas(true, false);
        }
      },
    });
    return result;
  };

  const handler = (e) => {
    const detail = e && e.detail;
    if (!detail || detail.node_id !== node.id) return;
    if (!autoAdvanceOn(node)) return;
    const widgets = widgetsByName(node);
    const modeWidget = widgets["mode"];
    const cycleWidget = widgets["cycle_index"];
    if (!modeWidget || modeWidget.value !== "Cycle" || !cycleWidget) return;
    const poolSize = detail.cycle_pool_size;
    if (!poolSize || poolSize <= 1) return;
    const current = Number(cycleWidget.value) || 0;
    const next = (current + 1) % poolSize;
    if (next !== current) setWidgetValue(node, cycleWidget, next);
  };
  api.addEventListener(EVENT_NAME, handler);

  const originalOnRemoved = node.onRemoved;
  node.onRemoved = function () {
    api.removeEventListener(EVENT_NAME, handler);
    if (typeof originalOnRemoved === "function") {
      originalOnRemoved.call(node);
    }
  };

  const inheritedDraw = node.onDrawForeground;
  node.onDrawForeground = function (ctx) {
    if (typeof inheritedDraw === "function") {
      try {
        inheritedDraw.call(node, ctx);
      } catch (err) {
        warn(`draw error: ${err}`);
      }
    }
    if (autoAdvanceOn(node) && hasCycleWidget(node) && ctx) {
      const modeWidget = widgetsByName(node)["mode"];
      if (!modeWidget || modeWidget.value === "Cycle") {
        try {
          ctx.save();
          ctx.font = "11px sans-serif";
          ctx.fillStyle = "#ffcf5a";
          ctx.fillText("↻", node.size[0] - 16, 14);
          ctx.restore();
        } catch (err) {
          // Canvas drawing is best-effort; the toggle in the menu is the
          // source of truth and must never depend on it.
        }
      }
    }
  };
}

app.registerExtension({
  name: EXT_NAME,
  async nodeCreated(node) {
    if (isStylebookNode(node)) {
      setupCycleNode(node);
    }
  },
});
