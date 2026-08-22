"""Safe project-local configuration for managed executable overrides."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from manager.tool_registry import ToolRegistry

DEFAULT_CONFIG_NAME = ".esim-tool-manager.json"


class ConfigurationError(ValueError):
    """Raised when a requested configuration change is invalid or cannot be saved."""


@dataclass(frozen=True)
class ConfigurationStatus:
    """State of the optional project-local configuration file."""

    valid: bool
    message: str


@dataclass(frozen=True)
class PathValidation:
    """Validation result for one configured executable path."""

    tool_id: str
    configured_path: str | None
    valid: bool
    message: str


class ConfigurationManager:
    """Read and safely update optional executable path overrides in JSON."""

    def __init__(self, registry: ToolRegistry, config_path: Path | None = None) -> None:
        self._registry = registry
        self.path = config_path or Path.cwd() / DEFAULT_CONFIG_NAME

    def status(self) -> ConfigurationStatus:
        """Report file availability and JSON/schema validity without changing it."""
        _, error = self._read()
        if error:
            return ConfigurationStatus(False, error)
        if not self.path.exists():
            return ConfigurationStatus(True, f"No configuration file at {self.path}; using PATH discovery.")
        return ConfigurationStatus(True, f"Configuration loaded from {self.path}.")

    def configured_path(self, tool_id: str) -> str | None:
        """Return the raw configured override for a known tool, if present and valid JSON."""
        data, error = self._read()
        if error:
            return None
        value = data["tool_paths"].get(tool_id.lower())
        return value if isinstance(value, str) else None

    def validate_path(self, tool_id: str) -> PathValidation:
        """Validate one configured path; absence means normal PATH lookup will be used."""
        tool = self._registry.get(tool_id)
        if tool is None:
            return PathValidation(tool_id, None, False, f"Unknown managed tool: {tool_id}")
        data, error = self._read()
        if error:
            return PathValidation(tool.identifier, None, False, error)
        configured = data["tool_paths"].get(tool.identifier)
        if configured is None:
            return PathValidation(tool.identifier, None, True, "No override configured; using PATH discovery.")
        if not isinstance(configured, str) or not configured.strip():
            return PathValidation(tool.identifier, None, False, "Configured executable path must be a non-empty string.")
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            return PathValidation(tool.identifier, configured, False, "Configured executable path does not exist or is not a file.")
        if os.name != "nt" and not os.access(candidate, os.X_OK):
            return PathValidation(tool.identifier, configured, False, "Configured executable path is not executable.")
        return PathValidation(tool.identifier, str(candidate), True, "Configured executable path is valid.")

    def set_path(self, tool_id: str, executable_path: str) -> None:
        """Save a validated executable override without touching the system PATH."""
        tool = self._registry.get(tool_id)
        if tool is None:
            raise ConfigurationError(f"Unknown managed tool: {tool_id}")
        candidate = Path(executable_path).expanduser()
        if not candidate.is_file():
            raise ConfigurationError("Path does not exist or is not a file.")
        if os.name != "nt" and not os.access(candidate, os.X_OK):
            raise ConfigurationError("Path is not executable.")
        data, error = self._read()
        if error and self.path.exists():
            raise ConfigurationError(error)
        data["tool_paths"][tool.identifier] = str(candidate)
        self._write(data)

    def clear_path(self, tool_id: str) -> None:
        """Remove an override so that future checks use normal PATH discovery."""
        tool = self._registry.get(tool_id)
        if tool is None:
            raise ConfigurationError(f"Unknown managed tool: {tool_id}")
        data, error = self._read()
        if error and self.path.exists():
            raise ConfigurationError(error)
        data["tool_paths"].pop(tool.identifier, None)
        self._write(data)

    def _read(self) -> tuple[dict[str, dict[str, str]], str | None]:
        """Load the strict, small JSON schema without leaking JSON exceptions."""
        empty: dict[str, dict[str, str]] = {"tool_paths": {}}
        if not self.path.exists():
            return empty, None
        try:
            with self.path.open("r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except (OSError, json.JSONDecodeError) as exc:
            return empty, f"Configuration could not be read: {exc}"
        if not isinstance(data, dict) or not isinstance(data.get("tool_paths", {}), dict):
            return empty, "Configuration must be a JSON object with a 'tool_paths' object."
        return {"tool_paths": data.get("tool_paths", {})}, None

    def _write(self, data: dict[str, dict[str, str]]) -> None:
        """Write only the project-local JSON file requested by the user."""
        try:
            with self.path.open("w", encoding="utf-8") as config_file:
                json.dump(data, config_file, indent=2, sort_keys=True)
                config_file.write("\n")
        except OSError as exc:
            raise ConfigurationError(f"Configuration could not be saved: {exc}") from exc
