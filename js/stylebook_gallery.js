import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import {
  ARTIST_CATEGORY_LABELS,
  ARTIST_CATEGORY_ORDER,
  ARTIST_COUNT,
  BULK_DATA_FILE,
  CATEGORIES,
  CATEGORY_LABELS,
  CURRENT_VERSION,
  MODIFIER_AXES,
  MODIFIER_LABELS_BY_AXIS,
  RELEASES,
} from "./stylebook_data.js";
import {
  MIN_NODE_WIDTH,
  isStylebookNode,
  makeWarn,
  resizeNode,
  setWidgetValue,
  widgetsByName,
} from "./stylebook_shared.js";

/*
 * Stylebook frontend.
 *
 * Everything here is wrapped so a frontend failure degrades the node
 * rather than breaking it. The node computes its result entirely on the
 * backend; this file only makes choosing easier.
 *
 * Four features:
 *
 *   1. A picker dialog, used by four nodes. The Style and Sheet nodes get
 *      preview thumbnails, sliced out of the per-category WebP atlases in
 *      ./previews; the Artist and Modifier nodes get a written reference
 *      list, because they have descriptions rather than pictures. Sheet
 *      opens it in multi-select mode and writes a list.
 *   2. Mode-gated widget visibility, identical on Style, Artist and
 *      Modifier: the manual pick matters only in Pick, the pool filters
 *      only in Random and Cycle, `cycle_index` only in Cycle, and the
 *      seed only in Random.
 *   3. Axis-gated modifier options: changing `axis` narrows the
 *      `modifier` dropdown to that axis. The backend ships every axis's
 *      modifiers in the options list so a saved value is never outside
 *      it, and reports a mismatch rather than applying the wrong one.
 *   4. A working "Fix node (recreate)", which lives in its own module,
 *      stylebook_recreate.js.
 *
 * Data comes from two generated files. stylebook_data.js holds the few
 * kilobytes a node needs before any dialog exists; stylebook_data.json
 * holds the corpus and is fetched the first time a picker opens, because
 * ComfyUI imports every .js under a pack's web directory at app start.
 * Both are generated. This file is hand-written and the generator never
 * touches it.
 */

const EXT_NAME = "stylebook.gallery";
const MODE_PICK = "Pick";
const MODE_RANDOM = "Random";
const MODE_CYCLE = "Cycle";
const SENTINEL_OFF = "Off";

// Pseudo-group shown as the first tab. Browsing everything at once is the
// common case: you often do not know which category a style lives in,
// and 400-plus tiles scroll perfectly well.
const GROUP_ALL = "__all__";

// Pseudo-group shown as the last tab, only once a local user_styles.json
// has actually added something. A custom entry still carries its real
// category/axis as `group`, so it shows up under "All" and its own
// category exactly like a built-in; this tab is purely a shortcut to "the
// things I added", filtered by `item.isCustom` rather than by group.
const GROUP_YOURS = "__yours__";

// Pseudo-group offered second, only when this release actually added
// something to that picker. Six hundred tiles is too many to rescan for
// what changed, and the data already knows: every entry carries the
// release it first shipped in.
const GROUP_NEW = "__new__";

const SORT_ALPHA = "az";
const SORT_NEWEST = "new";
const SORT_KEY = "stylebook.gallery.sort";

//: Rank of each release, newest highest. Sorting by "newest" ranks on
//: this rather than comparing version strings, because "0.10.0" sorts
//: before "0.9.0" as text and there is no reason to write a semver
//: comparator when the generator can just emit the order.
const RELEASE_RANK = new Map((RELEASES || []).map((v, i) => [v, i]));

/**
 * Chosen ordering, shared by every picker and remembered between opens.
 *
 * Module-level rather than per-dialog: a user who switches to newest-first
 * to see what a release added means it for the Artist reference too, and
 * having each picker forget independently is a small, constant annoyance.
 * localStorage is best-effort -- a private window or a browser with site
 * data blocked throws on access, and the default is fine there.
 */
let sortOrder = SORT_ALPHA;
try {
  const saved = window.localStorage.getItem(SORT_KEY);
  if (saved === SORT_NEWEST || saved === SORT_ALPHA) sortOrder = saved;
} catch (_) { /* storage unavailable; the default stands */ }

function setSortOrder(value) {
  sortOrder = value === SORT_NEWEST ? SORT_NEWEST : SORT_ALPHA;
  try {
    window.localStorage.setItem(SORT_KEY, sortOrder);
  } catch (_) { /* not worth telling anyone about */ }
}

/**
 * The style/artist/modifier corpus, fetched on first use.
 *
 * It is not imported. ComfyUI globs `**\/*.js` under every pack's web
 * directory and imports every hit, so a `.js` file here is parsed at app
 * start whether or not anyone opens a picker -- 300 KB charged to every
 * ComfyUI user, including the ones with no Stylebook node on the canvas.
 * As a `.json` fetched when a dialog first opens, it costs nothing until
 * it is wanted. See scripts/generate_js_data.py for the full reasoning.
 */
let bulk = null;
let bulkPromise = null;

