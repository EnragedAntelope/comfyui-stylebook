"""Shared helpers for the node classes.

Kept apart from ``stylebook_core`` so the engine stays free of any
ComfyUI import and remains testable on a runner without ComfyUI.
"""

from __future__ import annotations

try:
    from server import PromptServer  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - no ComfyUI in the test environment
    PromptServer = None  # type: ignore[assignment]

#: Longest readout shown on the node face. Past this the text stops being
#: glanceable and the node grows enough to shove the graph around.
READOUT_LIMIT = 300


def report(warnings: list[str]) -> None:
    """Print engine warnings to the ComfyUI console."""
    for warning in warnings:
        print(f"[Stylebook] {warning}")


def show_readout(
    unique_id,
    summary: str,
    detail: str = "",
    warnings: list[str] | None = None,
) -> None:
    """Display resolved output on the node face, as up to two lines.

    A prompt-composition pack whose output you cannot see without wiring a
    separate preview node is guessing, so every node shows what it actually
    produced. ``summary`` is a short line naming what this node resolved
    (see ``stylebook_core.resolved_summary``) -- short by construction, so
    it is never the thing that gets truncated. ``detail`` is further text
    (see ``stylebook_core.readout_detail``); Sheet passes only ``summary``,
    since its own summary already is the whole readout.

    Warnings win the whole space when there are any, because a warning
    explains why the output is not what was expected.

    Failure here is never allowed to break execution: the readout is a
    convenience, and the node's real output is its return value.
    """
    if PromptServer is None or not unique_id:
        return
    try:
        if warnings:
            text = " | ".join(warnings)
        elif summary and detail:
            text = f"{summary}\n{detail}"
        elif summary:
            text = summary
        else:
            text = "(nothing applied yet)"
        if len(text) > READOUT_LIMIT:
            # Truncate from the tail, so the short summary line -- and the
            # start of detail, which is where the user's own subject used
            # to eat the whole budget -- always survive intact.
            text = text[:READOUT_LIMIT - 1].rstrip() + "…"
        PromptServer.instance.send_progress_text(text, unique_id)
    except Exception as error:  # noqa: BLE001 - never break a render over this
        print(f"[Stylebook] could not show the node readout: {error}")


def send_resolved_event(
    unique_id,
    prompt: str,
    *,
    style: str | None = None,
    artist: str | None = None,
    modifier: str | None = None,
    axis: str | None = None,
    cycle_pool_size: int | None = None,
) -> None:
    """Tell the frontend what this node resolved, for Copy and Pin.

    ``prompt`` is the full, untruncated text -- what "Copy resolved prompt"
    puts on the clipboard, since the node-face readout above is capped and
    a copy button that copies a "..." is not the point of one. ``style``/
    ``artist``/``modifier``/``axis`` are this node's own pick, whichever of
    them apply, and are what "Pin this pick" writes back into this node's
    own widgets; Blend and Sheet never set any of the four, since neither
    has a single pick a Pin menu item could write back to a widget.

    Same never-break-a-render contract as show_readout.
    """
    if PromptServer is None or not unique_id:
        return
    try:
        PromptServer.instance.send_sync("stylebook.resolved", {
            "node_id": unique_id,
            "prompt": prompt,
            "style": style,
            "artist": artist,
            "modifier": modifier,
            "axis": axis,
            "cycle_pool_size": cycle_pool_size,
        })
    except Exception as error:  # noqa: BLE001 - never break a render over this
        print(f"[Stylebook] could not send the resolved event: {error}")
