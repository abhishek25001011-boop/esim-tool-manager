"""Metadata registry for tools managed by the application."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolMetadata:
    """Platform and command metadata needed to manage one tool."""

    identifier: str
    name: str
    executable: str
    version_command: tuple[str, ...]
    apt_package: str | None
    choco_package: str | None
    supported_systems: tuple[str, ...] = ("Linux", "Windows")


class ToolRegistry:
    """In-memory registry populated from independent, extensible tool definitions."""

    def __init__(self) -> None:
        # Imports are local to avoid a module-level circular import: individual tool
        # definitions use ToolMetadata from this module.
        from tools.kicad import metadata as kicad_metadata
        from tools.ngspice import metadata as ngspice_metadata

        definitions = (ngspice_metadata(), kicad_metadata())
        self._tools = {tool.identifier: tool for tool in definitions}

    def get(self, identifier: str) -> ToolMetadata | None:
        """Look up metadata by its stable lowercase identifier."""
        return self._tools.get(identifier.lower())

    def all(self) -> tuple[ToolMetadata, ...]:
        """Return every managed tool in registration order."""
        return tuple(self._tools.values())