function loadBulkData() {
  if (bulk) return Promise.resolve(bulk);
  if (!bulkPromise) {
    bulkPromise = fetch(assetURL("./" + BULK_DATA_FILE))
      .then((response) => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then((data) => {
        if (!data || typeof data !== "object") throw new Error("not an object");
        bulk = data;
        return bulk;
      })
      .catch((error) => {
        // Cleared so a retry can actually retry rather than re-resolving
        // the same rejection for the rest of the session.
        bulkPromise = null;
        throw error;
      });
  }
  return bulkPromise;
}

//: Fetched once in setup(). Read as {styles:[],artists:[],modifiers:[]}
//: even before the fetch resolves, so every item-source function below
//: can merge it in unconditionally with no extra null-checking.
let userData = { styles: [], artists: [], modifiers: [] };
let userDataVersion = 0;

// Artist category tabs. The list used to be flat, which made 590 entries
// searchable but not browsable: with no way to say "show me the
// photographers", the only route in was already knowing a name.
const ARTIST_GROUPS = [GROUP_ALL].concat(ARTIST_CATEGORY_ORDER || []);
const HIDDEN_TYPE = "stylebook_hidden";

const TILE_DISPLAY_PX = 168;

// --- small helpers --------------------------------------------------------

const warn = makeWarn(EXT_NAME);

function assetURL(relative) {
  try {
    return new URL(relative, import.meta.url).href;
  } catch (_) {
    return relative;
  }
}

/**
 * Fetch what a local user_styles.json added, for the "Yours" picker tab.
 *
 * A server route, not assetURL()'d: this pack's HTTP route
 * (stylebook_nodes/routes.py) is registered on the shared PromptServer
 * instance, not served relative to this file's own /extensions/... path.
 * Requested through api.fetchApi rather than a bare fetch("/stylebook/..."),
 * because a root-absolute path only resolves when ComfyUI is served from
 * the root of its origin -- behind a reverse proxy on a sub-path it 404s
 * and the "Yours" tab is silently empty. fetchApi applies the same base
 * path the rest of the frontend uses.
 *
 * A missing route, a network failure or a malformed response all leave
 * `userData` at its empty default -- every picker degrades to exactly
 * today's built-ins-only behaviour, never a broken tab.
 */
async function loadUserData() {
  const response = await api.fetchApi("/stylebook/user_data");
  if (!response.ok) return;
  const data = await response.json();
  if (!data || typeof data !== "object") return;
  userData = {
    styles: Array.isArray(data.styles) ? data.styles : [],
    artists: Array.isArray(data.artists) ? data.artists : [],
    modifiers: Array.isArray(data.modifiers) ? data.modifiers : [],
  };
  // Bumped so the memoised item lists below rebuild once, rather than
  // caching a built-ins-only list before this fetch landed.
  userDataVersion += 1;
}

/**
 * Human-facing name for a group key.
 *
 * Categories have real names in the data layer, because title-casing the
 * id produces "Three D Digital". Artist groups have no such table and
 * fall back to title-casing, which is fine for "fine-art".
 */
function groupName(key) {
  if (key === GROUP_ALL) return "All";
  if (key === GROUP_YOURS) return "Yours";
  // Named for the release, not just "New": a user who skipped a version
  // needs to know which one they are looking at.
  if (key === GROUP_NEW) return "New in " + CURRENT_VERSION;
  if (CATEGORY_LABELS && CATEGORY_LABELS[key]) return CATEGORY_LABELS[key];
  if (ARTIST_CATEGORY_LABELS && ARTIST_CATEGORY_LABELS[key]) {
    return ARTIST_CATEGORY_LABELS[key];
  }
  return String(key)
    .split(/[_-]/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * The position chip shown on a multi-selected entry.
 *
 * A tick would say "chosen" but not "third", and the sheet renders in the
 * order you picked, so the order is the part worth showing.
 */
function orderBadge(position) {
  const badge = document.createElement("span");
  badge.className = "stylebook-order";
  badge.textContent = String(position);
  badge.setAttribute("aria-label", "position " + position);
  return badge;
}

function initials(label) {
  const parts = String(label || "").split(/[\s&/.\-()]+/).filter(Boolean);
  return parts.slice(0, 2).map((w) => w.charAt(0).toUpperCase()).join("") || "?";
}

/**
 * Compare two labels the way data/ordering.py does.
 *
 * Accents and case folded away, runs of digits compared as numbers, so
 * "8-Bit" precedes "16-Bit" and "Naïve Art" lands next to "Nabis"
 * instead of after "Needlepoint".
 *
 * The gallery cannot simply read the generator's order: it interleaves
 * entries from a user's own user_styles.json, which the generator never
 * saw. That makes the same rule exist in two languages, so a frontend
 * test asserts that re-sorting ALL_STYLE_LABELS with this comparator is
 * a no-op. If Python and JS ever disagree, CI says so.
 *
 * Built inside a try, because a frontend failure has to degrade the node
 * rather than break it: without Intl the gallery falls back to code-point
 * order, which is merely the ordering we had before.
 */
const compareLabels = (() => {
  try {
    const collator = new Intl.Collator(undefined, {
      sensitivity: "base",
      numeric: true,
    });
    return (a, b) => collator.compare(a, b);
  } catch (_) {
    return (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  }
})();

/**
 * Sort comparator for picker items.
 *
 * The collator reports equality for anything differing only by accent or
 * case, so the raw label breaks the tie and the order stays stable.
 */
function byLabel(a, b) {
  const label = compareLabels(a.label, b.label);
  if (label !== 0) return label;
  return a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
}

// --- widget show/hide -----------------------------------------------------
// Swapping `type` and zeroing `computeSize` keeps the widget's value in the
// saved workflow, which simply removing it would not.

function hideWidget(widget) {
  if (!widget || widget.__sbHidden) return;
  widget.__sbHidden = true;
  widget.__sbType = widget.type;
  widget.__sbComputeSize = widget.computeSize;
  // Swapping the type hides it on older LiteGraph, which skips widget
  // types it does not recognise. Newer frontends ignore that and honour
  // a `hidden` flag instead, and a trailing widget stayed painted with
  // only the type swap. Set both.
  widget.type = HIDDEN_TYPE;
  widget.hidden = true;
  if (widget.options) {
    widget.__sbOptionHidden = widget.options.hidden;
    widget.options.hidden = true;
  }
  widget.computeSize = () => [0, -4];
}

function showWidget(widget) {
  if (!widget || !widget.__sbHidden) return;
  widget.__sbHidden = false;
  if (widget.__sbType) widget.type = widget.__sbType;
  widget.hidden = false;
  if (widget.options) widget.options.hidden = widget.__sbOptionHidden || false;
  // Most widgets define no computeSize of their own and rely on
  // LiteGraph's default, so the saved value is undefined. Assigning that
  // back would leave the zero-size stub in place and the widget would
  // never reappear. Delete the own property instead, which restores the
  // default. This, not the callback plumbing, is why toggling randomize
  // off never brought the artist dropdown back.
  if (typeof widget.__sbComputeSize === "function") {
    widget.computeSize = widget.__sbComputeSize;
  } else {
    delete widget.computeSize;
  }
  widget.__sbType = null;
  widget.__sbComputeSize = null;
  widget.__sbOptionHidden = undefined;
}

function setVisible(widget, visible) {
  (visible ? showWidget : hideWidget)(widget);
}

/**
 * Grey a widget out in place rather than removing it.
 *
 * Hiding a widget shifts everything below it, so a control can move out
 * from under the cursor between one click and the next. On the small
 * nodes, where a toggle swaps which of two widgets applies, disabling
 * keeps the node exactly the same height and nothing ever moves.
 *
 * `disabled` is honoured by current frontends; the label prefix is a
 * visible fallback for any build that ignores it, so the state is never
 * conveyed by nothing at all.
 */
function setEnabled(widget, enabled) {
  if (!widget) return;
  widget.disabled = !enabled;
  if (widget.options) widget.options.disabled = !enabled;
  if (widget.__sbLabel === undefined) widget.__sbLabel = widget.label ?? null;
  const base = widget.__sbLabel ?? widget.name;
  widget.label = enabled ? widget.__sbLabel ?? undefined : base + " (off)";
}

/**
 * Show or hide a seed together with its control_after_generate.
 *
 * ComfyUI appends that control as a separate sibling widget, so hiding
 * only the seed leaves a stray "control after generate" dropdown on the
 * node with nothing left to control.
 */
function setSeedVisible(widgets, visible) {
  setVisible(widgets.seed, visible);
  setVisible(widgets.control_after_generate, visible);
}

// --- preview sprite lookup ------------------------------------------------

function previewFor(category, styleId) {
  const index = bulk && bulk.PREVIEW_INDEX;
  const categories = index && index.categories;
  if (!categories) return null;
  const entry = categories[category];
  if (!entry || !entry.tiles) return null;
  const cell = entry.tiles[styleId];
  if (!cell) return null;
  return { atlas: entry.atlas, cols: entry.cols, rows: entry.rows, cell: cell };
}

/**
 * Show one cell of a sprite sheet inside a fluid-width element.
 *
 * The tile is sized by a CSS grid, so pixel offsets would drift as the
 * dialog resizes. Percentage background-size is relative to the element,
 * not the image, so an atlas `cols` tiles wide scaled to `cols * 100%`
 * makes each cell exactly one tile wide at any element size. Percentage
 * background-position then interpolates across the remaining cells,
 * which is why it divides by `cols - 1` rather than `cols`.
 */
function applySprite(element, preview) {
  const { cols, rows, cell } = preview;
  if (!cols || !rows) return false;
  const x = cols > 1 ? (cell[0] / (cols - 1)) * 100 : 0;
  const y = rows > 1 ? (cell[1] / (rows - 1)) * 100 : 0;
  element.style.backgroundImage =
    "url('" + assetURL("./previews/" + preview.atlas) + "')";
  element.style.backgroundRepeat = "no-repeat";
  element.style.backgroundSize = cols * 100 + "% " + rows * 100 + "%";
  element.style.backgroundPosition = x + "% " + y + "%";
  return true;
}

// --- item sources ---------------------------------------------------------

/**
 * Memoise an item list until the data behind it changes.
 *
 * renderGrid() runs on every keystroke, and each call used to rebuild
 * 600-plus objects and re-sort them before filtering. Nothing about that
 * list depends on the query. The only inputs that do change are the
 * fetched corpus and a late-arriving user_styles.json, so both are in the
 * cache key.
 */
function memoiseItems(build) {
  let cached = null;
  let key = "";
  return () => {
    const fresh = (bulk ? "b" : "-") + userDataVersion;
    if (cached && key === fresh) return cached;
    cached = build();
    key = fresh;
    return cached;
  };
}

/**
 * Precompute the lowercased text `matches()` searches.
 *
 * Every field used to be re-lowercased for every item on every keystroke.
 * The group's *display* name is folded in here too, so searching
 * "photography" still finds a tile whose group key is `photography` and
 * "Fine Art" still finds one whose key is `fine-art`.
 */
function withHaystack(item) {
  item.haystack = [
    item.label,
    item.id,
    item.group ? groupName(item.group) : "",
    item.detail || "",
    (item.aliases || []).join(" "),
  ].join(" ").toLowerCase();
  return item;
}

const styleItems = memoiseItems(function buildStyleItems() {
  const items = [];
  const byCategory = (bulk && bulk.STYLE_DATA_BY_CATEGORY) || {};
  for (const category of CATEGORIES) {
    const data = byCategory[category];
    if (!data || !Array.isArray(data.labels)) continue;
    for (let i = 0; i < data.labels.length; i++) {
      items.push(withHaystack({
        id: data.ids[i],
        label: data.labels[i],
        group: category,
        aliases: (data.aliases && data.aliases[i]) || [],
        scene: (data.scenes && data.scenes[i]) || "",
        added: (data.added && data.added[i]) || "",
        namesake: (data.namesakes && data.namesakes[i]) || "",
      }));
    }
  }
  // A custom style keeps its own category as `group`, so it appears under
  // "All" and its real category exactly like a built-in; isCustom is only
  // what the "Yours" tab filters on. It has no preview atlas entry, so the
  // tile falls back to the existing lettered-initials glyph automatically.
  for (const entry of userData.styles) {
    items.push(withHaystack({
      id: entry.id,
      label: entry.label,
      group: entry.category,
      aliases: [],
      scene: entry.scene || "",
      // A custom style has no release: it shipped with whoever wrote it.
      // Leaving it blank keeps it out of the "New" tab, which is about
      // what *this pack* added, and sorts it last under newest-first.
      added: "",
      namesake: "",
      isCustom: true,
    }));
  }
  // Sorted here rather than per tab, so "All", each category, "Yours"
  // and every search result come out alphabetical from one line -- and
  // a custom style lands among the built-ins rather than after them.
  return items.sort(byLabel);
});

const artistItems = memoiseItems(function buildArtistItems() {
  const items = [];
  const labels = (bulk && bulk.ARTIST_LABELS) || [];
  const categories = (bulk && bulk.ARTIST_CATEGORIES) || [];
  const aliases = (bulk && bulk.ARTIST_ALIASES) || [];
  const descriptors = (bulk && bulk.ARTIST_DESCRIPTORS) || [];
  const added = (bulk && bulk.ARTIST_ADDED) || [];
  for (let i = 0; i < labels.length; i++) {
    items.push(withHaystack({
      id: labels[i],
      label: labels[i],
      group: categories[i] || "artist",
      aliases: aliases[i] || [],
      detail: descriptors[i] || "",
      added: added[i] || "",
    }));
  }
  for (const entry of userData.artists) {
    items.push(withHaystack({
      id: entry.label,
      label: entry.label,
      group: entry.category || "artist",
      aliases: [],
      detail: entry.detail || "",
      added: "",
      isCustom: true,
    }));
  }
  return items.sort(byLabel);
});

// Deliberately unsorted, unlike styles and artists. Modifiers are grouped
// by axis and the `era` axis reads chronologically -- Ancient Classical,
// Edwardian, 1920s, 1950s. Alphabetising would scatter the decades to the
// top of the list. schema_options.modifier_options() makes the same call
// on the backend, and the two have to agree.
const modifierItems = memoiseItems(function buildModifierItems() {
  const items = ((bulk && bulk.MODIFIER_RECORDS) || []).map((rec) => withHaystack({
    id: rec.label,
    label: rec.label,
    group: rec.axis,
    aliases: rec.aliases || [],
    detail: rec.detail || "",
    added: rec.added || "",
  }));
  for (const entry of userData.modifiers) {
    items.push(withHaystack({
      id: entry.label,
      label: entry.label,
      group: entry.category,
      aliases: [],
      detail: entry.detail || "",
      added: "",
      isCustom: true,
    }));
  }
  return items;
});

function matches(item, query) {
  if (!query) return true;
  return item.haystack.includes(query.toLowerCase());
}

/** True when *item* was added by the release this build is. */
function isNew(item) {
  return Boolean(CURRENT_VERSION) && item.added === CURRENT_VERSION;
}

/**
 * Newest first, then alphabetical inside each release.
 *
 * Ties broken by label rather than left to the sort's stability: the
 * incoming list is already alphabetical, but saying so here means the
 * ordering survives someone changing that.
 */
function byNewest(a, b) {
  const ra = RELEASE_RANK.has(a.added) ? RELEASE_RANK.get(a.added) : -1;
  const rb = RELEASE_RANK.has(b.added) ? RELEASE_RANK.get(b.added) : -1;
  if (ra !== rb) return rb - ra;
  return byLabel(a, b);
}

// --- picker dialog --------------------------------------------------------

class StylebookPicker {
  /**
   * @param {object} config
   *   title         dialog heading
   *   items         () => array of {id,label,group,aliases}
   *   groups        array of group keys for the tab strip, or null for none
   *   showPreviews  slice thumbnails out of the preview atlases
   *   onSelect      (item) => void
   *   currentValue  () => the value currently held by the node
   */
  constructor(config) {
    this.config = config;
    this.query = "";
    this.activeGroup = (config.groups && config.groups[0]) || null;
    this.focusIndex = 0;
    this.visible = [];
    this.overlay = null;
    this.previousFocus = null;
  }

  open() {
    if (this.overlay) return;
    this.previousFocus = document.activeElement;
    // Multi mode starts from whatever the node already holds, so opening
    // the picker to add one more never silently discards the rest.
    this.chosen = this.config.multi
      ? (this.config.currentValues ? this.config.currentValues() : []).slice()
      : [];
    try {
      this.build();
      document.body.appendChild(this.overlay);
    } catch (error) {
      warn("failed to open picker", error);
      this.close();
      return;
    }
    requestAnimationFrame(() => {
      try {
        if (this.searchInput) this.searchInput.focus();
      } catch (_) { /* ignore */ }
    });
    // The dialog is on screen before the corpus is, so opening feels
    // instant on a cold load and the wait happens inside a frame that
    // already exists rather than behind an unresponsive button.
    this.ensureData();
  }

  /**
   * Fetch the corpus if this is the first picker opened this session.
   *
   * A failure is shown in the dialog with a retry rather than swallowed:
   * an empty gallery with no explanation reads as a broken pack, and the
   * one thing the user can usefully do about a missing file is try again.
   */
  ensureData() {
    if (bulk) {
      this.renderGrid();
      return;
    }
    this.showPlaceholder("Loading styles...");
    const opened = this.overlay;
    loadBulkData().then(
      () => {
        if (this.overlay !== opened) return;
        this.renderGrid();
      },
      (error) => {
        if (this.overlay !== opened) return;
        warn("could not load the style data", error);
        this.showPlaceholder(
          "Could not load the style data. Check that the pack's js/ folder "
          + "is complete, then try again.",
          () => this.ensureData()
        );
      }
    );
  }

  /** Replace the grid with a one-line message, optionally with a retry. */
  showPlaceholder(message, onRetry) {
    if (!this.grid) return;
    this.grid.replaceChildren();
    this._focused = null;
    this.grid.classList.remove("with-category");
    const box = document.createElement("div");
    box.className = "stylebook-empty";
    box.textContent = message;
    if (onRetry) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "stylebook-close";
      retry.textContent = "Try again";
      retry.addEventListener("click", onRetry);
      box.append(document.createElement("br"), retry);
    }
    this.grid.appendChild(box);
    if (this.count) this.count.textContent = "";
    this.visible = [];
  }

  close() {
    if (this.overlay && this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }
    this.overlay = null;
    this.grid = null;
    this.tabs = null;
    this.count = null;
    this.searchInput = null;
    this.sortSelect = null;
    this._focused = null;
    if (this._searchTimer) {
      clearTimeout(this._searchTimer);
      this._searchTimer = null;
    }
    // Returning focus to where it was keeps keyboard users oriented.
    try {
      if (this.previousFocus && this.previousFocus.focus) this.previousFocus.focus();
    } catch (_) { /* ignore */ }
  }

  build() {
    const overlay = document.createElement("div");
    overlay.className = "stylebook-overlay";

    const dialog = document.createElement("div");
    dialog.className = "stylebook-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", this.config.title);

    // Header: search box, live count, close button.
    const header = document.createElement("div");
    header.className = "stylebook-header";

    const search = document.createElement("input");
    search.type = "search";
    search.className = "stylebook-search";
    search.placeholder = this.config.searchPlaceholder;
    search.spellcheck = false;
    search.autocomplete = "off";
    search.setAttribute("aria-label", this.config.searchPlaceholder);
    // Debounced. A grid rebuild is cheap now that the item list is
    // memoised, but a fast typist still generated one full pass per
    // keystroke; coalescing them keeps the caret responsive on a laptop.
    search.addEventListener("input", (event) => {
      this.query = event.target.value || "";
      this.focusIndex = 0;
      if (this._searchTimer) clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => {
        this._searchTimer = null;
        this.renderGrid();
      }, 80);
    });
    this.searchInput = search;

    const count = document.createElement("span");
    count.className = "stylebook-count";
    count.setAttribute("aria-live", "polite");
    this.count = count;

    // Ordering control. Alphabetical is the default and stays the way in
    // when you know what you are looking for; newest-first answers the
    // other question a returning user has, which is what changed.
    const sort = document.createElement("select");
    sort.className = "stylebook-sort";
    sort.setAttribute("aria-label", "Sort order");
    for (const [value, text] of [[SORT_ALPHA, "A-Z"], [SORT_NEWEST, "Newest"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      sort.appendChild(option);
    }
    sort.value = sortOrder;
    sort.addEventListener("change", () => {
      setSortOrder(sort.value);
      this.focusIndex = 0;
      this.renderGrid();
    });
    this.sortSelect = sort;

    const close = document.createElement("button");
    close.type = "button";
    close.className = "stylebook-close";
    close.textContent = this.config.multi ? "Cancel" : "Close";
    close.addEventListener("click", () => this.close());

    if (this.config.multi) {
      // A confirm button, so cancelling out of a multi-select leaves the
      // node exactly as it was. Toggling tiles must not be destructive
      // until the user says so.
      const done = document.createElement("button");
      done.type = "button";
      done.className = "stylebook-close stylebook-done";
      done.addEventListener("click", () => this.commit());
      this.doneButton = done;
      header.append(search, sort, count, done, close);
      this.updateChosenCount();
    } else {
      header.append(search, sort, count, close);
    }

    // Tab strip, only when the source is grouped.
    if (this.config.groups) {
      const tabs = document.createElement("div");
      tabs.className = "stylebook-tabs";
      tabs.setAttribute("role", "tablist");
      this.tabs = tabs;
      dialog.append(header, tabs);
    } else {
      dialog.append(header);
    }

    const grid = document.createElement("div");
    grid.className = this.config.layout === "list"
      ? "stylebook-list"
      : "stylebook-grid";
    grid.setAttribute("role", "listbox");
    grid.tabIndex = 0;
    this.grid = grid;

    const footer = document.createElement("div");
    footer.className = "stylebook-footer";
    footer.textContent =
      "Arrow keys move, Enter selects, Escape closes. Type to search names and aliases.";

    dialog.append(grid, footer);
    overlay.appendChild(dialog);

    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) this.close();
    });
    // Clicks inside must not reach the canvas, which would deselect the node.
    overlay.addEventListener("click", (event) => event.stopPropagation());
    overlay.addEventListener("keydown", (event) => this.onKeyDown(event), true);

    this.overlay = overlay;
    if (this.tabs) this.renderTabs();
    this.renderGrid();
  }

  /**
   * Everything inside the dialog that Tab can land on, in document order.
   *
   * Tiles and rows are deliberately absent: they carry tabIndex -1 and
   * are driven by the arrow keys instead, so tabbing through 550 of them
   * is never something a user has to sit through.
   */
  focusableElements() {
    if (!this.overlay) return [];
    return Array.from(this.overlay.querySelectorAll(
      'input, button, [tabindex]:not([tabindex="-1"])'
    )).filter((el) => !el.disabled);
  }

  onKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      this.close();
      return;
    }

    // Keep Tab inside the dialog. It sets aria-modal and returns focus on
    // close, but without this the focus ring walked straight out of the
    // last control and onto the ComfyUI canvas behind the overlay, which
    // is still there and still interactive.
    if (event.key === "Tab") {
      const focusable = this.focusableElements();
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      const outside = !this.overlay.contains(active);
      if (event.shiftKey && (active === first || outside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || outside)) {
        event.preventDefault();
        first.focus();
      }
      return;
    }

    const columns = this.columnCount();
    const lastIndex = this.visible.length - 1;
    let next = null;

    if (event.key === "ArrowRight") next = this.focusIndex + 1;
    else if (event.key === "ArrowLeft") next = this.focusIndex - 1;
    else if (event.key === "ArrowDown") next = this.focusIndex + columns;
    else if (event.key === "ArrowUp") next = this.focusIndex - columns;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = lastIndex;
    else if (event.key === "Enter") {
      const item = this.visible[this.focusIndex];
      if (item) {
        event.preventDefault();
        event.stopPropagation();
        this.select(item);
      }
      return;
    } else {
      return;
    }

    if (next === null || lastIndex < 0) return;
    event.preventDefault();
    event.stopPropagation();
    this.focusIndex = Math.min(Math.max(next, 0), lastIndex);
    this.highlight();
  }

  columnCount() {
    // A list is one item per row, so up and down move by one.
    if (this.config.layout === "list") return 1;
    if (!this.grid) return 1;
    const width = this.grid.clientWidth || TILE_DISPLAY_PX;
    return Math.max(1, Math.floor(width / (TILE_DISPLAY_PX + 14)));
  }

  /**
   * Move the focus ring, touching two elements rather than all of them.
   *
   * This runs on every arrow key and every mouseenter. It used to
   * querySelectorAll the whole grid and walk 600-plus tiles per press,
   * which is the wrong shape of work for the hot navigation path: the
   * only elements that change are the one leaving focus and the one
   * taking it.
   */
  highlight() {
    if (!this.grid) return;
    const next = this.visible.length
      ? this.grid.children[this.focusIndex] || null
      : null;
    if (this._focused === next) {
      if (next && next.scrollIntoView) next.scrollIntoView({ block: "nearest" });
      return;
    }
    if (this._focused) {
      this._focused.classList.remove("focused");
      this._focused.setAttribute("aria-selected", "false");
    }
    this._focused = next;
    if (next) {
      next.classList.add("focused");
      next.setAttribute("aria-selected", "true");
      if (next.scrollIntoView) next.scrollIntoView({ block: "nearest" });
    }
  }

  renderTabs() {
    this.tabs.replaceChildren();
    for (const group of this.groups()) {
      const button = document.createElement("div");
      button.tabIndex = 0;
      const active = group === this.activeGroup && !this.query;
      button.className = "stylebook-tab" + (active ? " active" : "");
      button.textContent = groupName(group);
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", active ? "true" : "false");
      button.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          button.click();
        }
      });
      button.addEventListener("click", () => {
        this.activeGroup = group;
        this.query = "";
        this.focusIndex = 0;
        if (this.searchInput) this.searchInput.value = "";
        this.renderTabs();
        this.renderGrid();
      });
      this.tabs.appendChild(button);
    }
  }

  /**
   * The tab strip for this picker, with "New" inserted when it applies.
   *
   * Conditional for the same reason the "Yours" tab is: a tab that is
   * always there and sometimes empty teaches you to ignore it. A release
   * that adds styles but no modifiers shows the tab on the style gallery
   * only.
   */
  groups() {
    const base = this.config.groups;
    if (!base) return null;
    if (!this.config.items().some(isNew)) return base;
    const out = base.slice();
    out.splice(base[0] === GROUP_ALL ? 1 : 0, 0, GROUP_NEW);
    return out;
  }

  renderGrid() {
    if (!this.grid) return;
    if (!bulk) return;  // ensureData() is showing the placeholder
    this.grid.replaceChildren();
    this._focused = null;

    const all = this.config.items();
    // A search spans every group; without one, show the active tab only.
    this.visible = this.query
      ? all.filter((item) => matches(item, this.query))
      : this.config.groups && this.activeGroup !== GROUP_ALL
        ? this.activeGroup === GROUP_NEW
          ? all.filter(isNew)
          : this.activeGroup === GROUP_YOURS
            ? all.filter((item) => item.isCustom)
            : all.filter((item) => item.group === this.activeGroup)
        : all;

    // Sorted here, on the filtered list, rather than in the item source:
    // the source is memoised and shared, and re-sorting a few hundred
    // visible entries costs less than keeping two copies of the corpus.
    // Modifiers are the exception the pack has always made -- the `era`
    // axis reads chronologically and alphabetising scatters the decades --
    // so alphabetical order leaves their data order alone.
    if (sortOrder === SORT_NEWEST) {
      this.visible = this.visible.slice().sort(byNewest);
    }

    if (this.tabs) this.renderTabs();

    // The tile shows its category only where the tab strip does not
    // already say it. Sorting alphabetically dropped the grouping cue
    // that category-ordered tiles used to give for free, and in "All",
    // "Yours" or a search result there is otherwise nothing to say
    // whether a tile is a photography style or a craft one.
    this._showCategory = Boolean(
      this.config.showCategory &&
        (this.query ||
          this.activeGroup === GROUP_ALL ||
          this.activeGroup === GROUP_YOURS)
    );
    // The row height is fixed in CSS and cannot grow from its contents,
    // so the chip's line box has to be added to it deliberately.
    this.grid.classList.toggle("with-category", this._showCategory);

    if (this.count) {
      this.count.textContent =
        this.visible.length + (this.visible.length === 1 ? " result" : " results");
    }

    if (!this.visible.length) {
      const empty = document.createElement("div");
      empty.className = "stylebook-empty";
      empty.textContent = this.query
        ? 'Nothing matches "' + this.query + '".'
        : "Nothing in this category.";
      this.grid.appendChild(empty);
      return;
    }

    // In multi mode "chosen" is a set with an order; in single mode it is
    // one value. Both collapse to the same question per item: what
    // position does this hold, or none.
    const current = this.config.currentValue ? this.config.currentValue() : null;
    const positionOf = (label) => {
      if (this.config.multi) {
        const index = this.chosen.indexOf(label);
        return index >= 0 ? index + 1 : 0;
      }
      return current && current === label ? 1 : 0;
    };
    const fragment = document.createDocumentFragment();
    const build = this.config.layout === "list"
      ? this.buildRow.bind(this)
      : this.buildTile.bind(this);
    this.visible.forEach((item, index) => {
      fragment.appendChild(build(item, index, positionOf(item.label)));
    });
    this.grid.appendChild(fragment);
    this.highlight();
  }

  buildRow(item, index, position) {
    const row = document.createElement("div");
    row.className = "stylebook-row";
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", "false");
    row.tabIndex = -1;
    if (position) row.classList.add("selected");

    const name = document.createElement("div");
    name.className = "stylebook-row-name";
    name.textContent = item.label;
    if (isNew(item)) {
      const ribbon = document.createElement("span");
      ribbon.className = "stylebook-row-new";
      ribbon.textContent = "new";
      name.append(" ", ribbon);
    }
    if (this.config.multi && position) name.prepend(orderBadge(position));

    const detail = document.createElement("div");
    detail.className = "stylebook-row-detail";
    detail.textContent = item.detail || "";

    row.append(name, detail);
    row.addEventListener("click", () => this.select(item));
    row.addEventListener("mouseenter", () => {
      this.focusIndex = index;
      this.highlight();
    });
    return row;
  }

  buildTile(item, index, position) {
    // A div, not a button. ComfyUI's global stylesheet resets button
    // padding and sizing, and a button's intrinsic height does not grow
    // from an aspect-ratio child, so tiles collapsed to the label height.
    const tile = document.createElement("div");
    tile.className = "stylebook-tile";
    tile.setAttribute("role", "option");
    tile.setAttribute("aria-selected", "false");
    tile.tabIndex = -1;
    tile.setAttribute("data-group", item.group || "");
    const titleLines = [item.label];
    if (item.aliases.length) titleLines.push("also: " + item.aliases.join(", "));
    // Said in full in the tooltip, because the badge itself only has room
    // for one word and "scene" alone does not explain what will happen.
    if (item.scene) titleLines.push("Places your subject in " + item.scene + ".");
    // The style gallery promises an artist by naming one on the tile. Say
    // who, so the connection is visible here rather than only to whoever
    // thinks to search the Artist reference for the same name.
    if (item.namesake) titleLines.push("Named for " + item.namesake + ".");
    if (isNew(item)) titleLines.push("New in " + CURRENT_VERSION + ".");
    tile.title = titleLines.join("\n");
    if (position) tile.classList.add("selected");

    const art = document.createElement("div");
    art.className = "stylebook-tile-art";
    const preview = this.config.showPreviews
      ? previewFor(item.group, item.id)
      : null;
    if (preview && applySprite(art, preview)) {
      art.setAttribute("aria-hidden", "true");
    } else {
      // The art box is a zero-height padding box, so its fallback text
      // needs its own absolutely positioned child to sit inside it.
      const glyph = document.createElement("div");
      glyph.className = "stylebook-tile-initials";
      glyph.textContent = initials(item.label);
      art.appendChild(glyph);
    }

    // Overlaid on the art rather than added as a row. Tile height is fixed
    // by grid-auto-rows plus the --sb-* line variables, so any new line
    // inside a tile silently clips the label -- and jsdom cannot see that.
    // An absolutely positioned badge costs no layout.
    if (item.scene) {
      const badge = document.createElement("div");
      badge.className = "stylebook-tile-scene";
      badge.textContent = "scene";
      badge.setAttribute("aria-hidden", "true");
      art.appendChild(badge);
    }

    // Same trick, opposite corner. Absolutely positioned over the art for
    // the reason above: tile height is fixed by grid-auto-rows, so a new
    // line inside a tile clips the label where jsdom cannot see it.
    if (isNew(item)) {
      const ribbon = document.createElement("div");
      ribbon.className = "stylebook-tile-new";
      ribbon.textContent = "new";
      ribbon.setAttribute("aria-hidden", "true");
      art.appendChild(ribbon);
    }

    const label = document.createElement("div");
    label.className = "stylebook-tile-label";
    const labelText = document.createElement("span");
    labelText.textContent = item.label;
    if (this.config.multi && position) label.appendChild(orderBadge(position));
    label.appendChild(labelText);

    tile.append(art, label);

    if (this._showCategory && item.group) {
      const category = document.createElement("div");
      category.className = "stylebook-tile-cat";
      category.textContent = groupName(item.group);
      // Hidden from assistive tech on purpose. The tile's accessible
      // name already comes from its label and title; having a screen
      // reader read "Art Brut, Art Movements" for each of 450-plus
      // options is worse than saying nothing.
      category.setAttribute("aria-hidden", "true");
      tile.appendChild(category);
    }
    tile.addEventListener("click", () => this.select(item));
    tile.addEventListener("mouseenter", () => {
      this.focusIndex = index;
      this.highlight();
    });
    return tile;
  }

  select(item) {
    // In multi mode the dialog stays open and the click toggles
    // membership. Closing after every pick would make choosing eight
    // styles eight round trips through the button.
    if (this.config.multi) {
      this.toggle(item);
      return;
    }
    try {
      this.config.onSelect(item);
    } catch (error) {
      warn("selection failed", error);
    }
    this.close();
  }

  /** Add or remove *item* from the multi-select set, keeping pick order. */
  toggle(item) {
    const index = this.chosen.indexOf(item.label);
    if (index >= 0) this.chosen.splice(index, 1);
    else this.chosen.push(item.label);
    this.renderGrid();
    this.updateChosenCount();
  }

  updateChosenCount() {
    if (!this.doneButton) return;
    const total = this.chosen.length;
    this.doneButton.textContent = total
      ? "Use these " + total
      : "Use none";
  }

  commit() {
    try {
      if (this.config.onDone) this.config.onDone(this.chosen.slice());
    } catch (error) {
      warn("selection failed", error);
    }
    this.close();
  }
}

