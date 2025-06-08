#!/usr/bin/env python3
import os
import re

YAML_DIRS = [
    '../../postman/openapi/paths/v1',
    '../../postman/openapi/paths/v2',
]

def fix_broken_yaml_file(file_path):
    """Fix YAML files that have broken multiline descriptions due to incorrect quoting"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix broken multiline descriptions where quotes were incorrectly added
        # Pattern: description: "some text
        #          x-mdx-doc-path: ...
        content = re.sub(
            r'^(\s*description:\s*)"([^"]*?\n.*?)(x-mdx-doc-path:.*?)"\s*$',
            r'\1|\n\1  \2\3',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Fix simpler broken cases where description spans multiple lines incorrectly
        content = re.sub(
            r'^(\s*description:\s*)"([^"]*?\n[^"]*?)\s*$',
            r'\1|\n\1  \2',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Remove quotes from summary lines that should be quoted (keep the good ones)
        # Only remove quotes if they seem to be around simple method names
        content = re.sub(
            r'^(\s*summary:\s*)"(Komodo DeFi Framework Method:\s*[^"]*)"$',
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
    """Fix broken YAML files"""
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
                if fix_broken_yaml_file(file_path):
                    total_fixed += 1
                    print(f"Fixed: {filename}")
    
    print(f"\nFixed {total_fixed} out of {total_files} YAML files")

if __name__ == "__main__":
    main() 