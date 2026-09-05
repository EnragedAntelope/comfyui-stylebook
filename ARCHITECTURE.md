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
  stylebook_data.js       Generated. Never edit by hand. Small on purpose.
  stylebook_data.json     Generated. The corpus, fetched on first picker open.
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

A `data/model_families.py` once mapped checkpoint-name substrings to a
default `artist_detail`, and shipped to the registry for several releases
without a single caller: the Artist node has always taken that setting
from its own widget. It has been removed. Re-adding it means arguing
against the paragraph above first, not just wiring it up.

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

## Modifier preview tiles

Three of the six modifier axes are *purely visual*: `lighting`,
`color_grade` and `finish`. A sentence about Bleach Bypass tells you far
less than the picture does, and choosing between Rembrandt and Split
lighting from prose is guesswork. Since 0.14.0 those three ship rendered
tiles, built by the same pipeline as the style tiles.

### Why it needed almost no new code

`js/previews/index.json` keys its `categories` map by **the picker's group
key**, and every consumer looks that key up directly:
`previewFor(item.group, id)` in the gallery, `applySprite(group, id)` on
both public pages, and a plain iteration in
`generate_js_data._preview_sprites`. A modifier's group *is* its axis. So
adding `lighting`, `color_grade` and `finish` to that same map — none of
which collides with the twelve style categories — made sprite lookup work
everywhere with no new lookup code at all. The index `version` went 2 → 3;
it is additive, and a consumer reading it finds three extra keys it never
asks for.

The renderer needed no second path either. `render_one`, `build_workflow`
and `render_with_retry` take a style-shaped dict and never ask what kind
of thing it is, so `modifier_record()` hands them a synthetic one. Two
things keep the namespaces apart, because `chiaroscuro` is both a style id
and a lighting modifier id: source renders go to `previews/src/mod/`, and
the manifest section is `modifier_tiles`, not `tiles`.

`MANIFEST_VERSION` was deliberately **not** bumped for that new section.
`load_manifest()` discards a manifest whose version it does not recognise,
so bumping it would have thrown away every style tile hash and silently
queued a full re-render of the pack.

### What a tile shows, and the baseline

One fixed base render, varied only by the modifier: `MODIFIER_SUBJECT` (a
clothed person with head and shoulders in frame, a flat surface beside
them and a wall falling off behind, so direction, grade and finish all
have something to read on) and `MODIFIER_BASE_STYLE`. Both feed the tile
hash, so changing either re-renders exactly the affected tiles.

**The base style has to anchor the scene without asserting a rendering,
and that line was found by measurement rather than argument.** The first
version was one sentence — "A plain photographic rendering." — and it was
too thin: the modifier clause became almost the whole prompt, so the model
rendered the modifier *as the subject*. Colour grades flooded the frame
and lost the figure; Glossy Lacquer replaced the person with a black
lacquered mannequin head.

A second draft added photographic anchoring and also asserted "the person
sharp", "plain even exposure" and "natural perspective". That fixed the
grades and **suppressed** the finishes: Glossy Lacquer came back as an
ordinary untreated photograph, because the base was now contradicting the
axis it existed to display.

The wording that ships anchors only the scene and the framing and says
nothing about how the image is rendered, because that is precisely what
the modifier is for.

Three failure modes show up only in a rendered tile, and all three are
invisible when reading the record. A modifier must name the light or
finish's **behaviour**:

- Naming its **shape** makes an object. "a hard boundary where the falloff
  meets the black" drew a black rectangle over the face; "a bright edge"
  drew a glowing rectangle around the figure; "a bright halo" drew a neon
  ring around the head.
- Naming a **medium or a place** makes a scene. "lit through water"
  flooded the room; "wet reflective surfaces" built a rain-slick street.
- **Over-protecting the subject suppresses the axis.** Rim lighting
  under-exposes the front by definition, so a record insisting the face
  stays visible loses to it and the modifier disappears.

`rim_lighting` sits between the first and third of those and no wording
found so far satisfies both; it keeps its original text deliberately, and
its tile is known to be imperfect. Across a 16-render A/B/C it scored best of the three
on both edge energy and tonal spread, and it is the reason the colour
grade tiles show a face at all. If you change it, re-run that comparison
rather than reasoning about it — the sibling study in 0.12.0 nearly saw
twenty records rewritten when the harness was the thing at fault.

