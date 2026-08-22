"""Interactive entry point for the eSim Automated Tool Manager."""

from __future__ import annotations

import argparse

from manager.tool_manager import ToolManager
from manager.version_manager import VersionCheckResult, format_version
from manager.health_checker import HealthReport


def prompt_for_tool(manager: ToolManager) -> str | None:
    """Ask for a registered tool identifier and validate it."""
    tool_id = input("Tool ID: ").strip().lower()
    if not manager.registry.get(tool_id):
        print(f"Unknown tool: {tool_id}. Use 'List managed tools' to see IDs.")
        return None
    return tool_id


def print_version(result: VersionCheckResult) -> None:
    """Render a version-check result without repeating the subprocess call."""
    if result.installed and result.version is not None:
        print(f"[PASS] {result.tool.name}: executable found; version {format_version(result.version)}.")
    elif result.installed:
        print(f"[WARNING] {result.tool.name}: executable found, but version is unavailable. {result.message}")
    else:
        print(f"[WARNING] {result.tool.name}: not detected. {result.message}")


def print_command(command: tuple[str, ...]) -> None:
    """Display an argument-list command exactly as it will be passed to subprocess."""
    print("Command:", " ".join(command))


def print_header(title: str) -> None:
    """Print a consistent section header for interactive actions."""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def print_health_report(report: HealthReport) -> None:
    """Present a compact, actionable read-only environment report."""
    print_header("System Health / Dependency Check")
    for check in report.checks:
        print(f"[{check.status.value}] {check.label}: {check.message}")


def confirmed(action: str) -> bool:
    """Return true only for an explicit yes answer."""
    return input(f"{action} [y/N]: ").strip().lower() in {"y", "yes"}


def run(dry_run: bool = False) -> None:
    """Run the simple terminal menu."""
    manager = ToolManager()
    menu = (
        "\n1. List Tools\n2. Check Versions\n3. Install Tool"
        "\n4. Check Updates\n5. Update Tool\n6. System Health / Dependency Check\n7. Exit"
    )
    print_header("eSim Automated Tool Manager")
    if dry_run:
        print("[DRY RUN] System-changing commands will be displayed but never executed.")
    while True:
        print(menu)
        choice = input("Choose an option (1-7): ").strip()
        if choice == "1":
            print_header("Managed Tools")
            for tool in manager.list_tools():
                print(f"- {tool.identifier}: {tool.name} (executable: {tool.executable})")
        elif choice == "2":
            if tool_id := prompt_for_tool(manager):
                print_header("Version Check")
                print_version(manager.check_version(tool_id))
        elif choice == "3":
            if tool_id := prompt_for_tool(manager):
                print_header("Tool Installation")
                command = manager.install_command(tool_id)
                tool = manager.registry.get(tool_id)
                if command is None:
                    print(f"[ERROR] {tool.name}: installation unavailable. {manager.last_message}")
                else:
                    print(f"[INFO] {tool.name}: ready to install.")
                    print_command(command)
                    if dry_run:
                        print("[DRY RUN] Installation command was not executed.")
                    elif confirmed("Run this installation command?"):
                        result = manager.install(tool_id, confirmed=True)
                        outcome = "[PASS] Installation succeeded." if result.success else "[ERROR] Installation failed."
                        print(f"{tool.name}: {outcome} {result.message}")
                    else:
                        print(f"[WARNING] {tool.name}: installation cancelled.")
        elif choice == "4":
            if tool_id := prompt_for_tool(manager):
                print_header("Update Check")
                tool = manager.registry.get(tool_id)
                print(f"[INFO] {tool.name}: checking package-manager update status.")
                status = manager.check_update(tool_id)
                level = "[PASS]" if not status.update_available else "[WARNING]"
                print(f"{level} {tool.name}: {status.message}")
        elif choice == "5":
            if tool_id := prompt_for_tool(manager):
                print_header("Tool Update")
                tool = manager.registry.get(tool_id)
                print(f"[INFO] {tool.name}: checking current installation before update.")
                version_result = manager.check_version(tool_id)
                print_version(version_result)
                if not version_result.installed:
                    print(f"[ERROR] {tool.name}: update cannot continue because the executable was not detected.")
                    continue
                status = manager.check_update(tool_id)
                print(f"[INFO] {tool.name}: {status.message}")
                command = manager.update_command(tool_id)
                if not status.update_available:
                    continue
                if command is None:
                    print(f"[ERROR] {tool.name}: update unavailable. {manager.last_message}")
                else:
                    print_command(command)
                    if dry_run:
                        print("[DRY RUN] Update command was not executed.")
                    elif confirmed("Run this update command?"):
                        result = manager.update(tool_id, confirmed=True)
                        outcome = "[PASS] Update succeeded." if result.success else "[ERROR] Update failed."
                        print(f"{tool.name}: {outcome} {result.message}")
                    else:
                        print(f"[WARNING] {tool.name}: update cancelled.")
        elif choice == "6":
            print_health_report(manager.health_check())
        elif choice == "7":
            print("Goodbye.")
            return
        else:
            print("Please enter a number from 1 to 7.")


def parse_args() -> argparse.Namespace:
    """Parse command-line flags without introducing third-party dependencies."""
    parser = argparse.ArgumentParser(description="Manage selected eSim development tools.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display installation/update commands without executing them.",
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and start the interactive interface."""
    args = parse_args()
    try:
        run(dry_run=args.dry_run)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
