# Stylebook — ComfyUI style-injection node pack

Tired of typing style keywords from memory? **Stylebook** gives you a
deep, filterable taxonomy of visual styles you can pick, randomize, cycle,
or batch into a style sheet — all inside ComfyUI.

Four chainable nodes:
- **Style** — the exclusive medium axis: pick from 12 categories
- **Artist** — stack multiple artists, each with a hand-written descriptor
- **Modifier** — tilt one axis: lighting, colour grade, era, finish, or mood
- **Blend** — mix two styles at a ratio from 0.0 to 1.0

Zero dependencies. Works offline. Model-agnostic text output.

## Install

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EnragedAntelope/comfyui-stylebook.git
```

Restart ComfyUI. Find the nodes under `conditioning/stylebook`.

## Quick start

1. Add **Stylebook Style** → `conditioning/stylebook`
2. Pick a style from the dropdown, or set mode to `Random`
3. Add **Stylebook Modifier** → set axis to `lighting`, pick `Golden Hour`
4. Chain into **CLIPTextEncode**
5. Connect to your sampler

The `prompt` output contains your style text ready to encode.

## Nodes

| Node | What it does |
|---|---|
| **Style** | Pick a style. `Random` / `Cycle` / `Sheet` modes draw from the category + tag filter pool. |
| **Artist** | Layer one artist. Chain multiple to stack (Rembrandt × Picasso). |
| **Modifier** | One per axis: lighting, color grade, era, finish, mood. |
| **Blend** | Ratio-controlled blend of two styles. |

## Filtering & cycling

Set `mode` to `Random`, pick a `category`, and optionally type a
`tag_filter` like `bw, high-contrast`. Every run with the same seed
gives the same result.

## Style sheet

Set `mode` to `Sheet`, choose a count — Stylebook emits N different
styles for a contact sheet of one subject across many styles.

## Extending

Drop a `user_styles.json` in the pack root (copy `user_styles.example.json`
to start). Your styles survive `git pull`. See the example file for the
record format.

## YMMV

Previews show one model's interpretation on one subject at one seed.
Styles are written to be portable, but no style reads identically on
every model. Treat previews as a guide, not a guarantee.

## License

MIT
