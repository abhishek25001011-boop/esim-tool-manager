"""Mocked CLI tests that never invoke installation or update subprocesses."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import main
from manager.installer import CommandResult
from manager.tool_registry import ToolMetadata
from manager.updater import UpdateStatus
from manager.version_manager import VersionCheckResult


class DryRunCliTests(unittest.TestCase):
    tool = ToolMetadata("ngspice", "Ngspice", "ngspice", ("ngspice", "--version"), "ngspice", "ngspice")

    def _manager(self) -> Mock:
        manager = Mock()
        manager.registry.get.return_value = self.tool
        manager.install_command.return_value = ("choco", "install", "-y", "ngspice")
        manager.update_command.return_value = ("choco", "upgrade", "-y", "ngspice")
        manager.check_version.return_value = VersionCheckResult(self.tool, True, (42,), message="Detected version 42.")
        manager.check_update.return_value = UpdateStatus(True, "An update is available according to package-manager status.")
        manager.install.return_value = CommandResult(True, "Command completed successfully.")
        manager.update.return_value = CommandResult(True, "Command completed successfully.")
        return manager

    @patch("main.ToolManager")
    @patch("builtins.input", side_effect=["3", "ngspice", "9"])
    def test_dry_run_install_displays_command_without_execution(self, _input, manager_class) -> None:
        manager = self._manager()
        manager_class.return_value = manager
        output = io.StringIO()

        with redirect_stdout(output):
            main.run(dry_run=True)

        self.assertIn("choco install -y ngspice", output.getvalue())
        self.assertIn("[DRY RUN] Installation command was not executed.", output.getvalue())
        manager.install.assert_not_called()

    @patch("main.ToolManager")
    @patch("builtins.input", side_effect=["5", "ngspice", "9"])
    def test_dry_run_update_displays_command_without_execution(self, _input, manager_class) -> None:
        manager = self._manager()
        manager_class.return_value = manager
        output = io.StringIO()

        with redirect_stdout(output):
            main.run(dry_run=True)

        self.assertIn("choco upgrade -y ngspice", output.getvalue())
        self.assertIn("[DRY RUN] Update command was not executed.", output.getvalue())
        manager.update.assert_not_called()

    @patch("main.run")
    @patch("sys.argv", ["main.py", "--dry-run"])
    def test_main_starts_cli_with_dry_run_flag(self, run_mock) -> None:
        main.main()
        run_mock.assert_called_once_with(dry_run=True)


if __name__ == "__main__":
    unittest.main()
