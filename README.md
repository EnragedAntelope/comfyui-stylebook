# Stylebook: ComfyUI style-injection node pack

A deep, filterable taxonomy of visual styles you can pick, randomize,
cycle, or batch into a style sheet. All inside ComfyUI, all offline,
with zero dependencies.

Four chainable nodes, 12 categories, 190+ styles, 247+ artists.

## Install

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EnragedAntelope/comfyui-stylebook.git
```

Restart ComfyUI. Find the nodes under `conditioning/stylebook`.

## Quick start

1. Add **Stylebook Style** to your graph
2. Pick a style from the dropdown, or click **Open Style Gallery** to browse with previews
3. Add **Stylebook Artist** and pick an artist (chain more to stack)
4. Add **Stylebook Modifier** - choose an axis (lighting, color grade, era, finish, mood) and pick one
5. Connect the `prompt` output to a CLIPTextEncode node, then to your sampler

The `prompt` output contains ready-to-encode style text. The `style_chain` output connects between Stylebook nodes so they compose.

## Nodes

| Node | What it does |
|---|---|
| **Style** | The medium axis. `Pick` from 190+ styles across 12 categories, or use `Random` / `Cycle` / `Sheet` to draw from a filtered pool. Open the gallery to browse. |
| **Artist** | Layer one artist. Each carries a hand-written visual descriptor that works even when the model does not know the name. Chain multiple Artist nodes to stack influences. Default "Name + descriptor" works everywhere; switch to "Descriptor only" for recaption models (Flux, Z-Image, Krea). |
| **Modifier** | Tilt one rendering axis: lighting, color grade, era, finish, or mood. One modifier per axis - adding a second on the same axis replaces the first. Defaults to Off on every axis. |
| **Blend** | Mix two styles at a ratio from 0.0 (pure style A) to 1.0 (pure style B). Connect a second style chain into the `style B` input. |

## Best practices

Chain order matters. The recommended sequence is:

1. **Style** first — defines the medium and carries your subject prompt
2. **Artist** second — adds individual influence on top of the style
3. **Modifier** last — tilts the rendering axis (lighting, era, etc.)
4. Connect the final `prompt` output to CLIPTextEncode

Why this order: Style is exclusive (a second Style replaces the first).
Artists stack (append). Modifiers are per-axis. Putting Style first
ensures your subject prompt flows through all downstream nodes.

Prose format uses a space between style and prompt; tags format uses
a comma. Pick `tags` for keyword-heavy chains or `prose` for natural
language output.

## Filtering, cycling, and style sheets
Set `mode` to `Random`, pick a `category`, and optionally type a `tag_filter` like `bw, high-contrast`. Every run with the same seed gives the same result.

`Cycle` advances through the filtered pool deterministically - index 0 is the first match, index 1 is the second, wrapping around.

`Sheet` emits N different styles at once for a contact sheet of one subject across many looks.

## Using Stylebook with Identity Forge

Stylebook describes the *rendering*; Identity Forge describes the *subject*. They compose naturally, but a few axes overlap:

| Identity Forge field | Stylebook axis | Guidance |
|---|---|---|
| `lighting` | lighting modifier | Direct conflict. Set one to None/Off. |
| `mood` | mood modifier | Direct conflict. Set one to None/Off. |
| `shot_type` | Photography styles | Soft conflict. Styles that imply framing (macro, aerial) can fight an explicit shot_type. |
| `location` / `setting` | Object & Artifact | Artifact styles relocate the subject into a container. Expected, not a bug. |

Safe default: every Stylebook modifier axis starts at Off, so a fresh chain has zero conflicts.

## Extending

Drop a `user_styles.json` in the pack root (copy `user_styles.example.json` to start). Your styles, artists, and modifiers survive `git pull`. See the example file for the record format.

## Categories

12 style categories: Photography, Film & Cinema, Illustration, Painting & Traditional Media, Art Movements, Anime & Manga, Comics & Cartoons, 3D & Digital, Print & Graphic, Craft & Material, Object & Artifact, Collage & Mixed Media.

## YMMV

Previews show one model's interpretation on one subject at one seed. Styles are written to be portable, but no style reads identically on every model. Treat previews as a guide, not a guarantee.

## License

MIT
