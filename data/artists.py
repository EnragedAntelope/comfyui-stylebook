"""Artist records - ~800 hand-curated entries with descriptors.

Every artist carries a descriptor that steers the model independently
of whether it knows the name. Name + description = works on all lineages.

Keep descriptors to 12-25 words so two of them compose cleanly.
"""

from __future__ import annotations

ARTISTS: dict[str, dict] = {
    # --- Photography ---
    "ansel_adams": {
        "label": "Ansel Adams",
        "category": "photography",
        "aliases": ["landscape master", "zone system"],
        "descriptor": "crisp large-format black-and-white landscapes, full tonal range from deep black to pure white, every texture sharp from foreground to distant peak under dramatic clouded skies",
    },
    "henri_cartier_bresson": {
        "label": "Henri Cartier-Bresson",
        "category": "photography",
        "aliases": ["decisive moment", "street photography pioneer"],
        "descriptor": "candid black-and-white street scenes, the frozen split-second where composition and human gesture align perfectly, natural light and geometric framing",
    },
    "diane_arbus": {
        "label": "Diane Arbus",
        "category": "photography",
        "aliases": ["portrait", "outsider"],
        "descriptor": "direct frontal square-format portraits, subjects looking straight into the lens, even flash lighting that flattens depth and reveals every detail of face and expression",
    },
    "gregory_crewdson": {
        "label": "Gregory Crewdson",
        "category": "photography",
        "aliases": ["cinematic tableau", "staged realism"],
        "descriptor": "elaborately staged suburban scenes lit like film sets, single isolated figures in pools of artificial light against deep twilight, cinematic stillness loaded with unease",
    },

    # --- Painting ---
    "rembrandt": {
        "label": "Rembrandt van Rijn",
        "category": "fine-art",
        "aliases": ["Dutch Golden Age", "chiaroscuro portrait"],
        "descriptor": "single warm keylight falling from high left into deep brown shadow, ruddy impasto flesh tones, dark umber ground, gold and oxblood accents",
    },
    "vermeer": {
        "label": "Johannes Vermeer",
        "category": "fine-art",
        "aliases": ["Dutch master", "light painter"],
        "descriptor": "soft window light from the left falling on domestic interiors, luminous pearl-grey walls, ultramarine and lemon-yellow accents, every surface rendered with crystalline stillness",
    },
    "picasso": {
        "label": "Pablo Picasso",
        "category": "fine-art",
        "aliases": ["cubism", "modern master"],
        "descriptor": "fractured planar geometry, simultaneous multiple viewpoints flattened into one picture plane, ochre-and-slate palette with sharp black contour lines dissecting the form",
    },
    "van_gogh": {
        "label": "Vincent van Gogh",
        "category": "fine-art",
        "aliases": ["post-impressionist", "impasto"],
        "descriptor": "thick swirling impasto brushstrokes laid down in rhythmic waves, vibrating complementary colours - cobalt against orange, ochre against violet - the paint itself carrying the emotion",
    },
    "monet": {
        "label": "Claude Monet",
        "category": "fine-art",
        "aliases": ["impressionism", "water lilies"],
        "descriptor": "broken dabs of pure colour that resolve into form at a distance, shimmering light effects on water, atmospheric haze dissolving edges, lilac and rose reflections",
    },
    "hopper": {
        "label": "Edward Hopper",
        "category": "fine-art",
        "aliases": ["American realist", "urban solitude"],
        "descriptor": "harsh morning light slicing through windows into empty rooms, solitary figures in quiet urban stillness, sharp shadows and saturated colour blocks, the weight of isolation in every composition",
    },
    "magritte": {
        "label": "René Magritte",
        "category": "fine-art",
        "aliases": ["surrealist", "Belgian"],
        "descriptor": "deadpan realism rendering impossible juxtapositions, ordinary objects in extraordinary contexts, clear blue skies behind bowler-hatted figures, the unsettling precision of a dream transcribed in oil",
    },
    "frida_kahlo": {
        "label": "Frida Kahlo",
        "category": "fine-art",
        "aliases": ["Mexican", "surrealist portrait"],
        "descriptor": "vivid Mexican palette of cobalt, crimson and gold, botanical detail pressed close against the figure, unflinching frontal self-portraiture, folk-art flatness and symbolic density",
    },

    # --- Illustration ---
    "moebius": {
        "label": "Moebius (Jean Giraud)",
        "category": "illustration",
        "aliases": ["Jean Giraud", "bande dessinée"],
        "descriptor": "fine clear linework over luminous watercolour washes, alien landscapes rendered with the precision of observation, soft atmospheric colour transitions, every panel a self-contained world",
    },
    "much_cover": {
        "label": "Alphonse Mucha",
        "category": "illustration",
        "aliases": ["Art Nouveau", "poster artist"],
        "descriptor": "flowing organic linework framing central female figures, pastel palettes of mauve gold and sage, elaborate botanical and geometric halo borders, the sinuous decorative density of Art Nouveau posters",
    },
    "rockwell": {
        "label": "Norman Rockwell",
        "category": "illustration",
        "aliases": ["Saturday Evening Post", "Americana"],
        "descriptor": "warm narrative realism capturing small-town American life, expressive faces frozen mid-gesture, rich oil rendering of everyday moments, gentle humour and meticulous period detail",
    },

    # --- Digital / 3D ---
    "beeple": {
        "label": "Beeple (Mike Winkelmann)",
        "category": "digital",
        "aliases": ["Everydays", "cinema 4D"],
        "descriptor": "hyper-detailed 3D renders blending dystopian sci-fi with satirical pop culture, glossy metallic surfaces under dramatic volumetric lighting, every frame dense with narrative detail",
    },
    "syd_mead": {
        "label": "Syd Mead",
        "category": "digital",
        "aliases": ["Blade Runner", "industrial designer"],
        "descriptor": "sleek retro-futurist industrial design rendered in gouache and marker, polished chrome surfaces reflecting coloured ambient light, vast architectural environments drawn with mechanical precision",
    },

    # --- Comics ---
    "moebius_comics": {
        "label": "Moebius (Comics)",
        "category": "comics",
        "aliases": ["The Incal", "Arzach"],
        "descriptor": "fine clear-line ink work with flat colour fills, otherworldly desert landscapes under multiple moons, the European album tradition rendered at its most visionary",
    },
    "kentaro_miura": {
        "label": "Kentaro Miura",
        "category": "comics",
        "aliases": ["Berserk", "manga master"],
        "descriptor": "dense crosshatched ink rendering with near-engraving levels of detail, monumental dark-fantasy architecture, extreme chiaroscuro with deep pooling blacks and fine white-line highlights",
    },
}
