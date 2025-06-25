import json
import os
import requests
import time
import subprocess
from typing import Dict, Any, Set
from pathlib import Path
import sys

from utils.py.lib.constants.config_struct import EnhancedKomodoConfig
from utils.py.lib.utils.logging_utils import KomodoLogger
from utils.py.lib.managers.path_mapping_manager import EnhancedPathMapper


class ApiRequestProcessor:
    def __init__(self, config: EnhancedKomodoConfig, logger: KomodoLogger, kdf_branch: str = 'dev'):
        self.config = config
        self.logger = logger
        self.path_mapper = EnhancedPathMapper(config=self.config)
        self._load_dotenv()
        self.kdf_branch = kdf_branch
        self.enabled_coins: Set[str] = set()
        self.session = requests.Session()
        self.coins_config: Dict[str, Any] = {}
        self.protocol_to_activation: Dict[str, Any] = {}
        self.method_results_cache: Dict[str, Any] = {}
        self.completed_methods: Set[str] = set()
        self.activation_methods: Set[str] = set()
        self.v1_methods: Set[str] = set()
        self.v2_methods: Set[str] = set()

        # Mappings and Constants
        rpc_url = os.getenv("RPC_URL", "http://127.0.0.1")
        rpc_port = os.getenv("RPC_PORT", "7783")
        self.api_url = f"{rpc_url}:{rpc_port}"
        self.rpc_password = os.getenv("RPC_PASSWORD", "RPC_CONTRoL_USERP@SSW0RD")
        self.logger.info(f"API requests will be sent to: {self.api_url}")
        self._initialize_processor()

    def _load_dotenv(self):
        """Loads .env file from the docker data directory."""
        dotenv_path = self.config.directories.docker_dot_kdf_dir / ".env"
        if not dotenv_path.exists():
            self.logger.warning(f".env file not found at {dotenv_path}. Using default values.")
            return

        with open(dotenv_path, 'r') as f:
            for line in f.read().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    # Remove surrounding quotes if they exist
                    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                        value = value[1:-1]
                    os.environ[key] = value
                    # Uncomment to log env vars to console (for debugging)
                    # self.logger.info(f"ENV VAR: {key} = {value}")
        self.logger.success("Successfully loaded environment variables.")
        self.enable_hd = self._get_env_var_as_bool("ENABLE_HD", False)

    @staticmethod
    def _get_env_var_as_bool(var_name, default=False):
        """Gets an environment variable and converts it to a boolean."""
        value = os.getenv(var_name, str(default)).lower()
        return value in ['true', '1', 't', 'y', 'yes']

    @staticmethod
    def _get_env_var_as_int(var_name, default):
        """Gets an environment variable and converts it to an integer."""
        try:
            return int(os.getenv(var_name, str(default)))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_env_var_as_str_array(var_name, default=[]):
        """Gets a comma-separated string from env and converts to a list of strings."""
        
        value = os.getenv(var_name)
        value = value.replace('"', '').replace("'", '').replace(',', ' ')
        if not value:
            return default
        return [item.strip() for item in value.split(' ') if item.strip()]

    def generate_mm2_config(self):
        """Generates MM2.json from environment variables."""
        output_path = self.config.directories.docker_dot_kdf_dir / "MM2.json"

        # Assumes .env has been loaded into the environment by the calling script
        config_data = {
            "gui": os.getenv("GUI", "kdf_mdx_docs"),
            "rpcip": "0.0.0.0",
            "rpc_local_only": False,
            "enable_hd": self._get_env_var_as_bool("ENABLE_HD", False),
            "netid": self._get_env_var_as_int("NETID", 8762),
            "rpcport": self._get_env_var_as_int("RPC_PORT", 7783),
            "1inch_api": os.getenv("ONE_INCH_API", ""),
            "seednodes": self._get_env_var_as_str_array("SEED_NODES", []),
            "passphrase": os.getenv("PASSPHRASE", ""),
            "rpc_password": os.getenv("RPC_PASSWORD", ""),
            "use_watchers": self._get_env_var_as_bool("USE_WATCHERS", False),
            "i_am_seed": self._get_env_var_as_bool("I_AM_SEED", False),
            "is_bootstrap_node": self._get_env_var_as_bool("IS_BOOTSTRAP_NODE", False),
            "disable_p2p": self._get_env_var_as_bool("DISABLE_P2P", False),
            "use_trading_proto_v2": self._get_env_var_as_bool("USE_TRADING_PROTO_V2", False),
            "allow_weak_password": self._get_env_var_as_bool("ALLOW_WEAK_PASSWORD", True),
            "event_streaming_configuration": {
                "access_control_allow_origin": "*"
            }
        }

        try:
            self.logger.info(f"Generating {output_path}...")
            with open(output_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            self.logger.success(f"Successfully generated {output_path}")
        except Exception as e:
            self.logger.error(f"Error writing to {output_path}: {e}")
            sys.exit(1)

    def stop_container(self):
        try:
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=self.config.directories.docker_dir, check=True
            )
            self.logger.success("Container stopped successfully.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to stop container: {e}")
            return False

    def _initialize_processor(self):
        """Fetches coins config and updates initial enabled coins list."""
        self.logger.info("Initializing ApiRequestProcessor...")
        self._load_activation_mapping()
        self._load_mdx_methods()
        self._fetch_coins_config()
        self._fetch_coins_file()
        self.generate_mm2_config()
        

    def _load_mdx_methods(self):
        """Loads the kdf_mdx_methods.json file to determine method versions."""
        mdx_methods_path = self.config.directories.branched_reports_dir / self.config.directories.mdx_methods_report
        if not mdx_methods_path.exists():
            self.logger.error(f"MDX methods report not found at: {mdx_methods_path}")
            self.logger.error("Please run 'kdf-tools scan-mdx' to generate it.")
            return

        try:
            self.logger.info(f"Loading mdx methods from {mdx_methods_path}")
            with open(mdx_methods_path, 'r') as f:
                mdx_methods_data = json.load(f)
            
            self.v1_methods = set(mdx_methods_data.get("repository_data", {}).get("v1", {}).get("methods", []))
            self.v2_methods = set(mdx_methods_data.get("repository_data", {}).get("v2", {}).get("methods", []))
            
            self.logger.success(f"Successfully loaded {len(self.v1_methods)} v1 methods and {len(self.v2_methods)} v2 methods.")
        except Exception as e:
            self.logger.error(f"Error loading MDX methods report from {mdx_methods_path}: {e}")

    def _load_activation_mapping(self):
        """Loads the protocol_activation_mapping.json file."""
        mapping_file = self.config.directories.data_dir / "coins" / "protocol_activation_mapping.json"
        try:
            self.logger.info(f"Loading activation mapping from {mapping_file}")
            with open(mapping_file, 'r') as f:
                self.protocol_to_activation = json.load(f)

            # Populate activation_methods set
            for activations in self.protocol_to_activation.values():
                for method_name in activations.values():
                    if method_name:
                        self.activation_methods.add(method_name)
            
            self.logger.success(f"Successfully loaded protocol activation mapping and identified {len(self.activation_methods)} activation methods.")
        except FileNotFoundError:
            self.logger.error(f"Activation mapping file not found at: {mapping_file}")
            self.protocol_to_activation = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {mapping_file}: {e}")
            self.protocol_to_activation = {}

    def _fetch_coins_config(self, branch: str = "master"):
        """Fetches the coins_config.json file."""
        url = f"https://raw.githubusercontent.com/KomodoPlatform/coins/{branch}/utils/coins_config.json"
        try:
            self.logger.fetch(f"Fetching coins config from {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            self.coins_config = response.json()
            self.logger.success("Successfully fetched and loaded coins config.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch coins_config.json: {e}")
            self.coins_config = {}

    def _fetch_coins_file(self, branch: str = "master"):
        """Fetches the coins file."""
        url = f"https://raw.githubusercontent.com/KomodoPlatform/coins/{branch}/coins"
        try:
            self.logger.fetch(f"Fetching coins config from {url}")
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            self.coins_file = response.json()
            self.logger.success("Successfully fetched and loaded coins file.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch coins: {e}")
            self.coins_file = {}
        with open(self.config.directories.docker_dot_kdf_dir / "coins", "w") as f:
            json.dump(self.coins_file, f, indent=4)
            self.logger.success("Successfully saved coins file.")

    def _make_request(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper for making API requests."""
        self.logger.info(f"Sending request:\n{json.dumps(request_body, indent=2)}")
        try:
            request_body["userpass"] = self.rpc_password
            response = self.session.post(self.api_url, json=request_body, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err} - {response.text}")
            if 'Userpass is invalid' in response.text:
                self.logger.error(f"Userpass is invalid. Please check your .env file.")
                self.stop_container()
                sys.exit(1)
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": response.text}
        except Exception as e:
            self.logger.error(f"Request error occurred: {e}")
            return {"error": str(e)}


    def _update_enabled_coins(self):
        """Calls get_enabled_coins and updates the internal set."""
        self.logger.info("Updating list of enabled coins...")
        request_body = {
            "userpass": self.config.openapi.userpass,
            "mmrpc": "2.0",
            "method": "get_enabled_coins",
            "id": 0
        }
        response = self._make_request(request_body)
        if "result" in response:
            self.enabled_coins = {coin['ticker'] for coin in response["result"].get("coins", [])}
            self.logger.success(f"Successfully updated list of enabled coins.")
        else:
            self.logger.error(f"Failed to update list of enabled coins.")
        self.logger.info(f"Currently enabled coins: {self.enabled_coins}")
        


    def check_coin_is_active(self, request_body: Dict[str, Any]) -> bool:
        """Checks if the coin is active, and if not, activates it"""
        coins_to_activate = []
        for i in ['coin', 'ticker', 'base', 'rel']:
            if i in request_body:
                coin = request_body[i]
            elif i in request_body.get("params", {}):
                coin = request_body.get("params", {}).get(i)
            else:
                continue
            coins_to_activate.append(coin)
        if len(coins_to_activate) == 0:
            return True, None
        self.logger.info(f"Method: {request_body.get('method')} needs some coins to activate: {coins_to_activate}")
        for coin in coins_to_activate:
            if coin and coin not in self.enabled_coins:
                self.logger.warning(f"Coin '{coin}' is not enabled. Attempting activation...")
                if not self.activate_coin(coin):
                    self.logger.error(f"Skipping request as activation for '{coin}' failed.")
                    return False, coin
        return True, None

    def is_activation_method(self, method: str) -> bool:
        """Checks if a method is a known coin activation method."""
        return method in self.activation_methods

    def process_method_request(self, method: str, version: str):
        self.logger.info(f"Processing method: {method}, version: {version}")
        method_path = self.path_mapper.get_method_path('json', method, version)
        self.logger.info(f"Method path: {method_path}")
        if not Path(method_path).exists():
            self.logger.error(f"Method directory not found: {method_path}")
            return

        request_files = sorted(list(method_path.glob("request_*.json")))
        self.logger.info(f"---------------------------------------------------------")
        self.logger.info(f"Found {len(request_files)} request files in {method_path}")

        for request_file in request_files:
            with open(request_file, 'r') as f:
                request_body = json.load(f)

                # For activation methods, ensure coin is disabled first for a clean test
                if self.is_activation_method(method):
                    params = request_body.get("params", {})
                    ticker = params.get("ticker")
                    if ticker and ticker in self.enabled_coins:
                        self.logger.warning(f"Coin '{ticker}' is already enabled for activation test. Disabling first.")
                        if self.disable_coin(ticker):
                            time.sleep(1)  # Give a moment for the state to update
                        else:
                            self.logger.error(f"Failed to disable '{ticker}', skipping activation test for this example.")
                            continue

                # For kmd_rewards_info, ensure KMD is specified.
                # TODO: This is a hack to ensure KMD is enabled for kmd_rewards_info.
                # We should find a better way to do this. It is not a valid parameter for kmd_rewards_info.
                if method == "kmd_rewards_info":
                    if "params" in request_body:
                        if "coin" not in request_body["params"]:
                            request_body["params"]["coin"] = "KMD"
                    elif "coin" not in request_body:
                        request_body["coin"] = "KMD"
                        
                # Inject cached data from previous method calls
                request_body = self._inject_cached_data(method, request_body)

                # Dynamically set userpass from environment variable if available
                request_body["userpass"] = self.rpc_password
                
                coins_active, coin = self.check_coin_is_active(request_body)
                if not coins_active:
                    self.logger.error(f"Skipping request as activation for '{coin}' failed.")
                    continue

                # self.logger.info(f"Executing request from {request_file.name}")
                response = self._make_request(request_body)

                if response:
                    if "error" in response:
                        response_filename = request_file.name.replace("request_", "error_")
                    else:
                        # Cache successful response data for subsequent calls
                        self._cache_response_data(method, response)
                        self.completed_methods.add(method)
                        response_filename = request_file.name.replace("request_", "response_")

                    response_path = method_path / response_filename
                    with open(response_path, 'w') as f:
                        json.dump(response, f, indent=2)

                    self.logger.info(f"Response:\n{json.dumps(response, indent=2)}")
                    self.logger.save(f"Saved response to {response_path}")

    def _inject_cached_data(self, method: str, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Injects cached data from previous requests into the current request body."""
        params = request_body.get("params", {})

        # Handle task-based methods
        if "::" in method and not method.endswith("::init"):
            task_group = "::".join(method.split("::")[:-1])
            task_cache = self.method_results_cache.get("tasks", {}).get(task_group, {})
            if "task_id" in task_cache:
                self.logger.info(f"Injecting task_id {task_cache['task_id']} into request for {method}")
                params['task_id'] = task_cache['task_id']

        # Handle swap status
        if method == "my_swap_status":
            swap_cache = self.method_results_cache.get("swaps", [])
            if swap_cache:
                latest_swap = swap_cache[-1]
                if "uuid" in latest_swap:
                    self.logger.info(f"Injecting uuid {latest_swap['uuid']} into request for {method}")
                    params['uuid'] = latest_swap['uuid']

        # Handle message verification
        if method == "verify_message":
            signature_cache = self.method_results_cache.get("signatures", {})
            if "signature" in signature_cache:
                self.logger.info(f"Injecting signature for {method}")
                params.update(signature_cache)

        # Handle sending raw transaction
        if method == "send_raw_transaction":
            tx_cache = self.method_results_cache.get("unsigned_tx", {})
            if "tx_hex" in tx_cache:
                self.logger.info(f"Injecting tx_hex into request for {method}")
                params['tx_hex'] = tx_cache['tx_hex']
                
        request_body['params'] = params
        return request_body

    def _cache_response_data(self, method: str, response: Dict[str, Any]):
        """Caches relevant data from a successful response for later use."""
        result = response.get("result", {})
        if not result:
            return

        # Cache task_id for all init methods
        if method.endswith("::init") and "task_id" in result:
            task_group = "::".join(method.split("::")[:-1])
            if "tasks" not in self.method_results_cache:
                self.method_results_cache["tasks"] = {}
            self.method_results_cache["tasks"][task_group] = {"task_id": result["task_id"]}
            self.logger.info(f"Cached task_id for {task_group}: {result['task_id']}")

        # Cache swap UUIDs
        if method in ["buy", "sell"] and "uuid" in result:
            if "swaps" not in self.method_results_cache:
                self.method_results_cache["swaps"] = []
            self.method_results_cache["swaps"].append({"uuid": result["uuid"]})
            self.logger.info(f"Cached swap uuid: {result['uuid']}")

        # Cache signature data
        if method == "sign_message" and "signature" in result:
            self.method_results_cache["signatures"] = {
                "signature": result["signature"],
                "pubkey": result.get("pubkey")
            }
            self.logger.info(f"Cached message signature.")
            
        # Cache unsigned transaction hex
        if method == "get_unsigned_transaction" and "tx_hex" in result:
            self.method_results_cache["unsigned_tx"] = {"tx_hex": result["tx_hex"]}
            self.logger.info(f"Cached unsigned transaction hex.")

    def activate_coin(self, ticker: str, activation_type: str = 'default') -> bool:
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

        act_type_to_use = activation_options.get(activation_type)
        if not act_type_to_use:
            self.logger.error(f"No {activation_type} activation type for protocol '{protocol}'.")
            return False

        activation_method = activation_options.get(act_type_to_use)

        if activation_method is None:
            self.logger.error(f"Activation type '{act_type_to_use}' not available for protocol '{protocol}'.")
            return False
        if not activation_method:
            self.logger.error(f"Activation method for protocol '{protocol}' (type: {act_type_to_use}) is not determined. Skipping.")
            return False

        params = {"ticker": ticker}
        if activation_method.startswith("task::"):
            activation_params = {}
            if protocol in ["ETH", "ERC20"]:
                activation_params["nodes"] = coin_info.get("nodes", [])
                # The task-based ETH activation method requires this parameter, even if empty.
                activation_params["erc20_tokens_requests"] = []
                if "contract_address" in coin_info:
                    activation_params["contract_address"] = coin_info.get("contract_address")

            elif protocol in ["UTXO", "BCH", "SLP", "QTUM", "QRC20"]:
                activation_params["utxo_merge_params"] = {"merge_at": 10}
                rpc_data = {"servers": coin_info.get("electrum", [])}
                activation_params["mode"] = {"rpc": "Electrum", "rpc_data": rpc_data}
                if protocol in ["QRC20"]:
                    if "contract_address" in coin_info:
                        activation_params["contract_address"] = coin_info.get("contract_address")

            elif protocol == "ZHTLC":
                # TODO: Add the zcash params to the docker container
                zcash_params_path = os.getenv("ZCASH_PARAMS_PATH")
                if not zcash_params_path:
                    self.logger.warning("ZCASH_PARAMS_PATH not set, using default: /tmp/.zcash-params")
                    zcash_params_path = "/tmp/.zcash-params"

                rpc_data = {
                    "electrum_servers": coin_info.get("electrum", []),
                    "light_wallet_d_servers": coin_info.get("nodes", [])
                }
                activation_params["mode"] = {"rpc": "Light", "rpc_data": rpc_data}
                activation_params["zcash_params_path"] = zcash_params_path
                activation_params["scan_blocks_per_iteration"] = 100
                activation_params["scan_interval_ms"] = 200

            elif protocol in ["TENDERMINT", "TENDERMINTTOKEN"]:
                activation_params["rpc_urls"] = [node["url"] for node in coin_info.get("nodes", [])]

            elif protocol == "SIA":
                nodes = coin_info.get("nodes", [])
                if not nodes:
                    self.logger.error(f"Missing 'nodes' for SIA coin '{ticker}'.")
                    return False
                
                server_url = nodes[0].get("url")
                if not server_url:
                    self.logger.error(f"Missing 'url' in node configuration for SIA coin '{ticker}'.")
                    return False

                # Password for the SIA wallet daemon, should be in coin config
                password = coin_info.get("password")
                if password is None: # check for None to allow empty string
                    self.logger.error(f"Missing 'password' in config for SIA coin '{ticker}'.")
                    return False

                activation_params["client_conf"] = {
                    "server_url": server_url,
                    "password": password
                }

            params["activation_params"] = activation_params
        else:
            # Legacy non-task based activations
            if protocol in ["ETH", "ERC20"]:
                params["nodes"] = coin_info.get("nodes", [])
                if "contract_address" in coin_info:
                    params["contract_address"] = coin_info.get("contract_address")
            elif protocol in ["UTXO", "BCH", "SLP", "QTUM", "QRC20"]:
                params["utxo_merge_params"] = {"merge_at": 10}
                params["servers"] = coin_info.get("electrum", [])
            elif protocol in ["TENDERMINT", "TENDERMINTTOKEN"]:
                params["rpc_urls"] = [node["url"] for node in coin_info.get("nodes", [])]

        if activation_method in self.v2_methods:
            init_request = {
                "userpass": self.config.openapi.userpass,
                "method": activation_method,
                "mmrpc": "2.0",
                "params": params
            }
        else: # v1 method
            init_request = {
                "userpass": self.config.openapi.userpass,
                "method": activation_method,
                **params
            }
        
        self.logger.info(f"Sending activation request for '{ticker}' with method '{activation_method}'")
        init_response = self._make_request(init_request)

        # Handle "already initialized" error by disabling and retrying
        if init_response and init_response.get("error") and "already initialized" in init_response["error"]:
            self.logger.warning(f"Coin '{ticker}' already initialized. Disabling and retrying.")
            if self.disable_coin(ticker):
                time.sleep(1)  # Give a moment for the state to update
                self.logger.info(f"Retrying activation for '{ticker}'...")
                init_response = self._make_request(init_request)
            else:
                self.logger.error(f"Failed to disable '{ticker}', cannot proceed with activation.")
                return False

        # Handle task-based vs direct activation
        if activation_method in self.v2_methods:
            if init_response and "result" in init_response and "task_id" in init_response["result"]:
                task_id = init_response["result"]["task_id"]
                return self._poll_task_status(task_id, ticker, activation_method)
            else:
                self.logger.error(f"Task-based activation init failed for '{ticker}': {init_response}")
                return False
        else: # v1
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
                "mmrpc": "2.0",
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
                    self.logger.info(f"Activation in progress for '{ticker}'. Details: {details}")
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
        """Disables a coin. This is always a v1 method."""
        self.logger.info(f"Disabling coin '{ticker}'...")
        request_body = {
            "userpass": self.config.openapi.userpass,
            "method": "disable_coin",
            "coin": ticker
        }
        response = self._make_request(request_body)
        if response and response.get("result", {}).get("status") == "success":
            self.logger.success(f"Successfully disabled '{ticker}'.")
            self._update_enabled_coins()
            return True
        else:
            self.logger.error(f"Failed to disable '{ticker}': {response}")
            return False 