// --- mode-driven visibility, shared by all three picker nodes -------------

/**
 * Show only the widgets the current mode actually uses.
 *
 * Style, Artist and Modifier all read the same way now: a `mode` widget
 * near the top, then the picker, the pool filters, and the seed. One rule
 * drives all three, so they cannot drift apart again.
 *
 * `pickName` is whichever widget holds the manual choice on this node.
 */
function updateModeVisibility(widgets, pickName) {
  const mode = widgets.mode && widgets.mode.value;
  const isPick = mode === MODE_PICK;
  const isCycle = mode === MODE_CYCLE;
  const isRandom = mode === MODE_RANDOM;
  const usesPool = isRandom || isCycle;

  setVisible(widgets[pickName], isPick);
  // The Modifier node narrows by axis instead of by category and tag
  // filter, and its axis applies in every mode, so those two are simply
  // absent there rather than special-cased.
  if (widgets.category) setVisible(widgets.category, usesPool);
  if (widgets.tag_filter) setVisible(widgets.tag_filter, usesPool);
  setVisible(widgets.cycle_index, isCycle);
  setSeedVisible(widgets, isRandom);
}

/**
 * Wire a picker dialog to the node widget named `pickName`.
 *
 * Choosing from a picker implies Pick mode. The alternative is a
 * selection that is silently ignored because the node is still on Random,
 * which looks exactly like the picker being broken.
 */
