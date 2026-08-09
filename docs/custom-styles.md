# Custom styles, artists and modifiers

Stylebook is happiest as a shared pack: if you have a style, artist or
modifier worth adding, **please open an issue or a pull request** so
everyone gets it. `user_styles.json` exists for what a PR doesn't fit —
something private, something you are still tuning, or something you just
want to try tonight without waiting on a release.

It is parsed as plain JSON. No code is executed, and nothing in it can run
arbitrary Python.

## Where the file goes

By default: `user_styles.json` in the pack root (next to `README.md`), which
`.gitignore` already excludes so a `git pull` never touches it.

To keep it outside the pack entirely — so a ComfyUI Manager reinstall or a
`git clean` can't take it with it — set the environment variable
`STYLEBOOK_USER_STYLES` to a full path before ComfyUI starts:

```bash
export STYLEBOOK_USER_STYLES=/home/you/comfyui-user-data/stylebook.json
```

On Windows (PowerShell), set it as a user environment variable or in
whatever launcher script starts ComfyUI:

```powershell
$env:STYLEBOOK_USER_STYLES = "C:\Users\you\comfyui-user-data\stylebook.json"
```

Copy [`user_styles.example.json`](../user_styles.example.json) to start —
it has one worked example of each section.

## What happens on load

**ComfyUI caches the Python data layer at startup.** After editing the
file, restart ComfyUI — a running instance won't see the change, and a
prompt naming a value that exists in the file but not in the already-loaded
process will fail validation with a confusing "not in list" error that has
nothing to do with your JSON.

Once loaded, each entry is validated independently. A bad entry is skipped
with a reason printed to the ComfyUI console (never silently, and never by
crashing the rest of the pack); every other entry in the file still loads.
A valid entry whose id matches a built-in **overrides** that built-in.

Console output looks like:

```
[Stylebook] Ignoring style 'my_style' in user_styles.json: category 'my_category' is not one the pack ships (known: anime_manga, art_movements, ...)
[Stylebook] Loaded 2 custom style(s) from user_styles.json. Rejected 1 (see above).
```

Custom entries also appear in the gallery under a **Yours** tab (alongside
their real category, exactly like a built-in) once you reopen a picker
after the restart. A custom style has no preview image, so its tile shows
its initials instead of a rendered thumbnail.

## Why an entry gets rejected

| Reason | What it means |
|---|---|
| `missing required field '…'` | Every style needs `label` and `category`; every artist needs `label`; every modifier needs `label` and `axis`. |
| `'label' must be non-empty text` | `label` is missing, blank, or not a string. |
| `label '…' is reserved` | `None`, `Off` and `Random` are control words the pack itself uses in its dropdowns — no entry may claim one. |
| `'…' must be text, not …` | A field that must be a string (see the tables below) was a number, list, or other type. |
| `'…' must be a list of text…` | `aliases` or `blocks` was not a JSON array, or contained something other than a string. |
| `category '…' is not one the pack ships` / `axis '…' is not one the pack ships` | See the valid lists below. An unrecognised category doesn't crash anything, but the entry never surfaces under Random/Cycle-by-category and never gets its own gallery tab — it becomes hard to find, which is worth avoiding. |
| `label '…' duplicates an existing style/artist/modifier` | Another entry — built-in, or an earlier entry in the same file — already claims that label (case-insensitive). Only the first one wins; rename the later one. |

## Styles

```json
{
  "styles": {
    "my_custom_style": {
      "label": "My Custom Style",
      "category": "illustration",
      "aliases": ["custom"],
      "tags": "your custom, comma separated, style keywords",
      "prose": "A custom style description in prose form. At least 15 words describing the rendering across multiple primitive facets: colour, line, texture, lighting, and composition.",
      "negative": "",
      "preview": "illustration#00",
      "blocks": []
    }
  }
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `label` | yes | string | Shown in every dropdown and the gallery. Must be unique. |
| `category` | yes | string | One of: `photography`, `illustration`, `comics`, `film_cinema`, `painting`, `art_movements`, `anime_manga`, `three_d_digital`, `print_graphic`, `object_artifact`, `craft_material`, `collage_mixed`. |
| `tags` | no | string | Comma-separated keyword form. Used when a node's `format` is `tags`. |
| `prose` | no | string | Sentence form. Used when `format` is `prose`. Ship at least one of `tags`/`prose` or the style renders as nothing. |
| `negative` | no | string | What the style excludes, wired into a node's `negative` output. |
| `aliases` | no | list of strings | Extra search terms; do not need to be unique. |
| `blocks` | no | list of strings | Modifier axes this style already fixes, so a Modifier node on that axis is dropped with a warning instead of fighting the style. Axis names: see the Modifiers table below. |
| `scene` | no | string | Only for a style that decides *where* the subject is, not just how it is drawn. A short lower-case noun phrase — `"a deserted transitional interior"` — shown as a **scene** badge on the gallery tile and spelled out in its tooltip. Leave it out for the great majority of styles: one that merely changes the rendering has no scene, and a badge on everything tells the user nothing. |
| `preview` | no | string | Cosmetic only; the pack does not render a preview image for a custom style regardless of this value. |
| `id` (JSON key) | — | string | The key in the `"styles"` object *is* the id; don't also write an `"id"` field inside the record — it's set automatically from the key (and corrected if it disagrees), so there's nothing to keep in sync. Note that a saved workflow's Pick dropdown actually stores the *label*, not the id — so renaming `label` later still means re-picking the style in any workflow that already used it, the same as it would for a built-in. |

## Artists

```json
{
  "artists": {
    "my_custom_artist": {
      "label": "My Custom Artist",
      "category": "photography",
      "aliases": ["nickname"],
      "descriptor": "a one-line description of what their work actually looks like."
    }
  }
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `label` | yes | string | Must be unique. |
| `category` | no | string | If given, one of: `photography`, `illustration`, `comics`, `film`, `digital`, `fine-art`. Controls which tab of the artist reference it appears under. |
| `descriptor` | no | string | What the work looks like, in words — the whole reason to include one. It's what carries the look on a model that has never heard the name; set `artist_detail` to `Descriptor only` to use it that way. |
| `aliases` | no | list of strings | Extra search terms. |

## Modifiers

```json
{
  "modifiers": {
    "my_custom_modifier": {
      "label": "My Custom Modifier",
      "axis": "lighting",
      "aliases": ["nickname"],
      "tags": "your custom, keyword form",
      "prose": "A sentence describing the tilt this modifier applies.",
      "negative": ""
    }
  }
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `label` | yes | string | Must be unique. |
| `axis` | yes | string | Exactly one of: `lighting`, `color_grade`, `era`, `finish`, `mood`. A Modifier node holds one modifier per axis; a second on the same axis replaces the first. |
| `tags` / `prose` | no | string | Same contract as styles: ship at least one. |
| `negative` | no | string | Same contract as styles. |
| `aliases` | no | list of strings | Extra search terms. |

## Why not a save-to-file button?

It was asked for — a button that writes the current node's selection
straight into `user_styles.json` from the UI, the way some node packs let
you save a preset. Two things argue against it here:

- A frontend writing files inside `custom_nodes` is a real security and
  update-safety surface (write access from the browser into a directory
  that also gets Manager-managed git pulls), for a feature this pack has a
  much smaller version of already.
- A Stylebook selection is one dropdown value. The right-click **Pin this
  pick** menu item (see the README) already covers "I found something good
  on Random and want to keep it" in one click, with no new file format and
  no filesystem write from the browser.

If you outgrow the JSON file, a PR is genuinely the better path — you get
the gallery tile, the preview image, and everyone else gets it too.
