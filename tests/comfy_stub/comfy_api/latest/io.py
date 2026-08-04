"""A record-only stand-in for ``comfy_api.latest.io``, used only when the
real package is not importable (i.e. this process has no ComfyUI install).

This is what lets ``NodeSchemaTests`` (in ``tests/test_schemas.py``) run in
CI at all: without it, every ``StylebookStyle``/``StylebookArtist``/etc.
class body is skipped at import time by this pack's own
``try: from comfy_api.latest import io / except ImportError`` guard, and the
schema assertions have never once executed on a runner.

**This must never become the only thing those assertions see.** Registration
happens in ``tests/__init__.py``, which imports the *real* package first and
falls back to this one only on ``ImportError`` — so on a machine with
ComfyUI installed (this repo's own dev machine included), the schema tests
run against the genuine API, and this stub exists purely to cover the gap on
a runner that has neither ComfyUI nor a full V3 API implementation.

Scope is deliberately narrow: only the surface this pack actually calls,
confirmed by grepping every ``io.*`` construction across
``stylebook_nodes/stylebook_*.py``. It stores exactly the attributes those
call sites and the schema tests read (``id``, ``display_name``, ``default``,
``options``, ``tooltip``, ``optional``) and does nothing else — no
serialization, no execution-time ``hidden`` resolution, because schema
construction is all these tests need.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NumberDisplay(str, Enum):
    number = "number"
    slider = "slider"


class Hidden(str, Enum):
    unique_id = "UNIQUE_ID"
    prompt = "PROMPT"
    extra_pnginfo = "EXTRA_PNGINFO"


class Input:
    """Base for every ``*.Input`` below: id/display/optional/tooltip only.

    Deliberately carries no ``default`` -- matching the real API, where the
    base ``Input`` (what a socket-only type like ``Custom`` extends) has no
    ``default`` attribute at all, and only ``WidgetInput`` adds one. That
    structural gap is what lets ``tests/test_schemas.py`` tell a real widget
    apart from a link-only socket such as ``style_chain`` via
    ``hasattr(inp, "default")``, without hand-listing socket names.
    """

    def __init__(
        self,
        id: str,
        display_name: str | None = None,
        optional: bool = False,
        tooltip: str | None = None,
        **extra: Any,
    ) -> None:
        self.id = id
        self.display_name = display_name
        self.optional = optional
        self.tooltip = tooltip
        for key, value in extra.items():
            setattr(self, key, value)


class WidgetInput(Input):
    """Base for an Input that has a widget on the node face, and so
    contributes an entry to a saved workflow's ``widgets_values``."""

    def __init__(
        self,
        id: str,
        display_name: str | None = None,
        optional: bool = False,
        tooltip: str | None = None,
        default: Any = None,
        **extra: Any,
    ) -> None:
        super().__init__(id, display_name, optional, tooltip, **extra)
        self.default = default


class Output:
    """Base for every ``*.Output`` below."""

    def __init__(
        self,
        id: str | None = None,
        display_name: str | None = None,
        tooltip: str | None = None,
        is_output_list: bool = False,
        **extra: Any,
    ) -> None:
        self.id = id
        self.display_name = display_name if display_name else id
        self.tooltip = tooltip
        self.is_output_list = is_output_list
        for key, value in extra.items():
            setattr(self, key, value)


class _ComboOptions:
    """Holds a combo's option list under ``.values``, like the real widget."""

    def __init__(self, values: list[str] | None) -> None:
        self.values = values if values is not None else []


class Int:
    class Input(WidgetInput):
        def __init__(
            self,
            id: str,
            display_name: str | None = None,
            default: int | None = None,
            min: int | None = None,
            max: int | None = None,
            control_after_generate: bool | None = None,
            tooltip: str | None = None,
            optional: bool = False,
            **extra: Any,
        ) -> None:
            super().__init__(id, display_name, optional, tooltip, default, **extra)
            self.min = min
            self.max = max
            self.control_after_generate = control_after_generate


class Float:
    class Input(WidgetInput):
        def __init__(
            self,
            id: str,
            display_name: str | None = None,
            default: float | None = None,
            min: float | None = None,
            max: float | None = None,
            step: float | None = None,
            display_mode: NumberDisplay | None = None,
            tooltip: str | None = None,
            optional: bool = False,
            **extra: Any,
        ) -> None:
            super().__init__(id, display_name, optional, tooltip, default, **extra)
            self.min = min
            self.max = max
            self.step = step
            self.display_mode = display_mode


class String:
    class Input(WidgetInput):
        def __init__(
            self,
            id: str,
            display_name: str | None = None,
            multiline: bool = False,
            optional: bool = False,
            default: str | None = None,
            tooltip: str | None = None,
            **extra: Any,
        ) -> None:
            super().__init__(id, display_name, optional, tooltip, default, **extra)
            self.multiline = multiline

    class Output(Output):
        pass


class Combo:
    class Input(WidgetInput):
        def __init__(
            self,
            id: str,
            options: list[str] | None = None,
            display_name: str | None = None,
            default: str | None = None,
            control_after_generate: bool | None = None,
            tooltip: str | None = None,
            optional: bool = False,
            **extra: Any,
        ) -> None:
            super().__init__(id, display_name, optional, tooltip, default, **extra)
            # Real ComfyUI stores the raw list here; the options-object shape
            # (``.values``) shows up on the *frontend* widget, not this
            # schema Input. Node schema tests read the list directly.
            self.options = options if options is not None else []
            self.control_after_generate = control_after_generate


def Custom(io_type: str) -> type:
    """Mirrors the real ``io.Custom(io_type)``: a fresh Input/Output pair
    bound to one socket type string, e.g. ``STYLEBOOK_CHAIN``."""

    class _CustomInput(Input):
        def __init__(
            self,
            id: str,
            display_name: str | None = None,
            optional: bool = False,
            tooltip: str | None = None,
            **extra: Any,
        ) -> None:
            super().__init__(id, display_name, optional, tooltip, **extra)
            self.io_type = io_type

    class _CustomOutput(Output):
        def __init__(
            self,
            display_name: str | None = None,
            tooltip: str | None = None,
            is_output_list: bool = False,
            **extra: Any,
        ) -> None:
            super().__init__(None, display_name, tooltip, is_output_list, **extra)
            self.io_type = io_type

    class _CustomType:
        Input = _CustomInput
        Output = _CustomOutput

    return _CustomType


@dataclass
class Schema:
    """Definition of a V3 node's inputs/outputs. Subset of the real fields."""

    node_id: str
    display_name: str | None = None
    category: str = "sd"
    inputs: list[Input] = field(default_factory=list)
    outputs: list[Output] = field(default_factory=list)
    hidden: list[Hidden] = field(default_factory=list)
    description: str = ""


class ComfyNode:
    """Common base every Stylebook node schema class inherits from.

    No execution-time behaviour: these tests build and inspect
    ``define_schema()`` output, never call ``execute()``, which is where the
    real ComfyNode's ``hidden`` resolution and prompt-queue plumbing live.
    """


class NodeOutput:
    """Positional output bundle. Storage only; never inspected by these tests."""

    def __init__(self, *args: Any) -> None:
        self.args = args
