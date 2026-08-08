# Stylebook architecture

How the pack fits together, why the pieces are split the way they are,
and what to run before committing.

## Layout

Everything here is plain Python and plain JavaScript with no OS-specific
calls: paths are built with `pathlib`, nothing shells out, and the only
runtime dependency is ComfyUI itself. It runs the same on Windows, macOS
and Linux, and the test suite runs on a machine with no ComfyUI at all.

```
__init__.py               V3 entrypoint. Registers five nodes, sets WEB_DIRECTORY.
data/
  styles/                 One module per category, each a dict of style records.
  artists.py              Artist records, keyed by id.
  modifiers.py            Modifier records grouped onto five axes.
  user_data.py            Validates and merges an optional user_styles.json.
stylebook_nodes/
  stylebook_core.py       The engine. Pure functions, no ComfyUI import.
  schema_options.py       Dropdown option lists, sentinels, defaults, WIDGET_ORDER.
  node_support.py         Node-face readout and the stylebook.resolved event.
  routes.py                /stylebook/user_data HTTP route (needs server/aiohttp).
  user_data_payload.py    That route's payload shape. No ComfyUI import.
  stylebook_style.py      Style node   - exclusive medium axis.
  stylebook_artist.py     Artist node  - additive, chainable.
  stylebook_modifier.py   Modifier node - one per axis.
  stylebook_blend.py      Blend node   - two styles at a ratio.
  stylebook_sheet.py      Sheet node   - one subject, many styles, as a list.
js/
  stylebook_data.js       Generated. Never edit by hand.
  stylebook_shared.js     Helpers shared by every frontend module below.
  stylebook_gallery.js    Hand-written frontend. The generator never touches it.
  stylebook_recreate.js   A working "Fix node (recreate)". See below.
  stylebook_readout.js    "Copy resolved prompt" / "Pin this pick" menu items.
  stylebook_gallery.css   Themed against ComfyUI's CSS custom properties.
  previews/               Sprite atlases plus index.json, served statically.
previews/
  src/                    Full-size renders (gitignored, rebuildable).
  manifest.json           Content hash per tile. Drives incremental rebuilds.
scripts/                  Build and validation tooling. Not shipped to the registry.
docs/
  custom-styles.md         Field reference for user_styles.json.
tests/                    unittest suite, the data-layer validator, and:
  comfy_stub/               A stand-in comfy_api.latest.io. See "Testing the frontend" below.
  frontend/                 jsdom smoke tests for js/*.js. Run via `npm run test:frontend`.
```

## The chain protocol

Every node takes an optional `style_chain` and emits one, carrying JSON
on a socket of its own type, `STYLEBOOK_CHAIN`:

```json
{
  "_meta":     { "format": "prose", "user_prompt": "a cat" },
  "style":     { "id": "cyanotype", "...": "..." },
  "modifiers": [ { "axis": "lighting", "...": "..." } ],
  "artists":   [ { "label": "Claude Monet", "...": "..." } ]
}
```

### Why the chain has its own socket type

It used to be a plain STRING, on the reasoning that a chain is just JSON
and any string socket should reach any other. That reasoning was
backwards. Every node emits three strings, so wiring `prompt` into a
`style_chain` input connected happily and then parsed as an empty chain.
That is the whole of the reported "Blend says nothing is connected to
style B" bug: it was connected, to the wrong output, and nothing could
tell you because the types matched.

A distinct type makes the mistake impossible instead of merely
reportable. `prompt` and `negative` stay STRING and still reach any text
socket in ComfyUI, which is the flexibility anyone actually wanted.

Three composition rules, and they differ on purpose:

| Field | Rule | Why |
|---|---|---|
| `style` | Exclusive. A second Style node replaces the first. | Two mediums at once is a muddle, not a blend. Use the Blend node for that. |
| `artists` | Additive, capped at five. | Influences genuinely stack, but descriptors blur together past three. |
| `modifiers` | One per axis. A second on the same axis replaces it. | Two lighting settings cannot both be true. |

Every node re-renders the whole prompt from the merged chain, so the
`prompt` output is correct at any point in the chain and you can tap it
wherever you like.

## Why the engine has no ComfyUI import

