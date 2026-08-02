"""Model family auto-detection for artist name handling.

Each family entry maps a model filename substring to a default
``name_handling`` mode. The Artist node uses this to auto-select
whether to emit artist names, descriptors, or both. If a model is
not in this map, the default ``"name_descriptor"`` still works -
the name is simply redundant on recaption-lineage models rather
than broken.

This file is deliberately small: ~30 lines. It is a convenience,
not a rule engine. If it goes stale the default degrades to
"slightly redundant" rather than "wrong."
"""

#: Model family → default name_handling mode for the Artist node.
FAMILY_MAP: dict[str, str] = {
    # Booru-lineage: artist names are strong steering signals.
    "chroma":         "name_descriptor",
    "sd15":           "name_descriptor",
    "sdxl":           "name_descriptor",
    "pony":           "name_descriptor",
    "illustrious":    "name_descriptor",
    "noobai":         "name_descriptor",

    # Recaption-lineage: artist names were stripped by VLM captioners,
    # so the descriptor does all the work. Emitting just the name is
    # the least-wrong default - it avoids the "Rembrandt" token polluting
    # the prompt on a model that was never trained on it.
    "flux":           "descriptor_only",
    "flux2":          "descriptor_only",
    "zimage":         "descriptor_only",
    "krea":           "descriptor_only",
    "ideogram":       "descriptor_only",
    "sd35":           "descriptor_only",
    "qwen_image":     "descriptor_only",
}


def detect_family(model_path: str) -> str:
    """Return the best-guess family name for a model file path.

    Returns the empty string if no family matches.
    """
    lowered = model_path.lower()
    for family in FAMILY_MAP:
        if family in lowered:
            return family
    return ""


def default_name_handling(model_path: str) -> str:
    """Return the recommended ``name_handling`` mode for *model_path*.

    Falls back to ``"name_descriptor"`` when the model is unrecognised.
    """
    family = detect_family(model_path)
    return FAMILY_MAP.get(family, "name_descriptor")