function attachPicker(node, pickName, config, buttonLabel) {
  const picker = new StylebookPicker(
    Object.assign({}, config, {
      currentValue: () => {
        const widget = widgetsByName(node)[pickName];
        return widget ? widget.value : null;
      },
      onSelect: (item) => {
        const fresh = widgetsByName(node);
        if (fresh.mode && fresh.mode.value !== MODE_PICK) {
          setWidgetValue(node, fresh.mode, MODE_PICK);
        }
        if (config.beforeSelect) config.beforeSelect(node, item);
        setWidgetValue(node, widgetsByName(node)[pickName], item.label);
        updateModeVisibility(widgetsByName(node), pickName);
        resizeNode(node);
      },
    })
  );
  addButton(node, buttonLabel, () => picker.open());
  return picker;
}

// --- Style node -----------------------------------------------------------

function setupStyleNode(node) {
  const widgets = widgetsByName(node);
  if (!widgets.mode || !widgets.style) return false;

  attachPicker(node, "style", {
    title: "Stylebook style gallery",
    searchPlaceholder: "Search styles by name, alias or category",
    items: styleItems,
    // A getter, not a fixed array: userData.styles fills in asynchronously
    // in setup(), possibly after this node's picker was already
    // constructed, and this is read fresh every time the dialog renders.
    get groups() {
      return userData.styles.length
        ? [GROUP_ALL].concat(CATEGORIES, [GROUP_YOURS])
        : [GROUP_ALL].concat(CATEGORIES);
    },
    showPreviews: true,
    showCategory: true,
  }, "Open style gallery");

  syncOnChange(node, ["mode"], (fresh) => updateModeVisibility(fresh, "style"));
  return true;
}