`stylebook_core.py` and `schema_options.py` are pure Python. That is what
lets the test suite validate every dropdown, every default and the full
rendering path on a CI runner with no ComfyUI installed. The node classes
are thin wrappers: they build a schema, call an engine function, print
warnings, and return outputs.

Node modules guard their `comfy_api` import and define the node class only
when it succeeds, so importing them from a test never fails.

## Format, placement and the prose frame

`format` picks between two ways of describing a style:

- **tags** - a comma-separated keyword list.
- **prose** - a plain sentence.

Every style ships both, so switching is one click and loses nothing.
Which one a given model prefers is the user's call; the pack deliberately
does not name model families anywhere a user can see, because which
family reads which way changes faster than this repository does.

`placement` is `append` or `prepend`, defaulting to **append**. A model
reading a sentence follows that sentence's subject, and our style blocks
are paragraphs, so leading with one and naming the subject last is the
most common way to get the style honoured and the subject ignored.
Keyword lists are the other way round, which is why the tooltip points
tags users at `prepend` rather than deciding for them.

There is no `inherit` and no `auto` anywhere. `inherit` meant "use the
default" on a node with no upstream, which is a setting that does
nothing. The `auto` format claimed to choose prose when a style had prose
text, and every style has prose text, so it was always prose. The `auto`
placement applied a real rule, but a widget reading "auto" tells you
nothing about what your prompt will look like, so the rule moved into the
tooltip as advice and the widget now says what it does.

### The prose frame

In prose, the style block is introduced rather than appended bare:

```
append   {subject} Rendered as {style block}
prepend  Rendered as {style block} The image shows {subject}
```

Without that connective, a style whose prose opens on a noun phrase reads
as more scene content. Chaining a subject description into the
View-Master Slide style produced a prompt ending "...during winter. A
View-Master stereo slide with a cardboard mount holding a plastic film
strip", and the model put a View-Master in the picture instead of
rendering the picture as one. An explicit connective retags everything
after it as a description of the medium.

Two cases deliberately get no frame:

- **No subject.** There is no boundary to mark, and a bare "Rendered as
  ..." fragment is not a sentence.
- **Tags format.** A keyword list has no grammar to confuse, so a
  connective would be tokens spent on nothing. Position is the only
  signal there, and the leading terms weigh most.

The pack is unreleased, so nothing here carries a compatibility shim for
a shape we tried and discarded. If a saved workflow breaks because an
option changed, re-pick the widget.

### "Fix node (recreate)", and why we ship our own

That menu entry is not a ComfyUI feature. ComfyUI-Manager contributes it,
and on frontend 1.47 its implementation throws partway through:

```
TypeError: t.findInputSlot is not a function
  at LGraphNode.connect
  at node_info_copy   (node_fixer.js, reconnecting the inputs)
```

Node ids are strings now. Manager calls `src.connect(slot, dest.id,
name)`, and `connect` only resolves its second argument to a node when
that argument is a *number*, so a string id sails past the lookup and
`connect` calls `findInputSlot` on it. The callback creates the
replacement first and removes the original last, so the exception leaves
both on the canvas: the original still wired up, the replacement floating
unconnected on top of it. That is the whole of the reported bug, and it
is not specific to this pack: it happens to any node with a connected
input.

`js/stylebook_recreate.js` installs a correct one for Stylebook nodes and
takes the broken entry out of their menu. Nothing global is patched.

Three rules make a recreate correct, and each is a bug avoided:

1. **Pass the node object to `connect()`, never its id.** Ids are strings.
2. **Restore widget values by name, never by index.** Recreating a node
   is what you do *because* the schema changed, so an index-based copy
   writes every value into the wrong widget from the first added or
   removed input onward. A value that is no longer valid for a combo is
   dropped and reported, not forced: writing an invalid value produces a
   node that fails prompt validation over something the user never chose.
3. **Reconnect by slot name, never slot number**, for the same reason.

Remove the original *before* reconnecting. An input holds one link, so
reconnecting first fights the link still attached to the old node.

The menu entry is installed as an own property on the node instance, not
as another prototype wrapper. Every pack that adds menu entries wraps the
prototype, and the last wrapper installed runs its additions last; an
instance property shadows the whole chain, so we always see the finished
option list regardless of extension load order.

