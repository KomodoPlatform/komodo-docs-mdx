#!/usr/bin/env python3
import os
import re
import json

MDX_DIRS = {
    'legacy': '../../src/pages/komodo-defi-framework/api/legacy',
    'v2': '../../src/pages/komodo-defi-framework/api/v20',
    'v2-dev': '../../src/pages/komodo-defi-framework/api/v20-dev',
}
OUTPUT_FILE = 'page_methods.json'
METHOD_PAGES_FILE = 'method_pages.json'

def extract_title(content):
    m = re.search(r'export const title\s*=\s*"([^"]+)"', content)
    return m.group(1) if m else None

def extract_codegroups(content):
    # Returns a list of codegroup blocks (as strings)
    return re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)

def extract_methods_from_codegroup(block, is_legacy):
    v1_methods = []
    v2_methods = []
    # Find all code blocks (```...```)
    code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
    for code in code_blocks:
        # Find method name
        m = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
        if m:
            method = m.group(1)
            # Determine v1 or v2
            if is_legacy:
                v1_methods.append(method)
            elif '"mmrpc": "2.0"' in code:
                v2_methods.append(method)
            else:
                v1_methods.append(method)
    return v1_methods, v2_methods

def scan_mdx_files():
    results = []
    omit_path = os.path.relpath('../../src/pages/komodo-defi-framework/api/v20/index.mdx', '.')
    for version, base_dir in MDX_DIRS.items():
        is_legacy = (version == 'legacy')
        for root, _, files in os.walk(base_dir):
            if 'index.mdx' in files:
                mdx_path = os.path.relpath(os.path.join(root, 'index.mdx'), '.')
                if mdx_path == omit_path:
                    continue
                with open(os.path.join(root, 'index.mdx'), 'r', encoding='utf-8') as f:
                    content = f.read()
                title = extract_title(content)
                codegroups = extract_codegroups(content)
                v1_methods = []
                v2_methods = []
                for block in codegroups:
                    v1, v2 = extract_methods_from_codegroup(block, is_legacy)
                    v1_methods.extend(v1)
                    v2_methods.extend(v2)
                if codegroups:
                    results.append({
                        "file": mdx_path,
                        "title": title,
                        "extracted": {
                            "v1": sorted(list(set(v1_methods))),
                            "v2": sorted(list(set(v2_methods)))
                        }
                    })
    return results

def build_method_pages(page_methods):
    method_pages = {"v1": {}, "v2": {}}
    method_to_pages = {"v1": {}, "v2": {}}
    for entry in page_methods:
        file_path = entry["file"]
        for v in ["v1", "v2"]:
            for method in entry["extracted"][v]:
                if method in method_pages[v]:
                    # Log if a method is linked to more than one page
                    print(f"[WARN] Method '{method}' for {v} found in multiple pages: '{method_pages[v][method]}' and '{file_path}'")
                method_pages[v][method] = file_path
    return method_pages

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    results = scan_mdx_files()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} entries to {OUTPUT_FILE}")
    method_pages = build_method_pages(results)
    with open(METHOD_PAGES_FILE, 'w') as f:
        json.dump(method_pages, f, indent=2)
    print(f"Wrote method-to-page mapping to {METHOD_PAGES_FILE}")

if __name__ == "__main__":
    main() 