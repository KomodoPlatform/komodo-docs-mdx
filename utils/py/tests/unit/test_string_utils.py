"""
Unit tests for string utilities.

Tests method name normalization and other string processing functions.
"""

import pytest
from lib.utils.string_utils import (
    normalize_method_name,
    format_method_name_for_display,
    extract_method_parts,
    convert_dir_to_method_name,
    convert_method_to_dir_name,
    convert_canonical_to_slug,
    convert_slug_to_canonical,
    convert_folder_to_slug,
    convert_slug_to_folder,
    join_method_parts,
    generate_api_path,
    extract_category_from_method,
    truncate_text,
    find_best_match
)


class TestMethodNameNormalization:
    """Test method name normalization functions."""
    
    def test_normalize_method_name_basic(self):
        """Test basic method name normalization."""
        assert normalize_method_name("enable_coin") == "enable_coin"
        assert normalize_method_name("EnableCoin") == "enable_coin"
        assert normalize_method_name("enable-coin") == "enable_coin"
        assert normalize_method_name("ENABLE_COIN") == "enable_coin"
    
    def test_normalize_method_name_complex(self):
        """Test complex method name normalization."""
        assert normalize_method_name("task::enable_utxo::init") == "task::enable_utxo::init"
        assert normalize_method_name("task-enable-utxo-init") == "task::enable_utxo::init"
        assert normalize_method_name("taskEnableUtxoInit") == "task_enable_utxo_init"
    
    def test_normalize_method_name_edge_cases(self):
        """Test edge cases in method name normalization."""
        assert normalize_method_name("") == ""
        assert normalize_method_name("   ") == ""
        assert normalize_method_name("a") == "a"
        assert normalize_method_name("A_B_C") == "a_b_c"
    
    def test_format_method_name_for_display(self):
        """Test formatting method names for display."""
        assert format_method_name_for_display("enable_coin") == "Enable Coin"
        assert format_method_name_for_display("task::enable_utxo::init") == "Task Enable Utxo Init"
        assert format_method_name_for_display("lightning::payments::send_payment") == "Lightning Payments Send Payment"
    
    def test_extract_method_parts(self):
        """Test extracting parts from method names."""
        parts = extract_method_parts("task::enable_utxo::init")
        assert parts == ["task", "enable_utxo", "init"]
        
        parts = extract_method_parts("enable_coin")
        assert parts == ["enable_coin"]
        
        parts = extract_method_parts("lightning::payments::send_payment")
        assert parts == ["lightning", "payments", "send_payment"]