// --- Artist node ----------------------------------------------------------

function setupArtistNode(node) {
  const widgets = widgetsByName(node);
  if (!widgets.mode || !widgets.artist) return false;

  // "Reference", not "gallery". There are no pictures here, only written
  // descriptors, which is the word the Modifier picker had already
  // settled on.
  attachPicker(node, "artist", {
    title: "Stylebook artist reference",
    searchPlaceholder: "Search " + ARTIST_COUNT +
      " artists by name, movement, or what their work looks like",
    items: artistItems,
    get groups() {
      return userData.artists.length ? ARTIST_GROUPS.concat([GROUP_YOURS]) : ARTIST_GROUPS;
    },
    showPreviews: false,
    layout: "list",
  }, "Open artist reference");

  syncOnChange(node, ["mode"], (fresh) => updateModeVisibility(fresh, "artist"));
  return true;
}

// --- Modifier node --------------------------------------------------------

function setupModifierNode(node) {
  const widgets = widgetsByName(node);
  if (!widgets.axis || !widgets.modifier) return false;

  attachPicker(node, "modifier", {
    title: "Stylebook modifier reference",
    searchPlaceholder: "Search modifiers by name or by what they do",
    items: modifierItems,
    get groups() {
      return userData.modifiers.length
        ? [GROUP_ALL].concat(MODIFIER_AXES, [GROUP_YOURS])
        : [GROUP_ALL].concat(MODIFIER_AXES);
    },
    showPreviews: false,
    layout: "list",
    // Picking a modifier implies its axis, and the dropdown has to be
    // narrowed to that axis before the value is written, or the write
    // lands outside the widget's own option list.
    beforeSelect: (target, item) => {
      const fresh = widgetsByName(target);
      if (fresh.axis && fresh.axis.value !== item.group) {
        setWidgetValue(target, fresh.axis, item.group);
      }
      narrowModifierOptions(target, widgetsByName(target));
    },
  }, "Open modifier reference");

  syncOnChange(node, ["axis", "mode"], (fresh) => {
    narrowModifierOptions(node, fresh);
    updateModeVisibility(fresh, "modifier");
  });
  return true;
}

