#!/usr/bin/env python3
import os
import glob
import re

script_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(os.path.dirname(script_path))
DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

def gen_api_methods_table():
    komodefi_files = glob.glob(f'{root_path}/src/pages/komodo-defi-framework/**/index.mdx', recursive = True)
    methods_dict = {
        "legacy": [],
        "v20": [],
        "v20-dev": []
    }
    methods_list = []
    for file in komodefi_files:
        with open(file, 'r') as f:
            current_method = None
            for line in f.readlines():
                doc_path = file.replace(f'{root_path}/src/pages', '').replace('/index.mdx', '')
                if 'common_structures' in doc_path:
                    continue
                doc_split = doc_path.split('/')
                if len(doc_split) > 3:
                    section = doc_split[3]
                    if section in methods_dict:
                        # Track the most recent method heading
                        if line.strip().startswith('## '):
                            # Extract method name from heading, e.g. ## active_swaps {{label : 'active_swaps', tag : 'API-v2'}}
                            heading = line.strip()[3:]
                            # Only take up to the first space or curly brace
                            method_name = heading.split(' ')[0].split('{')[0].strip()
                            current_method = method_name
                        # When CodeGroup is found, use the most recent method heading
                        if 'CodeGroup' in line and current_method is not None:
                            method = current_method
                            hash_link = slugify(method)
                            link = f"[{method}]({doc_path}/#{hash_link})"
                            methods_dict[section].append({
                                "link": link,
                                "method": method,
                                "doc_url": doc_path
                            })
                            methods_list.append(method)
    methods_list = sorted(list(set(methods_list)))

    with open(f'{script_path}/methods_table.template', 'r') as f:
        template = f.read()
        with open(f'{root_path}/src/pages/komodo-defi-framework/api/index.mdx', 'w') as f2:
            f2.write(template)
            for method in methods_list:
                legacy = ""
                v20 = ""
                v20_dev = ""
                for i in methods_dict.keys():
                    for j in methods_dict[i]:
                        if j["method"] == method:
                            if i == "legacy":
                                legacy = j["link"]
                            if i == "v20":
                                v20 = j["link"]
                            if i == "v20-dev":
                                v20_dev = j["link"]
                legacy = escape_underscores(legacy)
                v20 = escape_underscores(v20)
                v20_dev = escape_underscores(v20_dev)
                line = "| {:^108} | {:^108} | {:^108} |".format(legacy, v20, v20_dev)
                f2.write(f"{line}\n")

def escape_underscores(s):
    output = ""
    for letter in s:
        if letter == "_":
            output += "\\_"
        else:
            output += letter
    return output

def slugify(text):
    text = text.split("{{")[0].strip()
    text = re.sub(r'[:_\s]+', '-', text)
    text = re.sub(r'[^a-zA-Z0-9\-]', '', text)
    return text.lower()

if __name__ == '__main__':
    gen_api_methods_table()
