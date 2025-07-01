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
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    raise SystemExit("Please install 'rich' inside your venv: pip install rich")

# ---------------------------------------------------------------------------
# Path boot-strapper so the script works regardless of where it is executed
# (repo root or any sub-folder). Mirrors logic used in walletconnect TUI.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_WORKSPACE_ROOT = next((p for p in _HERE.parents if (p / "utils").exists()), None)

if _WORKSPACE_ROOT and str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

# Internal imports (require workspace root on sys.path)
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

        # Force localhost usage (port 8777) as requested
        self.api_url = "http://127.0.0.1:8777"
        self.userpass = "RPC_UserP@SSW0RD"

        # Dummy node object for backward-compatible display only
        class _LocalNode:
            name = "localhost"
            api_url = "http://127.0.0.1:8777"
        self.active_node = _LocalNode()

        self.last_activation_task: Optional[dict] = None  # {'prefix': str, 'task_id': int}

    # --------------------------- RPC helpers ---------------------------
    def _rpc(self, method: str, params: dict | None = None):
        # Inject userpass and target the first configured node
        body = {
            "method": method,
            "mmrpc": "2.0",
            "params": params or {},
            "id": 0,
            "userpass": self.userpass,
        }
        resp = self.processor._make_request(self.api_url, body)
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

            # Automatically guide the user based on status
            status = res.get("status")
            details = res.get("details")

            if status == "UserActionRequired":
                if details == "EnterTrezorPin":
                    self.console.print("[yellow]Device requests PIN entry.[/]")
                    if Confirm.ask("Enter PIN now?"):
                        self.send_user_action("TrezorPin")
                elif details == "EnterTrezorPassphrase":
                    self.console.print("[yellow]Device requests passphrase entry.[/]")
                    if Confirm.ask("Enter passphrase now?"):
                        self.send_user_action("TrezorPassphrase")
        except Exception as e:
            self.console.print(f"[red]Status error: {e}[/]")

    def send_user_action(self, action_type: str):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        # Build request according to docs: user_action must be an object containing
        # the actual action details (action_type, pin/passphrase, etc.)
        user_action: dict = {"action_type": action_type}

        if action_type == "TrezorPin":
            pin = Prompt.ask("Enter Trezor PIN (as mapped)")
            user_action["pin"] = pin
        elif action_type == "TrezorPassphrase":
            passwd = Prompt.ask("Enter Trezor passphrase", password=True)
            user_action["passphrase"] = passwd

        payload: dict = {"task_id": task_id, "user_action": user_action}

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

    def activation_init(self):
        """Activate a coin using ApiRequestProcessor logic (task methods)."""
        ticker = Prompt.ask("Enter coin ticker (e.g., KMD, ETH, QTUM)").strip().upper()
        if not ticker:
            self.console.print("[yellow]No ticker entered.[/]")
            return

        # Build activation request via internal helper from ApiRequestProcessor logic
        request_body = self._build_activation_request(ticker)
        if request_body is None:
            return  # error already shown

        method = request_body["method"]
        params = request_body.get("params", {})

        try:
            result = self._rpc(method, params)
            task_id = result.get("task_id")
            if task_id is None:
                self.console.print("[red]Activation init did not return task_id; check response above.[/]")
                return
            self.last_activation_task = {"prefix": method.rsplit("::", 1)[0], "task_id": task_id}
            self.console.print(f"[green]Started activation of {ticker} – Task ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Activation init failed: {e}[/]")

    def activation_status(self):
        if not self._ensure_activation_task():
            return
        method = f"{self.last_activation_task['prefix']}::status"
        try:
            res = self._rpc(method, {"task_id": self.last_activation_task['task_id']})
            self.console.print_json(json.dumps(res, indent=2))

            status = res.get("status") or res.get("result", {}).get("status")
            details = res.get("details") or res.get("result", {}).get("details")

            if status == "UserActionRequired":
                if details == "EnterTrezorPin":
                    self.console.print("[yellow]Activation requires Trezor PIN.[/]")
                    if Confirm.ask("Enter PIN now?"):
                        self.activation_send_user_action("TrezorPin")
                elif details == "EnterTrezorPassphrase":
                    self.console.print("[yellow]Activation requires Trezor Passphrase.[/]")
                    if Confirm.ask("Enter passphrase now?"):
                        self.activation_send_user_action("TrezorPassphrase")
        except Exception as e:
            self.console.print(f"[red]Activation status error: {e}[/]")

    def activation_send_user_action(self, action_type: str):
        if not self._ensure_activation_task():
            return
        user_action: dict = {"action_type": action_type}
        if action_type == "TrezorPin":
            pin = Prompt.ask("Enter Trezor PIN (as mapped)")
            user_action["pin"] = pin
        elif action_type == "TrezorPassphrase":
            passwd = Prompt.ask("Enter Trezor passphrase", password=True)
            user_action["passphrase"] = passwd
        payload = {"task_id": self.last_activation_task['task_id'], "user_action": user_action}
        method = f"{self.last_activation_task['prefix']}::user_action"
        try:
            res = self._rpc(method, payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Activation user action error: {e}[/]")

    def activation_cancel(self):
        if not self._ensure_activation_task():
            return
        method = f"{self.last_activation_task['prefix']}::cancel"
        try:
            res = self._rpc(method, {"task_id": self.last_activation_task['task_id']})
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Activation cancel error: {e}[/]")

    # --------------------------- util ------------------------------
    def _ensure_task_id(self) -> Optional[int]:
        if self.last_task_id is None:
            inp = Prompt.ask("Enter task_id")
            if not inp.isdigit():
                self.console.print("[yellow]Invalid task_id.[/]")
                return None
            self.last_task_id = int(inp)
        return self.last_task_id

    def _ensure_activation_task(self) -> bool:
        if self.last_activation_task is None:
            self.console.print("[yellow]No activation task started yet.[/]")
            return False
        return True

    # ------------------------------------------------------------------
    # Activation request builder (simplified subset of ApiRequestProcessor)
    # ------------------------------------------------------------------
    def _build_activation_request(self, ticker: str) -> dict | None:
        """Construct init request for *ticker* following ApiRequestProcessor logic."""
        coin_info = self.processor.coins_config.get(ticker)
        if coin_info is None:
            self.console.print(f"[red]{ticker} not found in coins_config.json.[/]")
            return None

        protocol = coin_info.get("protocol", {}).get("type")
        act_map = self.processor.protocol_to_activation.get(protocol, {})
        method = act_map.get("task")
        if not method:
            self.console.print(f"[red]No task-based activation method for protocol {protocol}.[/]")
            return None

        params: dict = {"ticker": ticker}

        # --- protocol-specific param helpers (subset) ---
        if protocol in {"UTXO", "BCH", "SLP"}:
            servers = coin_info.get("electrum", [])
            params["activation_params"] = {
                "mode": {
                    "rpc": "Electrum",
                    "rpc_data": {"servers": servers},
                },
                "utxo_merge_params": {"merge_at": 10},
            }

        elif protocol in {"ETH", "ERC20"}:
            params.update({
                "nodes": coin_info.get("nodes", []),
            })
            if "swap_contract_address" in coin_info:
                params["swap_contract_address"] = coin_info["swap_contract_address"]

        # Always add Trezor priv_key_policy for this TUI
        params["priv_key_policy"] = {"type": "Trezor"}

        return {
            "userpass": self.userpass,
            "method": method,
            "mmrpc": "2.0",
            "params": params,
        }

    # --------------------------- menu loop -------------------------
    def run(self):
        while True:
            self.console.print(
                Panel(
                    f"[1] Init Trezor\n[2] Status\n[3] Send PIN\n[4] Send Passphrase\n[5] Cancel Init\n[6] Connection status\n[7] Coin Activation Init\n[8] Coin Activation Status\n[9] Coin Activation Send PIN\n[10] Coin Activation Send Passphrase\n[11] Cancel Coin Activation\n[q] Quit",
                    title=f"Trezor TUI ({self.branch})",
                    subtitle="Choose an action",
                )
            )
            choice = Prompt.ask("Your choice").strip().lower()
            if choice == "1":
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
            elif choice == "7":
                self.activation_init()
            elif choice == "8":
                self.activation_status()
            elif choice == "9":
                self.activation_send_user_action("TrezorPin")
            elif choice == "10":
                self.activation_send_user_action("TrezorPassphrase")
            elif choice == "11":
                self.activation_cancel()
            elif choice in {"q", "quit", "exit"}:
                break
            else:
                self.console.print("[yellow]Unknown option – valid options are 1-11 or q.[/]")

    # --------------------------- node selection -------------------------
    def _select_node(self):
        self.console.print("[yellow]Node selection disabled – TrezorTUI always uses http://127.0.0.1:8777[/]")


if __name__ == "__main__":
    TrezorTUI().run() 