There is one extra render, `_baseline`: the same subject and base style
with **no** modifier at all, packed into each of the three axis atlases.
A modifier tile is close to meaningless without the thing it deviates
from — "warmer than what?" is a fair question — so the public modifier
reference page shows it once at the head of each tiled axis, and the
picker's footer hint points at it.

### The picker's layout is per group, not per picker

`layout` and `showPreviews` used to be whole-picker config, read at four
points. They are now read through `activeLayout()` and `activePreviews()`,
which consult the config's optional `groupLayout` and `previewGroups`
maps against the tab currently shown; the grid's className moved out of
the constructor and into `renderGrid()` because it now changes when the
tab does. Result: Lighting, Colour Grade and Finish draw a tile grid,
while Era, Period Dress and Mood keep their rows and their descriptor
text. "All", "New", "Yours" and any search result span groups and fall
back to the picker's own `layout`.

`buildTile` also puts `item.detail` in the tooltip now. A style has no
`detail`; for a modifier the descriptor **is** the information, and a tile
has less room for text than a row.

One trap worth knowing: **a modifier is addressed by label everywhere in
this pack**, so the picker item's `id` is its label. The atlas is keyed by
record id, as every atlas is, because a label can be reworded and an id
cannot — hence `previewId` on the item and `mid` in `MODIFIER_RECORDS`.

`PREVIEW_AXES` in `scripts/build_previews.py` and `PREVIEWED_AXES` in
`js/stylebook_gallery.js` are one rule in two languages, bound by
`tests/test_previews.PreviewedAxesMirrorTests` — the same arrangement as
the ordering rule and its `Intl.Collator` mirror.

### `era` and `mood` are closed axes

The other three axes did not merely go un-tiled; two of them are closed to
new records, and this is written down so it is not re-proposed.

**`era` will not grow.** Since 0.12.0 an era modifier must describe light
*behaviour*, never a fixture or a garment (see below). Every candidate
worth having — Ancient Egyptian, Edo, Bronze Age, Belle Époque — reduces
under that constraint to light behaviour indistinguishable from
`Ancient Classical` or from an existing decade, and each one also costs a
paired `period_dress` record. The axis is complete, not neglected.

**`mood` will not grow either.** Twenty-one records already cover the
space, and every candidate generated against them (Wistful, Triumphant,
Anxious, Bittersweet, Austere) collapses into two existing moods. This is
the Ring Light argument from 0.13.0 applied before spending a render
rather than after: if stripping the one distinguishing word leaves
something already shipped, the record was never distinct.

`lighting`, `color_grade`, `finish` and `period_dress` stay open.

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
style's prose, keywords and negative. Shipping the whole prose corpus to
ComfyUI would roughly double what every user downloads, but on a page
somebody chose to open it is the most useful thing on it.

## Frontend

`stylebook_data.js` and `stylebook_data.json` are generated in full from
the Python data layer. `stylebook_gallery.js` is hand-written. Generated
and hand-written are separate files because a previous revision generated
into the middle of a hand-edited file, whole-file overwrite included,
which silently deleted the `export` statements the gallery imported and
took the entire frontend down. `--check` still passed, because it compared
the generated block against a fresh render of itself.

Keep that boundary. If the generator ever needs to emit something new, add
it to the generated files, never to the gallery.

### Why the corpus is a `.json`, not a `.js`

ComfyUI finds frontend extensions by globbing `**/*.js` under every pack's
web directory and importing every hit (`server.py`, `get_extensions`). It
does not check whether a file registers an extension: a `.js` file in
`js/` is parsed at app start regardless. The style corpus was about
300 KB of that, charged to every ComfyUI user on every load — including
the ones with no Stylebook node on the canvas.

So the split is by *when it is needed*, not by what it is:

- `stylebook_data.js` (a few KB) holds what a node needs before any dialog
  exists — the axis-to-modifier map that gates the Modifier widget, the
  category tables, the counts, the version.
- `stylebook_data.json` holds everything else and is fetched the first
  time a picker opens. The glob does not match it.

`tests/test_versions.LazyCorpusTests` is the tripwire: it fails if the
eager module grows past a few KB or if a corpus export reappears in it.

