"""Temporary-file tests for project-local executable configuration."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from manager.config_manager import ConfigurationError, ConfigurationManager
from manager.tool_registry import ToolRegistry


class ConfigurationManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.registry = ToolRegistry()
        self.config = ConfigurationManager(self.registry, self.root / "config.json")

    def test_missing_config_uses_path_discovery(self) -> None:
        self.assertTrue(self.config.status().valid)
        result = self.config.validate_path("ngspice")
        self.assertTrue(result.valid)
        self.assertIsNone(result.configured_path)

    def test_set_and_clear_valid_tool_path(self) -> None:
        executable = self.root / "ngspice"
        executable.touch()
        with patch("manager.config_manager.os.name", "nt"):
            self.config.set_path("ngspice", str(executable))
            self.assertEqual(self.config.configured_path("ngspice"), str(executable))
            self.assertTrue(self.config.validate_path("ngspice").valid)
            self.config.clear_path("ngspice")
        self.assertIsNone(self.config.configured_path("ngspice"))

    def test_invalid_json_and_missing_path_are_reported_safely(self) -> None:
        self.config.path.write_text("not-json", encoding="utf-8")
        self.assertFalse(self.config.status().valid)
        self.assertFalse(self.config.validate_path("ngspice").valid)
        self.config.path.write_text(json.dumps({"tool_paths": {"ngspice": "missing"}}), encoding="utf-8")
        self.assertFalse(self.config.validate_path("ngspice").valid)

    def test_invalid_path_is_not_saved(self) -> None:
        with self.assertRaises(ConfigurationError):
            self.config.set_path("ngspice", str(self.root / "missing"))
