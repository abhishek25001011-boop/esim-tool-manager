"""Ngspice metadata definition used by the default tool registry."""

from manager.tool_registry import ToolMetadata


def metadata() -> ToolMetadata:
    """Return the metadata required to manage Ngspice."""
    return ToolMetadata("ngspice", "Ngspice", "ngspice", ("ngspice", "--version"), "ngspice", "ngspice")
