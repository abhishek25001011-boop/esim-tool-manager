"""Platform-aware, explicitly invoked installation command handling."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

from manager.logger import get_logger
from manager.tool_registry import ToolMetadata


@dataclass(frozen=True)
class CommandResult:
    """Result of a requested package manager command."""

    success: bool
    message: str


class Installer:
    """Builds and executes install commands only after the CLI has confirmed them."""

    def __init__(self) -> None:
        self._logger = get_logger("installer")

    @staticmethod
    def system() -> str:
        """Return the running operating-system name."""
        return platform.system()

    def command_for(self, tool: ToolMetadata) -> tuple[str, ...] | None:
        """Return an available package-manager command, or None if unsupported."""
        system = self.system()
        if system not in tool.supported_systems:
            return None
        if system == "Linux" and tool.apt_package:
            return self.apt_command("install", "-y", tool.apt_package)
        if system == "Windows" and tool.choco_package and shutil.which("choco"):
            return ("choco", "install", "-y", tool.choco_package)
        return None

    @staticmethod
    def apt_command(*arguments: str) -> tuple[str, ...] | None:
        """Build an apt command, adding sudo only when it is available and needed."""
        if not shutil.which("apt"):
            return None
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return ("apt", *arguments)
        if shutil.which("sudo"):
            return ("sudo", "apt", *arguments)
        return None

    def execute(self, command: tuple[str, ...]) -> CommandResult:
        """Execute a previously confirmed command and accurately report its outcome."""
        try:
            completed = subprocess.run(command, check=False, text=True, capture_output=True)
        except PermissionError:
            message = "Permission denied. Try an elevated terminal where appropriate."
            self._logger.error("Package command permission error: %s", command)
            return CommandResult(False, message)
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Could not start package manager: {exc}"
            self._logger.error("%s", message)
            return CommandResult(False, message)
        if completed.returncode == 0:
            self._logger.info("Package command succeeded: %s", command)
            return CommandResult(True, "Command completed successfully.")
        detail = (completed.stderr or completed.stdout).strip()
        self._logger.error("Package command failed (%s): %s", completed.returncode, detail)
        return CommandResult(False, f"Command failed with code {completed.returncode}: {detail or 'no output'}")
