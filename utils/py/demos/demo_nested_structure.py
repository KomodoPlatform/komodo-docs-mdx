#!/usr/bin/env python3
"""
Demo and Diagnostic Script: Nested Directory Structure

This script demonstrates and tests the nested directory structure functionality.
It's useful for:
- Testing path mapping logic
- Comparing flat vs nested structures  
- Validating configuration changes
- Debugging path resolution issues

Usage:
    python demo_nested_structure.py              # Run full demo
    python demo_nested_structure.py --test-only  # Just test path mapping
    python demo_nested_structure.py --validate   # Validate current setup

The nested structure is actively used (USE_NESTED_STRUCTURE=true in sync_kdf.sh).
This demo helps understand and troubleshoot the system.
"""

import sys
import os
import argparse
from pathlib import Path

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from path_utils import PathMapper, VersionStatus

def demo_path_mapping():
    """Demonstrate the path mapping functionality."""
    print("🗂️  Nested Directory Structure Demo")
    print("=" * 50)
    
    mapper = PathMapper('.')
    
    # Test different method types
    test_methods = [
        ('active_swaps', 'src/pages/komodo-defi-framework/api/v20/swaps_and_orders/active_swaps/index.mdx', 'v2'),
        ('lightning::channels::open_channel', 'src/pages/komodo-defi-framework/api/v20/lightning/channels/open_channel/index.mdx', 'v2'),
        ('task::enable_eth::init', 'src/pages/komodo-defi-framework/api/v20/coin_activation/task_managed/enable_eth/init/index.mdx', 'v2'),
        ('stream::orderbook::enable', 'src/pages/komodo-defi-framework/api/v20/streaming/orderbook_enable/index.mdx', 'v2'),
        ('enable_nft', 'src/pages/komodo-defi-framework/api/v20/non_fungible_tokens/enable_nft/index.mdx', 'v2'),
        ('get_wallet_names', 'src/pages/komodo-defi-framework/api/v20/wallet/get_wallet_names/index.mdx', 'v2'),
        ('enable', 'src/pages/komodo-defi-framework/api/legacy/coin_activation/enable/index.mdx', 'v1')
    ]
    
    for method_name, mdx_path, version in test_methods:
        print(f"\n📄 Method: {method_name} ({version})")
        print(f"   MDX: {mdx_path}")
        
        mapping = mapper.get_method_path_mapping(method_name, mdx_path, version)
        
        print(f"   📁 Category: {mapping.category}")
        if mapping.subcategory:
            print(f"   📂 Subcategory: {mapping.subcategory}")
        print(f"   🔗 OpenAPI: {mapping.openapi_path}")
        print(f"   📦 JSON: {mapping.postman_json_path}")

def demo_version_handling():
    """Demonstrate version handling and migration support."""
    print("\n\n🔄 Version Migration Demo")
    print("=" * 50)
    
    mapper = PathMapper('.')
    
    print("Available versions:")
    for version in mapper.get_all_versions(include_deprecated=True):
        status = mapper.get_version_status(version)
        status_emoji = {
            VersionStatus.ACTIVE: "✅",
            VersionStatus.DEVELOPMENT: "🚧", 
            VersionStatus.DEPRECATED: "⚠️",
            VersionStatus.LEGACY: "📜"
        }
        print(f"  {status_emoji.get(status, '❓')} {version}: {status.value}")

def demo_structure_comparison():
    """Compare flat vs nested structures."""
    print("\n\n📊 Structure Comparison")
    print("=" * 50)
    
    method_name = "lightning::channels::open_channel"
    mdx_path = "src/pages/komodo-defi-framework/api/v20/lightning/channels/open_channel/index.mdx"
    version = "v2"
    
    # Nested structure
    mapper = PathMapper('.')
    nested_mapping = mapper.get_method_path_mapping(method_name, mdx_path, version)
    
    print("🗂️  NESTED STRUCTURE (New - Organized):")
    print(f"   OpenAPI: {nested_mapping.openapi_path}")
    print(f"   JSON: {nested_mapping.postman_json_path}")
    
    print("\n📁 FLAT STRUCTURE (Current - All in one folder):")
    print(f"   OpenAPI: openapi/paths/v2/lightning_channels_open_channel.yaml")
    print(f"   JSON: postman/json/kdf/v2/lightning-channels-open_channel/")
    
    print("\n💡 Benefits of nested structure:")
    print("   ✅ Organized by functional area (lightning/channels/)")
    print("   ✅ Easy to find related methods")
    print("   ✅ Scalable for future growth")
    print("   ✅ Matches documentation structure")
    print("   ✅ Handles version migrations gracefully")

def demo_future_flexibility():
    """Demonstrate how the system handles future changes."""
    print("\n\n🔮 Future Flexibility Demo")
    print("=" * 50)
    
    print("🔄 Version Migration Scenarios:")
    print("   1. v2-dev → v2: Methods automatically migrate to stable paths")
    print("   2. v2 → deprecated: Old paths preserved, new methods redirect")
    print("   3. New categories: Easy to add via category mappings")
    
    print("\n📝 Example: If we add v3 with new structure:")
    print("   - Add VersionConfig for v3 in path_utils.py")
    print("   - Update category mappings if needed")
    print("   - All generators automatically support v3")
    
    print("\n🏗️  Example: If we reorganize categories:")
    print("   - Update category_mappings in PathMapper")
    print("   - Old paths still work (backward compatibility)")
    print("   - New paths use updated structure")

def validate_setup():
    """Validate that the nested structure setup is working correctly."""
    print("🔍 Validating Nested Structure Setup")
    print("=" * 50)
    
    mapper = PathMapper('.')
    
    # Test a few key mappings
    test_cases = [
        ('active_swaps', 'src/pages/komodo-defi-framework/api/v20/swaps_and_orders/active_swaps/index.mdx', 'v2'),
        ('lightning::channels::open_channel', 'src/pages/komodo-defi-framework/api/v20/lightning/channels/open_channel/index.mdx', 'v2'),
    ]
    
    all_passed = True
    
    for method_name, mdx_path, version in test_cases:
        try:
            mapping = mapper.get_method_path_mapping(method_name, mdx_path, version)
            print(f"✅ {method_name}: Path mapping successful")
        except Exception as e:
            print(f"❌ {method_name}: Error - {e}")
            all_passed = False
    
    # Check version configs
    for version in ['v1', 'v2', 'v2-dev']:
        if version in mapper.version_configs:
            print(f"✅ Version {version}: Configuration found")
        else:
            print(f"❌ Version {version}: Configuration missing")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All validations passed! Nested structure is working correctly.")
    else:
        print("\n⚠️  Some validations failed. Check the configuration.")
    
    return all_passed

def main():
    """Main function with command line argument support."""
    parser = argparse.ArgumentParser(description='Demo and test nested directory structure')
    parser.add_argument('--test-only', action='store_true', 
                       help='Only run path mapping tests')
    parser.add_argument('--validate', action='store_true',
                       help='Validate current setup')
    
    args = parser.parse_args()
    
    if args.validate:
        validate_setup()
    elif args.test_only:
        demo_path_mapping()
    else:
        # Run full demo
        demo_path_mapping()
        demo_version_handling()
        demo_structure_comparison()
        demo_future_flexibility()
        
        print("\n\n🎉 Demo Complete!")
        print("The nested structure system is ready for implementation!")

if __name__ == "__main__":
    main() 