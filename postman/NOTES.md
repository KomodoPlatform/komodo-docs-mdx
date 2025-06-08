https://chatgpt.com/share/6843b38b-9ca0-800d-8f91-a62f05f96613

# Enhanced Logging Usage

from utils.py import MethodMapper, MDXToOpenAPIConverter

# Create mappings with detailed logging
mapper = MethodMapper(verbose=True)
mapper.save_unified_mapping()

# Convert MDX to OpenAPI
converter = MDXToOpenAPIConverter()
converter.convert_methods(version="v2", dry_run=True)

# Example Output:
# 
# === Processing V1 Methods ===
# [2024-01-15 14:30:25] activate_coins                    [✓ has yaml] [✓ has mdx]
# [2024-01-15 14:30:25] ban_pubkey                        [✓ has yaml] [✗ no mdx]
# [2024-01-15 14:30:25] best_orders                       [✓ has yaml] [✓ has mdx]
# 
# === Processing V2 Methods ===
# [2024-01-15 14:30:26] task::enable_eth_with_tokens      [✓ has yaml] [✓ has mdx]
# [2024-01-15 14:30:26] lightning::open_channel           [✗ no yaml] [✓ has mdx]
# 
# ============================================================
# MAPPING SUMMARY
# ============================================================
# Total methods: 150
#   v1: 75 methods  
#   v2: 75 methods
# 
# V1 Coverage:
#   ✓ Complete (both MDX & YAML): 65
#   ⚠ MDX only (missing YAML): 8
#   ⚠ YAML only (missing MDX): 2
#   ✗ Missing both: 0
# 
#   Methods missing YAML (v1):
#     - method_without_yaml_1
#     - method_without_yaml_2
# 
#   Methods missing MDX (v1):
#     - method_without_mdx_1
#     - method_without_mdx_2