// --- Sheet node -----------------------------------------------------------

/**
 * The Sheet node picks many styles at once, so its picker is the same
 * gallery in multi mode writing into a text box rather than a dropdown.
 *
 * A text box rather than a widget of its own because the value has to
 * survive being saved, copied between workflows and edited by hand, and
 * a multiline string does all three for free.
 */
function setupSheetNode(node) {
  const widgets = widgetsByName(node);
  if (!widgets.styles) return false;

  const picker = new StylebookPicker({
    title: "Choose styles for the sheet",
    searchPlaceholder: "Search styles by name, alias or category",
    items: styleItems,
    get groups() {
      return userData.styles.length
        ? [GROUP_ALL].concat(CATEGORIES, [GROUP_YOURS])
        : [GROUP_ALL].concat(CATEGORIES);
    },
    showPreviews: true,
    showCategory: true,
    multi: true,
    currentValues: () => parseStyleList(widgetsByName(node).styles),
    onDone: (labels) => {
      const target = widgetsByName(node).styles;
      // One per line. A comma-separated list is accepted on the way in,
      // but a line each is what a person can actually read back.
      setWidgetValue(node, target, labels.join("\n"));
      resizeNode(node);
    },
  });

  addButton(node, "Choose styles", () => picker.open());
  return true;
}

