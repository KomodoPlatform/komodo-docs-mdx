#!/usr/bin/env python3
import os
import re
import yaml
import json

YAML_DIRS = {
    'v1': '../../postman/openapi/paths/v1',
    'v2': '../../postman/openapi/paths/v2',
}
OUTPUT_FILE = 'method_yaml.json'

def extract_method_from_yaml(yaml_content):
    """Extract method name from YAML content"""
    try:
        data = yaml.safe_load(yaml_content)
        # Navigate through the YAML structure to find method enum
        for path, path_data in data.items():
            if 'post' in path_data:
                request_body = path_data['post'].get('requestBody', {})
                content = request_body.get('content', {})
                app_json = content.get('application/json', {})
                schema = app_json.get('schema', {})
                
                # Handle allOf structure
                if 'allOf' in schema:
                    for item in schema['allOf']:
                        if 'properties' in item:
                            method_prop = item['properties'].get('method')
                            if method_prop and 'enum' in method_prop:
                                return method_prop['enum'][0] if method_prop['enum'] else None
                
                # Handle direct properties structure
                if 'properties' in schema:
                    method_prop = schema['properties'].get('method')
                    if method_prop and 'enum' in method_prop:
                        return method_prop['enum'][0] if method_prop['enum'] else None
                        
                # Handle direct enum in method field (some v1 files)
                if 'properties' in schema and 'method' in schema['properties']:
                    method_field = schema['properties']['method']
                    if isinstance(method_field, dict) and 'enum' in method_field:
                        return method_field['enum'][0] if method_field['enum'] else None
                    elif isinstance(method_field, list):
                        return method_field[0] if method_field else None
                        
        # Fallback: try to extract from operationId or summary
        for path, path_data in data.items():
            if 'post' in path_data:
                operation_id = path_data['post'].get('operationId')
                if operation_id and operation_id != path.strip('/'):
                    return operation_id
                    
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
    except Exception as e:
        print(f"Error extracting method: {e}")
    return None

def scan_yaml_files():
    """Scan YAML files and build method to file mapping"""
    method_yaml = {"v1": {}, "v2": {}}
    
    for version, base_dir in YAML_DIRS.items():
        if not os.path.exists(base_dir):
            print(f"Warning: Directory {base_dir} does not exist")
            continue
            
        for filename in os.listdir(base_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml_path = os.path.join(base_dir, filename)
                relative_path = os.path.relpath(yaml_path, '.')
                
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()
                    
                    method = extract_method_from_yaml(yaml_content)
                    if method:
                        if method in method_yaml[version]:
                            print(f"[WARN] Method '{method}' for {version} found in multiple YAML files: '{method_yaml[version][method]}' and '{relative_path}'")
                        method_yaml[version][method] = relative_path
                    else:
                        print(f"[WARN] Could not extract method from {relative_path}")
                        
                except Exception as e:
                    print(f"Error processing {yaml_path}: {e}")
    
    return method_yaml

def main():
    """Main function to generate method to YAML mapping"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("Scanning YAML files...")
    method_yaml = scan_yaml_files()
    
    # Sort the methods for consistent output
    method_yaml_sorted = {
        version: dict(sorted(methods.items())) 
        for version, methods in method_yaml.items()
    }
    
    # Write the output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(method_yaml_sorted, f, indent=2)
    
    total_methods = sum(len(methods) for methods in method_yaml_sorted.values())
    print(f"Wrote {total_methods} method-to-YAML mappings to {OUTPUT_FILE}")
    print(f"  v1: {len(method_yaml_sorted['v1'])} methods")
    print(f"  v2: {len(method_yaml_sorted['v2'])} methods")

if __name__ == "__main__":
    main() 