A `.mjs` module with a dynamic `import()` would read better, but a module
import is subject to the server's MIME type for that extension, and
`mimetypes` on Windows takes its answer from the registry. `fetch` plus
`response.json()` enforces no MIME type at all.

The dialog opens before the corpus arrives and shows "Loading styles...",
then a message with a **Try again** button if the fetch fails. An empty
gallery with no explanation reads as a broken pack.

### What each entry's release stamp is for

`data/versions.py` maps every style, artist and modifier id to the release
it first shipped in, and lists every release oldest-first. It is generated
by `scripts/stamp_versions.py`:

```
python scripts/stamp_versions.py --check          # CI gate
python scripts/stamp_versions.py --stamp          # new entries -> this version
python scripts/stamp_versions.py --from-history   # rebuild from git
```

The habit is: add records, run `--stamp`. `--check` fails when a shipped
entry has no stamp, which is the failure the convention alone could not
catch — an unstamped style would simply sort as if it had always been
there and never appear under "New".

The gallery reads it for two things: the **New in x.y.z** tab, and the
**Newest first** sort. Both rank on position in `RELEASES` rather than
comparing version strings, because "0.10.0" sorts before "0.9.0" as text.
It is presentation data only — nothing here reaches a prompt, and no seed,
saved workflow or dropdown order depends on it.

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

That exception is now a field rather than a judgement call. See
"Styles that set the scene" below.

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

## Styles that set the scene

Most styles change *how* your subject is drawn. A minority also decide
*where* it is, and the difference matters enough to be visible before you
render rather than after.

Liminal Space is the clear case. The aesthetic comes from anthropology —
*limen*, a threshold — and names a transitional place emptied of the
people it was built for. Strip the place out and nothing survives but a
yellow-green fluorescent snapshot. The same is true of Vanitas without its
skull and guttering candle, Ikebana without its flowers, and de Chirico's
Metaphysical Art without its arcaded piazza.

Such a style declares an optional **`scene`** field: a short affirmative
noun phrase naming what it imposes.

```python
"scene": "a deserted transitional interior",
```

Three things read it, which is the whole reason it is data and not a
comment:

- **`tests/validate_data.py`** rejects scene nouns in any style that has
  *not* declared one, and in **every modifier**, which gets no `scene`
  escape at all — a modifier tilts one axis of the rendering and is never
  the reason a place is in the picture. That second half was missing for
  a while, and in the gap the Neon Noir lighting modifier shipped
  "rain-slick streets" in its tags: a wet street added to every image it
  touched, on an axis chosen for its colour. The lexicon had
  `rain-slicked` but not the bare `rain-slick` the modifier actually
  used, so even the styles-only pass would have missed it. The lexicon
  is deliberately narrow and hand-verified against every style in the pack, because the obvious wide version is
  mostly false positives — "paper" is a substrate, "hand" is hand-pulled,
  "plate" is a printing plate, "field" is depth of field, "face" is a coin
  face and "plane" is the picture plane. A narrow gate that is always
  right beats a broad one that trains you to skim past it. It also matches
  on word boundaries with an optional plural: a plain substring test found
  "alley" inside *gallery* and "wheat" inside *wheat-pasted*.
- **The gallery** badges those tiles and spells it out in the tooltip
  ("Places your subject in a deserted transitional interior"). The badge is
  absolutely positioned over the thumbnail, not added as a tile row,
  because tile height is fixed by `grid-auto-rows` and a new row silently
  clips the label — see "Frontend rules that are not optional".
- **`scripts/build_previews.py`** already had to know which styles are
  places, so that a preview renders the place rather than the category's
  stock person. `tests/test_scene.py` binds the two lists together.

Two deliberate limits. `scene` is **not** used for object and container
styles: `object_artifact` is a whole category meaning "the subject is
rendered inside the thing", and the gallery already shows category chips,
so a second signal would add surface area and no information. And a test
asserts fewer than a quarter of styles declare one — if `scene` becomes
common, the badge has stopped carrying meaning.

Generalise rather than over-specify. Liminal Space originally named
patterned corridor carpet and drop ceiling tiles, which pinned it to the
office-hallway variant and drew that carpet even when an empty pool was
wanted. It now names the class of place and lets the rendering signature
carry the rest.

