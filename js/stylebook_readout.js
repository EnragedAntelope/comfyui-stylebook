import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import {
  isStylebookNode,
  makeWarn,
  setWidgetValue,
  widgetsByName,
} from "./stylebook_shared.js";

/*
 * "Copy resolved prompt" and "Pin this pick" -- two context-menu items
 * driven by the `stylebook.resolved` event the backend sends alongside
 * the node-face readout (see stylebook_nodes/node_support.py).
 *
 * The node-face readout is capped at 300 characters and, for Style/
 * Artist/Modifier/Blend, has the user's own subject collapsed to a
 * literal "[subject]" marker -- useful to glance at, useless to copy.
 * "Copy resolved prompt" reads the full, untruncated text out of the
 * event payload instead.
 *
 * "Pin this pick" is the answer to a real feature request (found
 * something good on Random, want to keep it) that stops short of a
 * save/preset file: it writes the resolved label straight into this
 * node's own pick widget and flips `mode` to Pick, which is enough for a
 * single-choice node like these three. It has no target on Blend (a
 * blended style is a synthetic composite, not one named pick) or Sheet
 * (N styles, not one), so those two get Copy only.
 */

const EXT_NAME = "stylebook.readout";
const EVENT_NAME = "stylebook.resolved";
const warn = makeWarn(EXT_NAME);

//: comfyClass -> which widget Pin writes its result into, and which field
//: of the event payload holds that result.
const PIN_TARGETS = {
  StylebookStyle: { widget: "style", field: "style" },
  StylebookArtist: { widget: "artist", field: "artist" },
  StylebookModifier: { widget: "modifier", field: "modifier" },
};

/**
 * Copy text to the clipboard, working in both a secure context (the
 * normal case; ComfyUI on localhost or https qualifies) and one that
 * is not, where `navigator.clipboard` does not exist at all.
 */
function copyToClipboard(text) {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    return navigator.clipboard.writeText(text);
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    // Reports false rather than throwing when the copy did not happen,
    // which is the case this fallback exists for. Returning a resolved
    // promise regardless was how a silent denial looked like a success.
    if (!document.execCommand("copy")) {
      return Promise.reject(new Error("the browser refused the copy"));
    }
  } finally {
    textarea.remove();
  }
  return Promise.resolve();
}

/**
 * Say whether the copy worked.
 *
 * It was fire-and-forget: a clipboard write that a browser silently
 * denied -- which is what happens outside a secure context -- looked
 * exactly like one that succeeded, and there was nothing on screen either
 * way. ComfyUI's own toast is used when it is there, so the message lands
 * where the user already looks for feedback, with a floating pill as the
 * fallback for older frontends.
 */
function notify(message, isError) {
  try {
    const toast = app.extensionManager && app.extensionManager.toast;
    if (toast && typeof toast.add === "function") {
      toast.add({
        severity: isError ? "error" : "success",
        summary: "Stylebook",
        detail: message,
        life: isError ? 5000 : 2000,
      });
      return;
    }
  } catch (_) { /* fall through to the pill */ }

  try {
    const pill = document.createElement("div");
    pill.className = "stylebook-toast" + (isError ? " stylebook-toast-error" : "");
    pill.setAttribute("role", "status");
    pill.textContent = message;
    document.body.appendChild(pill);
    setTimeout(() => pill.remove(), isError ? 5000 : 2000);
  } catch (_) { /* nothing left to try */ }
}

function addMenuItems(node, options) {
  const resolved = node.__sbResolved;
  const hasPrompt = Boolean(resolved && resolved.prompt);

  options.push({
    content: hasPrompt ? "Copy resolved prompt" : "Copy resolved prompt (not run yet)",
    disabled: !hasPrompt,
    callback: () => {
      if (!hasPrompt) return;
      copyToClipboard(resolved.prompt).then(
        () => notify("Resolved prompt copied to the clipboard.", false),
        (error) => {
          warn("copy failed", error);
          notify(
            "Could not copy. Your browser blocks clipboard writes here -- "
            + "the prompt is also shown on the node face.",
            true
          );
        }
      );
    },
  });

  const pin = PIN_TARGETS[node.comfyClass];
  if (!pin) return;

  const value = resolved && resolved[pin.field];
  options.push({
    content: value ? "Pin this pick" : "Pin this pick (not run yet)",
    disabled: !value,
    callback: () => {
      if (!value) return;
      const widgets = widgetsByName(node);
      // The axis must land before the pick, or the modifier value gets
      // rejected as outside the widget's current (still old-axis) options.
      if (pin.field === "modifier" && resolved.axis && widgets.axis) {
        setWidgetValue(node, widgets.axis, resolved.axis);
      }
      if (widgets.mode) setWidgetValue(node, widgets.mode, "Pick");
      if (widgets[pin.widget]) setWidgetValue(node, widgets[pin.widget], value);
    },
  });
}

/**
 * Wire one node instance to the resolved-event stream and its own
 * right-click menu. Mirrors the exact "own instance property, preserve
 * `inherited`" pattern stylebook_recreate.js already uses for the same
 * hook, so the two compose instead of one clobbering the other.
 */
function setupReadoutNode(node) {
  const handler = (event) => {
    const detail = event && event.detail;
    if (!detail || String(detail.node_id) !== String(node.id)) return;
    node.__sbResolved = detail;
  };
  api.addEventListener(EVENT_NAME, handler);

  // Without this, every node ever created keeps a live listener forever,
  // even after being deleted from the graph -- a slow leak across
  // ordinary edit-and-undo workflow sessions.
  const inheritedRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    api.removeEventListener(EVENT_NAME, handler);
    if (typeof inheritedRemoved === "function") {
      try {
        return inheritedRemoved.apply(this, args);
      } catch (error) {
        warn("an upstream onRemoved handler failed", error);
      }
    }
    return undefined;
  };

  const inheritedMenu = node.getExtraMenuOptions;
  node.getExtraMenuOptions = function (canvas, options) {
    let result;
    if (typeof inheritedMenu === "function") {
      try {
        result = inheritedMenu.call(this, canvas, options);
      } catch (error) {
        warn("an upstream menu handler failed", error);
      }
    }
    try {
      addMenuItems(this, options);
    } catch (error) {
      warn("could not add the readout menu items", error);
    }
    return result;
  };
}

app.registerExtension({
  name: EXT_NAME,

  async nodeCreated(node) {
    try {
      if (!isStylebookNode(node)) return;
      setupReadoutNode(node);
    } catch (error) {
      warn("readout setup failed", error);
    }
  },
});
