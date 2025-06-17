#!/usr/bin/env python3
"""
Coins Configuration Loader

This module provides functionality to load and query the coins_config.json file
to provide contextually appropriate examples based on coin protocol types and
other configuration data.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..utils.logging_utils import get_logger


@dataclass
class CoinConfig:
    """Coin configuration data structure."""
    coin: str
    name: str
    protocol_type: str
    parent_coin: Optional[str] = None
    contract_address: Optional[str] = None
    derivation_path: Optional[str] = None
    chain_id: Optional[int] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    electrum: Optional[List[Dict[str, Any]]] = None
    decimals: Optional[int] = None
    swap_contract_address: Optional[str] = None
    sign_message_prefix: Optional[str] = None
    required_confirmations: Optional[int] = None
    is_testnet: bool = False
    
    @classmethod
    def from_config_dict(cls, coin_ticker: str, config: Dict[str, Any]) -> 'CoinConfig':
        """Create CoinConfig from configuration dictionary."""
        protocol = config.get("protocol", {})
        protocol_type = protocol.get("type", "Unknown")
        
        return cls(
            coin=coin_ticker,
            name=config.get("name", coin_ticker),
            protocol_type=protocol_type,
            parent_coin=config.get("parent_coin"),
            contract_address=config.get("contract_address"),
            derivation_path=config.get("derivation_path"),
            chain_id=config.get("chain_id"),
            nodes=config.get("nodes"),
            electrum=config.get("electrum"),
            decimals=config.get("decimals"),
            swap_contract_address=config.get("swap_contract_address"),
            sign_message_prefix=config.get("sign_message_prefix"),
            required_confirmations=config.get("required_confirmations"),
            is_testnet=config.get("is_testnet", False)
        )


class CoinsConfigLoader:
    """Loader for coins configuration data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the coins config loader."""
        self.logger = get_logger("coins-config-loader")
        
        # Default path to coins_config.json
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "data" / "coins" / "coins_config.json"
        
        self.config_path = config_path
        self._coins_data: Optional[Dict[str, Any]] = None
        self._coins_by_protocol: Optional[Dict[str, List[CoinConfig]]] = None
        
    def load_config(self) -> bool:
        """Load the coins configuration from file."""
        try:
            if not self.config_path.exists():
                self.logger.error(f"Coins config file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._coins_data = json.load(f)
            
            self.logger.info(f"✅ Loaded {len(self._coins_data)} coins from config")
            self._build_protocol_index()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load coins config: {e}")
            return False
    
    def _build_protocol_index(self):
        """Build an index of coins by protocol type."""
        if not self._coins_data:
            return
        
        self._coins_by_protocol = {}
        
        for coin_ticker, config in self._coins_data.items():
            try:
                coin_config = CoinConfig.from_config_dict(coin_ticker, config)
                protocol_type = coin_config.protocol_type
                
                if protocol_type not in self._coins_by_protocol:
                    self._coins_by_protocol[protocol_type] = []
                
                self._coins_by_protocol[protocol_type].append(coin_config)
                
            except Exception as e:
                self.logger.debug(f"Skipping coin {coin_ticker}: {e}")
        
        self.logger.info(f"📊 Indexed coins by protocol: {list(self._coins_by_protocol.keys())}")
    
    def get_coin_config(self, coin_ticker: str) -> Optional[CoinConfig]:
        """Get configuration for a specific coin."""
        if not self._coins_data:
            self.load_config()
        
        if not self._coins_data or coin_ticker not in self._coins_data:
            return None
        
        try:
            return CoinConfig.from_config_dict(coin_ticker, self._coins_data[coin_ticker])
        except Exception as e:
            self.logger.debug(f"Failed to parse config for {coin_ticker}: {e}")
            return None
    
    def get_coins_by_protocol(self, protocol_type: str) -> List[CoinConfig]:
        """Get all coins of a specific protocol type."""
        if not self._coins_by_protocol:
            self.load_config()
        
        if not self._coins_by_protocol:
            return []
        
        return self._coins_by_protocol.get(protocol_type, [])
    
    def get_example_coin_for_method(self, method_name: str) -> Optional[CoinConfig]:
        """Get an appropriate example coin based on the method name."""
        if not self._coins_by_protocol:
            self.load_config()
        
        if not self._coins_by_protocol:
            return None
        
        # Method-specific coin selection logic
        if "erc20" in method_name.lower():
            # For ERC20 methods, use ERC20 tokens
            erc20_coins = self.get_coins_by_protocol("ERC20")
            if erc20_coins:
                # Prefer well-known tokens like USDT
                for coin in erc20_coins:
                    if coin.coin in ["USDT-ERC20", "1INCH-ERC20", "USDC-ERC20"]:
                        return coin
                # Fall back to first available ERC20 token
                return erc20_coins[0]
        
        elif "bch" in method_name.lower():
            # For BCH methods, use BCH
            bch_coins = self.get_coins_by_protocol("BCH")
            if bch_coins:
                return bch_coins[0]
        
        elif "eth" in method_name.lower():
            # For ETH methods, use ETH
            eth_coins = self.get_coins_by_protocol("ETH")
            if eth_coins:
                return eth_coins[0]
        
        elif "lightning" in method_name.lower():
            # For Lightning methods, use Bitcoin
            btc_coins = self.get_coins_by_protocol("UTXO")
            for coin in btc_coins:
                if coin.coin in ["BTC", "tBTC"]:
                    return coin
        
        elif "utxo" in method_name.lower():
            # For UTXO methods, use KMD or other UTXO coins
            utxo_coins = self.get_coins_by_protocol("UTXO")
            if utxo_coins:
                # Prefer KMD for UTXO examples
                for coin in utxo_coins:
                    if coin.coin == "KMD":
                        return coin
                # Fall back to first UTXO coin
                return utxo_coins[0]
        
        elif "tendermint" in method_name.lower():
            # For Tendermint methods, use Cosmos-based coins
            tendermint_coins = self.get_coins_by_protocol("TENDERMINT")
            if tendermint_coins:
                return tendermint_coins[0]
        
        elif "qtum" in method_name.lower():
            # For QTUM methods, use QTUM
            qtum_coins = self.get_coins_by_protocol("QTUM")
            if qtum_coins:
                return qtum_coins[0]
        
        elif "z_coin" in method_name.lower() or "zcoin" in method_name.lower():
            # For Z-coin methods, use privacy coins
            zcoin_coins = self.get_coins_by_protocol("ZHTLC")
            if zcoin_coins:
                return zcoin_coins[0]
        
        # Default fallback - use KMD for general examples
        kmd_config = self.get_coin_config("KMD")
        if kmd_config:
            return kmd_config
        
        # Ultimate fallback - use first available coin
        if self._coins_by_protocol:
            for protocol_coins in self._coins_by_protocol.values():
                if protocol_coins:
                    return protocol_coins[0]
        
        return None
    
    def get_activation_params_example(self, coin_config: CoinConfig) -> Dict[str, Any]:
        """Generate appropriate activation parameters for a coin."""
        if coin_config.protocol_type == "ERC20":
            # ERC20 token activation
            return {
                "mode": {
                    "rpc": "Ethereum",
                    "rpc_data": {
                        "rpc_nodes": [
                            {
                                "url": coin_config.nodes[0]["url"] if coin_config.nodes else "https://eth.drpc.org"
                            }
                        ]
                    }
                }
            }
        
        elif coin_config.protocol_type == "UTXO":
            # UTXO coin activation
            electrum_url = "electrum1.cipig.net:10001"
            if coin_config.electrum:
                electrum_url = coin_config.electrum[0]["url"]
            
            return {
                "mode": {
                    "rpc": "Electrum",
                    "rpc_data": {
                        "electrum_servers": [
                            {
                                "url": electrum_url
                            }
                        ]
                    }
                }
            }
        
        elif coin_config.protocol_type == "ETH":
            # Ethereum activation
            return {
                "mode": {
                    "rpc": "Ethereum",
                    "rpc_data": {
                        "rpc_nodes": [
                            {
                                "url": coin_config.nodes[0]["url"] if coin_config.nodes else "https://eth.drpc.org"
                            }
                        ]
                    }
                }
            }
        
        else:
            # Generic activation
            return {
                "mode": {
                    "rpc": "Native",
                    "rpc_data": {}
                }
            }
    
    def get_available_protocols(self) -> List[str]:
        """Get list of all available protocol types."""
        if not self._coins_by_protocol:
            self.load_config()
        
        return list(self._coins_by_protocol.keys()) if self._coins_by_protocol else [] 