# eSim Automated Tool Manager

## Problem statement

This FOSSEE eSim Semester Internship 2026 screening-task prototype manages installation and package-manager updates for common eSim tools. It demonstrates safe tool discovery and real version detection without silently changing a user's machine.

## Overview

The application is a small, modular Python CLI. It supports Ngspice and KiCad, detects installed executables with `PATH`, reads their actual version output through `subprocess`, and uses available system package managers for installation and updates only after explicit confirmation.

## Implemented requirements

- List supported tools, check installed versions, install, check updates, and update through a menu.
- Metadata registry for Ngspice and KiCad.
- Real executable and version-command detection; no hardcoded installed versions.
- Linux `apt` and Windows Chocolatey commands, with package-manager/OS checks.
- Confirmation before every installation or update command.
- Read-only System Health / Dependency Check for OS, Python, package-manager, privilege readiness, executables, and detected versions.
- Standard-library logging and graceful handling of missing tools, commands, permissions, and invalid output.
- Unit tests that use mocked executable discovery and subprocess results.

## Supported tools and platforms

| Tool | Executable checked | Linux package | Windows package |
| --- | --- | --- | --- |
| Ngspice | `ngspice` | `ngspice` | `ngspice` |
| KiCad | `kicad-cli` | `kicad` | `kicad` |

Linux installation/update requires `apt` (and `sudo` when the process is not already elevated); Windows requires Chocolatey (`choco`).

## Setup and usage

Use Python 3.10 or later. No third-party dependencies are required.

```bash
python main.py
```

For a safe preview of installation and update commands:

```bash
python main.py --dry-run
```

Dry-run mode uses the same platform and package-manager command-building logic as normal mode, displays commands with a `[DRY RUN]` marker, and never executes an installation or update command or changes system configuration.

The professional menu provides List Tools, Check Versions, Install Tool, Check Updates, Update Tool, and System Health / Dependency Check. Choose `2`, enter `ngspice`, and the CLI runs its registered version command only if the executable exists. For an install, choose `3`; the exact command is displayed and runs only after entering `y` or `yes`. Choosing `5` first shows the detected current version, checks package-manager status, displays the exact update command, and then requests confirmation.

Choose `6` for **System Health / Dependency Check**. It performs no installation or update: it reports PASS/WARNING/FAIL status for the operating system, Python version, relevant package manager, Linux privilege readiness, and each managed tool's executable/version state.

## Testing

```bash
python -m unittest discover -v
```

The tests do not install, update, or invoke real software.

## Limitations

- Update availability is the package manager's currently configured repository status, not an independently fetched upstream "latest" version.
- `apt list --upgradable` does not refresh package indexes; users may run their normal system refresh first.
- Only `apt` and Chocolatey are included in this MVP; macOS and other Linux package managers are intentionally unsupported.

## Future improvements

Add other eSim tools, package managers such as `dnf`, `pacman`, and Homebrew, structured configuration, and richer repository/version reporting.
