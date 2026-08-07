# Stylebook research notes

Living TODO list of borderline, uncertain, or unchecked art-movement / artist
candidates for future PRs. **Every addition to the pack must be verified
against the existing data before it lands** — the searches behind this list
were exhaustive; re-search before adding.

## How this list is organised

Each entry has:
- **Candidate** — what to add
- **Status** — what the prior search found (PRESENT-AS-ALIAS / ABSENT / UNVERIFIED)
- **Why it needs review** — what makes the addition non-trivial
- **Action** — concrete next step (verify, draft, defer)

Prior search scope: case-insensitive grep across the full repo
(`C:\github_projects\comfyui-stylebook\`) including `node_modules` (the only
hits there were the third-party `tldts` TLD parser containing "ukiyo" as a
substring — irrelevant). Grep is case-sensitive; patterns used case-class
brackets (`[Kk]ahlo`) where required.

The definitive inventory as of 0.5.0:
- **454 styles** across 12 categories (art_movements, painting, film_cinema,
  comics, anime_manga hold the movement-style entries)
- **679 artists** across 6 canonical categories, 47 section headers
- Generated truth lives in `js/stylebook_data.js` (`STYLE_COUNT`, `ARTIST_COUNT`)

## What 0.5.0 added (the diff that just landed, uncommitted)

**21 styles** added to `data/styles/art_movements.py`:

| Style id | Label |
|---|---|
| `cobra` | CoBrA |
| `naive_art` | Naïve Art |
| `op_art` | Op Art |
| `nabis` | Nabis |
| `suprematism` | Suprematism |
| `art_brut` | Art Brut |
| `constructivism` | Constructivism |
| `hudson_river_school` | Hudson River School |
| `luminism` | Luminism |
| `tonalism` | Tonalism |
| `ashcan_school` | Ashcan School |
| `harlem_renaissance` | Harlem Renaissance |
| `muralism` | Mexican Muralism |
| `intimism` | Intimism |
| `byzantine` | Byzantine / Icon Painting |
| `celtic_art` | Celtic / Insular Art |
| `mingei` | Mingei |
| `wiener_werkstatte` | Wiener Werkstätte |
| `arts_and_crafts` | Arts and Crafts Movement |
| `photorealism` | Photorealism |
| `hyperrealism` | Hyperrealism |

**20 artists** added to `data/artists.py` (all `category: fine-art`):

| Artist id | Label |
|---|---|
| `friedensreich_hundertwasser` | Friedensreich Hundertwasser |
| `nikolai_sapunov` | Nikolai Sapunov |
| `aleksandra_ekster` | Aleksandra Ekster |
| `beauford_delaney` | Beauford Delaney |
| `horace_pippin` | Horace Pippin |
| `cecil_collins` | Cecil Collins |
| `filippo_marinetti` | Filippo Tommaso Marinetti |
| `albert_pinkham_ryder` | Albert Pinkham Ryder |
| `friedrich_schroder_sonnenstern` | Friedrich Schröder-Sonnenstern |
| `charles_filiger` | Charles Filiger |
| `suzanne_valadon` | Suzanne Valadon |
| `sofonisba_anguissola` | Sofonisba Anguissola |
| `elisabeth_vigee_le_brun` | Élisabeth Vigée Le Brun |
| `marguerite_zorach` | Marguerite Zorach |
| `aaron_douglas` | Aaron Douglas |
| `archibald_motley` | Archibald J. Motley Jr. |
| `william_h_johnson` | William H. Johnson |
| `augusta_savage` | Augusta Savage |
| `elizabeth_catlett` | Elizabeth Catlett |
| `lois_mailou_jones` | Loïs Mailou Jones |

---

## Style candidates — borderline (movement-adjacent, not yet added)

These appear in the data only as artist-level aliases or single-descriptor
mentions. Each is a real movement but the call about whether to add it as a
first-class style is judgement, not a clear gap.

| Candidate | Status | Why it needs review | Action |
|---|---|---|---|
| `technicolor` (film_cinema.py) | PRESENT as borderline film-era style | It's a colour process, not a movement. Already there. | Skip — already in pack |
| `pictorialism` (photography movement) | UNVERIFIED — never searched | Late-19th-century photography movement, distinct from `daguerreotype` etc. | Search the repo; if absent, add as a style |
| `pinhole` / `platinum_palladium_print` (photography) | UNVERIFIED | Borderline movement vs. technique | Verify; only add if missing as a movement |
| `shojo_manga` / `shonen_manga` (anime_manga) | PRESENT as genre entries | Could argue these are movements rather than demographics | Decide policy; not a clear gap |
| `synthwave` / `vaporwave` (3D/digital) | UNVERIFIED | Modern design movements of the 2010s | Verify; if absent, decide whether to add |
| `camden_town_group` (British Post-Impressionism) | UNVERIFIED | Real early-20th-century British movement near Sickert | Search; add if absent |
| `stuckism` (British contemporary) | ABSENT | Real but very small / polemical movement | Decide whether it's worth a record |
| `art_concret` (geometric abstraction) | UNVERIFIED | Adjacent to De Stijl; overlap risk | Verify; check overlap with existing De Stijl / Bauhaus / Suprematism before adding |
| `deformalism` | UNVERIFIED | Niche mid-century movement | Search; add if absent |
| `spatialism` (Fontana) | UNVERIFIED | Italian post-war movement | Search; add if absent |
| `metaphysical_art` / `pittura_metafisica` (de Chirico, Carrà) | UNVERIFIED | Real 1910s–20s Italian movement | Search; add if absent |
| `decadent_movement` (Beardsley, Aestheticism) | UNVERIFIED | Late-19th-century British aesthetic movement | Search; add if absent |
| `nouveau_realism` (Yves Klein, Arman, Spoerri) | UNVERIFIED | 1960s Paris movement | Search; add if absent |
| `fluxus` (movement) | PRESENT only as artist aliases (Nam June Paik, Joseph Beuys) | Movement exists as a concept; whether to add as a style is a judgement call — Fluxus is process-based and visually hard to fix | Decide policy |
| `arte_povera` (movement) | PRESENT only as artist aliases (Pistoletto, Kounellis) + section header (3136) | Same as Fluxus — movement exists, but the visual style is hard to pin down | Decide policy |
| `pattern_and_decoration` (movement) | PRESENT only as artist alias (line 3076) | Same | Decide policy |
| `lyrical_abstraction` (movement) | PRESENT only as artist alias (Zao Wou-Ki, line 2004) | Same | Decide policy |
| `photo_secession` (Stieglitz's group) | PRESENT only as Stieglitz artist alias (2990) | Movement exists as a concept | Decide policy |
| `monochrome` (Yves Klein) | UNVERIFIED — could overlap with minimalism / suprematism | | Search; check overlap before adding |
| `orphic_cubism` (variant) | ABSENT | "Orphism" is in pack; the "Orphic Cubism" variant is absent (no standalone "orphic" word) | Decide whether to add as a variant or leave as alias |

## Style candidates — ABSENT (confirmed zero matches, deferred from 0.5.0)

(none currently — 0.5.0 picked up the major gaps; only borderline candidates remain)

## Artist candidates — ABSENT (confirmed zero matches, deferred from 0.5.0)

(none currently — 0.5.0 picked up the major gaps)

## Categories to verify (not yet searched)

These were not in the original wishlist. Each needs its own dedicated search
before adding anything:

- **19th-century academic painters** (Bouguereau, Cabanel, Gérôme, Alma-Tadema)
- **Sculptors** (Rodin, Brancusi, Henry Moore, Barbara Hepworth, Louise Bourgeois, Giacometti, Arnaldo Pomodoro)
- **Arte Povera / Zero artists** (Fontana, Klein, Manzoni, Pistoletto, Boetti — Pistoletto and Kounellis are in the pack, but Fontana / Klein / Manzoni / Boetti are not)
- **American moderns** (Wayne Thiebaud, Richard Diebenkorn, Philip Guston, Joan Mitchell, Grace Hartigan, Helen Frankenthaler — Frankenthaler is in the pack, the rest uncertain)
- **Kitsch / commercial / outsider** (Bob Ross, Thomas Kinkade, Hilo Chen, Charles Fazzino)
- **Scientific illustration** (Ernst Haeckel, Beatrix Potter)
- **Art Nouveau individual practitioners** (Alphonse Mucha, Gustav Klimt — Klimt is in the pack, but the style `art_nouveau` is in the pack; verify whether Mucha is an artist)
- **20th-century design figures** (Saul Bass, Milton Glaser, Paul Rand, Massimo Vignelli, Stefan Sagmeister)
- **Pre-Columbian / indigenous / non-Western** — the pack has a "Chinese Traditional and Modern" section; whether other traditions are covered needs review

## What to NOT do

The pack was specifically called out for never crediting LoRAs or any other
external source. Style and artist records stand on their own names and real-
world provenance, not on the discovery channel. If a candidate only exists
as a Civitai LoRA (e.g. the rejected Tkachenko / Bradhamel style from the
0.4.0 cycle), it does not enter this pack. The criterion is: would a museum,
gallery, or art history textbook recognise this name?