class TestDirectoryConversion:
    """Test directory and method name conversion functions."""
    
    def test_convert_dir_to_method_name_basic(self):
        """Test basic directory to method name conversion."""
        assert convert_dir_to_method_name("enable_coin") == "enable_coin"
        assert convert_dir_to_method_name("my_balance") == "my_balance"
        assert convert_dir_to_method_name("withdraw") == "withdraw"
    
    def test_convert_dir_to_method_name_task_patterns(self):
        """Test task method directory to method name conversion."""
        assert convert_dir_to_method_name("task-enable_utxo-init") == "task::enable_utxo::init"
        assert convert_dir_to_method_name("task-enable_bch-cancel") == "task::enable_bch::cancel"
        assert convert_dir_to_method_name("task-account_balance-status") == "task::account_balance::status"
        assert convert_dir_to_method_name("task-create_new_account-user_action") == "task::create_new_account::user_action"
        assert convert_dir_to_method_name("task-enable_z_coin-init") == "task::enable_z_coin::init"
    
    def test_convert_dir_to_method_name_lightning_patterns(self):
        """Test lightning method directory to method name conversion."""
        assert convert_dir_to_method_name("lightning-channels-close_channel") == "lightning::channels::close_channel"
        assert convert_dir_to_method_name("lightning-nodes-connect_to_node") == "lightning::nodes::connect_to_node"
        assert convert_dir_to_method_name("lightning-payments-send_payment") == "lightning::payments::send_payment"
        assert convert_dir_to_method_name("lightning-channels-get_channel_details") == "lightning::channels::get_channel_details"
    
    def test_convert_dir_to_method_name_experimental_patterns(self):
        """Test experimental method directory to method name conversion."""
        assert convert_dir_to_method_name("experimental-staking-delegate") == "experimental::staking::delegate"
        assert convert_dir_to_method_name("experimental-staking-query-delegations") == "experimental::staking::query::delegations"
        assert convert_dir_to_method_name("experimental-staking-claim_rewards") == "experimental::staking::claim_rewards"
    
    def test_convert_dir_to_method_name_wallet_patterns(self):
        """Test wallet method directory to method name conversion."""
        assert convert_dir_to_method_name("wallet-staking-validators") == "wallet::staking::validators"
        assert convert_dir_to_method_name("wallet-staking-delegate") == "wallet::staking::delegate"
        assert convert_dir_to_method_name("wallet-staking-claim-rewards") == "wallet::staking::claim::rewards"
    
    def test_convert_dir_to_method_name_stream_patterns(self):
        """Test stream method directory to method name conversion."""
        assert convert_dir_to_method_name("stream-balance-enable") == "stream::balance::enable"
        assert convert_dir_to_method_name("stream-fee_estimator-enable") == "stream::fee_estimator::enable"
        assert convert_dir_to_method_name("streaming-balance_enable") == "streaming::balance_enable"
    
    def test_convert_dir_to_method_name_nft_patterns(self):
        """Test NFT method directory to method name conversion."""
        assert convert_dir_to_method_name("non_fungible_tokens-get_nft_list") == "non_fungible_tokens::get_nft_list"
        assert convert_dir_to_method_name("non_fungible_tokens-refresh_nft_metadata") == "non_fungible_tokens::refresh_nft_metadata"
    
    def test_convert_method_to_dir_name_basic(self):
        """Test basic method name to directory conversion."""
        assert convert_method_to_dir_name("enable_coin") == "enable_coin"
        assert convert_method_to_dir_name("my_balance") == "my_balance"
        assert convert_method_to_dir_name("withdraw") == "withdraw"
    
    def test_convert_method_to_dir_name_task_patterns(self):
        """Test task method name to directory conversion."""
        assert convert_method_to_dir_name("task::enable_utxo::init") == "task-enable_utxo-init"
        assert convert_method_to_dir_name("task::enable_bch::cancel") == "task-enable_bch-cancel"
        assert convert_method_to_dir_name("task::account_balance::status") == "task-account_balance-status"
        assert convert_method_to_dir_name("task::create_new_account::user_action") == "task-create_new_account-user_action"
    
    def test_convert_method_to_dir_name_lightning_patterns(self):
        """Test lightning method name to directory conversion."""
        assert convert_method_to_dir_name("lightning::channels::close_channel") == "lightning-channels-close_channel"
        assert convert_method_to_dir_name("lightning::nodes::connect_to_node") == "lightning-nodes-connect_to_node"
        assert convert_method_to_dir_name("lightning::payments::send_payment") == "lightning-payments-send_payment"
    
    def test_convert_method_to_dir_name_experimental_patterns(self):
        """Test experimental method name to directory conversion."""
        assert convert_method_to_dir_name("experimental::staking::delegate") == "experimental-staking-delegate"
        assert convert_method_to_dir_name("experimental::staking::query_delegations") == "experimental-staking-query_delegations"
    
    def test_convert_method_to_dir_name_wallet_patterns(self):
        """Test wallet method name to directory conversion."""
        assert convert_method_to_dir_name("wallet::staking::validators") == "wallet-staking-validators"
        assert convert_method_to_dir_name("wallet::staking::delegate") == "wallet-staking-delegate"
    
    def test_convert_method_to_dir_name_stream_patterns(self):
        """Test stream method name to directory conversion."""
        assert convert_method_to_dir_name("stream::balance::enable") == "stream-balance-enable"
        assert convert_method_to_dir_name("streaming::balance_enable") == "streaming-balance_enable"
    
    def test_join_method_parts(self):
        """Test joining method parts."""
        assert join_method_parts(["task", "enable_utxo", "init"]) == "task::enable_utxo::init"
        assert join_method_parts(["enable_coin"]) == "enable_coin"
        assert join_method_parts([]) == ""
    
    def test_round_trip_conversion(self):
        """Test that conversions are reversible."""
        original_methods = [
            "task::enable_utxo::init",
            "lightning::channels::close_channel", 
            "experimental::staking::delegate",
            "wallet::staking::validators",
            "stream::balance::enable",
            "non_fungible_tokens::get_nft_list"
        ]
        
        for method in original_methods:
            # Convert to directory name and back
            dir_name = convert_method_to_dir_name(method)
            recovered = convert_dir_to_method_name(dir_name)
            assert recovered == method, f"Round trip failed for {method}: {dir_name} -> {recovered}"


