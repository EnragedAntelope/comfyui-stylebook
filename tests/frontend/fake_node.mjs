/**
 * Builds a LiteGraph-shaped fake node from the fixture the Python side
 * generates (scripts/dump_frontend_fixtures.py --check gates this file
 * staying in sync with schema_options.WIDGET_ORDER). One node type's
 * widgets, in the real serialization order, each carrying the type/value/
 * options the corresponding define_schema() input actually declares.
 */

import { readFileSync } from "node:fs";

const FIXTURES = JSON.parse(
  readFileSync(new URL("./fixtures/nodes.json", import.meta.url), "utf8")
);

/**
 * @param {string} comfyClass e.g. "StylebookStyle"
 * @param {string|number} [id] LiteGraph node id; defaults to a stable value
 *   since most tests only need *a* node id, not a specific one.
 */
export function makeNode(comfyClass, id = "1") {
  const widgetDefs = FIXTURES[comfyClass];
  if (!widgetDefs) {
    throw new Error(`fixtures/nodes.json has no entry for ${comfyClass}`);
  }

  const node = {
    id,
    comfyClass,
    size: [140, 80],
    widgets: widgetDefs.map((def) => ({
      name: def.name,
      type: def.type,
      value: def.value,
      // LiteGraph keeps a combo's choices at widget.options.values; other
      // widget kinds carry an options object too but this pack's frontend
      // code only ever reads .values, so an empty object is a faithful
      // stand-in for the rest.
      options: def.options ? { values: def.options.slice() } : {},
      callback: null,
      disabled: false,
      hidden: false,
      label: undefined,
    })),
    graph: {
      getLink: () => null,
      links: {},
    },
    setSize(size) {
      this.size = size;
    },
    setDirtyCanvas() {},
    computeSize() {
      return [this.size[0], this.size[1]];
    },
    onDrawForeground: null,
    getExtraMenuOptions: null,
  };

  node.addWidget = function addWidget(type, name, value, callback, options) {
    const widget = {
      name,
      type,
      value,
      options: options || {},
      callback: typeof callback === "function" ? callback : null,
    };
    this.widgets.push(widget);
    return widget;
  };

  return node;
}

export function widgetByName(node, name) {
  return node.widgets.find((widget) => widget.name === name);
}
