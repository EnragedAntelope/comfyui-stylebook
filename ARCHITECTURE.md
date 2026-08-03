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
  user_data.py            Merges an optional user_styles.json over the built-ins.
stylebook_nodes/
  stylebook_core.py       The engine. Pure functions, no ComfyUI import.
  schema_options.py       Dropdown option lists, sentinels and defaults.
  stylebook_style.py      Style node   - exclusive medium axis.
  stylebook_artist.py     Artist node  - additive, chainable.
  stylebook_modifier.py   Modifier node - one per axis.
  stylebook_blend.py      Blend node   - two styles at a ratio.
  stylebook_sheet.py      Sheet node   - one subject, many styles, as a list.
js/
  stylebook_data.js       Generated. Never edit by hand.
  stylebook_gallery.js    Hand-written frontend. The generator never touches it.
  stylebook_recreate.js   A working "Fix node (recreate)". See below.
  stylebook_gallery.css   Themed against ComfyUI's CSS custom properties.
  previews/               Sprite atlases plus index.json, served statically.
previews/
  src/                    Full-size renders (gitignored, rebuildable).
  manifest.json           Content hash per tile. Drives incremental rebuilds.
scripts/                  Build and validation tooling. Not shipped to the registry.
tests/                    unittest suite plus the data-layer validator.
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
python -m unittest discover -s tests -v
python scripts/generate_js_data.py --check
python scripts/build_previews.py --check
```

Or `python scripts/pre_commit_check.py`, which runs the lot.

The data validator is not decoration. It fails the build on duplicate
labels, ids that disagree with their key, records claiming a reserved
sentinel word, thin descriptions, and double-encoded text. Each of those
rules exists because that exact defect shipped once.
