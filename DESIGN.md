# Design

## Architecture

`main.py` owns the interactive menu. `ToolManager` orchestrates the registry, version manager, installer, and updater. Each concern is deliberately separated so new eSim tools or package managers can be added without changing the menu.

## Module responsibilities

- `tool_registry.py`: immutable `ToolMetadata` records and the registry that loads tool definitions.
- `version_manager.py`: executable lookup, safe subprocess version capture, parsing, and numeric comparison.
- `installer.py`: OS/package-manager detection and confirmed package command execution.
- `updater.py`: package-manager update-status check and update command construction.
- `logger.py`: shared standard-library logging setup.
- `config_manager.py`: project-local JSON executable overrides and path validation; it never modifies system configuration.
- `tools/`: independent Ngspice and KiCad metadata definitions; add a similar module for each future tool.

## Tool registry

Each tool module returns a record containing a stable ID, display name, executable, version command, supported OS names, and `apt`/Chocolatey package names. The registry loads those records in memory for clarity; extending it requires adding a tool module and registering its metadata factory.

## Installation flow

1. The CLI validates the selected ID and asks the installer for a platform command.
2. The command is shown to the user.
3. Only an explicit `y` or `yes` runs it; the `ToolManager` also rejects programmatic install/update calls unless they carry an explicit confirmation flag.
4. The subprocess return code and output determine the result. Permission and execution failures are reported without crashing.

## Version-checking flow

1. `shutil.which` verifies that the executable is on `PATH`.
2. The discovered executable path is used with the registered version arguments, captured output, and a timeout.
3. A numeric version is parsed from stdout/stderr; otherwise the executable is reported as found with unparseable output. No installed version is fabricated.

## Configuration and readiness flow

The optional `.esim-tool-manager.json` contains only a `tool_paths` object mapping managed IDs to explicit executable files. Configuration is validated before version detection; absent configuration safely falls back to `PATH`. The health checker reuses those validations and version results to produce an eSim readiness level of READY, WARNING, or NOT READY with recommendations. No registry or system environment variable is modified.

## Update flow

The update flow first detects the installed executable and displays its current version. `apt list --upgradable` and `choco outdated --limit-output` then provide package-manager status. The program states this basis rather than inventing an upstream latest version. When an update is listed, the exact apt command (using `sudo` when needed and available) or `choco upgrade -y <package>` command is displayed before the CLI asks confirmation.

## Error handling strategy

Unknown IDs, unsupported systems, unavailable package managers, missing executables, subprocess exceptions, nonzero results, permissions errors, and malformed version output become explanatory results rather than uncaught exceptions. Actions are logged through Python's `logging` module.