## Preview pipeline

Thumbnails are content-addressed. `previews/manifest.json` stores, per
style, a hash of everything that affects the image: its prose, tags and
negative, the category subject, the model, and every sampler setting.

```
python scripts/build_previews.py --check    # what drifted (no GPU needed)
python scripts/build_previews.py --build    # render only those, then repack
python scripts/build_previews.py --pack     # repack atlases only
```

Edit a style's text and its hash stops matching, so `--check` reports the
tile as stale and CI fails. Add a style and it reports as missing. This is
what keeps the gallery honest as the data grows.

Two details worth preserving:

- The render feeds each style's **own** `negative` field, on top of a
  small shared base. Styles defined by what they exclude (ligne claire's
  "no hatching, no cast shadows") render as their own opposite without it.
- The render prompt is built the way the node builds it, subject first
  with the style trailing. A tile that does not represent node output is
  worse than no tile.

Rendering needs Pillow for the packing step. That is a build-time tool
only; the node pack itself has no runtime dependencies.

A style whose subject is a place rather than a person needs an entry in
`STYLE_SUBJECT`. The category subject puts a figure front and centre,
which is the one thing Liminal Space, Googie and Metaphysical Art are
defined by not having. Word those overrides affirmatively for the same
reason the data validator forbids negation in a positive prompt: "no
people" is the most reliable way to get people.

## The public gallery page

`scripts/build_gallery_page.py` renders every style to a single static
page at `docs/gallery/index.html`, which GitHub Pages serves from `main`.
The pack's pitch is "look at it before you commit", and until this existed
the only way to look was to install it first.

It reuses rather than duplicates: the committed WebP atlases, and
`generate_js_data._preview_sprites` for the sprite arithmetic. Pages
serves the whole repository, so the page reaches the atlases at
`../../js/previews/` and nothing is copied. `--check` is a CI gate, like
every other generator here.

One deliberate difference from the in-app gallery: this page shows each
style's prose, keywords and negative. Shipping 460-odd prose blocks in
`stylebook_data.js` would roughly double the payload every ComfyUI user
downloads, but on a page somebody chose to open it is the most useful
thing on it.

## Frontend

`stylebook_data.js` is generated in full from the Python data layer.
`stylebook_gallery.js` is hand-written. They are separate files because a
previous revision generated into the middle of a hand-edited file, whole-file
overwrite included, which silently deleted the `export` statements the
gallery imported and took the entire frontend down. `--check` still passed,
because it compared the generated block against a fresh render of itself.

Keep that boundary. If the generator ever needs to emit something new, add
it to `stylebook_data.js`, never to the gallery.

Gallery thumbnails are sliced out of per-category WebP atlases with CSS
sprite offsets, expressed in grid units: an atlas `cols` tiles wide is
scaled to `cols * 100%` of one tile, and cells are addressed with
percentage positions. Tiles are a **definite** size (`--sb-tile`) with an
explicit `grid-auto-rows`, not a fluid `1fr` column, which also means the
gallery renders identically at any window size, zoom or display scaling.

The frontend is strictly optional. Everything it does is convenience; the
node computes its result entirely on the backend, and every frontend
operation is wrapped so a failure degrades rather than breaks.

### Frontend rules that are not optional

Each of these was a shipped bug. Lint, the test suite and node
registration were all green while the UI was visibly broken, so verify
frontend changes in a browser and measure the DOM.

- **Do not use `<button>` for tiles or tabs.** ComfyUI's global stylesheet
  resets bare button padding, and a button's intrinsic height does not
  grow from an aspect-ratio child. Use divs with `role`, plus the scoped
  reset at the top of the stylesheet.
- **Do not size a grid row from `aspect-ratio` or percentage padding.**
  Both resolve to zero when a grid computes a row's intrinsic height
  contribution, so rows collapse and every tile overlaps the next.
- **Hide a widget with the type swap AND `widget.hidden = true`.** The
  type swap alone is ignored by newer frontends, which leaves a trailing
  hidden widget still painted.
- **Restore `computeSize` with `delete`, never by reassigning.** Most
  widgets have no own `computeSize` and use LiteGraph's default, so the
  saved value is `undefined`; assigning it back leaves the zero-size stub
  and the widget never reappears.
