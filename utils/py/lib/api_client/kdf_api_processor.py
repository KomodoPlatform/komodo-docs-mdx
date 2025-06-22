import json
import os
import requests
import logging
import time
import subprocess
from typing import Dict, Any, Set, List
from pathlib import Path

from utils.py.lib.constants.config_struct import EnhancedKomodoConfig
from utils.py.lib.utils.logging_utils import KomodoLogger


class ApiRequestProcessor:
    def __init__(self, config: EnhancedKomodoConfig, logger: KomodoLogger, activation_type: str = None, kdf_branch: str = 'dev'):
        self.config = config
        self.logger = logger
        self.activation_type = activation_type
        self.kdf_branch = kdf_branch
        self.enabled_coins: Set[str] = set()
        self.session = requests.Session()
        self.coins_config: Dict[str, Any] = {}
        self.protocol_to_activation: Dict[str, Any] = {}

        # Mappings and Constants
        self.api_url = "http://127.0.0.1:7783"  # TODO: Make this configurable
        self._initialize_processor()

    def _initialize_processor(self):
        """Fetches coins config and updates initial enabled coins list."""
        self.logger.info("Initializing ApiRequestProcessor...")
        self._load_activation_mapping()
        self._fetch_coins_config()
        self._update_enabled_coins()

    def _load_activation_mapping(self):
        """Loads the protocol_activation_mapping.json file."""
        mapping_file = self.config.directories.data_dir / "coins" / "protocol_activation_mapping.json"
        try:
            self.logger.info(f"Loading activation mapping from {mapping_file}")
            with open(mapping_file, 'r') as f:
                self.protocol_to_activation = json.load(f)
            self.logger.success("Successfully loaded protocol activation mapping.")
        except FileNotFoundError:
            self.logger.error(f"Activation mapping file not found at: {mapping_file}")
            self.protocol_to_activation = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {mapping_file}: {e}")
            self.protocol_to_activation = {}

    def _fetch_coins_config(self):
        """Fetches the coins_config.json file."""
        url = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json"
        try:
            self.logger.fetch(f"Fetching coins config from {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            self.coins_config = response.json()
            self.logger.success("Successfully fetched and loaded coins config.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch coins_config.json: {e}")
            self.coins_config = {}

    def _make_request(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper for making API requests."""
        try:
            response = self.session.post(self.api_url, json=request_body, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err} - {response.text}")
        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request error occurred: {req_err}")
        return {"error": "Request failed in _make_request"}

    def _update_enabled_coins(self):
        """Calls get_enabled_coins and updates the internal set."""
        self.logger.info("Updating list of enabled coins...")
        request_body = {
            "userpass": self.config.openapi.userpass,
            "method": "get_enabled_coins"
        }
        response = self._make_request(request_body)
        if "result" in response and isinstance(response["result"], list):
            self.enabled_coins = {coin['ticker'] for coin in response["result"]}
            self.logger.info(f"Currently enabled coins: {self.enabled_coins}")
        else:
            self.logger.warning("Could not update enabled coins list.")

    def get_method_path(self, method: str, version: str) -> Path:
        """Constructs the path to the method's JSON files directory."""
        filesystem_method_name = method.replace('::', '-')
        version_dir = self.config.directories.postman_json_v2 if version == 'v2' else self.config.directories.postman_json_v1
        return version_dir / filesystem_method_name

    def process_method_requests(self, method: str, version: str, force_disable: bool = False):
        method_path = self.get_method_path(method, version)
        if not method_path.exists():
            self.logger.error(f"Method directory not found: {method_path}")
            return

        request_files = sorted(list(method_path.glob("request_*.json")))
        self.logger.info(f"Found {len(request_files)} request files in {method_path}")

        for request_file in request_files:
            with open(request_file, 'r') as f:
                request_body = json.load(f)

            coin = request_body.get("params", {}).get("coin")
            if coin and coin not in self.enabled_coins:
                self.logger.warning(f"Coin '{coin}' is not enabled. Attempting activation...")
                if not self.activate_coin(coin):
                    self.logger.error(f"Skipping request as activation for '{coin}' failed.")
                    continue
            
            if force_disable and coin:
                self.logger.info(f"Force disabling '{coin}' before request.")
                self.disable_coin(coin)


            self.logger.info(f"Executing request from {request_file.name}")
            response = self._make_request(request_body)

            if response:
                response_filename = request_file.name.replace("request_", "response_")
                response_path = method_path / response_filename
                with open(response_path, 'w') as f:
                    json.dump(response, f, indent=2)
                self.logger.save(f"Saved response to {response_path}")

            if "error" in response:
                error_log_path = self.config.directories.reports_dir / "request_errors.log"
                message_to_log = (
                    f"----------- ERROR LOG -----------\n"
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Method: {method}\n"
                    f"Request File: {request_file.name}\n"
                    f"Request Body: {json.dumps(request_body, indent=2)}\n"
                    f"Response: {json.dumps(response, indent=2)}\n"
                    f"---------------------------------\n\n"
                )
                self.logger.error(f"API error for {method} ({request_file.name}). See {error_log_path} for details.")
                with open(error_log_path, 'a') as f:
                    f.write(message_to_log)

    def activate_coin(self, ticker: str) -> bool:
        self.logger.info(f"Attempting to activate '{ticker}'...")
        coin_info = self.coins_config.get(ticker)
        if not coin_info:
            self.logger.error(f"'{ticker}' not found in coins_config.json.")
            return False

        protocol = coin_info.get("protocol", {}).get("type")
        activation_options = self.protocol_to_activation.get(protocol)

        if not activation_options:
            self.logger.error(f"Protocol '{protocol}' for coin '{ticker}' is not defined in protocol_to_activation map.")
            return False

        # Determine which activation type to use
        act_type_to_use = self.activation_type
        if not act_type_to_use:
            act_type_to_use = activation_options.get("default")
            if not act_type_to_use:
                self.logger.error(f"No default activation type for protocol '{protocol}'.")
                return False
            self.logger.info(f"No activation type specified, using default: '{act_type_to_use}'")

        activation_method = activation_options.get(act_type_to_use)

        if activation_method is None:
            self.logger.error(f"Activation type '{act_type_to_use}' not available for protocol '{protocol}'.")
            return False
        if not activation_method:
            self.logger.error(f"Activation method for protocol '{protocol}' (type: {act_type_to_use}) is not determined. Skipping.")
            return False

        # Build params - This is a simplified version and might need expansion
        params = {"ticker": ticker}
        # Common logic for ETH-like tokens
        if protocol in ["ETH", "ERC20"]:
            params["nodes"] = coin_info.get("nodes", [])
            if "contract_address" in coin_info:
                params["contract_address"] = coin_info.get("contract_address")
        elif protocol in ["UTXO", "BCH"]:
            params["utxo_merge_params"] = {"merge_at": 10}
            params["electrum_servers"] = coin_info.get("electrum", [])
        elif protocol == "SLP":
            params["utxo_merge_params"] = {"merge_at": 10}
            params["electrum_servers"] = coin_info.get("electrum", [])
            # SLP might have specific token id params
        elif protocol in ["QTUM", "QRC20"]:
            params["electrum_servers"] = coin_info.get("electrum", [])
            if "contract_address" in coin_info:
                 params["contract_address"] = coin_info.get("contract_address")
        elif protocol in ["TENDERMINT", "TENDERMINTTOKEN"]:
            params["rpc_urls"] = [node["url"] for node in coin_info.get("nodes", [])]


        init_request = {
            "userpass": self.config.openapi.userpass,
            "method": activation_method,
            "params": params
        }
        
        self.logger.info(f"Sending activation request for '{ticker}' with method '{activation_method}'")
        init_response = self._make_request(init_request)

        # Handle task-based vs direct activation
        if activation_method.startswith("task::"):
            if "result" in init_response and "task_id" in init_response["result"]:
                task_id = init_response["result"]["task_id"]
                return self._poll_task_status(task_id, ticker, activation_method)
            else:
                self.logger.error(f"Task-based activation init failed for '{ticker}': {init_response}")
                return False
        else:
            # Handle legacy/direct activation
            if init_response and "result" in init_response and "error" not in init_response:
                self.logger.success(f"Successfully activated '{ticker}' with direct method.")
                self._update_enabled_coins()
                return True
            else:
                self.logger.error(f"Direct activation failed for '{ticker}': {init_response}")
                return False

    def _poll_task_status(self, task_id: int, ticker: str, init_method: str) -> bool:
        # Derives the status method from the init method. e.g., task::enable_utxo::init -> task::enable_utxo::status
        status_method = init_method.replace("::init", "::status")

        self.logger.info(f"Polling status for task {task_id} using {status_method}")
        for _ in range(20):  # Poll for max 100 seconds
            status_request = {
                "userpass": self.config.openapi.userpass,
                "method": status_method,
                "params": {"task_id": task_id}
            }
            status_response = self._make_request(status_request)
            if status_response and "result" in status_response:
                status = status_response["result"].get("status")
                details = status_response["result"].get("details")
                self.logger.info(f"Activation status for '{ticker}' (Task {task_id}): {status}")
                if status == "Ok":
                    self.logger.success(f"Successfully activated '{ticker}'. Details: {details}")
                    self._update_enabled_coins()
                    return True
                elif status == "InProgress":
                    time.sleep(5)
                    continue
                else: # Failed, Aborted etc.
                    self.logger.error(f"Activation failed for '{ticker}'. Status: {status}, Details: {details}")
                    return False
            else:
                self.logger.error(f"Failed to get status for task {task_id}: {status_response}")
                return False
        self.logger.error(f"Polling timed out for task {task_id} for coin '{ticker}'.")
        return False
        
    def disable_coin(self, ticker: str) -> bool:
        """Disables a coin."""
        self.logger.info(f"Disabling coin '{ticker}'...")
        request_body = {
            "userpass": self.config.openapi.userpass,
            "method": "disable_coin",
            "params": {"coin": ticker}
        }
        response = self._make_request(request_body)
        if response and response.get("result", {}).get("status") == "success":
            self.logger.success(f"Successfully disabled '{ticker}'.")
            self._update_enabled_coins()
            return True
        else:
            self.logger.error(f"Failed to disable '{ticker}': {response}")
            return False 