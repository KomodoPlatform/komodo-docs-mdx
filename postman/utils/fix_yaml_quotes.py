#!/usr/bin/env python3
import os
import re

YAML_DIRS = [
    '../../postman/openapi/paths/v1',
    '../../postman/openapi/paths/v2',
]

def fix_yaml_file(file_path):
    """Fix YAML file by quoting summary fields that contain colons"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix summary lines that contain colons but aren't quoted
        # Only match single-line summaries that end properly (not continuing to next line)
        content = re.sub(
            r'^(\s*summary:\s*)([^"\'\r\n]*:\s*[^"\'\r\n]*)\s*$',
            r'\1"\2"',
            content,
            flags=re.MULTILINE
        )
        
        # Only fix simple single-line descriptions that contain colons
        # Avoid matching multiline descriptions (those that don't end the line)
        content = re.sub(
            r'^(\s*description:\s*)([^"\'\|\>\r\n]*:\s*[^"\'\|\>\r\n]*)\s*$',
            r'\1"\2"',
            content,
            flags=re.MULTILINE
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all YAML files in the specified directories"""
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
                if fix_yaml_file(file_path):
                    total_fixed += 1
                    print(f"Fixed: {filename}")
    
    print(f"\nFixed {total_fixed} out of {total_files} YAML files")

if __name__ == "__main__":
    main() 