- **Never resize a node from `onDrawForeground`.** Widgets backed by a DOM
  element, such as a multiline text box, are positioned from the geometry
  the in-progress frame already committed, so the box detaches from the
  node. Defer with `requestAnimationFrame`.
- **Hide a seed together with its `control_after_generate`.** ComfyUI adds
  that control as a separate sibling widget.
- **A control must never move out from under the cursor.** Put a toggle
  above the widgets it swaps, and prefer greying a widget out in place to
  removing it, so the node height does not change as you click.
- **Recreating a node: pass the node object, map by name.** See below.
- **A non-serialising widget must actually not serialise.** The gallery
  button still wrote a trailing null into `widgets_values` with only
  `{serialize: false}` in its options, making the saved array one longer
  than the schema. Anything mapping values onto widgets by index drifts
  by one from there, which is how a recreated node loses its links. Set
  `widget.serialize = false` on the widget itself as well.

## The node-face readout and `stylebook.resolved`

Every node shows two lines on its own face: `stylebook_core.resolved_summary`
(a short "Style · Artist · Modifier (axis)" line, never truncated) and
`readout_detail` (the rendered style/artist/modifier text, with the user's
own subject collapsed to a literal `[subject]` marker). Both are built in
`node_support.show_readout`.

This replaced a single-line readout that showed the rendered prompt
truncated from the front. With `placement=append` (the default) the
subject leads, so every node in a chain showed the same opening of the
user's own text, and the style — the one thing the node actually added —
was always past the 300-character cut. Worse, Random mode had no readout
at all: nothing named what got picked. `readout_detail` renders with an
empty subject specifically to dodge `render_prompt`'s framing connectives
(see "Two cases deliberately get no frame" above), which leaves exactly
the style/artist/modifier text with no half-sentence around it — the part
of the prompt this node is actually responsible for, which is also the
part worth spending the truncation budget on.

Alongside the readout, `node_support.send_resolved_event` sends a
`stylebook.resolved` PromptServer event: `{node_id, prompt, style, artist,
modifier, axis}`, with `prompt` full and untruncated. `js/stylebook_readout.js`
listens for it and adds two context-menu items:

- **Copy resolved prompt**, on all five nodes: the clipboard gets `prompt`
  from the event, not the capped node-face text.
- **Pin this pick**, on Style/Artist/Modifier only: writes the resolved
  label into that node's own pick widget (plus `axis` on Modifier) and
  flips `mode` to Pick. Blend's style is a synthetic merged composite and
  Sheet resolves N styles, so neither has a single pick to pin — both
  still get Copy, just not Pin.

A listener is registered per node instance and unsubscribed from
`node.onRemoved` (chained the same way `getExtraMenuOptions` is, below).
Skipping that is a real, if slow, memory leak: every node ever created
would keep a live `api` listener forever, even after being deleted from
the graph.

## `WIDGET_ORDER`: one source of truth

`schema_options.WIDGET_ORDER` is the serialised widget order per node, as
ComfyUI actually writes `widgets_values` — read off a live node with
`serialize()`, not inferred. Two things about it are not obvious from
`define_schema`: a seed with `control_after_generate` contributes two
entries, and a DOM-backed multiline widget (`user_prompt`, `styles`) always
sorts after every plain widget regardless of its position in the schema.

Three things read this one constant, so they cannot drift apart:
`tests/test_engine.py`'s `ExampleWorkflowTests` (checks the shipped example
workflows against it), `tests/test_schemas.py`'s
`WidgetOrderDerivationTests` (checks it is still derivable from the live
`define_schema()` output), and `scripts/dump_frontend_fixtures.py` (feeds it
to the jsdom tests below). A schema change that forgets to update this
constant now fails on the Python side before it ever reaches a saved
workflow.

## Testing the frontend without a browser

Six bugs — including the CI gate that had never once run and the Artist
node silently losing its picker button — shipped through a fully green
Python suite, because nothing in the pipeline ever opened the page. Two
layers close that gap.

