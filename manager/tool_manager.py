"""High-level safe operations used by the command-line interface."""

from __future__ import annotations

from manager.installer import CommandResult, Installer
from manager.health_checker import HealthChecker, HealthReport
from manager.tool_registry import ToolMetadata, ToolRegistry
from manager.updater import UpdateStatus, Updater
from manager.version_manager import VersionCheckResult, VersionManager


class ToolManager:
    """Coordinate registry, version detection, installation, and updates."""

    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.installer = Installer()
        self.version_manager = VersionManager()
        self.updater = Updater(self.installer)
        self.health_checker = HealthChecker(self.registry, self.version_manager, self.installer)
        self.last_message = ""

    def list_tools(self) -> tuple[ToolMetadata, ...]:
        return self.registry.all()

    def health_check(self) -> HealthReport:
        """Return a read-only system and managed-tool readiness report."""
        return self.health_checker.check()

    def _tool(self, identifier: str) -> ToolMetadata | None:
        tool = self.registry.get(identifier)
        self.last_message = "" if tool else f"Unknown managed tool: {identifier}"
        return tool

    def check_version(self, identifier: str) -> VersionCheckResult:
        tool = self._tool(identifier)
        if tool is None:
            raise ValueError(self.last_message)
        return self.version_manager.check(tool)

    def install_command(self, identifier: str) -> tuple[str, ...] | None:
        tool = self._tool(identifier)
        if tool is None:
            return None
        command = self.installer.command_for(tool)
        if command is None:
            self.last_message = "Unsupported OS or required package manager is unavailable."
        return command

    def install(self, identifier: str, *, confirmed: bool = False) -> CommandResult:
        """Install a tool only when the caller has explicitly confirmed the action."""
        if not confirmed:
            return CommandResult(False, "Installation requires explicit confirmation.")
        command = self.install_command(identifier)
        if command is None:
            return CommandResult(False, self.last_message)
        return self.installer.execute(command)

    def check_update(self, identifier: str) -> UpdateStatus:
        tool = self._tool(identifier)
        if tool is None:
            return UpdateStatus(False, self.last_message)
        return self.updater.check(tool)

    def update_command(self, identifier: str) -> tuple[str, ...] | None:
        """Return the supported update command without executing it."""
        tool = self._tool(identifier)
        if tool is None:
            return None
        command = self.updater.command_for(tool)
        if command is None:
            self.last_message = "Unsupported OS or required package manager is unavailable for updates."
        return command

    def update(self, identifier: str, *, confirmed: bool = False) -> CommandResult:
        """Update a tool only when the caller has explicitly confirmed the action."""
        if not confirmed:
            return CommandResult(False, "Update requires explicit confirmation.")
        tool = self._tool(identifier)
        if tool is None:
            return CommandResult(False, self.last_message)
        return self.updater.update(tool)
