"""KiCad metadata definition used by the default tool registry."""

from manager.tool_registry import ToolMetadata


def metadata() -> ToolMetadata:
    """Return the metadata required to manage KiCad."""
    return ToolMetadata("kicad", "KiCad", "kicad-cli", ("kicad-cli", "version"), "kicad", "kicad")
