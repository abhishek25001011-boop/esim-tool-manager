# eSim Automated Tool Manager

## Project Overview

This project implements a modular Python-based automated tool manager for the FOSSEE eSim Semester Internship 2026 screening task.

It manages Ngspice and KiCad through a safe terminal interface: it discovers tools, detects their real installed versions, prepares platform-aware installation and update commands, and requires explicit confirmation before any system-changing action.

## Implemented Features

- Tool registry for Ngspice and KiCad.
- Real executable discovery and version detection using `subprocess`.
- Linux `apt` and Windows Chocolatey installation and update workflows.
- Explicit confirmation and return-code-based success/failure reporting.
- `--dry-run` mode that displays install/update commands without executing them.
- System Health / Dependency Check for OS, Python, package managers, privileges, executable availability, and versions.
- Project-local JSON executable-path configuration without changing the Windows registry or system `PATH`.
- eSim Environment Readiness report with READY, WARNING, or NOT READY guidance.
- Standard-library logging, error handling, and mocked unit tests.

## Supported Tools and Platforms

| Tool    | Executable Checked | Linux Package | Windows Package |
| ------- | ------------------ | ------------- | --------------- |
| Ngspice | `ngspice`          | `ngspice`     | `ngspice`       |
| KiCad   | `kicad-cli`        | `kicad`       | `kicad`         |

Linux installation and updates require `apt` and, when the process is not elevated, `sudo`. Windows installation and updates require Chocolatey (`choco`).

## Setup

Use Python 3.10 or later. No third-party dependencies are required.

```bash
python main.py
```

## Usage

The interactive menu provides:

- List Tools
- Check Versions
- Install Tool
- Check Updates
- Update Tool
- System Health / Dependency Check
- Tool Configuration / Executable Paths
- eSim Environment Readiness

Installation and update commands are shown before execution and run only after entering `y` or `yes`.

### Dry-Run Mode

Preview the same installation and update commands without changing the system:

```bash
python main.py --dry-run
```

Dry-run mode never executes installation or update commands and never changes system configuration.

## Configuration Handling

Choose **Tool Configuration / Executable Paths** to view, set, or clear Ngspice and KiCad executable overrides. Overrides are stored in `.esim-tool-manager.json` in the current project directory and must point to existing executable files.

When no override is configured, the manager uses normal `PATH` discovery. The application never modifies the Windows registry, system environment variables, or system `PATH`.

## Environment Readiness

**System Health / Dependency Check** reports PASS, WARNING, and FAIL results for host and tool dependencies. **eSim Environment Readiness** summarizes the same checks as READY, WARNING, or NOT READY and provides actionable recommendations.

## Testing

```bash
python -m unittest discover -v
```

The unit tests use mocks and temporary files where appropriate; they do not install, update, or modify real system software.

## Limitations

- Update availability comes from configured package-manager repositories; the application does not invent upstream latest-version data.
- `apt list --upgradable` does not refresh package indexes.
- This MVP supports `apt` and Chocolatey only; macOS and other Linux package managers are not currently supported.

## Future Improvements

Potential extensions include additional eSim tools, package managers such as `dnf`, `pacman`, and Homebrew, richer repository/version reporting, automated environment diagnostics, and broader cross-platform support.
