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
    "robert_capa": {
        "label": "Robert Capa",
        "category": "photography",
        "aliases": ["war photography", "magnum founder"],
        "descriptor": "grainy high-contrast black-and-white war reportage shot up close under fire, motion blur and raw urgency capturing the chaos of combat at ground level",
    },
    "dorothea_lange": {
        "label": "Dorothea Lange",
        "category": "photography",
        "aliases": ["documentary", "FSA photographer"],
        "descriptor": "empathetic black-and-white documentary portraits of Depression-era poverty, dust and hardship framed with quiet dignity, available natural light and tight medium compositions",
    },
    "sebastiao_salgado": {
        "label": "Sebastiao Salgado",
        "category": "photography",
        "aliases": ["social documentary", "epic monochrome"],
        "descriptor": "epic black-and-white social documentary with dramatic chiaroscuro, monumental compositions of labour and landscape, deep tonal gradations rendering human struggle at biblical scale",
    },
    "steve_mccurry": {
        "label": "Steve McCurry",
        "category": "photography",
        "aliases": ["National Geographic", "color documentary"],
        "descriptor": "saturated Kodachrome color portraits of South Asian culture, piercing direct gazes into the lens, rich textile textures and golden-hour light across weathered faces",
    },
    "annie_leibovitz": {
        "label": "Annie Leibovitz",
        "category": "photography",
        "aliases": ["celebrity portrait", "Rolling Stone"],
        "descriptor": "theatrical large-format celebrity portraits with elaborate sets and props, subjects in dramatic poses under controlled studio light, narrative richness of a painted tableau",
    },
    "richard_avedon": {
        "label": "Richard Avedon",
        "category": "photography",
        "aliases": ["fashion portrait", "studio minimalism"],
        "descriptor": "high-contrast studio portraits against seamless white backgrounds, subjects isolated in stark even light, motion blur and sharp expression revealing psychological intensity",
    },
    "helmut_newton": {
        "label": "Helmut Newton",
        "category": "photography",
        "aliases": ["provocative fashion", "glamor noir"],
        "descriptor": "glossy high-contrast black-and-white fashion photography, powerful women in provocative poses, nighttime urban settings with hard flash and deep shadow, voyeuristic tension",
    },
    "cindy_sherman": {
        "label": "Cindy Sherman",
        "category": "photography",
        "aliases": ["conceptual self-portrait", "identity art"],
        "descriptor": "elaborate costume and prosthetic self-portraits exploring constructed female identity, harsh color lighting and saturated tones, uncanny transformation through media stereotype",
    },
    "andreas_gursky": {
        "label": "Andreas Gursky",
        "category": "photography",
        "aliases": ["large-scale color", "Dusseldorf school"],
        "descriptor": "massive digitally assembled color photographs of global systems, vast repetitive patterns of architecture and crowds, flat even light and razor detail from every distance",
    },
    "hiroshi_sugimoto": {
        "label": "Hiroshi Sugimoto",
        "category": "photography",
        "aliases": ["minimalist seascape", "long exposure"],
        "descriptor": "monochrome seascapes reduced to two bands of gray, horizon splitting misty sea from pale sky, long-exposure stillness dissolving time into pure meditative abstraction",
    },
    "william_eggleston": {
        "label": "William Eggleston",
        "category": "photography",
        "aliases": ["color pioneer", "New West"],
        "descriptor": "saturated dye-transfer color photographs of mundane American vernacular, tricycles and ceilings in vivid red and blue, democratic framing elevating the ordinary to strange beauty",
    },
    "stephen_shore": {
        "label": "Stephen Shore",
        "category": "photography",
        "aliases": ["color photography", "American surfaces"],
        "descriptor": "large-format color photographs of banal American streetscapes and interiors, deadpan composition with precise color balance, flat daylight revealing the texture of everyday places",
    },
    "joel_meyerowitz": {
        "label": "Joel Meyerowitz",
        "category": "photography",
        "aliases": ["color street", "New Color"],
        "descriptor": "vibrant color street photography in natural light, layered compositions of urban figures and reflections, saturated reds and yellows capturing the energy of city sidewalks",
    },
    "nan_goldin": {
        "label": "Nan Goldin",
        "category": "photography",
        "aliases": ["intimate diary", "raw color"],
        "descriptor": "raw flash-lit color snapshots of intimate domestic life, bruised skin and tangled sheets in tungsten warmth, unflinching proximity to vulnerability and desire in close quarters",
    },
    "martin_parr": {
        "label": "Martin Parr",
        "category": "photography",
        "aliases": ["satirical color", "British documentary"],
        "descriptor": "oversaturated ring-flash color photographs of tourist culture and British seaside, garish food and sunburned skin rendered in clinical detail, wry social observation through color",
    },
    "daido_moriyama": {
        "label": "Daido Moriyama",
        "category": "photography",
        "aliases": ["are bure boke", "provoke style"],
        "descriptor": "high-contrast grainy black-and-white street snapshots, blurred and tilted urban fragments, harsh flash against deep shadow, the rough texture of Tokyo alleyways and alienation",
    },
    "garry_winogrand": {
        "label": "Garry Winogrand",
        "category": "photography",
        "aliases": ["street photography", "snapshot aesthetic"],
        "descriptor": "energetic black-and-white street photographs shot from the hip, tilted wide-angle frames packed with overlapping figures, the chaotic visual rhythm of mid-century American sidewalks",
    },
    "lee_friedlander": {
        "label": "Lee Friedlander",
        "category": "photography",
        "aliases": ["social landscape", "self-portrait"],
        "descriptor": "complex black-and-white urban scenes with the photographer reflected in storefront glass, layered signage and shadow, the social landscape woven into intricate graphic compositions",
    },
    "saul_leiter": {
        "label": "Saul Leiter",
        "category": "photography",
        "aliases": ["color abstraction", "early color"],
        "descriptor": "painterly color photographs through rain-streaked windows and layered reflections, soft reds and yellows against snow-damp streets, quiet abstract compositions built from overlapping planes",
    },
    "vivian_maier": {
        "label": "Vivian Maier",
        "category": "photography",
        "aliases": ["street photographer", "hidden nanny"],
        "descriptor": "sharp black-and-white street photography of Chicago and New York, children and eccentrics framed with wit and geometric precision, the unposed texture of everyday urban life",
    },
    "irving_penn": {
        "label": "Irving Penn",
        "category": "photography",
        "aliases": ["studio portrait", "still life"],
        "descriptor": "minimalist studio portraits against seamless gray paper, precise corner light on fashion and still life, clean tonal gradation and quiet intensity in every composed frame",
    },
    "gordon_parks": {
        "label": "Gordon Parks",
        "category": "photography",
        "aliases": ["social documentary", "Black experience"],
        "descriptor": "black-and-white documentary of the Black American experience across decades, from Depression poverty to Civil Rights portraits, natural light carrying dignity and social urgency",
    },
    "robert_frank": {
        "label": "Robert Frank",
        "category": "photography",
        "aliases": ["the Americans", "beat photography"],
        "descriptor": "grainy off-kilter black-and-white road photographs of American isolation, tilted frames and heavy shadow, flags and jukeboxes blurred into a restless critique of postwar society",
    },
    "walker_evans": {
        "label": "Walker Evans",
        "category": "photography",
        "aliases": ["documentary style", "FSA"],
        "descriptor": "straight-on large-format black-and-white documentary of Depression-era America, weathered facades and storefront signs in even daylight, austere composition with quiet formal rigor",
    },
    "weegee": {
        "label": "Weegee (Arthur Fellig)",
        "category": "photography",
        "aliases": ["tabloid noir", "crime photography"],
        "descriptor": "harsh direct-flash black-and-white crime scenes and nightlife, stark graphic compositions of wet asphalt and neon, the tabloid underworld rendered in stark high-contrast silver gelatin",
    },
    "man_ray": {
        "label": "Man Ray",
        "category": "photography",
        "aliases": ["surrealist photography", "rayograph"],
        "descriptor": "solarized portraits and abstract photograms placing objects directly on photosensitive paper, high-contrast silver halation and dreamlike distortion, the uncanny logic of surrealism in chemical form",
    },
    "edward_weston": {
        "label": "Edward Weston",
        "category": "photography",
        "aliases": ["straight photography", "organic form"],
        "descriptor": "razor-sharp close-ups of shells peppers and nudes with deep tonal gradation, sculptural form revealed through precise focus and smooth gradations of silver gelatin light",
    },
    "august_sander": {
        "label": "August Sander",
        "category": "photography",
        "aliases": ["typological portrait", "New Objectivity"],
        "descriptor": "systematic black-and-white typological portraits of every German social class, subjects posed squarely in neutral daylight, formal rigor documenting an entire society face by face",
    },
    "berenice_abbott": {
        "label": "Berenice Abbott",
        "category": "photography",
        "aliases": ["Changing New York", "modernist document"],
        "descriptor": "crisp black-and-white architectural photographs of New York transformation, soaring Art Deco facades and demolition sites in precise geometric composition, modernist clarity of form",
    },
    "james_nachtwey": {
        "label": "James Nachtwey",
        "category": "photography",
        "aliases": ["war photographer", "conflict documentary"],
        "descriptor": "searing black-and-white and desaturated color war photography from every modern conflict, tight framing on suffering and resilience, moral urgency rendered in stark tonal contrast",
    },
    "don_mccullin": {
        "label": "Don McCullin",
        "category": "photography",
        "aliases": ["war photography", "British documentary"],
        "descriptor": "raw black-and-white war photography and British working-class documentary, harsh contrast and deep grain, unflinching proximity to violence and poverty in stark silver gelatin tones",
    },
    "mary_ellen_mark": {
        "label": "Mary Ellen Mark",
        "category": "photography",
        "aliases": ["empathetic portrait", "documentary"],
        "descriptor": "deeply empathetic black-and-white portraits of marginalized communities, intimate natural light and close framing, subjects rendered with dignity amid hardship in rich tonal gradation",
    },
    "elliott_erwitt": {
        "label": "Elliott Erwitt",
        "category": "photography",
        "aliases": ["humor street", "witness"],
        "descriptor": "wry black-and-white street photographs of absurd juxtaposition, dogs in sunglasses and ironic advertisements, precise timing and deadpan composition capturing the humor hidden in everyday life",
    },
    "rene_burri": {
        "label": "Rene Burri",
        "category": "photography",
        "aliases": ["reportage", "Magnum"],
        "descriptor": "dynamic black-and-white reportage with strong diagonal compositions, Che Guevara portrait and mid-century cultural moments, high-contrast graphic boldness in decisive framing",
    },
    "josef_koudelka": {
        "label": "Josef Koudelka",
        "category": "photography",
        "aliases": ["Prague Spring", "exile documentary"],
        "descriptor": "grainy wide-angle black-and-white of the 1968 Prague invasion and Romani communities, tilted horizons and heavy shadow, displacement and exile rendered in raw silver halide texture",
    },
    "raghu_rai": {
        "label": "Raghu Rai",
        "category": "photography",
        "aliases": ["Indian documentary", "Magnum India"],
        "descriptor": "intimate color and monochrome photographs of Indian daily life and political upheaval, saturated tones and decisive moments, spiritual and chaotic subcontinental light",
    },
    "fan_ho": {
        "label": "Fan Ho",
        "category": "photography",
        "aliases": ["Hong Kong street", "chiaroscuro street"],
        "descriptor": "high-contrast black-and-white street photographs of 1950s Hong Kong, dramatic shafts of light cutting through narrow alleyways, figures silhouetted against deep shadow in geometric frames",
    },
    "rinko_kawauchi": {
        "label": "Rinko Kawauchi",
        "category": "photography",
        "aliases": ["ephemeral color", "Japanese contemporary"],
        "descriptor": "luminous soft-focus color photographs of fleeting domestic and natural moments, overexposed highlights and pale pastel palette, the ordinary world rendered fragile and quietly transcendent",
    },
    "alec_soth": {
        "label": "Alec Soth",
        "category": "photography",
        "aliases": ["Mississippi journey", "large-format American"],
        "descriptor": "large-format color photographs of lonely figures along the Mississippi, motel rooms and river towns in muted natural light, quiet weight of American isolation",
    },
    "todd_hido": {
        "label": "Todd Hido",
        "category": "photography",
        "aliases": ["suburban noir", "atmospheric color"],
        "descriptor": "atmospheric color photographs shot through car windows at dusk, suburban houses bleeding color in rain-streaked glass, moody isolation and cinematic grain evoking film-noir memory",
    },
    "gregory_halpern": {
        "label": "Gregory Halpern",
        "category": "photography",
        "aliases": ["Magnum American", "layered color"],
        "descriptor": "layered saturated color photographs of American myth and marginal figures, dense overlapping textures and warm golden light, dreamlike juxtaposition in vivid hues",
    },
    "thomas_struth": {
        "label": "Thomas Struth",
        "category": "photography",
        "aliases": ["Dusseldorf school", "museum photography"],
        "descriptor": "precise large-format color photographs of empty museum galleries and wide-angle streets, viewers facing paintings across cool evenly lit spaces, deep perspective and neutral tonal balance",
    },
    "rineke_dijkstra": {
        "label": "Rineke Dijkstra",
        "category": "photography",
        "aliases": ["portrait", "Dutch contemporary"],
        "descriptor": "direct large-format color portraits of adolescents and new mothers against plain backgrounds, unflinching daylight and shallow depth, awkwardness and vulnerability without artifice or retouching",
    },
    "jeff_wall": {
        "label": "Jeff Wall",
        "category": "photography",
        "aliases": ["staged photography", "backlit transparency"],
        "descriptor": "massive backlit color transparencies merging staged photography and painting, digitally composited scenes with cinematic depth and controlled light, the constructed moment rendered at painterly scale",
    },
    "philip_lorca_dicorcia": {
        "label": "Philip-Lorca diCorcia",
        "category": "photography",
        "aliases": ["staged street", "cinematic color"],
        "descriptor": "cinematic color photographs of strangers posed under controlled light on city streets, movie-inspired backdrops and colored gels, documentary and fiction dissolving into staged atmosphere",
    },
    "nadav_kander": {
        "label": "Nadav Kander",
        "category": "photography",
        "aliases": ["atmospheric portrait", "Israeli British"],
        "descriptor": "atmospheric color portraits of soldiers and politicians veiled in haze, shallow depth of field and warm sepia tones, weight of history in soft painterly light",
    },
    "tim_walker": {
        "label": "Tim Walker",
        "category": "photography",
        "aliases": ["fantasy fashion", "storybook"],
        "descriptor": "elaborate fantasy fashion tableaus with oversized props and models in surreal costumes, soft diffused light and pastel palette, whimsical storybook detail at scale",
    },
    "paolo_roversi": {
        "label": "Paolo Roversi",
        "category": "photography",
        "aliases": ["ethereal portrait", "long exposure fashion"],
        "descriptor": "ethereal soft-focus portraits using long exposures on film, ghostly luminous skin against dark backgrounds, fashion subjects rendered with intimate blur and delicate muted color",
    },
    "david_lachapelle": {
        "label": "David LaChapelle",
        "category": "photography",
        "aliases": ["pop surrealism", "hypercolor"],
        "descriptor": "hyper-saturated digitally layered scenes packed with religious and pop-culture iconography, glossy artificial color and maximalist composition, the sacred and profane rendered in candy-coated excess",
    },
    "erwin_olaf": {
        "label": "Erwin Olaf",
        "category": "photography",
        "aliases": ["conceptual portrait", "Dutch staged"],
        "descriptor": "meticulously staged color portraits of androgynous figures in controlled environments, cool polished lighting and saturated palette, narrative tension between beauty and discomfort",
    },
    "alex_prager": {
        "label": "Alex Prager",
        "category": "photography",
        "aliases": ["staged tableau", "retro noir"],
        "descriptor": "meticulously staged color tableaus of multiple figures in retro mid-century styling, harsh Hollywood lighting and saturated palette, Hitchcockian tension frozen in glossy artificial stillness",
    },
    "lorna_simpson": {
        "label": "Lorna Simpson",
        "category": "photography",
        "aliases": ["conceptual identity", "text and image"],
        "descriptor": "conceptual black-and-white photographic fragments of Black women paired with anonymous text captions, hair and back-of-head compositions exploring identity construction through language and image",
    },
    "carrie_mae_weems": {
        "label": "Carrie Mae Weems",
        "category": "photography",
        "aliases": ["narrative photography", "kitchen table series"],
        "descriptor": "staged color and sepia narrative sequences of domestic life, artist at kitchen table in warm tonal light, African American history composed with quiet formal precision",
    },
    "graciela_iturbide": {
        "label": "Graciela Iturbide",
        "category": "photography",
        "aliases": ["Mexican documentary", "indigenous portrait"],
        "descriptor": "stark black-and-white photographs of indigenous Mexican ceremonies and daily life, geometric framing and dramatic natural light, ritual continuity in rich silver gelatin tone",
    },
    "manuel_alvarez_bravo": {
        "label": "Manuel Alvarez Bravo",
        "category": "photography",
        "aliases": ["Mexican modernism", "symbolist"],
        "descriptor": "precisely composed black-and-white frames of geometric shadow and colonial architecture, indigenous figures and everyday objects charged with quiet symbolism, Mexican modernism in silver halide light",
    },
    "zhang_kechun": {
        "label": "Zhang Kechun",
        "category": "photography",
        "aliases": ["Chinese landscape", "New Color China"],
        "descriptor": "large-format color photographs of China rapid transformation, tiny figures dwarfed by vast construction sites and polluted rivers, muted hazy tones capturing environmental scale",
    },
    "michael_kenna": {
        "label": "Michael Kenna",
        "category": "photography",
        "aliases": ["minimalist landscape", "long exposure"],
        "descriptor": "minimalist black-and-white landscapes with extreme long exposure, solitary trees and industrial silhouettes against misty water, soft silver tonality and meditative stillness in every frame",
    },
    "paul_strand": {
        "label": "Paul Strand",
        "category": "photography",
        "aliases": ["modernist street", "straight photography"],
        "descriptor": "sharp geometric black-and-white street photographs with strong graphic patterns, light and shadow forming abstract compositions, modernist precision elevating everyday urban scenes to formal study",
    },
    "imogen_cunningham": {
        "label": "Imogen Cunningham",
        "category": "photography",
        "aliases": ["botanical study", "Group f/64"],
        "descriptor": "razor-sharp black-and-white botanical photographs of flowers and succulents, intricate petal texture and smooth tonal gradation, the elegant geometry of organic form in precise silver light",
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

    # --- Fine Art: Renaissance to Baroque ---
    "leonardo_da_vinci": {
        "label": "Leonardo da Vinci",
        "category": "fine-art",
        "aliases": ["Renaissance master", "sfumato"],
        "descriptor": "soft sfumato blending edges into atmospheric haze, warm umber underpainting glowing through translucent flesh tones, pyramidal compositions balanced with geometric precision",
    },
    "michelangelo": {
        "label": "Michelangelo",
        "category": "fine-art",
        "aliases": ["High Renaissance", "monumental figure"],
        "descriptor": "muscular sculptural figures rendered in chalky stone-grey tones, dramatic contrapposto poses, deep shadow carving out monumental forms against austere backgrounds",
    },
    "raphael": {
        "label": "Raphael",
        "category": "fine-art",
        "aliases": ["High Renaissance", "classical harmony"],
        "descriptor": "balanced pyramidal compositions with soft modelling, warm golden light on idealised faces, clear colour harmonies of rose and lapis, edges dissolved in gentle atmospheric gradation",
    },
    "caravaggio": {
        "label": "Caravaggio",
        "category": "fine-art",
        "aliases": ["tenebrism", "Baroque realism"],
        "descriptor": "violent chiaroscuro with a single shaft of light cutting through pitch black, raw flesh tones emerging from deep umber shadow, theatrical close-up compositions",
    },
    "rubens": {
        "label": "Peter Paul Rubens",
        "category": "fine-art",
        "aliases": ["Flemish Baroque", "flesh painter"],
        "descriptor": "luscious impasto flesh in rose and pearl, dynamic diagonal compositions swirling with muscular figures, rich velvet reds and golds under warm Northern light",
    },
    "botticelli": {
        "label": "Sandro Botticelli",
        "category": "fine-art",
        "aliases": ["Early Renaissance", "Florentine"],
        "descriptor": "linear grace with elongated figures in flowing drapery, pale pastel palette of rose and sage, gold-leaf highlights, contours drawn with calligraphic precision",
    },
    "titian": {
        "label": "Titian",
        "category": "fine-art",
        "aliases": ["Venetian Renaissance", "colourist"],
        "descriptor": "rich Venetian colour built in layered glazes, warm flesh glowing against deep crimson and gold, loose late brushwork anticipating Impressionism, atmospheric light unifying all",
    },
    "el_greco": {
        "label": "El Greco",
        "category": "fine-art",
        "aliases": ["Spanish Mannerism", "elongated figures"],
        "descriptor": "stretched spectral figures in acid green and cold blue, flickering flame-like brushwork, elongated forms reaching upward into stormy skies, mystical light from within",
    },
    "velazquez": {
        "label": "Diego Velazquez",
        "category": "fine-art",
        "aliases": ["Spanish Golden Age", "court painter"],
        "descriptor": "loose broken brushwork resolving into realism at distance, cool silver-grey light, deep blacks and muted earth tones, atmospheric perspective dissolving distant forms",
    },
    "zurbaran": {
        "label": "Francisco de Zurbaran",
        "category": "fine-art",
        "aliases": ["Spanish Baroque", "monastic painter"],
        "descriptor": "austere tenebrist compositions with single cold light, monumental still figures in heavy monastic robes, deep black backgrounds, textures of wool and stone with sculptural weight",
    },
    "bosch": {
        "label": "Hieronymus Bosch",
        "category": "fine-art",
        "aliases": ["Northern Renaissance", "fantastical"],
        "descriptor": "teeming fantastical scenes crowded with hybrid creatures and grotesques, meticulous fine brushwork in earthy greens and browns, hellish landscapes of writhing figures under cold light",
    },
    "bruegel": {
        "label": "Pieter Bruegel the Elder",
        "category": "fine-art",
        "aliases": ["Flemish Renaissance", "peasant scenes"],
        "descriptor": "bird's-eye panoramic landscapes crowded with peasant figures, earthy palette of brown green and grey, meticulous small-scale detail, winter skies heavy with snow over frozen villages",
    },

    # --- Fine Art: 18th-19th Century ---
    "watteau": {
        "label": "Jean-Antoine Watteau",
        "category": "fine-art",
        "aliases": ["Rococo", "fete galante"],
        "descriptor": "silvery pastel brushwork of silk-clad figures in dreamlike garden parties, soft rose and sage palette, melancholy atmosphere of fading pleasure under dappled tree light",
    },
    "boucher": {
        "label": "Francois Boucher",
        "category": "fine-art",
        "aliases": ["Rococo", "decorative painter"],
        "descriptor": "polished porcelain-smooth surfaces in blush pink and sky blue, plump mythological figures in frothy pastel settings, decorative elegance with no rough edge anywhere",
    },
    "fragonard": {
        "label": "Jean-Honore Fragonard",
        "category": "fine-art",
        "aliases": ["Rococo", "erotic painter"],
        "descriptor": "feathery rapid brushwork in warm cream and rose, swirling garden scenes with frolicking figures, the fluid energy of Rococo captured in loose spirited strokes",
    },
    "goya": {
        "label": "Francisco Goya",
        "category": "fine-art",
        "aliases": ["Spanish Romantic", "court to dark"],
        "descriptor": "raw expressive brushwork shifting from elegant court portraits to black-painting nightmares, deep ochre and burnt sienna, savage shadow and harsh light exposing human brutality",
    },
    "ingres": {
        "label": "Jean-Auguste-Dominique Ingres",
        "category": "fine-art",
        "aliases": ["Neoclassical", "linear precision"],
        "descriptor": "porcelain-smooth invisible brushwork with razor-sharp contour lines, cool polished flesh tones, elongated elegant poses, every edge precise and every surface perfectly finished",
    },
    "turner": {
        "label": "J.M.W. Turner",
        "category": "fine-art",
        "aliases": ["British Romantic", "light and atmosphere"],
        "descriptor": "whirling atmospheric storms of golden light and mist, colour dissolving form into luminous energy, thin glazes and thick impasto in seascapes of sublime chaos",
    },
    "constable": {
        "label": "John Constable",
        "category": "fine-art",
        "aliases": ["British landscape", "naturalist"],
        "descriptor": "fresh broken touches of green and white capturing cloud-shadowed English meadows, sparkling light on water, textured bark and leaf, honest texture of rural light",
    },
    "delacroix": {
        "label": "Eugene Delacroix",
        "category": "fine-art",
        "aliases": ["French Romantic", "colour and movement"],
        "descriptor": "vigorous colourful brushwork full of violent motion, exotic subjects in saturated crimson and gold, complementary colour contrasts vibrating with dramatic energy and passion",
    },
    "corot": {
        "label": "Jean-Baptiste-Camille Corot",
        "category": "fine-art",
        "aliases": ["Barbizon school", "landscape poet"],
        "descriptor": "soft silvery-green landscape tones under diffused morning light, gentle atmospheric haze softening every edge, poetic stillness in woodland and river scenes rendered with quiet lyricism",
    },
    "millet": {
        "label": "Jean-Francois Millet",
        "category": "fine-art",
        "aliases": ["Barbizon school", "peasant painter"],
        "descriptor": "monumental earth-toned figures bent in labour across golden fields, warm dusky light on rustic gestures, dignity of rural work in heavy quiet brushwork",
    },

    # --- Fine Art: Impressionism and Post-Impressionism ---
    "courbet": {
        "label": "Gustave Courbet",
        "category": "fine-art",
        "aliases": ["Realism", "earth painter"],
        "descriptor": "thick earthy impasto applied with palette knife, raw flesh and stone rendered in heavy brown-green tones, unidealised rural subjects under cold natural light",
    },
    "manet": {
        "label": "Edouard Manet",
        "category": "fine-art",
        "aliases": ["proto-Impressionist", "modern life"],
        "descriptor": "bold flat areas of colour with sharp contrasts, black and white massed against warm flesh, broad confident brushwork bridging Old Master and modern subject",
    },
    "degas": {
        "label": "Edgar Degas",
        "category": "fine-art",
        "aliases": ["Impressionist", "ballet painter"],
        "descriptor": "asymmetric compositions with figures cropped by the frame, pastel flesh tones under warm footlights, swift charcoal lines capturing dancers mid-gesture in rehearsal haze",
    },
    "cezan": {
        "label": "Paul Cezanne",
        "category": "fine-art",
        "aliases": ["Post-Impressionist", "structural painter"],
        "descriptor": "constructive brushstroke of parallel hatched planes, colour modulated in faceted geometric steps, apples and mountains built from cylinder and sphere under warm Provencal light",
    },
    "gauguin": {
        "label": "Paul Gauguin",
        "category": "fine-art",
        "aliases": ["Post-Impressionist", "Synthetism"],
        "descriptor": "flat areas of saturated tropical colour bounded by dark cloisonnist outlines, Tahitian figures in vivid ochre and cobalt, decorative patterning and symbolic flatness",
    },
    "seurat": {
        "label": "Georges Seurat",
        "category": "fine-art",
        "aliases": ["Pointillism", "Neo-Impressionism"],
        "descriptor": "systematic dots of pure colour placed side by side to optically mix, shimmering light vibration across park scenes and circuses, scientific precision meeting decorative harmony",
    },
    "pissarro": {
        "label": "Camille Pissarro",
        "category": "fine-art",
        "aliases": ["Impressionist", "landscape elder"],
        "descriptor": "broken colour brushwork of rural and urban scenes, warm earth tones under soft grey skies, textured impasto capturing muddy roads and rooftops in dappled light",
    },
    "sisley": {
        "label": "Alfred Sisley",
        "category": "fine-art",
        "aliases": ["Impressionist", "pure landscape"],
        "descriptor": "delicate atmospheric landscapes in pale blue and silver, river reflections and overcast skies rendered with subtle tonal gradation, quiet light dissolving every edge into mist",
    },
    "morisot": {
        "label": "Berthe Morisot",
        "category": "fine-art",
        "aliases": ["Impressionist", "domestic light"],
        "descriptor": "light swift brushwork in pastel white and rose, women and children in sunlit gardens, translucent texture of gauze and lace in feathery impressionist strokes",
    },
    "cassatt": {
        "label": "Mary Cassatt",
        "category": "fine-art",
        "aliases": ["Impressionist", "mother and child"],
        "descriptor": "tender domestic scenes of mothers and children in warm light, soft pink and lavender tones, bold flat pattern from Japanese prints merged with Impressionist colour",
    },
    "toulouse_lautrec": {
        "label": "Henri de Toulouse-Lautrec",
        "category": "fine-art",
        "aliases": ["Post-Impressionist", "Montmartre"],
        "descriptor": "sinuous ink outlines filled with flat washes of colour, cabaret performers and dancers in gaslit interiors, Japanese-influenced cropping and bold graphic poster compositions",
    },

    # --- Fine Art: Symbolism and Art Nouveau ---
    "klimt": {
        "label": "Gustav Klimt",
        "category": "fine-art",
        "aliases": ["Vienna Secession", "golden phase"],
        "descriptor": "opulent gold leaf and mosaic patterning enveloping sensual female figures, Byzantine-influenced decorative surface, flesh rendered in soft naturalism against shimmering ornamental flatness",
    },
    "schiele": {
        "label": "Egon Schiele",
        "category": "fine-art",
        "aliases": ["Vienna Secession", "Expressionist portrait"],
        "descriptor": "angular jagged linework around contorted emaciated figures, raw flesh in sickly ochre and bruised violet, twisted poses and direct gazes charged with nervous erotic tension",
    },
    "munch": {
        "label": "Edvard Munch",
        "category": "fine-art",
        "aliases": ["Symbolist", "Expressionist pioneer"],
        "descriptor": "wavy sinuous lines of acid colour expressing anxiety and longing, blood-red skies and sickly green faces, emotional states rendered in swirling atmospheric brushwork",
    },
    "modigliani": {
        "label": "Amedeo Modigliani",
        "category": "fine-art",
        "aliases": ["School of Paris", "elongated portrait"],
        "descriptor": "elongated swan-neck figures with blank almond-eyed faces, warm terracotta and ochre tones, smooth flattened forms inspired by African sculpture and Italian Primitives",
    },
    "bonnard": {
        "label": "Pierre Bonnard",
        "category": "fine-art",
        "aliases": ["Intimist", "colour decorator"],
        "descriptor": "lush saturated colour filling domestic interiors and garden scenes, warm checkered tablecloths and sun-drenched bathrooms, pattern and light dissolving form into pure decorative sensation",
    },
    "vuillard": {
        "label": "Edouard Vuillard",
        "category": "fine-art",
        "aliases": ["Intimist", "patterned interior"],
        "descriptor": "dusky muted interiors where figures merge into wallpaper pattern, warm brown and olive tones, domestic scenes rendered in flat matte texture with quiet decorative intimacy",
    },

    # --- Fine Art: Early Modern and Abstract ---
    "kandinsky": {
        "label": "Wassily Kandinsky",
        "category": "fine-art",
        "aliases": ["abstract pioneer", "Bauhaus"],
        "descriptor": "pure abstract compositions of floating geometric shapes in vivid primary colour, circles and triangles dancing like visual music, spiritual rhythm in pure form",
    },
    "malevich": {
        "label": "Kazimir Malevich",
        "category": "fine-art",
        "aliases": ["Suprematism", "geometric abstraction"],
        "descriptor": "pure geometric shapes floating on white ground, black squares and red wedges reduced to essential form, absolute zero of painting where colour shape are all",
    },
    "mondrian": {
        "label": "Piet Mondrian",
        "category": "fine-art",
        "aliases": ["De Stijl", "Neoplasticism"],
        "descriptor": "strict grid of black horizontal and vertical lines enclosing rectangles of pure red blue and yellow against white, absolute harmony through geometric reduction",
    },
    "klee": {
        "label": "Paul Klee",
        "category": "fine-art",
        "aliases": ["Bauhaus", "poetic abstraction"],
        "descriptor": "whimsical childlike symbols and arrows on tinted grounds, delicate watercolour washes beneath fine linework, pictographic poetry balancing abstraction and representation with gentle humour",
    },
    "miro": {
        "label": "Joan Miro",
        "category": "fine-art",
        "aliases": ["Surrealist", "biomorphic abstraction"],
        "descriptor": "playful biomorphic shapes in primary colour on bright grounds, stars eyes and ladders in spontaneous childlike line, joy of pure colour and form unbound",
    },
    "duchamp": {
        "label": "Marcel Duchamp",
        "category": "fine-art",
        "aliases": ["Dada", "conceptual art"],
        "descriptor": "cool detached irony in readymade objects and optical paintings, mechanical drawing precision applied to absurd subjects, the idea overriding the hand in conceptual art",
    },
    "chagall": {
        "label": "Marc Chagall",
        "category": "fine-art",
        "aliases": ["School of Paris", "dreamlike folk art"],
        "descriptor": "floating lovers and fiddlers in saturated jewel colour against deep blue night skies, folk-memory imagery rendered in loose expressive brushwork with childlike wonder",
    },

    # --- Fine Art: Surrealism ---
    "dali": {
        "label": "Salvador Dali",
        "category": "fine-art",
        "aliases": ["Surrealist", "paranoiac-critical"],
        "descriptor": "hyper-realistic academic technique rendering melting clocks and impossible architecture, barren Catalonian landscapes under cold light, dream imagery painted with photographic precision",
    },
    "ernst": {
        "label": "Max Ernst",
        "category": "fine-art",
        "aliases": ["Surrealist", "Dada"],
        "descriptor": "rubbing and frottage textures generating strange forest and bird imagery, collage novels of uncanny juxtaposition, dark primordial forms emerging from automated technique",
    },
    "de_chirico": {
        "label": "Giorgio de Chirico",
        "category": "fine-art",
        "aliases": ["Metaphysical painting", "proto-Surrealist"],
        "descriptor": "empty arcaded piazzas with impossibly long shadows, mannequin figures and classical architecture under cold raking light, the uncanny stillness of a dream frozen in oil",
    },

    # --- Fine Art: German Expressionism ---
    "kirchner": {
        "label": "Ernst Ludwig Kirchner",
        "category": "fine-art",
        "aliases": ["Die Brucke", "German Expressionist"],
        "descriptor": "jagged angular figures in acid colours, elongated bodies with mask-like faces on Berlin streets, nervous scratchy linework and clashing hues expressing urban anxiety",
    },
    "nolde": {
        "label": "Emil Nolde",
        "category": "fine-art",
        "aliases": ["Die Brucke", "colour ecstatic"],
        "descriptor": "thick impasto of pure saturated colour applied directly, religious and floral subjects blazing in red and gold, ecstatic spiritual intensity in raw pigment",
    },
    "grosz": {
        "label": "George Grosz",
        "category": "fine-art",
        "aliases": ["New Objectivity", "satirical"],
        "descriptor": "biting caricature of Weimar society in harsh ink and acid colour, grotesque fat businessmen and war cripples, angular cynical linework exposing corruption and moral decay",
    },
    "dix": {
        "label": "Otto Dix",
        "category": "fine-art",
        "aliases": ["New Objectivity", "war painter"],
        "descriptor": "unsentimental hyper-detailed portraits of war veterans and society women, cold realist technique exposing scarred flesh and painted faces, savage social critique in enamel precision",
    },
    "beckmann": {
        "label": "Max Beckmann",
        "category": "fine-art",
        "aliases": ["German Expressionist", "figurative"],
        "descriptor": "crowded compressed compositions of figures in claustrophobic interiors, heavy black outlines and dark earthy palette, existential drama rendered in monumental static poses",
    },

    # --- Fine Art: Abstract Expressionism ---
    "pollock": {
        "label": "Jackson Pollock",
        "category": "fine-art",
        "aliases": ["Action painting", "drip painting"],
        "descriptor": "dense web of poured and dripped enamel paint layered across unstretched canvas, rhythmic all-over composition with no centre, the physical gesture of painting made visible",
    },
    "rothko": {
        "label": "Mark Rothko",
        "category": "fine-art",
        "aliases": ["Colour field", "Abstract Expressionist"],
        "descriptor": "soft-edged rectangular fields of luminous colour floating on stained canvas, deep maroon against orange, the paint breathed on in thin veils creating meditative emotional space",
    },
    "de_kooning": {
        "label": "Willem de Kooning",
        "category": "fine-art",
        "aliases": ["Action painting", "figurative abstraction"],
        "descriptor": "aggressive slashing brushwork tearing at the figure, flesh tones and raw canvas visible through violent gestural strokes, the body dissolving and reassembling in paint",
    },

    # --- Fine Art: Figurative Modern ---
    "bacon": {
        "label": "Francis Bacon",
        "category": "fine-art",
        "aliases": ["existential figurative", "screaming pope"],
        "descriptor": "smudged distorted faces trapped in geometric cages, raw flesh in bloody red and bruised violet, the scream caught in blurred motion against flat painted backgrounds",
    },
    "freud": {
        "label": "Lucian Freud",
        "category": "fine-art",
        "aliases": ["British figurative", "flesh painter"],
        "descriptor": "thick impasto flesh in raw pink and bruised purple, nudes examined with unflinching clinical intensity, every fold and blemish built up in heavy sculpted paint",
    },
    "auerbach": {
        "label": "Frank Auerbach",
        "category": "fine-art",
        "aliases": ["British figurative", "thick impasto"],
        "descriptor": "massive encrusted layers of oil paint scraped and rebuilt daily, heads and landscapes from dense geological strata of pigment, weight of paint as subject",
    },
    "kossoff": {
        "label": "Leon Kossoff",
        "category": "fine-art",
        "aliases": ["British figurative", "London painter"],
        "descriptor": "fluid rushing brushwork in warm earth tones, London streets and swimming pools in trembling liquid paint, city felt through physical energy of brushstroke",
    },
    "hodgkin": {
        "label": "Howard Hodgkin",
        "category": "fine-art",
        "aliases": ["British colourist", "painted frame"],
        "descriptor": "bold decorative colour extending onto the picture frame, memory-paintings of emotional encounters in warm saturated tones, the boundary between image and object dissolved in paint",
    },

    # --- Fine Art: American Modern ---
    "okeeffe": {
        "label": "Georgia O'Keeffe",
        "category": "fine-art",
        "aliases": ["American modernist", "flower painter"],
        "descriptor": "massive close-up flowers and bleached desert bones rendered in smooth gradated colour, soft organic forms filling the frame, Precisionist clarity meeting sensual abstraction",
    },
    "whistler": {
        "label": "James McNeill Whistler",
        "category": "fine-art",
        "aliases": ["Tonalism", "Nocturne"],
        "descriptor": "misty tonal harmonies in blue grey and gold, figures and fog dissolving into atmospheric abstraction, the painting as musical composition in subtle muted colour",
    },
    "sargent": {
        "label": "John Singer Sargent",
        "category": "fine-art",
        "aliases": ["portrait virtuoso", "Gilded Age"],
        "descriptor": "dazzling bravura brushwork capturing satin and skin in single strokes, elegant figures in warm interior light, confidence of effortless society portraiture",
    },
    "rivera": {
        "label": "Diego Rivera",
        "category": "fine-art",
        "aliases": ["Mexican Muralist", "social realism"],
        "descriptor": "monumental fresco compositions of workers and indigenous history, solid volumetric figures in earthy Mexican palette, narrative density and political purpose in every wall-sized scene",
    },

    # --- Fine Art: Pop and Contemporary ---
    "warhol": {
        "label": "Andy Warhol",
        "category": "fine-art",
        "aliases": ["Pop Art", "screen print"],
        "descriptor": "flat silkscreened images of celebrities and soup cans in acid pop colour, mechanical repetition draining the hand from art, mass-production aesthetics meeting cool deadpan glamour",
    },
    "lichtenstein": {
        "label": "Roy Lichtenstein",
        "category": "fine-art",
        "aliases": ["Pop Art", "comic strip"],
        "descriptor": "Ben-Day dots and bold black outlines mimicking cheap comic printing, melodramatic close-ups in primary colour, the mass-produced image elevated to high art through mechanical precision",
    },
    "richter": {
        "label": "Gerhard Richter",
        "category": "fine-art",
        "aliases": ["photo-painting", "German contemporary"],
        "descriptor": "photo-based paintings dragged with a soft brush into blurred uncertainty, family portraits and abstract squeegee works, the tension between photographic truth and painted ambiguity",
    },
    "hockney": {
        "label": "David Hockney",
        "category": "fine-art",
        "aliases": ["British Pop", "California pool"],
        "descriptor": "flat bright colour of Californian swimming pools and Yorkshire landscapes, clean hard-edge acrylic rendering of water and lawn, cheerful decorativeness of sunlight on surface",
    },
    "basquiat": {
        "label": "Jean-Michel Basquiat",
        "category": "fine-art",
        "aliases": ["Neo-Expressionist", "street art"],
        "descriptor": "raw graffiti-inspired figures with crown and skull motifs, text and anatomy scrawled in urgent black and red, energy of the street translated into painting",
    },
    "johns": {
        "label": "Jasper Johns",
        "category": "fine-art",
        "aliases": ["Neo-Dada", "flag painter"],
        "descriptor": "encaustic wax and collage building up flags targets and numbers, familiar symbols made strange through thick textured surface, the known image questioned through material density",
    },
    "rauschenberg": {
        "label": "Robert Rauschenberg",
        "category": "fine-art",
        "aliases": ["Combine", "Neo-Dada"],
        "descriptor": "white painted surfaces receiving silk-screened images and attached objects, Combines merging painting and sculpture, the boundary between art and life dissolved in layered assemblage",
    },
    "close": {
        "label": "Chuck Close",
        "category": "fine-art",
        "aliases": ["Photorealist", "grid portrait"],
        "descriptor": "massive hyper-detailed faces built from grid cells of colour, photographic source translated cell by cell into painted surface, the pore-level intimacy of mechanical reproduction",
    },
    "riley": {
        "label": "Bridget Riley",
        "category": "fine-art",
        "aliases": ["Op Art", "perceptual"],
        "descriptor": "precise geometric patterns of black and white creating optical vibration and movement, the retina fooled by systematic line and curve, perception itself made visible",
    },
    "hirst": {
        "label": "Damien Hirst",
        "category": "fine-art",
        "aliases": ["YBA", "conceptual"],
        "descriptor": "clinical display of preserved animals and spot paintings in industrial colour, the shock of death aestheticised in formaldehyde and enamel, concept dominating the painted surface",
    },
    "emin": {
        "label": "Tracey Emin",
        "category": "fine-art",
        "aliases": ["YBA", "confessional"],
        "descriptor": "raw autobiographical neon and textile works spelling out intimate confessions, handwritten text and sewn appliques in vulnerable colour, the personal made public without filter",
    },
    "doig": {
        "label": "Peter Doig",
        "category": "fine-art",
        "aliases": ["British contemporary", "atmospheric landscape"],
        "descriptor": "dreamlike landscapes and architectural scenes rendered in lush textured paint, reflections on water and snow in muted colour, memory and photograph blurred into painterly atmosphere",
    },
    "ofili": {
        "label": "Chris Ofili",
        "category": "fine-art",
        "aliases": ["YBA", "decoration"],
        "descriptor": "richly decorated paintings incorporating beadwork and collage, Afrofuturist figures in psychedelic colour, the decorative and the political layered in glittering surface texture",
    },
    "saville": {
        "label": "Jenny Saville",
        "category": "fine-art",
        "aliases": ["British figurative", "flesh"],
        "descriptor": "monumental flesh-coloured bodies filling the frame, thick impasto of bruised pink and yellow, the weight and texture of flesh examined at overwhelming scale without idealisation",
    },
    "utril_o": {
        "label": "Maurice Utrillo",
        "category": "fine-art",
        "aliases": ["School of Paris", "Montmartre"],
        "descriptor": "quiet Parisian street scenes in muted white and grey, Montmartre facades under overcast skies, the melancholy of empty corners rendered in simple honest brushwork",
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

    # --- Sculpture ---
    "rodin": {
        "label": "Auguste Rodin",
        "category": "fine-art",
        "aliases": ["sculpture master", "bronze figure"],
        "descriptor": "rough-textured bronze catching raking light, muscular torsos emerging from unfinished stone, deep shadow pools in modelled flesh, raw energy of clay preserved in cast metal",
    },
    "bernini": {
        "label": "Gian Lorenzo Bernini",
        "category": "fine-art",
        "aliases": ["baroque sculptor", "marble virtuoso"],
        "descriptor": "polished white marble rendered with impossible softness, drapery flowing as if wind-blown, ecstatic faces lit from within, theatrical space and dramatic gesture frozen in stone",
    },
    "donatello": {
        "label": "Donatello",
        "category": "fine-art",
        "aliases": ["early renaissance", "bronze sculptor"],
        "descriptor": "lean muscular bronze and stone figures with sharp anatomical precision, restrained classical poses, shallow relief carving that plays light across subtle surface transitions",
    },
    "michelangelo": {
        "label": "Michelangelo",
        "category": "fine-art",
        "aliases": ["high renaissance", "marble sculptor"],
        "descriptor": "monumental marble figures emerging from rough-hewn stone, twisting contrapposto poses, highly polished flesh surfaces against textured backgrounds, idealized anatomy straining against material limits",
    },
    "brancusi": {
        "label": "Constantin Brancusi",
        "category": "fine-art",
        "aliases": ["modernist sculptor", "abstract form"],
        "descriptor": "highly polished bronze and marble surfaces reduced to essential curves, ovoid and aerodynamic forms catching reflected light, pedestals integral to the sculpture's spatial presence",
    },
    "giacometti": {
        "label": "Alberto Giacometti",
        "category": "fine-art",
        "aliases": ["existential sculptor", "elongated figure"],
        "descriptor": "gaunt elongated bronze figures with rough pitted surfaces, wire-thin limbs and hollowed faces, standing alone in empty space, texture of eroded plaster preserved in cast",
    },
    "henry_moore": {
        "label": "Henry Moore",
        "category": "fine-art",
        "aliases": ["organic abstraction", "reclining figure"],
        "descriptor": "monumental bronze and stone forms with hollowed voids and rounded organic contours, landscape-like surfaces weathered to matte patina, body abstracted into hill and valley",
    },
    "barbara_hepworth": {
        "label": "Barbara Hepworth",
        "category": "fine-art",
        "aliases": ["abstract sculptor", "pierced form"],
        "descriptor": "smooth carved stone and wood with pierced openings framing space, taut strings across hollowed interiors, flowing biomorphic curves in polished bronze and painted wood",
    },
    "louise_bourgeois": {
        "label": "Louise Bourgeois",
        "category": "fine-art",
        "aliases": ["installation art", "psychological sculpture"],
        "descriptor": "monumental bronze and fabric forms combining organic body parts with architectural space, rough stitched surfaces and polished metal, uncanny scale of domestic objects turned monumental",
    },
    "anish_kapoor": {
        "label": "Anish Kapoor",
        "category": "fine-art",
        "aliases": ["installation sculptor", "void explorer"],
        "descriptor": "highly polished concave metal surfaces inverting reflected space, deep pigment voids in raw stone, monumental scale absorbing the viewer into reflective or absorptive depths",
    },
    "damien_hirst": {
        "label": "Damien Hirst",
        "category": "fine-art",
        "aliases": ["yba", "conceptual sculpture"],
        "descriptor": "stainless steel and glass cases preserving suspended animal forms, diamond-encrusted skulls gleaming under clinical light, pharmaceutical dot paintings in saturated acrylic colour grids",
    },
    "jeff_koons": {
        "label": "Jeff Koons",
        "category": "fine-art",
        "aliases": ["pop sculptor", "kitsch master"],
        "descriptor": "mirror-polished stainless steel balloon animals and floral sculptures reflecting the surrounding space, flawless industrial surfaces in saturated candy colours, banal objects elevated to monumental scale",
    },

    # --- Contemporary / Installation ---
    "yayoi_kusama": {
        "label": "Yayoi Kusama",
        "category": "fine-art",
        "aliases": ["polka dots", "infinity rooms"],
        "descriptor": "obsessive repetition of polka dots and net patterns covering every surface, mirrored infinity rooms dissolving space, soft sculptural protrusions in vivid primary colours",
    },
    "takashi_murakami": {
        "label": "Takashi Murakami",
        "category": "fine-art",
        "aliases": ["superflat", "otaku art"],
        "descriptor": "flat acrylic surfaces in hyper-saturated candy colours, smiling flowers and cartoon eyes rendered with anime precision, layered screen-print textures blurring high art and mass production",
    },
    "ai_weiwei": {
        "label": "Ai Weiwei",
        "category": "fine-art",
        "aliases": ["conceptual artist", "chinese contemporary"],
        "descriptor": "readymade industrial materials assembled into monumental geometric installations, sunflower seeds in porcelain, steel rebar twisted into organic forms, mass and repetition as political statement",
    },

    # --- Street Art / Urban ---
    "banksy": {
        "label": "Banksy",
        "category": "fine-art",
        "aliases": ["street art", "stencil art"],
        "descriptor": "stencil-cut spray paint on weathered urban walls, monochrome figures with sardonic visual punchlines, rough concrete texture behind clean graphic silhouettes, subversive wit in public space",
    },
    "kaws": {
        "label": "KAWS",
        "category": "fine-art",
        "aliases": ["street art", "toy sculpture"],
        "descriptor": "vinyl and fiberglass sculptures with X-ed out eyes and skull heads, flat acrylic in muted greys and pastels, cartoon forms at monumental public scale",
    },
    "jr": {
        "label": "JR",
        "category": "fine-art",
        "aliases": ["street photographer", "wheatpaste"],
        "descriptor": "massive black-and-white photographic portraits wheatpasted onto building facades and ground planes, grainy high-contrast imagery scaled to architectural proportion, community faces transformed into public monument",
    },
    "shepard_fairey": {
        "label": "Shepard Fairey",
        "category": "fine-art",
        "aliases": ["obey giant", "propaganda art"],
        "descriptor": "bold screen-printed graphics in limited palettes of red black and cream, stylized faces with star motifs and propaganda typography, rough stencil texture on layered wheatpaste",
    },

    # --- Contemporary Painting: Portraiture ---
    "kehinde_wiley": {
        "label": "Kehinde Wiley",
        "category": "fine-art",
        "aliases": ["contemporary portrait", "old master remix"],
        "descriptor": "hyper-detailed oil portraits of young black men and women in classical European compositions, ornate decorative backgrounds in flat patterned colour, luminous skin against floral ornament",
    },
    "amy_sherald": {
        "label": "Amy Sherald",
        "category": "fine-art",
        "aliases": ["contemporary portrait", "american realism"],
        "descriptor": "grey-scale skin tones against vivid flat colour backgrounds, frontal seated poses with direct gaze, smooth oil rendering of fabric and flesh, quiet everyday dignity",
    },
    "kerry_james_marshall": {
        "label": "Kerry James Marshall",
        "category": "fine-art",
        "aliases": ["american painter", "black identity"],
        "descriptor": "deeply saturated flat acrylic paintings with jet-black skin tones as pure positive form, layered references to old master composition and comic-strip clarity, lush patterned backgrounds",
    },

    # --- Contemporary Painting: Abstraction ---
    "mark_bradford": {
        "label": "Mark Bradford",
        "category": "fine-art",
        "aliases": ["abstract painter", "material abstraction"],
        "descriptor": "massive canvases from layered torn paper and billboard fragments sanded to reveal buried strata, muted urban palettes, texture of city walls as abstract surface",
    },
    "julie_mehretu": {
        "label": "Julie Mehretu",
        "category": "fine-art",
        "aliases": ["abstract painter", "architectural abstraction"],
        "descriptor": "vast layered canvases of architectural drawing erased and redrawn, translucent veils of colour over dense graphite and ink, energy of urban plans frozen in abstraction",
    },
    "gerhard_richter": {
        "label": "Gerhard Richter",
        "category": "fine-art",
        "aliases": ["abstract painter", "photo painting"],
        "descriptor": "photorealistic portraits blurred by dragged wet paint, abstract squeegeed surfaces in layered translucent colour, the tension between photographic precision and painterly destruction of the image",
    },
    "cy_twombly": {
        "label": "Cy Twombly",
        "category": "fine-art",
        "aliases": ["gestural abstraction", "scribble painter"],
        "descriptor": "loose looping pencil and crayon lines over pale stained grounds, gestural scrawls and erased marks on raw canvas, energy of handwriting as monumental abstract composition",
    },
    "anselm_kiefer": {
        "label": "Anselm Kiefer",
        "category": "fine-art",
        "aliases": ["neo-expressionist", "german painter"],
        "descriptor": "massive canvases encrusted with lead ash straw and shellac, scorched earth tones and burnt umber surfaces, weight of history embedded in thick material texture",
    },

    # --- Contemporary Painting: Figurative ---
    "georg_baselitz": {
        "label": "Georg Baselitz",
        "category": "fine-art",
        "aliases": ["neo-expressionist", "inverted painter"],
        "descriptor": "upside-down figurative oil paintings with rough expressive brushwork, raw canvas visible beneath thick impasto, distorted bodies in muddy earth tones, the shock of inverted composition",
    },
    "neo_rauch": {
        "label": "Neo Rauch",
        "category": "fine-art",
        "aliases": ["leipzig school", "surrealist painter"],
        "descriptor": "dreamlike narrative scenes in muted oil tones, factory workers and surreal figures in impossible architectural spaces, flat matte surface of socialist realism haunted by fantasy",
    },
    "jenny_saville": {
        "label": "Jenny Saville",
        "category": "fine-art",
        "aliases": ["flesh painter", "body monumental"],
        "descriptor": "monumental flesh-toned oil paintings where thick impasto presses against the picture plane, bruised purples and raw pinks, visceral body weight at overwhelming scale",
    },
    "cecily_brown": {
        "label": "Cecily Brown",
        "category": "fine-art",
        "aliases": ["gestural painter", "erotic abstraction"],
        "descriptor": "lush oil paintings where figurative forms dissolve into energetic brushwork, warm flesh tones and deep reds in abstract carnal space, threshold between recognition and paint",
    },
    "peter_doig": {
        "label": "Peter Doig",
        "category": "fine-art",
        "aliases": ["atmospheric painter", "memory landscape"],
        "descriptor": "dreamlike landscapes and architectural scenes in soft acrylic washes, blurred reflective water surfaces, figures half-lost in atmospheric haze, colour of memory and old photographs",
    },
    "marlene_dumas": {
        "label": "Marlene Dumas",
        "category": "fine-art",
        "aliases": ["wet-on-wet painter", "psychological portrait"],
        "descriptor": "thin oil paint poured and brushed on raw canvas, pale flesh tones and deep pooling blacks, wet-on-wet blurring, vulnerability exposed in every drip and stain",
    },
    "luc_tuymans": {
        "label": "Luc Tuymans",
        "category": "fine-art",
        "aliases": ["belgian painter", "faded memory"],
        "descriptor": "pale washed-out oil paintings from photographic sources, muted desaturated colour and soft blurred edges, historical trauma in the flat tone of faded film stills",
    },
    "michael_borremans": {
        "label": "Michaël Borremans",
        "category": "fine-art",
        "aliases": ["belgian painter", "uncanny realism"],
        "descriptor": "small-scale oil paintings with smooth enamel-like surfaces, figures in ambiguous rituals under flat even lighting, muted earth tones and eerie stillness refusing explanation",
    },

    # --- Chinese Contemporary ---
    "zeng_fanzhi": {
        "label": "Zeng Fanzhi",
        "category": "fine-art",
        "aliases": ["chinese expressionist", "mask series"],
        "descriptor": "thick impasto portraits with schoolboy uniforms and white masks, rough scraped paint in cold blue-grey tones, alienation of modern chinese youth in heavy textured oil",
    },
    "yue_minjun": {
        "label": "Yue Minjun",
        "category": "fine-art",
        "aliases": ["chinese pop", "laughing man"],
        "descriptor": "grinning self-portrait faces repeated across canvases in bright enamel colours, cartoonish figures with closed eyes and laughing mouths, flat graphic surface of propaganda turned self-parody",
    },
    "zhang_xiaogang": {
        "label": "Zhang Xiaogang",
        "category": "fine-art",
        "aliases": ["bloodline series", "chinese portrait"],
        "descriptor": "pale formal portraits in flat oil with soft blurred features, pale skin tones against muted backgrounds, quiet melancholy of family photographs from chinese cultural revolution",
    },
    "yoshitomo_nara": {
        "label": "Yoshitomo Nara",
        "category": "fine-art",
        "aliases": ["japanese pop", "cute aggression"],
        "descriptor": "large-eyed cartoon children in flat acrylic colour fields, slanting suspicious gazes and hidden weapons, sugary surface of kawaii culture undercut by quiet menace and isolation",
    },

    # --- Classic Illustration ---
    "arthur_rackham": {
        "label": "Arthur Rackham",
        "category": "illustration",
        "aliases": ["golden age illustrator", "fairy tale"],
        "descriptor": "gnarled ink linework over muted watercolour washes, twisted tree forms and spindly figures, sepia and umber palette with touches of gold leaf",
    },
    "kay_nielsen": {
        "label": "Kay Nielsen",
        "category": "illustration",
        "aliases": ["Art Deco illustrator", "orientalist"],
        "descriptor": "elegant elongated figures in stylized Art Deco compositions, flat colour planes with fine black outlines, exotic oriental motifs in jewel-tone palettes",
    },
    "edmund_dulac": {
        "label": "Edmund Dulac",
        "category": "illustration",
        "aliases": ["watercolour master", "Persian settings"],
        "descriptor": "richly layered watercolour glazes in deep jewel tones, ornate Middle Eastern and Persian settings, decorative borders framing romantic narrative scenes",
    },
    "nc_wyeth": {
        "label": "N.C. Wyeth",
        "category": "illustration",
        "aliases": ["American illustrator", "adventure scenes"],
        "descriptor": "bold brushwork in warm earth tones, heroic figures in dramatic outdoor light, sweeping landscape compositions with strong diagonal movement",
    },
    "maxfield_parrish": {
        "label": "Maxfield Parrish",
        "category": "illustration",
        "aliases": ["Parrish blue", "classical architecture"],
        "descriptor": "luminous cobalt blue skies over idealized classical architecture, smooth enamel-like surfaces, golden hour light casting long shadows across imaginary landscapes",
    },
    "beatrix_potter": {
        "label": "Beatrix Potter",
        "category": "illustration",
        "aliases": ["animal illustrator", "miniature scenes"],
        "descriptor": "delicate watercolour rendering of small animals in miniature settings, soft natural palette of moss green and dusty rose, precise botanical detail",
    },
    "maurice_sendak": {
        "label": "Maurice Sendak",
        "category": "illustration",
        "aliases": ["Where the Wild Things Are", "expressive creatures"],
        "descriptor": "expressive crosshatched ink lines with watercolour wash, wild creatures rendered with emotional intensity, dense decorative patterns filling every corner",
    },
    "chris_van_allsburg": {
        "label": "Chris Van Allsburg",
        "category": "illustration",
        "aliases": ["graphite rendering", "surreal domestic"],
        "descriptor": "graphite-like tonal rendering in muted grey-green palette, dramatic low-angle perspectives, mysterious light sources casting deep shadows across surreal domestic scenes",
    },
    "quentin_blake": {
        "label": "Quentin Blake",
        "category": "illustration",
        "aliases": ["loose ink", "childlike energy"],
        "descriptor": "loose energetic ink lines with spontaneous watercolour splashes, exaggerated gestural figures, childlike immediacy and joyful visual chaos",
    },
    "dr_seuss": {
        "label": "Dr. Seuss",
        "category": "illustration",
        "aliases": ["whimsical line", "impossible architecture"],
        "descriptor": "playful curving ink lines with flat colour fills, impossible architecture and impossible creatures, whimsical perspective distortions and bouncy rhythmic compositions",
    },

    # --- Modern Illustration ---
    "shaun_tan": {
        "label": "Shaun Tan",
        "category": "illustration",
        "aliases": ["hyperreal graphite", "melancholic creatures"],
        "descriptor": "hyperreal graphite rendering of impossible creatures in desolate landscapes, muted sepia palette, dreamlike scale shifts and melancholic atmospheric perspective",
    },
    "oliver_jeffers": {
        "label": "Oliver Jeffers",
        "category": "illustration",
        "aliases": ["flat colour", "primary palette"],
        "descriptor": "simple flat colour shapes with hand-drawn black outlines, limited palette of primary colours, childlike figure drawing with emotional directness",
    },
    "christian_robinson": {
        "label": "Christian Robinson",
        "category": "illustration",
        "aliases": ["geometric figures", "vibrant primary"],
        "descriptor": "bold flat colour shapes in vibrant primary palette, simplified geometric figures, playful compositional balance with generous white space",
    },
    "carson_ellis": {
        "label": "Carson Ellis",
        "category": "illustration",
        "aliases": ["folk-art woodcut", "naive perspective"],
        "descriptor": "folk-art woodcut aesthetic with hand-carved texture, limited earth-tone palette, naive perspective and decorative pattern work",
    },
    "jon_klassen": {
        "label": "Jon Klassen",
        "category": "illustration",
        "aliases": ["minimal flat", "deadpan composition"],
        "descriptor": "minimal flat colour fields with subtle texture, understated character design, deadpan compositions with precise negative space",
    },
    "brian_froud": {
        "label": "Brian Froud",
        "category": "illustration",
        "aliases": ["faerie illustrator", "creature designer"],
        "descriptor": "whimsical creature design with organic textured rendering, earthy natural palette, faerie folklore aesthetic with detailed botanical and geological elements",
    },
    "charles_vess": {
        "label": "Charles Vess",
        "category": "illustration",
        "aliases": ["folk-art illustration", "mythological subjects"],
        "descriptor": "folk-art inspired linework with watercolour wash, mythological and fairy tale subjects, decorative border work and medieval manuscript aesthetic",
    },
    "yoshitaka_amano": {
        "label": "Yoshitaka Amano",
        "category": "illustration",
        "aliases": ["ethereal linework", "Japanese fantasy"],
        "descriptor": "ethereal flowing linework with luminous colour washes, elongated elegant figures, dreamlike fantasy imagery with Japanese aesthetic sensibility",
    },
    "james_jean": {
        "label": "James Jean",
        "category": "illustration",
        "aliases": ["surreal narrative", "symbolic imagery"],
        "descriptor": "surreal narrative illustration with precise rendering, layered symbolic imagery, rich colour palette with decorative pattern work and botanical detail",
    },
    "mary_blair": {
        "label": "Mary Blair",
        "category": "illustration",
        "aliases": ["mid-century modern", "bold flat colour"],
        "descriptor": "bold flat colour shapes with graphic composition, vibrant primary palette, stylized mid-century modern aesthetic with childlike wonder",
    },

    # --- Concept Art ---
    "craig_mullins": {
        "label": "Craig Mullins",
        "category": "digital",
        "aliases": ["digital impasto", "epic landscapes"],
        "descriptor": "expressive digital brushwork with thick impasto texture, dramatic chiaroscuro lighting, loose painterly rendering of epic landscape and architectural scenes",
    },
    "feng_zhu": {
        "label": "Feng Zhu",
        "category": "digital",
        "aliases": ["industrial design", "dynamic perspective"],
        "descriptor": "dynamic industrial design concepts with strong perspective, metallic surface rendering under dramatic lighting, detailed mechanical and architectural environments",
    },
    "john_park": {
        "label": "John Park",
        "category": "digital",
        "aliases": ["volumetric lighting", "epic scale"],
        "descriptor": "atmospheric digital painting with soft volumetric lighting, epic scale environments, rich colour gradients transitioning from warm foreground to cool distance",
    },
    "raphael_lacoste": {
        "label": "Raphael Lacoste",
        "category": "digital",
        "aliases": ["moody atmosphere", "organic forms"],
        "descriptor": "moody atmospheric rendering with strong value contrast, organic forms emerging from deep shadow, cinematic composition with dramatic sky treatment",
    },
    "jaime_jones": {
        "label": "Jaime Jones",
        "category": "digital",
        "aliases": ["vibrant colour", "dynamic action"],
        "descriptor": "vibrant colour palette with strong complementary contrasts, dynamic figure poses in action, detailed environmental storytelling with rich atmospheric perspective",
    },
    "ryan_church": {
        "label": "Ryan Church",
        "category": "digital",
        "aliases": ["industrial concept", "technical precision"],
        "descriptor": "detailed industrial concept design with technical precision, atmospheric rendering, sci-fi vehicle and environment design with realistic material textures",
    },
    "doug_chiang": {
        "label": "Doug Chiang",
        "category": "digital",
        "aliases": ["futuristic design", "industrial aesthetic"],
        "descriptor": "sleek futuristic design with strong industrial aesthetic, detailed mechanical rendering, cinematic composition and atmospheric perspective",
    },
    "nathan_fowkes": {
        "label": "Nathan Fowkes",
        "category": "digital",
        "aliases": ["dramatic lighting", "environmental storytelling"],
        "descriptor": "atmospheric digital painting with dramatic lighting, epic landscape composition, rich colour gradients and environmental storytelling",
    },
    "maciej_kuciara": {
        "label": "Maciej Kuciara",
        "category": "digital",
        "aliases": ["dynamic sci-fi", "mechanical design"],
        "descriptor": "dynamic sci-fi concept art with strong perspective, detailed mechanical design, dramatic lighting and cinematic composition",
    },

    # --- Comics ---
    "jack_kirby": {
        "label": "Jack Kirby",
        "category": "comics",
        "aliases": ["dynamic ink", "cosmic power"],
        "descriptor": "bold dynamic ink lines with heavy black shadows, explosive action poses, cosmic energy effects and technological detail rendered with raw power",
    },
    "will_eisner": {
        "label": "Will Eisner",
        "category": "comics",
        "aliases": ["ink wash", "cinematic panels"],
        "descriptor": "expressive ink wash with strong graphic composition, cinematic panel layouts, dramatic chiaroscuro and atmospheric urban settings",
    },
    "osamu_tezuka": {
        "label": "Osamu Tezuka",
        "category": "comics",
        "aliases": ["fluid linework", "emotive eyes"],
        "descriptor": "fluid expressive linework with large emotive eyes, dynamic action sequences, clean character design with detailed background rendering",
    },
    "bill_watterson": {
        "label": "Bill Watterson",
        "category": "comics",
        "aliases": ["watercolour comics", "natural palette"],
        "descriptor": "loose expressive watercolour with bold ink outlines, vibrant natural palette, dynamic figure movement and atmospheric landscape rendering",
    },
    "chris_ware": {
        "label": "Chris Ware",
        "category": "comics",
        "aliases": ["mechanical precision", "retro design"],
        "descriptor": "precise mechanical linework with flat colour fills, intricate panel layouts, retro graphic design aesthetic with obsessive decorative detail",
    },
    "art_spiegelman": {
        "label": "Art Spiegelman",
        "category": "comics",
        "aliases": ["expressionist ink", "high contrast"],
        "descriptor": "raw expressionist ink drawing with heavy black areas, rough hatching texture, stark high-contrast rendering with emotional directness",
    },
    "daniel_clowes": {
        "label": "Daniel Clowes",
        "category": "comics",
        "aliases": ["clean linework", "deadpan expression"],
        "descriptor": "clean precise linework with flat colour areas, retro graphic design aesthetic, deadpan character expression and meticulous period detail",
    },
    "frank_miller": {
        "label": "Frank Miller",
        "category": "comics",
        "aliases": ["high contrast", "spotlight noir"],
        "descriptor": "high-contrast black and white ink work with dramatic spotlighting, heavy black shadows, stylized figure poses and graphic composition",
    },
    "todd_mcfarlane": {
        "label": "Todd McFarlane",
        "category": "comics",
        "aliases": ["extreme poses", "organic linework"],
        "descriptor": "extreme dynamic poses with flowing organic linework, dense crosshatching texture, exaggerated anatomy and elaborate costume detail",
    },
    "jim_lee": {
        "label": "Jim Lee",
        "category": "comics",
        "aliases": ["detailed ink", "dynamic action"],
        "descriptor": "detailed precise ink linework with fine crosshatching, dynamic action poses, polished rendering with strong value contrast and atmospheric depth",
    },
    "mike_mignola": {
        "label": "Mike Mignola",
        "category": "comics",
        "aliases": ["heavy black", "gothic atmosphere"],
        "descriptor": "heavy black ink masses with minimal mid-tone, angular geometric figure design, gothic atmosphere with occult symbolism and stark composition",
    },
    "craig_thompson": {
        "label": "Craig Thompson",
        "category": "comics",
        "aliases": ["delicate ink", "intimate character"],
        "descriptor": "delicate ink linework with watercolour wash, intimate character studies, detailed architectural and landscape rendering with emotional directness",
    },

    # --- Digital Art ---
    "android_jones": {
        "label": "Android Jones",
        "category": "digital",
        "aliases": ["psychedelic digital", "neon palette"],
        "descriptor": "psychedelic digital painting with vibrant neon colour palettes, fluid organic forms, luminous glowing effects and surreal biomorphic imagery",
    },
    "gmunk": {
        "label": "GMUNK",
        "category": "digital",
        "aliases": ["geometric design", "bold typography"],
        "descriptor": "clean geometric digital design with bold typography, high-contrast colour schemes, futuristic UI elements and precision vector graphics",
    },
    "ash_thorp": {
        "label": "Ash Thorp",
        "category": "digital",
        "aliases": ["interface design", "neon accent"],
        "descriptor": "sleek futuristic interface design with dark backgrounds, glowing neon accent lines, technical blueprint aesthetic and cinematic HUD elements",
    },
    "sparth": {
        "label": "Sparth",
        "category": "digital",
        "aliases": ["sci-fi concept", "volumetric lighting"],
        "descriptor": "atmospheric sci-fi concept art with volumetric lighting, industrial mechanical design, moody colour palettes and epic scale environments",
    },
    "aaron_griffin": {
        "label": "Aaron Griffin",
        "category": "digital",
        "aliases": ["atmospheric perspective", "dramatic lighting"],
        "descriptor": "detailed digital painting with rich atmospheric perspective, dramatic lighting effects, epic fantasy and sci-fi environments with strong narrative",
    },
    "james_gilleard": {
        "label": "James Gilleard",
        "category": "digital",
        "aliases": ["vibrant colour", "stylized character"],
        "descriptor": "vibrant colour palette with strong graphic composition, stylized character design, dynamic poses and clean digital rendering",
    },
    "wlop": {
        "label": "WLOP",
        "category": "digital",
        "aliases": ["ethereal lighting", "romantic fantasy"],
        "descriptor": "ethereal digital painting with soft luminous lighting, flowing fabric and hair rendering, romantic fantasy aesthetic with delicate colour transitions",
    },
    "lois_van_baarle": {
        "label": "Lois van Baarle",
        "category": "digital",
        "aliases": ["vector character", "smooth gradients"],
        "descriptor": "clean vector-style character design with smooth colour gradients, expressive pose and gesture, modern illustration aesthetic with vibrant palette",
    },
    "ross_tran": {
        "label": "Ross Tran",
        "category": "digital",
        "aliases": ["bold colour", "graphic impact"],
        "descriptor": "dynamic digital painting with bold colour choices, dramatic lighting and atmosphere, stylized character design with strong graphic impact",
    },
}
