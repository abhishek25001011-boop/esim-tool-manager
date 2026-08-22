"""Read-only environment and dependency health checks for managed tools."""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from manager.installer import Installer
from manager.config_manager import ConfigurationManager
from manager.tool_registry import ToolRegistry
from manager.version_manager import VersionCheckResult, VersionManager, format_version


class HealthStatus(str, Enum):
    """Severity levels shown by the system health report."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(frozen=True)
class HealthCheck:
    """One human-readable, non-mutating environment check."""

    label: str
    status: HealthStatus
    message: str


@dataclass(frozen=True)
class HealthReport:
    """A complete snapshot of host, package-manager, and tool readiness."""

    checks: tuple[HealthCheck, ...]


@dataclass(frozen=True)
class ReadinessReport:
    """Readiness assessment derived from the health report and its failures."""

    level: str
    message: str
    recommendations: tuple[str, ...]
    health: HealthReport


class HealthChecker:
    """Build a reusable read-only health report from existing manager services."""

    def __init__(
        self,
        registry: ToolRegistry,
        version_manager: VersionManager,
        installer: Installer,
        configuration: ConfigurationManager | None = None,
        which: Callable[[str], str | None] = shutil.which,
        python_version: Callable[[], str] = platform.python_version,
    ) -> None:
        self._registry = registry
        self._version_manager = version_manager
        self._installer = installer
        self._configuration = configuration or ConfigurationManager(registry)
        self._which = which
        self._python_version = python_version

    def check(self) -> HealthReport:
        """Inspect the environment without starting package-manager commands."""
        system = self._installer.system()
        checks = [
            HealthCheck("Operating system", HealthStatus.PASS, system),
            HealthCheck("Python", HealthStatus.PASS, self._python_version()),
            self._configuration_check(),
            self._package_manager_check(system),
        ]
        checks.extend(self._tool_check(tool.identifier) for tool in self._registry.all())
        return HealthReport(tuple(checks))

    def readiness(self) -> ReadinessReport:
        """Summarize current health with actionable, truthful readiness advice."""
        health = self.check()
        failed = [check for check in health.checks if check.status is HealthStatus.FAIL]
        warnings = [check for check in health.checks if check.status is HealthStatus.WARNING]
        if failed:
            level = "NOT READY"
            message = "One or more required environment checks failed."
        elif warnings:
            level = "WARNING"
            message = "The environment is usable with attention to the listed warnings."
        else:
            level = "READY"
            message = "All managed environment checks passed."
        recommendations = tuple(check.message for check in (*failed, *warnings))
        return ReadinessReport(level, message, recommendations, health)

    def _configuration_check(self) -> HealthCheck:
        """Include optional configuration validity in the shared health report."""
        status = self._configuration.status()
        level = HealthStatus.PASS if status.valid else HealthStatus.FAIL
        return HealthCheck("Configuration", level, status.message)

    def _package_manager_check(self, system: str) -> HealthCheck:
        """Report required package-manager and safe privilege readiness."""
        if system == "Linux":
            if not self._which("apt"):
                return HealthCheck("apt", HealthStatus.FAIL, "apt was not found on PATH.")
            if self._installer.apt_command("--version") is None:
                return HealthCheck(
                    "apt",
                    HealthStatus.WARNING,
                    "apt is available, but root access or sudo is unavailable for package actions.",
                )
            return HealthCheck("apt", HealthStatus.PASS, "apt is available for package actions.")
        if system == "Windows":
            if self._which("choco"):
                return HealthCheck("Chocolatey", HealthStatus.PASS, "Chocolatey is available on PATH.")
            return HealthCheck("Chocolatey", HealthStatus.FAIL, "Chocolatey (choco) was not found on PATH.")
        return HealthCheck(
            "Package manager",
            HealthStatus.WARNING,
            f"No package-manager integration is configured for {system}.",
        )

    def _tool_check(self, identifier: str) -> HealthCheck:
        """Translate an existing real version check into health-report status."""
        path_validation = self._configuration.validate_path(identifier)
        if not path_validation.valid:
            return HealthCheck(self._registry.get(identifier).name, HealthStatus.FAIL, path_validation.message)
        result: VersionCheckResult = self._version_manager.check(
            self._registry.get(identifier), path_validation.configured_path
        )
        if not result.installed:
            return HealthCheck(result.tool.name, HealthStatus.WARNING, result.message)
        if result.version is None:
            return HealthCheck(result.tool.name, HealthStatus.WARNING, result.message)
        return HealthCheck(
            result.tool.name,
            HealthStatus.PASS,
            f"{path_validation.message} Executable available; version {format_version(result.version)} detected.",
        )
