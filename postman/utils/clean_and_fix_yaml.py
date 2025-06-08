#!/usr/bin/env python3
import os
import re

YAML_DIRS = [
    '../../postman/openapi/paths/v1',
    '../../postman/openapi/paths/v2',
]

def clean_and_fix_yaml_file(file_path):
    """Remove all incorrectly added quotes, then selectively add them back where needed"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Step 1: Remove incorrectly added quotes from summary and description lines
        # Remove quotes from summary lines
        content = re.sub(
            r'^(\s*summary:\s*)"([^"]*)"(\s*)$',
            r'\1\2\3',
            content,
            flags=re.MULTILINE
        )
        
        # Remove quotes from description lines (including broken multiline ones)
        content = re.sub(
            r'^(\s*description:\s*)"([^"]*?)$',
            r'\1\2',
            content,
            flags=re.MULTILINE
        )
        
        # Clean up any remaining orphaned quotes at the end of lines
        content = re.sub(r'"\s*$', '', content, flags=re.MULTILINE)
        
        # Step 2: Selectively add quotes back where needed
        # Add quotes to summary lines that contain colons (the original problem)
        content = re.sub(
            r'^(\s*summary:\s*)(.*?:\s*.*?)(\s*)$',
            r'\1"\2"\3',
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
    """Clean and fix all YAML files"""
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
                if clean_and_fix_yaml_file(file_path):
                    total_fixed += 1
                    print(f"Fixed: {filename}")
    
    print(f"\nFixed {total_fixed} out of {total_files} YAML files")

if __name__ == "__main__":
    main() 