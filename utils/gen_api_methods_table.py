#!/usr/bin/env python3
import os
import glob

script_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(script_path)

def gen_api_methods_table():
    atomicdex_files = glob.glob(f'{root_path}/src/pages/atomicdex/**/index.mdx', recursive = True)
    methods_dict = {
        "legacy": [],
        "v20": [],
        "v20-dev": []
    }
    methods_list = []
    for file in atomicdex_files:
        with open(file, 'r') as f:
            for line in f.readlines():
                doc_path = file.replace(f'{root_path}/src/pages', '').replace('/index.mdx', '')
                doc_split = doc_path.split('/')
                if len(doc_split) > 3:
                    section = doc_split[3]
                    if section in methods_dict:
                        if 'CodeGroup' in line and "label" in line:
                            method = line.split('label="')[1].split('"')[0]
                            link = f"[{escape_underscores(method)}]({doc_path}/#{(method.replace('::', '_'))})"
                            methods_dict[section].append({
                                "link": link,
                                "method": method,
                                "doc_url": doc_path
                            })
                            methods_list.append(method)
    methods_list = sorted(list(set(methods_list)))

    with open(f'{script_path}/methods_table.template', 'r') as f:
        template = f.read()
        with open(f'{root_path}/src/pages/atomicdex/api/index.mdx', 'w') as f2:
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
                line = "| {:^108} | {:^108} | {:^108} |".format(legacy, v20, v20_dev)
                f2.write(f"{line}\n")

def escape_underscores(s):
    output = ""
    for letter in s:
        if letter == "_":
            output += "\_"
        else:
            output += letter
    return output

if __name__ == '__main__':
    gen_api_methods_table()