/** Read the Sheet node's styles box as a list of labels. */
function parseStyleList(widget) {
  if (!widget || typeof widget.value !== "string") return [];
  const seen = new Set();
  const items = [];
  for (const raw of widget.value.split(/[\n,]/)) {
    const label = raw.trim();
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    items.push(label);
  }
  return items;
}

// --- shared option narrowing ---------------------------------------------

function narrowModifierOptions(node, widgets) {
  const axis = widgets.axis && widgets.axis.value;
  const labels = MODIFIER_LABELS_BY_AXIS[axis];
  if (!labels || !widgets.modifier || !widgets.modifier.options) return;

  const allowed = [SENTINEL_OFF].concat(labels);
  widgets.modifier.options.values = allowed;
  // A value left over from another axis would be rejected by the backend
  // with a clear message, but resetting here means the user never has to
  // read that message in the first place.
  if (!allowed.includes(widgets.modifier.value)) {
    setWidgetValue(node, widgets.modifier, SENTINEL_OFF);
  }
}

// --- shared node plumbing -------------------------------------------------

/**
 * Re-apply `sync` whenever any of the named widget values changes.
 *
 * Widget `callback` is not a reliable change hook: whether it fires, and
 * whether `widget.value` is already updated when it does, varies between
 * ComfyUI frontend versions and between widget types. Relying on it left
 * the Artist node unable to bring its dropdown back when `randomize` was
 * switched off again.
 *
 * Watching values on the draw loop instead is version-independent and
 * also catches changes that never route through a callback at all:
 * loading a workflow, undo, or an API-driven edit. The comparison is a
 * few string reads per frame and only does work when something differs.
 */