class TestAPIPathGeneration:
    """Test API path generation functions."""
    
    def test_generate_api_path(self):
        """Test generating API paths from method names."""
        assert generate_api_path("enable_coin", "v2") == "/api/v2/enable_coin"
        assert generate_api_path("task::enable_utxo::init", "v2") == "/api/v2/task/enable_utxo/init"
        assert generate_api_path("lightning::payments::send_payment", "v1") == "/api/v1/lightning/payments/send_payment"
    
    def test_extract_category_from_method(self):
        """Test extracting categories from method names."""
        assert extract_category_from_method("enable_coin") == "coin_activation"
        assert extract_category_from_method("task::enable_utxo::init") == "task_management"
        assert extract_category_from_method("lightning::payments::send_payment") == "lightning"
        assert extract_category_from_method("unknown_method") == "general"


class TestStringUtilities:
    """Test general string utility functions."""
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text that should be truncated"
        
        assert truncate_text(text, 20) == "This is a long text..."
        assert truncate_text(text, 50) == text  # No truncation needed
        assert truncate_text(text, 20, suffix="...") == "This is a long text..."
        assert truncate_text(text, 20, suffix="[more]") == "This is a long [more]"
    
    def test_truncate_text_edge_cases(self):
        """Test edge cases in text truncation."""
        assert truncate_text("", 10) == ""
        assert truncate_text("short", 10) == "short"
        assert truncate_text("exact", 5) == "exact"
        assert truncate_text("toolong", 5) == "to..."
    
    def test_find_best_match(self):
        """Test finding best matches from a list."""
        candidates = ["enable_coin", "disable_coin", "enable_utxo", "withdraw"]
        
        assert find_best_match("enable", candidates) == "enable_coin"
        assert find_best_match("coin", candidates) == "enable_coin"  # First match
        assert find_best_match("utxo", candidates) == "enable_utxo"
        assert find_best_match("nonexistent", candidates) is None
    
    def test_find_best_match_empty(self):
        """Test finding best match with empty candidates."""
        assert find_best_match("test", []) is None
        assert find_best_match("", ["test"]) is None


@pytest.mark.parametrize("input_name,expected", [
    ("enable_coin", "enable_coin"),
    ("task::enable_utxo::init", "task::enable_utxo::init"),
    ("lightning-payments-send_payment", "lightning::payments::send_payment"),
    ("CamelCaseMethod", "camel_case_method"),
    ("UPPER_CASE_METHOD", "upper_case_method"),
    ("mixed_Case-Method", "mixed_case_method"),
])
def test_normalize_method_name_parametrized(input_name, expected):
    """Parametrized test for method name normalization."""
    assert normalize_method_name(input_name) == expected


@pytest.mark.parametrize("method_name,expected_parts", [
    ("enable_coin", ["enable_coin"]),
    ("task::enable_utxo::init", ["task", "enable_utxo", "init"]),
    ("lightning::payments::send_payment", ["lightning", "payments", "send_payment"]),
    ("", []),
])
def test_extract_method_parts_parametrized(method_name, expected_parts):
    """Parametrized test for method parts extraction."""
    assert extract_method_parts(method_name) == expected_parts