**Known edge, deliberately not solved.** Nothing stops two scene styles
being combined — a Blend of Liminal Space and Vanitas asks for a corridor
and a tabletop at once, and Sheet can resolve several scene styles in one
list. `blocks` handles the equivalent conflict on modifier axes, but there
is no scene-versus-scene equivalent and none is planned. Adding one would
put real complexity into Blend and Sheet to prevent a combination nobody
has yet reported wanting to avoid. Revisit if it is actually reported.

## Modifiers must not add an entity

The scene rule above catches *places*. It walked straight past the defect
that prompted 0.12.0, because a wig is not a place.

**Eleven of the twenty `era` modifiers enumerated garments, furniture and
light fixtures as free-standing nouns.** `baroque_17c` listed wigs, collars,
sleeves, silks, lace, oak furniture and drapery. `georgian_18c` listed
powdered wigs, frock coats, panniered gowns, fans, shoes and mahogany.
`victorian` listed gaslight, dark wood, brass fixtures, etched glass,
velvet drapes and oil-lamp ambiance. Two `mood` modifiers had it too:
`heroic` asserted a figure held dead centre with wind lifting fabric and
hair, and `lonely` asserted a single figure alone in the frame.

On Randomize, that axis is applied to whatever the user asked for. A text
encoder cannot render a wig without a head or a frock coat without
shoulders, so it invents them: mannequins wearing wigs, gaslit parlours
around a subject that was never in a parlour, a small human figure
standing on a mountain the user asked to be alone.

### The rule

**Name the light's behaviour, never its fixture** — and more generally,
**convert every entity noun into an attribute of whatever is already in
frame.**

There are two different things hiding under "light". A *fixture* —
candlelight, gaslight, an oil lamp, an exposed filament bulb — can be
instantiated as an object in the picture. A light's *behaviour* cannot:
colour temperature, direction, softness, falloff rate, contrast ratio and
ambient fill are properties of the rendering, and there is no object for
the model to draw. The same split holds for surface, ornament, palette and
process.

```
victorian, BEFORE
  "gaslight casting a warm amber glow over dark wood and brass, ornate
   filigree and etched glass catching the light, velvet drapes and
   oil-lamp ambiance softening every surface..."
      ^ gas lamp   ^ furniture      ^ glass panes  ^ curtains  ^ oil lamp

victorian, AFTER
  "carrying nineteenth-century warmth: low amber light falling off fast
   into deep shadow with barely any fill, a sepia-leaning palette of
   umber, oxblood and bottle green, every surface densely ornamented,
   hand-finished and slightly darkened with age, the detail softened as
   though by a long exposure."
      ^ light behaviour  ^ palette  ^ surface treatment  ^ process
```

Nothing in the second version can become an object. "Densely ornamented
and hand-finished" applies itself to whatever the subject already is,
which is what a modifier axis is for.

**Stated honestly: this cannot be driven to zero.** A text encoder attends
to every token, and "gilt" will gild things. The bar that is achievable
and testable is narrower, and it is the one the validator enforces: *an
era modifier must never add an entity — no body, no lamp, no chair, no
room.* Altering the colour, light, surface and finish of what is already
there is the axis doing its job.

### What enforces it

`tests/validate_data._check_entity_content` runs `_ENTITY_NOUNS` — worn
things, furniture and soft furnishing, light fixtures, appliances — over
every modifier's `tags` and `prose`, reusing the same word-boundary
matcher as the scene rule. It is **hot on modifiers** and exempts only the
`period_dress` axis, whose whole job is entities. A per-record
`_ENTITY_EXEMPT` map exists on the same written-reason contract as
`_SCENE_EXEMPT`, and is currently empty.

Over **styles** it is hot too, since 0.13.0. The escape is the declared
`depicts` field, described below — not an exemption map.

### Why a declared field beat an exemption map

0.12.0 ran this rule over styles in report mode only, printing a count and
offering no way to act on it, because a style may legitimately *be* the
object: Vinyl Record Sleeve, Furniture Design Render, Candle Making, Cameo
Brooch. The obvious fix is an exemption map in `validate_data.py`. It was
considered and rejected, for three reasons an agent-maintained repo makes
sharp:

- **Nothing checks an exemption still points at a live record.** The
  existing `_SCENE_EXEMPT` contract only asserts that a *reason* exists.
  Rename or drop the style and the entry rots into a lie that still
  silences the rule.