function syncOnChange(node, names, sync) {
  const readAll = () => {
    const widgets = widgetsByName(node);
    const values = names.map((name) => {
      const widget = widgets[name];
      return widget ? String(widget.value) : "";
    });
    // Serialised rather than concatenated, so ["ab", ""] and ["a", "b"]
    // can never compare equal.
    return JSON.stringify(values);
  };

  const apply = () => {
    try {
      sync(widgetsByName(node));
      resizeNode(node);
    } catch (error) {
      warn("widget sync failed", error);
    }
  };

  node.__sbLastValues = readAll();
  apply();

  // Update immediately on interaction, so the node responds the instant a
  // widget is clicked rather than on the next repaint. The draw-loop check
  // below stays as the safety net: it is what catches workflow loads,
  // undo, and any frontend version where this callback does not fire or
  // fires before the value is committed.
  const watched = widgetsByName(node);
  for (const name of names) {
    const widget = watched[name];
    if (!widget) continue;
    const previous = widget.callback;
    widget.callback = function (...args) {
      let result;
      if (typeof previous === "function") {
        try {
          result = previous.apply(this, args);
        } catch (error) {
          warn("upstream widget callback failed", error);
        }
      }
      node.__sbLastValues = readAll();
      apply();
      return result;
    };
  }

  const previousDraw = node.onDrawForeground;
  node.onDrawForeground = function (...args) {
    if (typeof previousDraw === "function") {
      try {
        previousDraw.apply(this, args);
      } catch (error) {
        warn("upstream onDrawForeground failed", error);
      }
    }
    try {
      const current = readAll();
      if (current === node.__sbLastValues || node.__sbPending) return;
      node.__sbLastValues = current;
      // Never resize during a draw. Widgets backed by a DOM element, such
      // as the multiline user_prompt, are positioned from the node
      // geometry that the in-progress frame already committed, so
      // changing the node's height mid-render leaves the textarea
      // floating detached from the node until something else forces a
      // relayout. Defer to the next frame instead.
      node.__sbPending = true;
      requestAnimationFrame(() => {
        node.__sbPending = false;
        apply();
      });
    } catch (error) {
      node.__sbPending = false;
      warn("widget sync check failed", error);
    }
  };
}

function addButton(node, label, onClick) {
  try {
    const button = node.addWidget("button", label, null, onClick, {
      serialize: false,
    });
    // The options flag alone is not enough on every frontend version: the
    // button still serialised as a trailing null, making widgets_values
    // one longer than the schema. Anything that maps saved values onto
    // widgets by index then drifts by one, which is how "Fix node
    // (recreate)" ends up with a node whose links do not line up.
    if (button) {
      button.serialize = false;
      button.serializeValue = undefined;
      if (button.options) button.options.serialize = false;
    }
    resizeNode(node);
    return button;
  } catch (error) {
    warn("could not attach '" + label + "' button", error);
    return null;
  }
}

// --- registration ---------------------------------------------------------

const SETUP = {
  StylebookStyle: setupStyleNode,
  StylebookArtist: setupArtistNode,
  StylebookModifier: setupModifierNode,
  StylebookSheet: setupSheetNode,
};

/** Widen a freshly created node so its prompt readout is legible. */
function applyDefaultWidth(node) {
  if (!node.size || node.size[0] >= MIN_NODE_WIDTH) return;
  node.setSize([MIN_NODE_WIDTH, node.size[1]]);
}

const configured = new WeakSet();

const CSS_MARKER = "data-stylebook-css";

/**
 * ComfyUI serves everything in WEB_DIRECTORY but only auto-loads the .js
 * files, so the stylesheet has to be linked in explicitly.
 */
function injectCSS() {
  if (document.querySelector("[" + CSS_MARKER + "]")) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = assetURL("./stylebook_gallery.css");
  link.setAttribute(CSS_MARKER, "1");
  document.head.appendChild(link);
}

app.registerExtension({
  name: EXT_NAME,

  async setup() {
    try {
      injectCSS();
    } catch (error) {
      warn("stylesheet injection failed", error);
    }
    try {
      await loadUserData();
    } catch (error) {
      warn("could not load custom styles from user_styles.json", error);
    }
  },

  async nodeCreated(node) {
    try {
      if (!isStylebookNode(node)) return;
      const type = node.comfyClass || (node.constructor && node.constructor.type);
      if (configured.has(node)) return;
      configured.add(node);
      // Blend and Sheet have no widget logic but still show a readout,
      // so they get the wider default too.
      const setup = SETUP[type];
      if (setup) setup(node);
      applyDefaultWidth(node);
    } catch (error) {
      warn("node setup failed", error);
    }
  },
});
