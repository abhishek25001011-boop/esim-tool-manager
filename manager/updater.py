"""Repository-status checks and update commands for supported package managers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from manager.installer import CommandResult, Installer
from manager.logger import get_logger
from manager.tool_registry import ToolMetadata


@dataclass(frozen=True)
class UpdateStatus:
    """Package-manager update information without inventing upstream versions."""

    update_available: bool
    message: str


class Updater:
    """Uses the installed package manager's current repository status."""

    def __init__(self, installer: Installer) -> None:
        self._installer = installer
        self._logger = get_logger("updater")

    def check(self, tool: ToolMetadata) -> UpdateStatus:
        """Check update status without claiming an exact latest version."""
        system = self._installer.system()
        if system not in tool.supported_systems:
            message = f"{tool.name} is not supported on {system}."
            self._logger.warning("%s update check: %s", tool.identifier, message)
            return UpdateStatus(False, message)
        if system == "Linux" and tool.apt_package and shutil.which("apt"):
            command = ("apt", "list", "--upgradable")
            package = tool.apt_package
        elif system == "Windows" and tool.choco_package and shutil.which("choco"):
            command = ("choco", "outdated", "--limit-output")
            package = tool.choco_package
        else:
            message = "No supported package manager is available for update checking."
            self._logger.warning("%s update check: %s", tool.identifier, message)
            return UpdateStatus(False, message)
        try:
            completed = subprocess.run(command, check=False, text=True, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Could not check package-manager status: {exc}"
            self._logger.error("%s update check: %s", tool.identifier, message)
            return UpdateStatus(False, message)
        if completed.returncode != 0:
            message = f"Package-manager status check failed: {(completed.stderr or '').strip()}"
            self._logger.error("%s update check: %s", tool.identifier, message)
            return UpdateStatus(False, message)
        lines = completed.stdout.lower().splitlines()
        available = any(line.startswith(package.lower() + "/") or line.startswith(package.lower() + "|") for line in lines)
        message = (
            "An update is available according to the package manager's current repository status."
            if available
            else "No update is listed by the package manager's current repository status."
        )
        self._logger.info("%s update check: %s", tool.identifier, message)
        return UpdateStatus(available, message)

    def command_for(self, tool: ToolMetadata) -> tuple[str, ...] | None:
        """Return a package-manager update command for a registered tool."""
        system = self._installer.system()
        if system not in tool.supported_systems:
            return None
        if system == "Linux" and tool.apt_package:
            return self._installer.apt_command("install", "--only-upgrade", "-y", tool.apt_package)
        if system == "Windows" and tool.choco_package and shutil.which("choco"):
            return ("choco", "upgrade", "-y", tool.choco_package)
        return None

    def update(self, tool: ToolMetadata) -> CommandResult:
        """Run the update command after confirmation has been obtained by the caller."""
        command = self.command_for(tool)
        if command is None:
            return CommandResult(False, "No supported package manager is available for this update.")
        return self._installer.execute(command)