**The Python side: a stand-in for `comfy_api.latest.io`.** Every node
module does `try: from comfy_api.latest import io / except ImportError`
and only defines its class when that succeeds, so `NodeSchemaTests` used
to `raise unittest.SkipTest("ComfyUI not installed")` in CI and never ran
there at all. `tests/comfy_stub/comfy_api/latest/io.py` is a record-only
implementation of exactly the surface this pack uses. `tests/__init__.py`
registers it on `sys.path` **only if the real package is not importable**
— real-first, stub-fallback, so this repo's own dev machine (with ComfyUI
installed) always exercises the genuine API and the stub only covers a
runner that has neither.

That registration has to happen in `tests/__init__.py`, and every
`unittest discover` invocation in this repo needs `-t .`
(`python -m unittest discover -s tests -t . -v`). Reason, found the hard
way: a module only runs its top-level code once per process, so if
`test_engine.py` imports `stylebook_nodes.*` before the stub is
registered, `_COMFY_AVAILABLE` is permanently `False` for that module for
the rest of the run, and no later registration undoes it. `-t .` makes
`tests` a genuine subpackage of the repo root, which is what forces
Python's import system — not `unittest`'s own directory-walk, which does
not give this guarantee on its own — to run `tests/__init__.py` before any
`test_*.py` file in it.

**The JS side: `tests/frontend/`, run via `npm run test:frontend`.**
`hooks.mjs` registers a `node:module` resolve hook
(`module.registerHooks`, not the deprecated `module.register`) that
redirects any specifier ending `/scripts/app.js` or `/scripts/api.js` to
`stubs/`, by suffix rather than exact path so it survives `js/` files at
different relative depths. That is what lets the real, unmodified
`js/stylebook_gallery.js` (etc.) be imported outside ComfyUI at all.
`fake_node.mjs` builds a LiteGraph-shaped node from
`fixtures/nodes.json` — generated by `scripts/dump_frontend_fixtures.py`
from `WIDGET_ORDER` and the live schemas, `--check`-gated the same way
`generate_js_data.py` is, so a Python rename breaks the JS fixture lookup
instead of silently drifting from it.

Honest limit: jsdom has no layout engine, so `clientWidth` reads 0 and
anything depending on real layout, CSS or drag/drop cannot be exercised
here. This catches wiring, visibility, serialization and dialog logic —
the class of bug that has actually shipped — not painting. It does not
replace opening the page before a release.

## `/stylebook/user_data` and the "Yours" tab

`stylebook_nodes/routes.py` registers a read-only route on the shared
`PromptServer.instance.routes`, imported from `__init__.py` inside
`try/except ImportError` so the pack (and the test suite) still load
without `server`/`aiohttp`. It has no parameters and does no filesystem
access at request time — it serialises `USER_ADDED_STYLES`/`_ARTISTS`/
`_MODIFIERS`, which are already resident in process memory from the merge
that ran at import. The payload shape itself lives in the ComfyUI-free
`user_data_payload.py`, which is what `tests/test_user_data.py` actually
exercises.

`js/stylebook_gallery.js` fetches this once in `setup()` and merges the
results into `styleItems()`/`artistItems()`/`modifierItems()`. A custom
entry keeps its real category/axis as `group`, so it shows up under "All"
and its own category exactly like a built-in; a synthetic `GROUP_YOURS`
tab is added only once there is something to put in it, filtered by
`item.isCustom` rather than by group. A missing route, a failed fetch or a
malformed response all leave the module-level `userData` at its empty
default — every picker degrades to exactly the built-ins-only behaviour
from before this existed, never a broken tab.

Two environment variables, read once by `data/user_data.py` at import:

- `STYLEBOOK_IGNORE_USER_STYLES=1` makes every `apply_user_*` a no-op.
  `scripts/generate_js_data.py`, `scripts/dump_frontend_fixtures.py`,
  `scripts/build_previews.py` and `tests/validate_data.py` all set this
  before importing `data`, because without it a maintainer's own local
  `user_styles.json` gets baked into a shipped artifact and makes
  `--check` pass or fail depending on whose machine ran it.
- `STYLEBOOK_USER_STYLES=/path/to/file.json` moves the file outside the
  pack directory, so a Manager reinstall or `git clean` cannot take it
  with it.

## The three picker nodes are one design