- **An exemption is invisible to the user.** The thing being exempted is
  precisely the thing worth telling them: this style will put an object in
  your frame. A private list turns a user-visible signal into a
  maintainer's note.
- **The gate is trivially self-granted.** Whoever writes a costume clause
  writes the exemption sentence thirty seconds later, and CI goes green.

Declaring on the record fixes all three at once. A `depicts` phrase is
checked against the live record by definition — it *is* the record — it
becomes a gallery badge, and it costs a sentence the user reads rather
than one only a maintainer sees. It is the same move `scene` already made,
for the same reason.

Two categories are exempt **by definition** rather than by declaration:
`object_artifact` and `craft_material`, in
`_ENTITY_EXEMPT_CATEGORIES`. Both already mean "the subject is rendered
*as* the thing", which is the same argument that keeps them out of the
`scene` rule, and the gallery's category chip already tells the user. A
second signal for a case that has one is surface area with no information.

### `depicts`: what the style brings with it

```python
"depicts": "an elaborate transformation costume",
```

`scene` answers *where this style puts your subject*. `depicts` answers
*what this style puts in the frame whatever your subject is*. Fashion
Photography is not relocating you, but it is definitely dressing you;
Magical Girl Transformation brings a costume to a picture of a mountain.
The two are independent and a style may carry both — Vanitas declares an
arranged tabletop still life **and** a skull, a candle and an hourglass.

Like `scene`, it is **declaration only and never reaches the prompt**.
Nothing under `stylebook_nodes/` reads it; only the validator, the
generator and the two galleries do. So declaring it on an existing style
does not move `tile_hash` and costs no render — only the styles whose text
is actually reworded go stale. (It *does* ride along in the serialized
`style_chain` JSON, because a Style node puts the whole record on the
socket, exactly as `scene` and `namesake` already do. No consumer reads
it.)

The badge sits **top-left** on a gallery tile: `scene` holds bottom-left
and `new` holds top-right, so no two can collide. `tests/test_scene.py`
holds it to the same contract as `scene` — a non-blank lower-case noun
phrase of at most twelve words, no trailing period — plus a share ceiling.
The ceiling matters more here than it does for `scene`, because `depicts`
is an escape from a *hot* rule: the cheapest way to silence that rule is
to declare the field instead of fixing the record. If the count climbs,
the badge has stopped carrying information.

The noun list is narrow and hand-verified, like `_SCENE_NOUNS`, and the
absences are as deliberate as the entries: `drape` is the fall of cloth
(Cloth Simulation and Knitwear both use it correctly), `uniform` matches
inside "uniform-weight", and `panel` and `screen` collide with the picture
plane, screen printing and screentone.

`room` **is** in `_SCENE_NOUNS`, including the idioms. That is on purpose:
a text encoder has no idiom, so "leaving room for a title" is a request
for a room. All four styles it hit were reworded rather than exempted.
`interior` is **not** in the list, because half its occurrences are the
geometric sense — "unshaded interiors", "washed interior shading", "every
interior a single flat tone" — which is correct rendering vocabulary.

## `era` and `period_dress` are one axis split in two

Deleting the wardrobe would have been a real capability loss: Identity
Forge owns the subject, but it does identity and framing, not period
costume, so nothing else in the toolchain covers it. So the text moved
rather than going away. Every garment, hairpiece, fabric, fastening and
accessory cut from `era` in 0.12.0 lives on its `period_dress` partner,
one per era, in the same chronological order.

`era` tilts **how the image is rendered** and names no object, so it is
safe to randomize on any subject. `period_dress` **puts period wardrobe
and its fittings in the picture**, which is exactly what the entity rule
forbids everywhere else — hence `_ENTITY_EXEMPT_AXES`.

Keeping both on one axis was considered and rejected. `axis` has no
`Random` option and `stable_choice` picks *within* the chosen axis, so
Randomize on `era` can never reach a dress record. Shipping "Victorian"
and "Victorian Dress" side by side on one axis would hand Randomize a coin
flip and reproduce the original complaint exactly.

Adding the axis broke nothing, and each path was checked rather than
assumed: no preview tile was affected at the time (`period_dress`
is not one of the three axes that gained tiles in 0.14.0); the `axis` widget is a combo
built from `axis_options()`, so a new option is additive and a saved
`"era"` still resolves; no widget is added, removed or reordered, so no
saved `widgets_values` moves; `stable_choice` hashes per candidate, so no
existing seed moves; and only `color_grade` is ever named in a style's
`blocks`, so no style needed a `blocks` change.

