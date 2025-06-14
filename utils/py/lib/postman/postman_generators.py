#!/usr/bin/env python3
"""
Postman Collection and Environment Generators

Handles generation of Postman collections and environment files.
Manages metadata, pre-request scripts, and variable definitions.
"""

import uuid
from datetime import datetime
from typing import Dict, List

from .postman_organizers import PostmanFolder


class CollectionGenerator:
    """
    Generates Postman collections with proper metadata and structure.
    """
    
    def generate_postman_collection(self, version: str, folders: List[PostmanFolder], 
                                   total_requests: int) -> Dict:
        """
        Generate a complete Postman collection.
        
        Args:
            version: API version
            folders: Organized folder structure
            total_requests: Total number of requests
            
        Returns:
            Complete Postman collection dictionary
        """
        collection = {
            "info": self._generate_collection_info(version, total_requests),
            "item": [],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": self._generate_pre_request_script()
                    }
                }
            ],
            "variable": self._generate_collection_variables(version)
        }
        
        # Convert folders to Postman format
        from .postman_organizers import PostmanStructureBuilder
        builder = PostmanStructureBuilder()
        
        for folder in folders:
            collection["item"].append(builder.folder_to_postman_item(folder))
        
        return collection
    
    def _generate_collection_info(self, version: str, total_requests: int) -> Dict:
        """Generate collection info section."""
        return {
            "name": f"Komodo DeFi Framework {version.upper()} API",
            "description": self._generate_collection_description(version, total_requests),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": str(uuid.uuid4()),
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            }
        }
    
    def _generate_collection_description(self, version: str, total_requests: int) -> str:
        """Generate comprehensive collection description."""
        return f"""# Komodo DeFi Framework {version.upper()} API Collection

This collection contains {total_requests} example requests for the Komodo DeFi Framework {version.upper()} API.

## 🚀 Getting Started

1. **Set Environment Variables**:
   - `kdf_url`: Your KDF instance endpoint (e.g., `http://127.0.0.1:7783`)
   - `userpass`: Your configured RPC password

2. **Authentication**:
   - All requests use the `userpass` parameter for authentication
   - Update the default password in the environment variables

3. **Request Format**:
   - All requests use POST method with JSON payload
   - Set `Content-Type: application/json` header

## 📚 Documentation

- [Official API Documentation](https://developers.komodoplatform.com/basic-docs/komodo-defi-framework/api/{version}/)
- [Setup Guide](https://developers.komodoplatform.com/basic-docs/komodo-defi-framework/setup/)
- [GitHub Repository](https://github.com/KomodoPlatform/komodo-defi-framework)

## 🧪 Testing

Each request includes comprehensive test scripts that validate:
- Response status codes
- Response structure
- Error handling
- Performance metrics

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _generate_pre_request_script(self) -> List[str]:
        """Generate pre-request script for all requests."""
        return [
            "// Pre-request script for KDF API",
            "// Ensure required variables are set",
            "",
            "if (!pm.environment.get('kdf_url')) {",
            "    console.warn('⚠️ kdf_url environment variable not set');",
            "}",
            "",
            "if (!pm.environment.get('userpass')) {",
            "    console.warn('⚠️ userpass environment variable not set');",
            "}",
            "",
            "// Set timestamp for request tracking",
            "pm.globals.set('request_timestamp', new Date().toISOString());"
        ]
    
    def _generate_collection_variables(self, version: str) -> List[Dict[str, str]]:
        """Generate collection-level variables."""
        return [
            {
                "key": "kdf_url",
                "value": "http://127.0.0.1:7783",
                "description": "KDF instance URL with IP/domain and port"
            },
            {
                "key": "userpass", 
                "value": "RPC_UserP@SSW0RD",
                "description": "RPC authentication password (update this!)"
            },
            {
                "key": "api_version",
                "value": version,
                "description": f"API version: {version}"
            }
        ]


class EnvironmentGenerator:
    """
    Generates Postman environment files with comprehensive variable sets.
    """
    
    def generate_environment_file(self, version: str) -> Dict:
        """
        Generate a complete Postman environment file.
        
        Args:
            version: API version
            
        Returns:
            Complete environment dictionary
        """
        return {
            "id": str(uuid.uuid4()),
            "name": f"KDF {version.upper()} Environment",
            "values": self._generate_environment_variables(version),
            "_postman_variable_scope": "environment"
        }
    
    def _generate_environment_variables(self, version: str) -> List[Dict]:
        """Generate comprehensive set of environment variables."""
        # Core connection variables
        core_vars = self._get_core_variables(version)
        
        # Trading variables
        trading_vars = self._get_trading_variables()
        
        # Task management variables
        task_vars = self._get_task_variables()
        
        # 1inch integration variables
        oneinch_vars = self._get_oneinch_variables()
        
        return core_vars + trading_vars + task_vars + oneinch_vars
    
    def _get_core_variables(self, version: str) -> List[Dict]:
        """Get core connection and authentication variables."""
        return [
            {
                "key": "kdf_url",
                "value": "http://127.0.0.1:7783",
                "description": "KDF instance URL with IP/domain and port",
                "enabled": True
            },
            {
                "key": "url",
                "value": "127.0.0.1",
                "description": "KDF instance IP or domain",
                "enabled": True
            },
            {
                "key": "port",
                "value": "7783",
                "description": "KDF instance port",
                "enabled": True
            },
            {
                "key": "userpass", 
                "value": "RPC_UserP@SSW0RD",
                "description": "RPC authentication password (update this!)",
                "type": "secret",
                "enabled": True
            },
            {
                "key": "api_version",
                "value": version,
                "description": f"API version: {version}",
                "enabled": True
            },
            {
                "key": "mm2_version",
                "value": "",
                "description": "KDF/MM2 version number",
                "enabled": True
            },
            {
                "key": "address",
                "value": "127.0.0.1:7783",
                "description": "Full KDF address (IP:port)",
                "enabled": True
            }
        ]
    
    def _get_trading_variables(self) -> List[Dict]:
        """Get trading-related variables."""
        return [
            {
                "key": "coin",
                "value": "KMD",
                "description": "Primary coin ticker",
                "enabled": True
            },
            {
                "key": "electrum_coin",
                "value": "KMD",
                "description": "Electrum-based coin ticker",
                "enabled": True
            },
            {
                "key": "base",
                "value": "KMD",
                "description": "Base coin for trading pairs",
                "enabled": True
            },
            {
                "key": "rel",
                "value": "BTC",
                "description": "Related coin for trading pairs",
                "enabled": True
            },
            {
                "key": "amount",
                "value": "1.0",
                "description": "Trading amount",
                "enabled": True
            },
            {
                "key": "slippage",
                "value": "0.5",
                "description": "Acceptable slippage percentage",
                "enabled": True
            },
            {
                "key": "fee",
                "value": "0",
                "description": "Trading fee",
                "enabled": True
            },
            {
                "key": "chain_id",
                "value": "1",
                "description": "Blockchain chain ID (1 = Ethereum mainnet)",
                "enabled": True
            },
            {
                "key": "account_id",
                "value": "0",
                "description": "Account ID for HD wallets",
                "enabled": True
            }
        ]
    
    def _get_task_variables(self) -> List[Dict]:
        """Get task management variables."""
        return [
            {
                "key": "enable_utxo_taskid",
                "value": "",
                "description": "Task ID for UTXO enable operations",
                "enabled": True
            },
            {
                "key": "scan_new_addresses_taskid",
                "value": "",
                "description": "Task ID for address scanning operations",
                "enabled": True
            },
            {
                "key": "init_withdraw_taskid",
                "value": "",
                "description": "Task ID for withdrawal operations",
                "enabled": True
            }
        ]
    
    def _get_oneinch_variables(self) -> List[Dict]:
        """Get 1inch integration variables."""
        return [
            {
                "key": "ONE_INCH_API_TEST_AUTH",
                "value": "",
                "description": "1inch API authentication token",
                "type": "secret",
                "enabled": True
            },
            {
                "key": "protocols",
                "value": "null",
                "description": "1inch protocols parameter",
                "enabled": True
            },
            {
                "key": "gas_price",
                "value": "null",
                "description": "Gas price for Ethereum transactions",
                "enabled": True
            },
            {
                "key": "complexity_level",
                "value": "null",
                "description": "1inch complexity level",
                "enabled": True
            },
            {
                "key": "parts",
                "value": "null",
                "description": "1inch split parts parameter",
                "enabled": True
            },
            {
                "key": "main_route_parts",
                "value": "null",
                "description": "1inch main route parts",
                "enabled": True
            },
            {
                "key": "gas_limit",
                "value": "null",
                "description": "Gas limit for transactions",
                "enabled": True
            },
            {
                "key": "include_tokens_info",
                "value": "true",
                "description": "Include token information in responses",
                "enabled": True
            },
            {
                "key": "include_protocols",
                "value": "true",
                "description": "Include protocol information",
                "enabled": True
            },
            {
                "key": "include_gas",
                "value": "true",
                "description": "Include gas estimation",
                "enabled": True
            },
            {
                "key": "connector_tokens",
                "value": "null",
                "description": "1inch connector tokens",
                "enabled": True
            },
            {
                "key": "excluded_protocols",
                "value": "null",
                "description": "Protocols to exclude from 1inch",
                "enabled": True
            },
            {
                "key": "permit",
                "value": "null",
                "description": "Permit parameter for 1inch",
                "enabled": True
            },
            {
                "key": "compatibility",
                "value": "null",
                "description": "Compatibility mode",
                "enabled": True
            },
            {
                "key": "receiver",
                "value": "null",
                "description": "Receiver address",
                "enabled": True
            },
            {
                "key": "referrer",
                "value": "null",
                "description": "Referrer address",
                "enabled": True
            },
            {
                "key": "disable_estimate",
                "value": "false",
                "description": "Disable gas estimation",
                "enabled": True
            },
            {
                "key": "allow_partial_fill",
                "value": "true",
                "description": "Allow partial order fills",
                "enabled": True
            },
            {
                "key": "use_permit2",
                "value": "false",
                "description": "Use permit2 for approvals",
                "enabled": True
            }
        ] 