Style, Artist and Modifier all do the same job on different axes, so they
read identically: a `mode` widget of Pick, Random or Cycle, then the
manual picker, then the filters Random and Cycle draw from, then the
seed. One function in the frontend drives visibility for all three, so
they cannot drift apart again.

The Artist node used to carry a `randomize` boolean instead. A boolean
cannot express Cycle at all, and it made two nodes doing the same job
look like they did different jobs.

Defaults differ on purpose, and only once:

| Node | Default mode | Why |
|---|---|---|
| Style | Random | A freshly dropped node that renders nothing looks broken rather than empty. |
| Artist | Random | Same. |
| Modifier | Pick, with `Off` | A modifier is a deliberate finishing tilt. One that applied a random lighting the moment it landed would be changing your image without being asked, and `Off` is a real member of its option list rather than an empty selection. |

## Resolving a hand-typed style name

`get_style` is strict: id or label only. It backs the dropdown, where the
value always came from the option list, so a widget that quietly resolved
a near-miss would hide a real mismatch.

`resolve_style_name` is for the Sheet node's text box, where a human
typed the name. Order matters, because 12 aliases collide with a real
label elsewhere in the pack and 6 are claimed by two styles at once:

1. An exact id or label wins outright. "Deep Focus" is both a label and
   somebody else's alias; the label is what you meant.
2. An alias claimed by exactly one style resolves to it. "Ukiyo-e" is a
   term people know and it is an alias of Woodblock Print.
3. An alias claimed by several resolves to nothing and returns the
   candidates, so the node can name them. "diorama" is Tilt-Shift and
   Museum Diorama; picking one would be a coin flip presented as an
   answer.

Both lookups go through dicts built once at import. A linear scan per
name meant resolving a list of eight cost eight passes over every record.

### Tag filtering has exactly one implementation

`stylebook_core.filter_pool` (and `filter_artist_pool`) is it: comma-
separated terms, every one must match, checked against tags, prose, label
and aliases. `data/styles/get_style_ids` and `data/artists.get_artist_ids`
take a `category` only and nothing else.

There used to be a second, narrower one on `get_style_ids` itself:
whole-string substring matching against `tags + prose`. Under it, any
filter containing a comma matched nothing at all — the exact bug already
fixed once in `filter_pool`. It was removed rather than fixed a second
time, because the real problem was having two implementations with
different semantics reachable from the same layer. If you need to filter
the data layer by tag, use `filter_pool`; do not add the parameter back to
`get_style_ids`.

## Ordering: one rule, two languages

Every list a person reads is ordered by `data/ordering.py`'s
`label_sort_key`: accents and case folded away, runs of digits compared as
numbers. It exists because a bare `sorted()` ranks by code point, and that
got two things visibly wrong. Accented names sorted past Z, so
`Élisabeth Vigée Le Brun` was the **last** entry in the artist dropdown,
after `ZBrush Sculpt Render`. And digits ranked as text, so
`16-Bit Pixel Art` came before `8-Bit Pixel Art`.

The gallery cannot just read the generator's order. It interleaves entries
from a user's own `user_styles.json`, which the generator never saw, so it
needs a live comparator — `Intl.Collator(undefined, {sensitivity: "base",
numeric: true})` in `js/stylebook_gallery.js`. That puts the same rule in
two languages, which is a drift risk, so `tests/frontend/gallery.test.mjs`
asserts that re-sorting `ALL_STYLE_LABELS` (ordered by the Python key)
with the JS comparator changes nothing. One assertion, and the two cannot
silently diverge.

Styles and artists sort. **Modifier axes deliberately do not**: the `era`
axis reads chronologically — Ancient Classical, Edwardian, 1920s, 1950s —
and alphabetising would drag the decades to the top and scatter them.
`schema_options.modifier_options()` and the gallery's `modifierItems()`
both leave that list in data order, and they have to agree.

The gallery's tiles gained a category chip at the same time. Sorting
alphabetically is much easier to scan but throws away the grouping cue
that category-ordered tiles gave for free, so the chip puts it back — only
in "All", "Yours" and search results, where the tab strip does not already
name the category. Its height feeds `--sb-cat`, which `grid-auto-rows`
adds to the row: the grid row height is explicit (see **Frontend**), so a
line added inside a tile has to be added to the row too, or it is clipped.
jsdom does not lay out CSS grid and will not catch that.

