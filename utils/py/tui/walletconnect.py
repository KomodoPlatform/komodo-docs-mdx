"""
Prototype WalletConnect TUI
---------------------------------
Interact with the Komodo DeFi Framework WalletConnect helper
methods (`wc_new_connection`, `wc_get_sessions`, etc.) from the
terminal.  Relies on the existing ApiRequestProcessor so it obeys
your current .env / docker-compose setup.

Run this from the repo root (after activating the venv):

    python utils/py/tui/walletconnect_tui.py

Dependencies (install in the venv if missing):
    pip install rich qrcode-terminal
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List

# Third-party, optional imports. We handle absence gracefully.
try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
except ImportError:
    print("[!] rich not installed – install with `pip install rich` for a nicer UI.")
    Console = None  # type: ignore

try:
    import qrcode
except ImportError:
    qrcode = None  # type: ignore

# Internal library imports – the main reason we are here
from utils.py.lib.constants.config_struct import EnhancedKomodoConfig
from utils.py.lib.utils.logging_utils import KomodoLogger
from utils.py.lib.api_client.kdf_api_processor import ApiRequestProcessor
from utils.py.kdf_tools import KDFTools


# --------------------------------------------------------------------------------------
# Helper utilities
# --------------------------------------------------------------------------------------

def _get_console() -> Console:
    if Console is not None:
        return Console()
    # Fallback minimal console
    class _Dummy:
        def print(self, *a, **k):
            print(*a)
    return _Dummy()  # type: ignore

def _display_qr(uri: str):
    """Render the WalletConnect URI as an ASCII QR code (if `qrcode` is available).

    If the `qrcode` library is missing, fall back to printing the raw URI.
    """

    if qrcode is None:
        print("[QR code omitted – install `qrcode` to render]")
        print(uri)
        return

    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    # Use two characters wide blocks to get a roughly square aspect ratio in terminal
    black = "\u2588\u2588"  # Full block x2
    white = "  "

    for row in matrix:
        line = ''.join([black if cell else white for cell in row])
        print(line)


def _choose(names: List[str], console: Console) -> Optional[str]:
    """Prompt the user to choose one of the given names, returns the chosen element or None."""
    if not names:
        console.print("[bold red]No sessions found[/]")
        return None
    for idx, name in enumerate(names, 1):
        console.print(f"[{idx}] {name}")
    while True:
        choice = Prompt.ask("Select # (or Enter to cancel)")
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        console.print("Invalid selection – try again")


# --------------------------------------------------------------------------------------
# Core TUI application
# --------------------------------------------------------------------------------------

def main():
    console = _get_console()

    console.print("[bold cyan]Initializing WalletConnect TUI …[/]")
    cfg = EnhancedKomodoConfig()  # auto-detects workspace root & branches
    active_branch = cfg.kdf_branch or "unknown"

    logger = KomodoLogger("walletconnect-tui")
    logger.logger.setLevel("ERROR")  # quiet internal logging

    # Tools helper (start/stop/build etc.)
    tools = KDFTools()
    processor = tools.processor  # reuse underlying ApiRequestProcessor

    console.print("[green]Ready.[/]")

    def _menu_text() -> str:
        return (
            "[1] New connection\n"
            "[2] List sessions\n"
            "[3] Get session details\n"
            "[4] Ping session\n"
            "[5] Delete session\n"
            "[6] Start KDF container (no rebuild)\n"
            "[7] Stop KDF container\n"
            "[8] Switch KDF branch\n"
            "[9] Rebuild & restart container\n"
            "[q] Quit"
        )

    while True:
        console.print(
            Panel(_menu_text(), title=f"WalletConnect TUI ({active_branch})", subtitle="Choose an action")
        )
        choice = Prompt.ask("Your choice").strip().lower()

        if choice == "1":
            _handle_new_connection(processor, console)
        elif choice == "2":
            _handle_list_sessions(processor, console)
        elif choice == "3":
            _handle_get_session(processor, console)
        elif choice == "4":
            _handle_ping_session(processor, console)
        elif choice == "5":
            _handle_delete_session(processor, console)
        elif choice == "6":
            _start_container_no_build(cfg, tools, console, active_branch)
        elif choice == "7":
            tools.stop_container_command(argparse.Namespace())  # type: ignore  # simple namespace
        elif choice == "8":
            new_branch = Prompt.ask("Enter new branch name", default=active_branch).strip()
            if new_branch and new_branch != active_branch:
                _switch_branch_and_restart(tools, console, new_branch)
                active_branch = new_branch
        elif choice == "9":
            _rebuild_and_restart(tools, console, active_branch)
        elif choice in {"q", "quit", "exit"}:
            console.print("Goodbye!")
            break
        else:
            console.print("[yellow]Unknown option – try again.[/]")


# --------------------------------------------------------------------------------------
# Action Handlers
# --------------------------------------------------------------------------------------

def _handle_new_connection(processor: ApiRequestProcessor, console: Console):
    console.print("[bold]Create a new WalletConnect connection[/]")

    # Allow user to supply a JSON file path with required_namespaces or accept defaults
    path = Prompt.ask(
        "Path to JSON with required_namespaces (leave blank for default EIP155 + Cosmos example)",
        default="",
        show_default=False,
    ).strip()

    if path:
        try:
            with open(path, "r") as f:
                required_namespaces = json.load(f)
        except Exception as e:
            console.print(f"[red]Failed to load JSON: {e}[/]")
            return
    else:
        # Minimal example – ETH mainnet & Cosmoshub
        required_namespaces = {
            "eip155": {
                "chains": ["eip155:1"],
                "methods": [
                    "eth_sendTransaction",
                    "eth_signTransaction",
                    "personal_sign",
                ],
                "events": ["accountsChanged", "chainChanged"],
            },
            "cosmos": {
                "chains": ["cosmos:cosmoshub-4"],
                "methods": ["cosmos_signDirect", "cosmos_signAmino", "cosmos_getAccounts"],
                "events": [],
            },
        }

    req = {
        "method": "wc_new_connection",
        "mmrpc": "2.0",
        "params": {"required_namespaces": required_namespaces},
        "id": 0,
    }

    resp = processor._make_request(req)
    if "error" in resp:
        console.print(f"[red]Error: {resp['error']}[/]")
        return

    uri = resp.get("result", {}).get("url")
    if not uri:
        console.print(f"[red]Unexpected response: {resp}[/]")
        return

    console.print("[green]Connection URI:[/]")
    console.print(uri)
    _display_qr(uri)


def _handle_list_sessions(processor: ApiRequestProcessor, console: Console):
    req = {"method": "wc_get_sessions", "mmrpc": "2.0", "params": {}, "id": 0}
    resp = processor._make_request(req)
    if "error" in resp:
        console.print(f"[red]Error: {resp['error']}[/]")
        return

    sessions = resp.get("result", {}).get("sessions", [])
    if not sessions:
        console.print("[yellow]No active sessions.[/]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Topic", overflow="fold")
    table.add_column("Wallet", overflow="fold")
    table.add_column("Chains")
    table.add_column("Expiry")

    for sess in sessions:
        wallet_name = sess.get("metadata", {}).get("name", "N/A")
        chains = ", ".join(
            [
                chain
                for ns in sess.get("namespaces", {}).values()
                for chain in ns.get("chains", [])
            ]
        )
        table.add_row(sess.get("topic"), wallet_name, chains, str(sess.get("expiry")))

    console.print(table)


def _prompt_topic(processor: ApiRequestProcessor, console: Console) -> Optional[str]:
    """Prompt the user for a session topic, offering a list if available."""
    req = {"method": "wc_get_sessions", "mmrpc": "2.0", "params": {}, "id": 0}
    resp = processor._make_request(req)
    session_topics = [s.get("topic") for s in resp.get("result", {}).get("sessions", [])]
    if not session_topics:
        console.print("[yellow]No sessions found.[/]")
        return None

    # Offer a menu to pick one
    chosen = _choose(session_topics, console)
    return chosen


def _handle_get_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    req = {
        "method": "wc_get_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = processor._make_request(req)
    console.print_json(json.dumps(resp, indent=2))


def _handle_ping_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    req = {
        "method": "wc_ping_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = processor._make_request(req)
    console.print(resp)


def _handle_delete_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    if not Confirm.ask(f"Are you sure you want to delete session {topic}?"):
        return
    req = {
        "method": "wc_delete_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = processor._make_request(req)
    console.print(resp)


# --------------------------------------------------------------------------------------
# Container management helpers
# --------------------------------------------------------------------------------------

import argparse
import subprocess


def _compose_file(cfg: EnhancedKomodoConfig):
    return cfg.directories.docker_dir / "docker-compose.yml"


def _start_container_no_build(cfg: EnhancedKomodoConfig, tools: KDFTools, console: Console, branch: str):
    compose = _compose_file(cfg)
    if not compose.exists():
        console.print(f"[red]docker-compose.yml not found at {compose} – cannot start container.[/]")
        return
    console.print(f"[cyan]Starting container for branch {branch} (no rebuild)…[/]")
    try:
        subprocess.run(
            [
                "docker",
                "compose",
                "--file",
                str(compose),
                "up",
                "-d",
            ],
            check=True,
            cwd=cfg.directories.docker_dir,
        )
        console.print("[green]Container started.[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start container: {e}[/]")


def _rebuild_and_restart(tools: KDFTools, console: Console, branch: str):
    console.print(f"[cyan]Rebuilding and restarting container on branch {branch}…[/]")
    args = argparse.Namespace(kdf_branch=branch, commit=None, clean=False)
    tools.start_container_command(args)


def _switch_branch_and_restart(tools: KDFTools, console: Console, new_branch: str):
    console.print(f"[cyan]Switching to branch {new_branch} and restarting container…[/]")
    # Stop current container
    tools.stop_container_command(argparse.Namespace())  # type: ignore
    # Start with new branch (build may occur automatically)
    args = argparse.Namespace(kdf_branch=new_branch, commit=None, clean=False)
    tools.start_container_command(args)


if __name__ == "__main__":
    main() 