"""Read-only unit tests for environment and dependency health reporting."""

import unittest
from unittest.mock import Mock

from manager.health_checker import HealthChecker, HealthStatus
from manager.installer import Installer
from manager.tool_registry import ToolRegistry
from manager.version_manager import VersionCheckResult


class HealthCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.installer = Mock(spec=Installer)
        self.installer.system.return_value = "Linux"
        self.installer.apt_command.return_value = ("sudo", "apt", "--version")
        self.version_manager = Mock()

    def test_report_includes_host_package_manager_and_real_tool_results(self) -> None:
        ngspice = self.registry.get("ngspice")
        kicad = self.registry.get("kicad")
        self.version_manager.check.side_effect = (
            VersionCheckResult(ngspice, True, (42,), message="Detected version 42."),
            VersionCheckResult(kicad, False, message="Executable 'kicad-cli' was not found on PATH."),
        )
        checker = HealthChecker(
            self.registry,
            self.version_manager,
            self.installer,
            which=lambda name: "/usr/bin/apt" if name == "apt" else None,
            python_version=lambda: "3.13.0",
        )

        report = checker.check()

        self.assertEqual([check.status for check in report.checks], [
            HealthStatus.PASS,
            HealthStatus.PASS,
            HealthStatus.PASS,
            HealthStatus.PASS,
            HealthStatus.PASS,
            HealthStatus.WARNING,
        ])
        self.assertIn("version 42", report.checks[4].message)
        self.assertIn("not found", report.checks[5].message)
        self.installer.apt_command.assert_called_once_with("--version")

    def test_linux_reports_missing_apt_without_running_commands(self) -> None:
        checker = HealthChecker(
            self.registry,
            self.version_manager,
            self.installer,
            which=lambda _name: None,
            python_version=lambda: "3.13.0",
        )
        self.version_manager.check.return_value = VersionCheckResult(
            self.registry.get("ngspice"), False, message="not found"
        )

        report = checker.check()

        self.assertEqual(report.checks[3].status, HealthStatus.FAIL)
        self.assertIn("apt was not found", report.checks[3].message)
        self.installer.apt_command.assert_not_called()

    def test_windows_reports_chocolatey_status(self) -> None:
        self.installer.system.return_value = "Windows"
        self.version_manager.check.return_value = VersionCheckResult(
            self.registry.get("ngspice"), False, message="not found"
        )
        checker = HealthChecker(
            self.registry,
            self.version_manager,
            self.installer,
            which=lambda name: "C:/choco.exe" if name == "choco" else None,
            python_version=lambda: "3.13.0",
        )

        report = checker.check()

        self.assertEqual(report.checks[3].label, "Chocolatey")
        self.assertEqual(report.checks[3].status, HealthStatus.PASS)
        self.installer.apt_command.assert_not_called()

    def test_readiness_is_not_ready_when_a_required_check_fails(self) -> None:
        self.version_manager.check.return_value = VersionCheckResult(
            self.registry.get("ngspice"), False, message="not found"
        )
        checker = HealthChecker(
            self.registry,
            self.version_manager,
            self.installer,
            which=lambda _name: None,
            python_version=lambda: "3.13.0",
        )

        readiness = checker.readiness()

        self.assertEqual(readiness.level, "NOT READY")
        self.assertTrue(any("apt was not found" in item for item in readiness.recommendations))


if __name__ == "__main__":
    unittest.main()
