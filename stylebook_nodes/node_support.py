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


def show_readout(unique_id, prompt: str, warnings: list[str] | None = None) -> None:
    """Display the resolved prompt on the node face.

    A prompt-composition pack whose output you cannot see without wiring
    a separate preview node is guessing, so every node shows what it
    actually produced. Warnings win the space when there are any, because
    a warning explains why the prompt is not what you expected.

    Failure here is never allowed to break execution: the readout is a
    convenience, and the node's real output is its return value.
    """
    if PromptServer is None or not unique_id:
        return
    try:
        if warnings:
            text = " | ".join(warnings)
        elif prompt:
            text = prompt
        else:
            text = "(no style applied yet)"
        if len(text) > READOUT_LIMIT:
            text = text[:READOUT_LIMIT - 3].rstrip() + "..."
        PromptServer.instance.send_progress_text(text, unique_id)
    except Exception as error:  # noqa: BLE001 - never break a render over this
        print(f"[Stylebook] could not show the node readout: {error}")
