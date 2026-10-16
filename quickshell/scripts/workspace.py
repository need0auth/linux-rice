"""Switch numbered workspaces using the running Hyprland config provider."""

import json
import re


def command(value, run_command, error_type):
    """Build a dispatcher argv after validating the target and querying Hyprland.

    Hyprland's Lua provider expects a dispatcher expression. Older Hyprlang
    sessions use the original ``workspace N`` command. Query the provider just
    as Quickshell does, rather than guessing from a distribution's version.
    """
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", value) or int(value) > 2147483647:
        raise error_type("Workspace must be a positive integer between 1 and 2147483647.")

    status = run_command(["hyprctl", "-j", "status"])
    if status.strip() == "unknown request":
        provider = "hyprlang"
    else:
        try:
            details = json.loads(status)
        except (TypeError, ValueError) as exc:
            raise error_type("Could not determine Hyprland's config provider.") from exc
        provider = details.get("configProvider") if isinstance(details, dict) else None

    if provider == "lua":
        return ["hyprctl", "dispatch", f'hl.dsp.focus({{ workspace = "{value}" }})']
    if provider == "hyprlang":
        return ["hyprctl", "dispatch", "workspace", value]
    raise error_type("This Hyprland config provider does not support workspace switching.")


def activate(value, run_command, error_type):
    """Activate an existing or empty numbered workspace and report IPC errors."""
    reply = run_command(command(value, run_command, error_type))
    # Some hyprctl versions return exit status 0 even for dispatcher errors.
    if reply.strip() != "ok":
        detail = " ".join(str(reply).split())[:200]
        raise error_type(f"Could not switch workspace: {detail or 'empty Hyprland response'}")
