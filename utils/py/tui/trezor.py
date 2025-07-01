"""Trezor Device TUI
====================
Minimal terminal UI to drive Komodo DeFi Framework Trezor helper
methods (task::init_trezor::* and trezor_connection_status).

Launch (from repo root, venv active):

    python -m utils.py.tui.trezor

Dependencies: same as other TUIs (rich).
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    raise SystemExit("Please install 'rich' inside your venv: pip install rich")

from utils.py.kdf_tools import KDFTools
from utils.py.lib.constants.config_struct import EnhancedKomodoConfig
from utils.py.lib.api_client.kdf_api_processor import ApiRequestProcessor


class TrezorTUI:
    def __init__(self):
        self.console = Console()
        self.tools = KDFTools()
        self.processor: ApiRequestProcessor = self.tools.processor
        self.last_task_id: Optional[int] = None
        self.branch = EnhancedKomodoConfig().kdf_branch or "unknown"
        # Active node starts with first in config
        self.active_node = self.processor.config.nodes[0]

    # --------------------------- RPC helpers ---------------------------
    def _rpc(self, method: str, params: dict | None = None):
        # Inject userpass and target the first configured node
        node = self.active_node
        body = {
            "method": method,
            "mmrpc": "2.0",
            "params": params or {},
            "id": 0,
            "userpass": node.userpass,
        }
        resp = self.processor._make_request(node.api_url, body)
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result", {})

    # --------------------------- actions ------------------------------
    def init_device(self):
        dev_pk = Prompt.ask("Known device pubkey (optional)", default="").strip() or None
        params = {"device_pubkey": dev_pk} if dev_pk else {}
        try:
            res = self._rpc("task::init_trezor::init", params)
            self.last_task_id = res["task_id"]
            self.console.print(f"[green]Started init – Task ID {self.last_task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Init failed: {e}[/]")

    def status(self):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        try:
            res = self._rpc("task::init_trezor::status", {"task_id": task_id})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Status error: {e}[/]")

    def send_user_action(self, action_type: str):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        payload: dict = {"task_id": task_id, "action_type": action_type}
        if action_type == "TrezorPin":
            pin = Prompt.ask("Enter Trezor PIN (as mapped)")
            payload["pin"] = pin
        elif action_type == "TrezorPassphrase":
            passwd = Prompt.ask("Enter Trezor passphrase", password=True)
            payload["passphrase"] = passwd
        try:
            res = self._rpc("task::init_trezor::user_action", payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]User action error: {e}[/]")

    def cancel(self):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        try:
            res = self._rpc("task::init_trezor::cancel", {"task_id": task_id})
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Cancel error: {e}[/]")

    def connection_status(self):
        pk = Prompt.ask("Expected device pubkey (optional)", default="").strip() or None
        params = {"device_pubkey": pk} if pk else {}
        try:
            res = self._rpc("trezor_connection_status", params)
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/]")

    # --------------------------- util ------------------------------
    def _ensure_task_id(self) -> Optional[int]:
        if self.last_task_id is None:
            inp = Prompt.ask("Enter task_id")
            if not inp.isdigit():
                self.console.print("[yellow]Invalid task_id.[/]")
                return None
            self.last_task_id = int(inp)
        return self.last_task_id

    # --------------------------- menu loop -------------------------
    def run(self):
        while True:
            self.console.print(
                Panel(
                    f"[0] Select node (current: {self.active_node.name})\n[1] Init Trezor\n[2] Status\n[3] Send PIN\n[4] Send Passphrase\n[5] Cancel Init\n[6] Connection status\n[q] Quit",
                    title=f"Trezor TUI ({self.branch})",
                    subtitle="Choose an action",
                )
            )
            choice = Prompt.ask("Your choice").strip().lower()
            if choice == "0":
                self._select_node()
            elif choice == "1":
                self.init_device()
            elif choice == "2":
                self.status()
            elif choice == "3":
                self.send_user_action("TrezorPin")
            elif choice == "4":
                self.send_user_action("TrezorPassphrase")
            elif choice == "5":
                self.cancel()
            elif choice == "6":
                self.connection_status()
            elif choice in {"q", "quit", "exit"}:
                break
            else:
                self.console.print("[yellow]Unknown option[/]")

    # --------------------------- node selection -------------------------

    def _select_node(self):
        nodes = self.processor.config.nodes
        self.console.print("[bold]Select node to use:[/]")
        for idx, node in enumerate(nodes, 1):
            self.console.print(f"[{idx}] {node.name} – {node.api_url}")
        choice = Prompt.ask("Choice (Enter to cancel)")
        if not choice:
            return
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(nodes):
                self.active_node = nodes[idx-1]
                self.console.print(f"[cyan]Switched to node {self.active_node.name} ({self.active_node.api_url})[/]")
                return
        self.console.print("[yellow]Invalid selection – node unchanged.[/]")


if __name__ == "__main__":
    TrezorTUI().run() 