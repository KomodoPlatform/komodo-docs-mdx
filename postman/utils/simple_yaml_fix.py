#!/usr/bin/env python3
import os
import re

YAML_DIRS = [
    '../../postman/openapi/paths/v1',
    '../../postman/openapi/paths/v2',
]

def simple_yaml_fix(file_path):
    """Simple fix: only quote summary lines that contain colons and aren't already quoted"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed_lines = []
        changed = False
        
        for line in lines:
            # Only fix summary lines that:
            # 1. Start with summary:
            # 2. Contain a colon in the value part
            # 3. Are not already quoted
            # 4. Are complete on one line
            if re.match(r'^\s*summary:\s*[^"\']*:\s*[^"\'\r\n]*\s*$', line):
                # Extract the indentation and value
                match = re.match(r'^(\s*summary:\s*)(.*)$', line)
                if match:
                    indent_and_key = match.group(1)
                    value = match.group(2).strip()
                    # Quote the value
                    fixed_line = f'{indent_and_key}"{value}"\n'
                    fixed_lines.append(fixed_line)
                    changed = True
                    continue
            
            fixed_lines.append(line)
        
        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            return True
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Apply simple YAML fixes"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    total_fixed = 0
    total_files = 0
    
    for yaml_dir in YAML_DIRS:
        if not os.path.exists(yaml_dir):
            print(f"Warning: Directory {yaml_dir} does not exist")
            continue
            
        for filename in os.listdir(yaml_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                total_files += 1
                file_path = os.path.join(yaml_dir, filename)
                if simple_yaml_fix(file_path):
                    total_fixed += 1
                    print(f"Fixed: {filename}")
    
    print(f"\nFixed {total_fixed} out of {total_files} YAML files")

if __name__ == "__main__":
    main() 