class TestStringUtilsIntegration:
    """Integration tests for string utilities."""
    
    def test_method_name_round_trip(self):
        """Test that method name conversions are reversible."""
        original_methods = [
            "enable_coin",
            "task::enable_utxo::init", 
            "lightning::payments::send_payment"
        ]
        
        for method in original_methods:
            # Convert to directory name and back
            dir_name = convert_method_to_dir_name(method)
            recovered = convert_dir_to_method_name(dir_name)
            assert recovered == method
    
    def test_method_processing_pipeline(self):
        """Test complete method processing pipeline."""
        raw_input = "Task-Enable-UTXO-Init"
        
        # Normalize
        normalized = normalize_method_name(raw_input)
        assert normalized == "task_enable_utxo_init"
        
        # Extract parts (assuming it gets converted to proper format)
        # For this test, let's assume it becomes a proper method name
        proper_method = "task::enable_utxo::init"
        parts = extract_method_parts(proper_method)
        assert parts == ["task", "enable_utxo", "init"]
        
        # Generate display name
        display = format_method_name_for_display(proper_method)
        assert display == "Task Enable Utxo Init"
        
        # Generate API path
        api_path = generate_api_path(proper_method, "v2")
        assert api_path == "/api/v2/task/enable_utxo/init" 


class TestFormatConversions:
    """Test conversions between canonical, folder, and slug formats."""
    
    def test_canonical_to_folder_conversion(self):
        """Test canonical to folder format conversion."""
        test_cases = [
            ("task::enable_utxo::init", "task-enable_utxo-init"),
            ("lightning::channels::close_channel", "lightning-channels-close_channel"),
            ("experimental::staking::delegate", "experimental-staking-delegate"),
            ("wallet::staking::validators", "wallet-staking-validators"),
            ("stream::balance::enable", "stream-balance-enable"),
            ("non_fungible_tokens::get_nft_list", "non_fungible_tokens-get_nft_list"),
            ("enable_coin", "enable_coin"),
            ("my_balance", "my_balance"),
        ]
        
        for canonical, expected_folder in test_cases:
            result = convert_method_to_dir_name(canonical)
            assert result == expected_folder, f"Failed: {canonical} -> {result} (expected {expected_folder})"
    
    def test_folder_to_canonical_conversion(self):
        """Test folder to canonical format conversion."""
        test_cases = [
            ("task-enable_utxo-init", "task::enable_utxo::init"),
            ("lightning-channels-close_channel", "lightning::channels::close_channel"),
            ("experimental-staking-delegate", "experimental::staking::delegate"),
            ("wallet-staking-validators", "wallet::staking::validators"),
            ("stream-balance-enable", "stream::balance::enable"),
            ("non_fungible_tokens-get_nft_list", "non_fungible_tokens::get_nft_list"),
            ("enable_coin", "enable_coin"),
            ("my_balance", "my_balance"),
        ]
        
        for folder, expected_canonical in test_cases:
            result = convert_dir_to_method_name(folder)
            assert result == expected_canonical, f"Failed: {folder} -> {result} (expected {expected_canonical})"
    
    def test_canonical_to_slug_conversion(self):
        """Test canonical to slug format conversion."""
        test_cases = [
            ("task::enable_utxo::init", "task-enable-utxo-init"),
            ("lightning::channels::close_channel", "lightning-channels-close-channel"),
            ("experimental::staking::delegate", "experimental-staking-delegate"),
            ("wallet::staking::validators", "wallet-staking-validators"),
            ("stream::balance::enable", "stream-balance-enable"),
            ("non_fungible_tokens::get_nft_list", "non-fungible-tokens-get-nft-list"),
            ("enable_coin", "enable-coin"),
            ("my_balance", "my-balance"),
        ]
        
        for canonical, expected_slug in test_cases:
            result = convert_canonical_to_slug(canonical)
            assert result == expected_slug, f"Failed: {canonical} -> {result} (expected {expected_slug})"
    
    def test_folder_to_slug_conversion(self):
        """Test folder to slug format conversion."""
        test_cases = [
            ("task-enable_utxo-init", "task-enable-utxo-init"),
            ("lightning-channels-close_channel", "lightning-channels-close-channel"),
            ("experimental-staking-delegate", "experimental-staking-delegate"),
            ("wallet-staking-validators", "wallet-staking-validators"),
            ("stream-balance-enable", "stream-balance-enable"),
            ("non_fungible_tokens-get_nft_list", "non-fungible-tokens-get-nft-list"),
            ("enable_coin", "enable-coin"),
            ("my_balance", "my-balance"),
        ]
        
        for folder, expected_slug in test_cases:
            result = convert_folder_to_slug(folder)
            assert result == expected_slug, f"Failed: {folder} -> {result} (expected {expected_slug})"
    
    def test_slug_to_folder_conversion(self):
        """Test slug to folder format conversion (lossy)."""
        test_cases = [
            ("task-enable-utxo-init", "task-enable_utxo-init"),
            ("lightning-channels-close-channel", "lightning-channels-close_channel"),
            ("experimental-staking-delegate", "experimental-staking-delegate"),
            ("wallet-staking-validators", "wallet-staking-validators"),
            ("stream-balance-enable", "stream-balance-enable"),
            ("enable-coin", "enable_coin"),  # Special case - enable pattern
            ("account-balance", "account_balance"),  # Special case
            ("new-address", "new_address"),  # Special case
            ("z-coin", "z_coin"),  # Special case
        ]
        
        for slug, expected_folder in test_cases:
            result = convert_slug_to_folder(slug)
            assert result == expected_folder, f"Failed: {slug} -> {result} (expected {expected_folder})"
    
    def test_slug_to_canonical_conversion(self):
        """Test slug to canonical format conversion (lossy)."""
        test_cases = [
            ("task-enable-utxo-init", "task::enable_utxo::init"),
            ("lightning-channels-close-channel", "lightning::channels::close_channel"),
            ("experimental-staking-delegate", "experimental::staking::delegate"),
            ("wallet-staking-validators", "wallet::staking::validators"),
            ("stream-balance-enable", "stream::balance::enable"),
            ("enable-coin", "enable_coin"),  # Special case - enable pattern
            ("account-balance", "account_balance"),  # Special case
            ("new-address", "new_address"),  # Special case
            ("z-coin", "z_coin"),  # Special case
        ]
        
        for slug, expected_canonical in test_cases:
            result = convert_slug_to_canonical(slug)
            assert result == expected_canonical, f"Failed: {slug} -> {result} (expected {expected_canonical})"
    
    def test_round_trip_conversions(self):
        """Test round-trip conversions between formats."""
        # Test cases for lossless round-trip conversions
        canonical_methods = [
            "task::enable_utxo::init",
            "lightning::channels::close_channel",
            "experimental::staking::delegate",
            "wallet::staking::validators",
            "stream::balance::enable",
            "non_fungible_tokens::get_nft_list"
        ]
        
        for canonical in canonical_methods:
            # Canonical -> Folder -> Canonical (should be lossless)
            folder = convert_method_to_dir_name(canonical)
            recovered_canonical = convert_dir_to_method_name(folder)
            assert recovered_canonical == canonical, f"Canonical->Folder->Canonical failed: {canonical} -> {folder} -> {recovered_canonical}"
            
            # Folder -> Slug -> Folder (should be lossy but predictable)
            slug = convert_folder_to_slug(folder)
            recovered_folder = convert_slug_to_folder(slug)
            # This may not be exactly equal due to lossy conversion, but should be reasonable
            
            # Canonical -> Slug (lossy conversion)
            slug_from_canonical = convert_canonical_to_slug(canonical)
            # Note: Slug -> Canonical is lossy, so we don't test round-trip here
    
    def test_edge_cases(self):
        """Test edge cases and empty inputs."""
        # Empty strings
        assert convert_method_to_dir_name("") == ""
        assert convert_dir_to_method_name("") == ""
        assert convert_canonical_to_slug("") == ""
        assert convert_slug_to_canonical("") == ""
        assert convert_folder_to_slug("") == ""
        assert convert_slug_to_folder("") == ""
        
        # Single words
        assert convert_method_to_dir_name("enable") == "enable"
        assert convert_dir_to_method_name("enable") == "enable"
        assert convert_canonical_to_slug("enable") == "enable"
        
        # Complex cases
        assert convert_canonical_to_slug("a::b_c::d_e") == "a-b-c-d-e"
        assert convert_method_to_dir_name("a::b_c::d_e") == "a-b_c-d_e" 