Four places had to learn the new axis and none of them is the gallery,
which reads `MODIFIER_AXES` out of generated data and title-cases the id:
`data/modifiers.AXES`, `tests/validate_data._EXPECTED_AXES`,
`data/user_data._AXES` (a deliberate mirror, kept honest by
`tests/test_user_data.BlocksAxisTests`), and the `axis_labels` map in
`scripts/build_reference_pages.py`, which indexes rather than `.get()`s
and so raises rather than quietly omitting.

## Styles named after a person

Some styles carry somebody's name — `Akira Kurosawa Rain`,
`Hitchcockian`, `Fellini-Esque`, `One Piece (Oda)`. Each one is a promise
the Artist picker has to keep. Finding a style named for Kurosawa in the
gallery and then getting nothing back for "Kurosawa" in the artist search
is the pack contradicting itself, and a batch of these had no artist
record at all until this check was written.

The declaration is the optional **`namesake`** field on the style record
itself, naming the artist label that must exist. It used to be a map
inside `tests/validate_data.py`, where a maintainer adding a style never
saw it; as data it sits beside the prose it belongs to, and it earns its
keep three ways rather than one:

1. `_check_person_styles` fails if the named artist has no record.
2. The picker tooltip and the public gallery both say "Named for ...", so
   the connection is visible before the render instead of only to whoever
   thinks to search the Artist reference for the same name.
3. `_check_undeclared_namesakes` closes the gap the old map could not.

That third one is the interesting half. The old map caught a **broken**
promise — a declared namesake with no artist record — but never a
**missing** one: a new person-named style simply had to remember to add
its line, and nothing noticed when it did not. The detector now flags any
style whose label shares a name-length word with a shipped artist's label
and declares no `namesake`; the maintainer either declares it or records
why it is a coincidence in `_NAMESAKE_EXEMPT`, with a written reason, the
same contract `_SCENE_EXEMPT` uses.

"Name-length" is five characters, and that threshold is load-bearing:
four admits "Ross", "Wood", "Lee" and "Ray", each of which collides with
a style word ("Wood Engraving", "Ray Traced Render") while naming nobody.
Parenthetical qualifiers are stripped from artist labels first, or
"Moebius (Comics)" would flag every style with "Comics" in its name.
Across every style and artist the pack ships it produces exactly two
false positives, both about Clyfford Still and both exempted.
(`tests/validate_data.py` reports the true totals; a number written
here would go stale silently.)

The hole that remains, stated plainly: an adjectival label — "Sirkian
Melodrama", "Hitchcockian" — shares no whole word with "Douglas Sirk" or
"Alfred Hitchcock", so only the author can declare those. What the
detector does catch is the case that actually recurs, a style named for
somebody the pack already ships. Styles named only for a work, a studio
or a movement (Cowboy Bebop, Evangelion, Studio Ghibli, Superflat) carry
no `namesake` by design: no person is named on the tile, so nothing is
promised.

## Adding a style

1. Add the record to the right module under `data/styles/`. Required
   fields: `id` (matching the key), `label`, `category`, `aliases`,
   `tags`, `prose`, `negative`, `preview`, `blocks`. Optional: `scene`,
   only if the style decides where the subject is — see above.
2. Write `tags` as concrete visual noun phrases. A list of mood adjectives
   ("sudden, jarring, explosive") gives a model nothing to render.
3. Write `negative` as what this style is *not*. It is used both at render
   time and in the preview build.
4. Set `blocks` when the style already fixes an axis. A cyanotype fixes
   `color_grade`, so a Sepia modifier on top would fight it. Every style
   that is monochrome or single-hue by definition currently does this.
5. If the label names a person, add the artist record and set
   `namesake` on the style — see above.
6. Run `python scripts/stamp_versions.py --stamp` so the entry knows which
   release it arrived in.
7. Run the gate below, then `--build` the preview.

## Local gate

Run all of these before committing:

```
python -m ruff check .
python tests/validate_data.py
python -m unittest discover -s tests -t . -v
python scripts/stamp_versions.py --check
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
