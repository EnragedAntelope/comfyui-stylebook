"""Modifier records - per-axis style adjustments.

A modifier tilts the rendering without defining the primary style.
Five axes: lighting, color_grade, era, finish, mood.

Every modifier carries both ``tags`` and ``prose`` so it works in
either output format.
"""

from __future__ import annotations

#: Modifier axes - the buckets modifiers are grouped into.
AXES: tuple[str, ...] = ("lighting", "color_grade", "era", "finish", "mood")

#: Sentinels for the modifier combo.
_OFF = "Off"
_RANDOM = "Random"

#: All modifier records keyed by id.
MODIFIERS: dict[str, dict] = {
    # --- lighting ---
    "golden_hour": {
        "label": "Golden Hour",
        "axis": "lighting",
        "aliases": ["sunset light", "warm sidelight"],
        "tags": "golden hour, warm directional light from low sun, long shadows, amber-orange highlights, rim-lit edges, softened contrast",
        "prose": "lit by golden-hour sunlight falling low from the side - long crisp shadows, rim-lit edges glowing amber-orange against softened warm highlights, the whole scene wrapped in the last deep light of the afternoon.",
        "negative": "cool daylight, flat overhead sun, harsh noonday shadows",
    },
    "rim_lighting": {
        "label": "Rim Lighting",
        "axis": "lighting",
        "aliases": ["backlight", "edge light"],
        "tags": "rim lighting, strong backlight creating bright edge contour, dark foreground, silhouette glow, hazy light wrap",
        "prose": "rim-lit: a strong backlight traces every contour in a bright white edge against a dark ground, the subject solid and readable through outline alone, with a faint hazy bloom where the light wraps around the form.",
        "negative": "flat frontal lighting, fill flash, even ambient light",
    },
    "neon_noir": {
        "label": "Neon Noir",
        "axis": "lighting",
        "aliases": ["cyberpunk lighting", "neon street"],
        "tags": "neon lighting, rain-slick streets, coloured gels, magenta-and-cyan split tones, deep shadows, volumetric fog catching coloured light",
        "prose": "bathed in neon: coloured gels split the scene into magenta and cyan, volumetric fog catches every beam, rain-slick surfaces mirror the glow in sharp reflections, and deep shadows swallow everything the light doesn't touch.",
        "negative": "natural sunlight, warm tungsten, flat office lighting",
    },
    "chiaroscuro": {
        "label": "Chiaroscuro",
        "axis": "lighting",
        "aliases": ["dramatic light", "Rembrandt lighting"],
        "tags": "chiaroscuro, single strong keylight, deep near-black shadow, high contrast, sculptural light, dark ground",
        "prose": "lit with chiaroscuro: a single strong keylight carves the subject out of near-black shadow, the form reading through extreme contrast with large areas falling away into the dark ground.",
        "negative": "flat lighting, fill light, high-key, overcast ambient",
    },

    # --- color_grade ---
    "black_and_white": {
        "label": "Black & White",
        "axis": "color_grade",
        "aliases": ["bw", "monochrome", "grayscale"],
        "tags": "black and white, monochrome, grayscale, no colour, silver tones, high-key whites to deep blacks",
        "prose": "rendered in black and white: the full tonal range from bright high-key whites to deep blacks, every surface read through luminance alone with no colour information anywhere in the image.",
        "negative": "colour, saturated, vivid hues, multicoloured",
    },
    "sepia": {
        "label": "Sepia",
        "axis": "color_grade",
        "aliases": ["vintage photo", "brown tone"],
        "tags": "sepia toning, warm brown monochrome, faded photograph look, cream highlights, chocolate shadows",
        "prose": "toned in sepia: warm browns replace the grayscale, cream-coloured highlights bleeding into chocolate shadows, the whole image carrying the faded warmth of an old photograph.",
        "negative": "full colour, cool blue tones, digital sharpness",
    },
    "duotone": {
        "label": "Duotone",
        "axis": "color_grade",
        "aliases": ["two-tone", "split tone"],
        "tags": "duotone, two-colour palette, shadows tinted one hue highlights another, graphic posterised colour, stark colour separation",
        "prose": "graded as a duotone: shadows tinted one hue, highlights another, the midtones a stark graphic transition between the two, posterised into flat colour bands.",
        "negative": "natural colour, full spectrum, subtle gradients, photorealistic colour",
    },

    # --- era ---
    "_1970s": {
        "label": "1970s",
        "axis": "era",
        "aliases": ["70s", "seventies"],
        "tags": "1970s aesthetic, warm orange-brown palette, film grain, soft focus, wood-panelled interiors, earth tones, avocado green, harvest gold",
        "prose": "steeped in 1970s aesthetic: warm orange-brown earth tones, soft film grain, the slight soft-focus bloom of the era's lenses, avocado green and harvest gold accents grounding the image in the decade.",
        "negative": "modern clean lines, digital sharpness, cool LED lighting, minimalist",
    },
    "_1980s": {
        "label": "1980s",
        "axis": "era",
        "aliases": ["80s", "eighties", "retrowave"],
        "tags": "1980s aesthetic, neon colours, chrome and glass, geometric patterns, synthwave palette, high-contrast lighting, bold graphic design",
        "prose": "pure 1980s: neon pinks and electric blues against chrome and black glass, bold geometric grids, high-contrast lighting with coloured gels, the graphic confidence of the decade in every surface.",
        "negative": "beige, wood grain, soft focus, film grain, natural tones",
    },
    "victorian": {
        "label": "Victorian",
        "axis": "era",
        "aliases": ["19th century", "gaslight"],
        "tags": "Victorian era, gaslight glow, sepia-warm tones, ornate filigree, dark wood, brass fixtures, etched glass, velvet drapes, oil lamp ambiance",
        "prose": "dressed in Victorian sensibility: gaslight casting a warm amber glow over dark wood and brass, ornate filigree and etched glass catching the light, velvet drapes and oil-lamp ambiance softening every surface into the deep warmth of the 19th century.",
        "negative": "modern materials, neon, plastic, LED, minimalist, digital",
    },

    # --- finish ---
    "film_grain": {
        "label": "Film Grain",
        "axis": "finish",
        "aliases": ["grainy", "35mm", "analog"],
        "tags": "heavy film grain, analog texture, 35mm film look, subtle colour shifts in grain, celluloid warmth, slight softness at edges",
        "prose": "finished with heavy 35mm film grain: a visible particulate texture across the whole image, subtle colour shifts dancing in the grain, the slight softness and warmth of celluloid at the edges.",
        "negative": "digital clean, noise-free, perfectly smooth gradients, CGI sharpness",
    },
    "vignette": {
        "label": "Vignette",
        "axis": "finish",
        "aliases": ["darkened edges", "spotlight falloff"],
        "tags": "vignette, darkened edges fading to black, spotlight concentration on centre, gradual luminance falloff, tunnel effect",
        "prose": "framed by a strong vignette: the edges fall off into deep black, drawing the eye to the centre in a gradual luminance tunnel - the subject spotlit by the frame itself.",
        "negative": "even edge-to-edge lighting, full-frame brightness, no focus point",
    },
    "bloom_glow": {
        "label": "Bloom / Glow",
        "axis": "finish",
        "aliases": ["soft glow", "haze", "diffusion"],
        "tags": "bloom, soft diffused glow around bright areas, haze filter, light bleeding across edges, dreamy soft-focus, lifted blacks",
        "prose": "finished with a soft bloom: bright areas spill a diffused glow across adjacent edges, highlights bleeding into the shadows with a dreamy haze, blacks lifted into a gentle grey so nothing bites into pure darkness.",
        "negative": "sharp contrast, hard edges, crisp definition, pure blacks",
    },

    # --- mood ---
    "melancholic": {
        "label": "Melancholic",
        "axis": "mood",
        "aliases": ["somber", "wistful", "blue mood"],
        "tags": "melancholic mood, desaturated cool tones, overcast light, downward gaze, quiet stillness, blue-grey palette",
        "prose": "the mood is melancholic: desaturated cool tones under an overcast light, a quiet stillness in the composition, the whole scene holding its breath in blue-grey silence.",
        "negative": "joyful, vibrant, energetic, bright, celebratory, warm cheer",
    },
    "sinister": {
        "label": "Sinister",
        "axis": "mood",
        "aliases": ["ominous", "unsettling", "dark"],
        "tags": "sinister mood, low-key lighting, unsettling atmosphere, deep shadows swallowing detail, cold colour temperature, slight dutch angle, something-wrong feeling",
        "prose": "the mood is sinister: low-key lighting barely revealing forms, unsettling cold colour temperature, deep shadows swallowing detail at the edges, a slight dutch tilt making everything feel slightly wrong.",
        "negative": "cheerful, safe, bright, warm, inviting, comfortable",
    },
    "serene": {
        "label": "Serene",
        "axis": "mood",
        "aliases": ["peaceful", "calm", "tranquil"],
        "tags": "serene mood, soft diffused light, pastel palette, gentle atmosphere, balanced composition, quiet calm, still waters, clear skies",
        "prose": "the mood is serene: soft diffused light falling evenly across a pastel palette, the composition balanced and still, a gentle quiet calm that asks nothing of the viewer.",
        "negative": "chaotic, aggressive, harsh, loud, frantic, dark, oppressive",
    },
}

#: Per-axis modifier id lists - used for cycling/randomizing within an axis.
MODIFIERS_BY_AXIS: dict[str, list[str]] = {}
for _mod_id, _mod in MODIFIERS.items():
    _axis = _mod.get("axis", "")
    MODIFIERS_BY_AXIS.setdefault(_axis, []).append(_mod_id)

#: Sentinel values for the modifier node.
MODIFIER_OFF = _OFF
MODIFIER_RANDOM = _RANDOM
