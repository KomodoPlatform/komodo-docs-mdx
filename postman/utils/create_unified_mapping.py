#!/usr/bin/env python3
import os
import json
import re

def extract_operation_id_from_yaml(file_path):
    """Extract operationId from YAML file without full parsing"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for operationId line
        match = re.search(r'^\s*operationId:\s*(.+?)\s*$', content, re.MULTILINE)
        if match:
            operation_id = match.group(1).strip()
            # Remove quotes if present
            operation_id = operation_id.strip('"\'')
            return operation_id
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def load_existing_mappings():
    """Load existing method mappings"""
    try:
        with open('method_pages.json', 'r') as f:
            method_pages = json.load(f)
    except FileNotFoundError:
        print("method_pages.json not found")
        method_pages = {"v1": {}, "v2": {}}
    
    return method_pages

def scan_yaml_files():
    """Scan YAML files using operationId"""
    yaml_dirs = {
        'v1': '../../postman/openapi/paths/v1',
        'v2': '../../postman/openapi/paths/v2',
    }
    
    method_yaml = {"v1": {}, "v2": {}}
    
    for version, base_dir in yaml_dirs.items():
        if not os.path.exists(base_dir):
            continue
            
        for filename in os.listdir(base_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml_path = os.path.join(base_dir, filename)
                relative_path = os.path.relpath(yaml_path, '.')
                
                operation_id = extract_operation_id_from_yaml(yaml_path)
                if operation_id:
                    # Convert operation_id back to method name
                    # For task-based methods, convert dashes to colons
                    if operation_id.startswith('task-'):
                        method = operation_id.replace('-', '::')
                    elif operation_id.startswith('lightning-'):
                        method = operation_id.replace('-', '::')
                    elif operation_id.startswith('stream-'):
                        method = operation_id.replace('-', '::')
                    else:
                        method = operation_id
                    
                    method_yaml[version][method] = relative_path
                else:
                    print(f"Could not extract operationId from {relative_path}")
    
    return method_yaml

def create_unified_mapping():
    """Create unified mapping of method -> {mdx: path, yaml: path}"""
    print("Loading existing MDX mappings...")
    method_pages = load_existing_mappings()
    
    print("Scanning YAML files...")
    method_yaml = scan_yaml_files()
    
    # Create unified mapping
    unified = {"v1": {}, "v2": {}}
    
    # Get all methods from both sources
    all_methods = {"v1": set(), "v2": set()}
    for version in ["v1", "v2"]:
        all_methods[version].update(method_pages[version].keys())
        all_methods[version].update(method_yaml[version].keys())
    
    # Build unified mapping
    for version in ["v1", "v2"]:
        for method in sorted(all_methods[version]):
            unified[version][method] = {
                "mdx": method_pages[version].get(method),
                "yaml": method_yaml[version].get(method)
            }
    
    return unified

def main():
    """Generate unified method mapping"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    unified = create_unified_mapping()
    
    # Write unified mapping
    with open('unified_method_mapping.json', 'w') as f:
        json.dump(unified, f, indent=2)
    
    # Print statistics
    total_methods = sum(len(methods) for methods in unified.values())
    v1_methods = len(unified["v1"])
    v2_methods = len(unified["v2"])
    
    print(f"\nCreated unified mapping with {total_methods} total methods")
    print(f"  v1: {v1_methods} methods")
    print(f"  v2: {v2_methods} methods")
    
    # Print some stats about coverage
    for version in ["v1", "v2"]:
        with_both = sum(1 for m in unified[version].values() if m["mdx"] and m["yaml"])
        mdx_only = sum(1 for m in unified[version].values() if m["mdx"] and not m["yaml"])
        yaml_only = sum(1 for m in unified[version].values() if not m["mdx"] and m["yaml"])
        
        print(f"  {version} coverage: {with_both} both, {mdx_only} MDX only, {yaml_only} YAML only")

if __name__ == "__main__":
    main() 