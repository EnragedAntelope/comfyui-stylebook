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
 * every queued run while the node is in Cycle mode, wrapping at the pool
 * size the backend reports in the `stylebook.resolved` event.
 *
 * The advance hangs off the widget's `afterQueued` hook, not off the
 * `stylebook.resolved` event. ComfyUI serialises every item of a Batch count
 * before any of them executes, so an execution event arrives after the whole
 * batch is already queued: advancing there ran the same index N times and then
 * jumped by N. `afterQueued` fires once per queued item, which is what makes a
 * batch of N walk N consecutive entries. The event now only supplies the pool
 * size to wrap at; before the first run it is unknown, and the backend takes
 * the index modulo the pool anyway, so the widget just counts up.
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

// LiteGraph node modes that do not execute: NEVER (muted) and BYPASS.
const INACTIVE_MODES = new Set([2, 4]);

/** Step `cycle_index` by one, wrapping at the pool size when it is known. */
function advanceCycle(node, cycleWidget, poolSize) {
  if (!autoAdvanceOn(node) || INACTIVE_MODES.has(node.mode)) return;
  const modeWidget = widgetsByName(node)["mode"];
  if (!modeWidget || modeWidget.value !== "Cycle") return;
  // A pool of one has nowhere to go.
  if (poolSize === 1) return;
  const current = Number(cycleWidget.value) || 0;
  const max = Number(cycleWidget.options && cycleWidget.options.max);
  // Size unknown (first run): the backend takes the index modulo the pool,
  // so count up and only wrap at the widget's own ceiling.
  const next = poolSize > 0
    ? (current + 1) % poolSize
    : (Number.isFinite(max) && current >= max ? 0 : current + 1);
  if (next !== current) setWidgetValue(node, cycleWidget, next);
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

  // 0 = not reported yet. Updated by every run's event.
  let poolSize = 0;
  const handler = (e) => {
    const detail = e && e.detail;
    if (!detail || String(detail.node_id) !== String(node.id)) return;
    const reported = Number(detail.cycle_pool_size);
    if (Number.isFinite(reported) && reported > 0) poolSize = reported;
  };
  api.addEventListener(EVENT_NAME, handler);

  const cycleWidget = widgetsByName(node)["cycle_index"];
  if (cycleWidget) {
    const inheritedAfterQueued = cycleWidget.afterQueued;
    cycleWidget.afterQueued = function (...args) {
      if (typeof inheritedAfterQueued === "function") {
        try {
          inheritedAfterQueued.apply(this, args);
        } catch (err) {
          warn(`an upstream afterQueued handler failed: ${err}`);
        }
      }
      try {
        advanceCycle(node, cycleWidget, poolSize);
      } catch (err) {
        warn(`cycle advance failed: ${err}`);
      }
    };
  }

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