Ordering is presentation only. Nothing the engine does depends on it — see
**Seed stability** below for why.

## Seed stability, stated honestly

`Random` is stable and `Cycle` is not, and the tooltips say so.

`stable_choice` scores every candidate against the seed with a hash and
takes the winner, rather than indexing a sorted list. Pool order is
therefore irrelevant: reordering the data changes nothing, and adding an
entry only changes the seeds where the newcomer happens to score highest,
about one in N. Indexing a sorted list would instead shift every later
entry, so shipping one new artist would silently change what most saved
workflows produce.

`cycle_index` genuinely is a position in a sorted list, because sweeping
a category in order is the whole point of it. Adding entries shifts what
an index returns. That is a fair trade for the feature, but it must be
said out loud rather than left for someone to discover.

## Negation, in both directions

Two rules, both learned from defects that shipped.

**A `negative` field must never contain a negated clause.** It is fed
straight into a negative prompt, and text encoders handle negation
poorly, so "no wax" lands as "wax" and suppresses the thing it was meant
to protect. Candle Making shipped with `negative` = "no wax, no wick, no
flame, digital rendering, cold material, no glow, no translucency, opaque
solid". Three of those clauses are correct exclusions; the other five
named the style's own defining features. A quarter of the pack carried
252 such clauses between them. They were deleted rather than rewritten, because in every case
the surviving clauses already stated the real opposite.

**Positive text must not carry bare negations either.** Same mechanism,
opposite field. Line Art's tags read "pure contour, no shading, no
colour" while also saying "the interior left blank white", so the
negation bought nothing and cost the encoder reading "shading" and
"colour". Say the affirmative and stop.

Phrases naming a process rather than a visible property are exempt:
"painted without hesitation" and "exhibited without jury" describe no
property of the image, so rewriting them would be motion without
improvement.

## Writing style text

Three rules, each learned from a defect.

**Describe the rendering, not the subject.** Macro photography once listed
"dew drops" and "insect-eye perspective" in its tags. Those are examples
of things people photograph up close, not properties of macro rendering,
so they appeared in images of whatever the user actually asked for. A
style may only name a subject when the subject *is* the style: Ikebana is
an arrangement of flowers, and removing the flowers leaves nothing.

**State properties affirmatively, not only as negations.** Rendering
Ligne Claire without its negative keeps the uniform line weight and loses
the flat colour, because the positive stated the line weight affirmatively
and left the flat colour to a "no hatching, no shading" clause. Models act
on "every interior filled with one single flat tone" far more reliably
than on "no shading". Say both: the negative sharpens it, and the
affirmative means the style still holds at CFG 1 where no negative
applies.

**Concrete visual nouns, not mood adjectives.** A tag string reading
"sudden, jarring, explosive, rapid" gives a model nothing to draw. This
was confined to one category and is now guarded by a review script.

## Adding a style

1. Add the record to the right module under `data/styles/`. Required
   fields: `id` (matching the key), `label`, `category`, `aliases`,
   `tags`, `prose`, `negative`, `preview`, `blocks`.
2. Write `tags` as concrete visual noun phrases. A list of mood adjectives
   ("sudden, jarring, explosive") gives a model nothing to render.
3. Write `negative` as what this style is *not*. It is used both at render
   time and in the preview build.
4. Set `blocks` when the style already fixes an axis. A cyanotype fixes
   `color_grade`, so a Sepia modifier on top would fight it. Every style
   that is monochrome or single-hue by definition currently does this.
5. Run the gate below, then `--build` the preview.

## Local gate

Run all of these before committing:

```
python -m ruff check .
python tests/validate_data.py
python -m unittest discover -s tests -t . -v
python scripts/generate_js_data.py --check
python scripts/dump_frontend_fixtures.py --check
python scripts/build_previews.py --check
npm ci && npm run test:frontend
```

Or `python scripts/pre_commit_check.py`, which runs the Python half of the
lot (everything except the frontend suite, which needs Node).

The data validator is not decoration. It fails the build on duplicate
labels, ids that disagree with their key, records claiming a reserved
sentinel word, thin descriptions, and double-encoded text. Each of those
rules exists because that exact defect shipped once.
