"""Tests that never call a real executable, installer, or package manager."""

import subprocess
import unittest
from unittest.mock import Mock, patch

from main import confirmed
from manager.installer import Installer
from manager.tool_registry import ToolMetadata
from manager.tool_manager import ToolManager
from manager.updater import Updater
from manager.version_manager import VersionManager, compare_versions, parse_version


class VersionUtilityTests(unittest.TestCase):
    def test_parse_common_tool_outputs(self) -> None:
        self.assertEqual(parse_version("ngspice-42"), (42,))
        self.assertEqual(parse_version("KiCad CLI version 8.0.1"), (8, 0, 1))
        self.assertIsNone(parse_version("version unavailable"))

    def test_compare_trailing_zeroes_safely(self) -> None:
        self.assertEqual(compare_versions((1, 2), (1, 2, 0)), 0)
        self.assertLess(compare_versions((1, 2, 3), (1, 3)), 0)
        self.assertGreater(compare_versions((10,), (9, 9)), 0)


class VersionManagerTests(unittest.TestCase):
    tool = ToolMetadata("demo", "Demo", "demo", ("demo", "--version"), None, None)

    def test_missing_executable_is_not_installed(self) -> None:
        manager = VersionManager(which=lambda _: None)
        result = manager.check(self.tool)
        self.assertFalse(result.installed)
        self.assertIn("not found", result.message)

    def test_detects_actual_runner_output(self) -> None:
        seen_command: tuple[str, ...] | None = None

        def fake_runner(*_args, **_kwargs):
            nonlocal seen_command
            seen_command = _args[0]
            return subprocess.CompletedProcess(["demo"], 0, "Demo 2.5.0", "")

        manager = VersionManager(which=lambda _: "/mock/demo", runner=fake_runner)
        result = manager.check(self.tool)
        self.assertTrue(result.installed)
        self.assertEqual(result.version, (2, 5, 0))
        self.assertEqual(seen_command, ("/mock/demo", "--version"))

    def test_invalid_version_output_does_not_crash(self) -> None:
        def fake_runner(*_args, **_kwargs):
            return subprocess.CompletedProcess(["demo"], 0, "unparseable", "")

        result = VersionManager(which=lambda _: "/mock/demo", runner=fake_runner).check(self.tool)
        self.assertTrue(result.installed)
        self.assertIsNone(result.version)

    def test_nonzero_version_command_does_not_report_a_version(self) -> None:
        def fake_runner(*_args, **_kwargs):
            return subprocess.CompletedProcess(["demo"], 1, "Demo 9.9", "failure")

        result = VersionManager(which=lambda _: "/mock/demo", runner=fake_runner).check(self.tool)
        self.assertIsNone(result.version)
        self.assertIn("code 1", result.message)


class ToolManagerSafetyTests(unittest.TestCase):
    def test_unknown_tool_never_produces_a_package_command(self) -> None:
        """Invalid input must stop before any install/update subprocess can run."""
        manager = ToolManager()
        self.assertIsNone(manager.install_command("not-a-tool"))
        self.assertIn("Unknown managed tool", manager.last_message)
        status = manager.check_update("not-a-tool")
        self.assertFalse(status.update_available)
        self.assertIn("Unknown managed tool", status.message)

    def test_system_actions_require_explicit_confirmation(self) -> None:
        """The service boundary must not run package commands by default."""
        manager = ToolManager()
        manager.installer.execute = Mock()
        install_result = manager.install("ngspice")
        update_result = manager.update("ngspice")
        self.assertFalse(install_result.success)
        self.assertFalse(update_result.success)
        self.assertIn("confirmation", install_result.message)
        self.assertIn("confirmation", update_result.message)
        manager.installer.execute.assert_not_called()


class PackageManagerLogicTests(unittest.TestCase):
    tool = ToolMetadata("demo", "Demo", "demo", ("demo", "--version"), "demo", "demo")

    @patch("manager.installer.shutil.which", return_value="/usr/bin/apt")
    @patch("manager.installer.platform.system", return_value="Linux")
    def test_linux_install_command_is_constructed_without_execution(self, *_mocks) -> None:
        self.assertEqual(
            Installer().command_for(self.tool), ("sudo", "apt", "install", "-y", "demo")
        )

    @patch("manager.installer.shutil.which", return_value="C:/ProgramData/choco.exe")
    @patch("manager.installer.platform.system", return_value="Windows")
    def test_windows_install_command_is_constructed_without_execution(self, *_mocks) -> None:
        self.assertEqual(
            Installer().command_for(self.tool), ("choco", "install", "-y", "demo")
        )

    @patch("manager.installer.shutil.which", return_value="/usr/bin/apt")
    @patch("manager.installer.platform.system", return_value="Linux")
    def test_linux_update_command_is_constructed_without_execution(self, *_mocks) -> None:
        self.assertEqual(
            Updater(Installer()).command_for(self.tool),
            ("sudo", "apt", "install", "--only-upgrade", "-y", "demo"),
        )

    @patch("manager.installer.os.geteuid", return_value=0, create=True)
    @patch("manager.installer.shutil.which", return_value="/usr/bin/apt")
    @patch("manager.installer.platform.system", return_value="Linux")
    def test_elevated_linux_install_omits_sudo(self, *_mocks) -> None:
        self.assertEqual(Installer().command_for(self.tool), ("apt", "install", "-y", "demo"))

    @patch("manager.installer.shutil.which", side_effect=lambda name: "/usr/bin/apt" if name == "apt" else None)
    @patch("manager.installer.platform.system", return_value="Linux")
    def test_linux_without_sudo_does_not_propose_an_unrunnable_command(self, *_mocks) -> None:
        self.assertIsNone(Installer().command_for(self.tool))

    @patch("manager.updater.shutil.which", return_value="C:/ProgramData/choco.exe")
    @patch("manager.installer.platform.system", return_value="Windows")
    def test_windows_update_command_is_constructed_without_execution(self, *_mocks) -> None:
        self.assertEqual(
            Updater(Installer()).command_for(self.tool), ("choco", "upgrade", "-y", "demo")
        )

    @patch("manager.updater.subprocess.run")
    @patch("manager.updater.shutil.which", return_value="/usr/bin/apt")
    @patch("manager.installer.platform.system", return_value="Linux")
    def test_apt_update_status_is_parsed_without_real_package_manager(self, mock_system, mock_which, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            ["apt"], 0, "Listing...\ndemo/stable 2.0 amd64 [upgradable from: 1.0]", ""
        )
        status = Updater(Installer()).check(self.tool)
        self.assertTrue(status.update_available)
        self.assertIn("package manager", status.message)
        mock_run.assert_called_once_with(
            ("apt", "list", "--upgradable"), check=False, text=True, capture_output=True, timeout=30
        )

    @patch("manager.installer.platform.system", return_value="Windows")
    def test_unsupported_platform_does_not_check_or_update(self, _mock_system) -> None:
        linux_only = ToolMetadata("demo", "Demo", "demo", ("demo", "--version"), "demo", None, ("Linux",))
        updater = Updater(Installer())
        self.assertFalse(updater.check(linux_only).update_available)
        self.assertIsNone(updater.command_for(linux_only))


class CliConfirmationTests(unittest.TestCase):
    @patch("builtins.input", return_value="yes")
    def test_confirmation_requires_an_explicit_yes(self, _mock_input) -> None:
        self.assertTrue(confirmed("Run command?"))

    @patch("builtins.input", return_value="")
    def test_confirmation_defaults_to_no(self, _mock_input) -> None:
        self.assertFalse(confirmed("Run command?"))


if __name__ == "__main__":
    unittest.main()
