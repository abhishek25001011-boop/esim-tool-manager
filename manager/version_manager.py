"""Real executable discovery, version parsing, and safe comparison helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from manager.logger import get_logger
from manager.tool_registry import ToolMetadata

Version = tuple[int, ...]
_VERSION_PATTERN = re.compile(r"(?<!\d)(\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?|\d+)(?!\d)")


@dataclass(frozen=True)
class VersionCheckResult:
    """The outcome of checking one executable without assuming a version."""

    tool: ToolMetadata
    installed: bool
    version: Version | None = None
    raw_output: str = ""
    message: str = ""


def parse_version(text: str) -> Version | None:
    """Extract a numeric version from arbitrary command output, if present."""
    match = _VERSION_PATTERN.search(text)
    if not match:
        return None
    numeric_part = match.group(1).split("-", 1)[0].split("+", 1)[0]
    try:
        return tuple(int(part) for part in numeric_part.split("."))
    except ValueError:
        return None


def format_version(version: Version | None) -> str:
    """Render a parsed version for CLI output."""
    return ".".join(map(str, version)) if version else "unknown"


def compare_versions(left: Version, right: Version) -> int:
    """Compare numeric version tuples, treating absent trailing parts as zero."""
    length = max(len(left), len(right))
    padded_left = left + (0,) * (length - len(left))
    padded_right = right + (0,) * (length - len(right))
    return (padded_left > padded_right) - (padded_left < padded_right)


class VersionManager:
    """Checks installed tool versions using the actual tool executable."""

    def __init__(
        self,
        which: Callable[[str], str | None] = shutil.which,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._which = which
        self._runner = runner
        self._logger = get_logger("version")

    def check(self, tool: ToolMetadata) -> VersionCheckResult:
        """Find the executable, run its version command, and parse its output."""
        path = self._which(tool.executable)
        if not path:
            message = f"Executable '{tool.executable}' was not found on PATH."
            self._logger.info("%s: %s", tool.identifier, message)
            return VersionCheckResult(tool, False, message=message)
        try:
            completed = self._runner(
                (path, *tool.version_command[1:]), capture_output=True, text=True, check=False, timeout=15
            )
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Could not run version command: {exc}"
            self._logger.error("%s: %s", tool.identifier, message)
            return VersionCheckResult(tool, True, message=message)
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
        if completed.returncode != 0:
            message = f"Version command exited with code {completed.returncode}."
            version = None
        else:
            version = parse_version(output)
        if completed.returncode == 0 and version is None:
            message = "Executable was found, but its version output could not be parsed."
        elif completed.returncode == 0:
            message = f"Detected version {format_version(version)}."
        self._logger.info("%s version check: %s", tool.identifier, message)
        return VersionCheckResult(tool, True, version, output, message)
