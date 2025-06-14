#!/usr/bin/env python3
import os
import glob
import re
import sys

class TableManager:
    def __init__(self, root_path=None, script_path=None):
        self.script_path = script_path or os.path.dirname(os.path.realpath(__file__))
        self.root_path = root_path or os.path.dirname(os.path.dirname(self.script_path))
        self.DATA_DIR = os.path.join(self.script_path, 'data')

    def generate_api_methods_table(self, template_path=None, output_path=None):
        komodefi_files = glob.glob(f'{self.root_path}/src/pages/komodo-defi-framework/**/index.mdx', recursive=True)
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
                    doc_path = file.replace(f'{self.root_path}/src/pages', '').replace('/index.mdx', '')
                    if 'common_structures' in doc_path:
                        continue
                    doc_split = doc_path.split('/')
                    if len(doc_split) > 3:
                        section = doc_split[3]
                        if section in methods_dict:
                            if line.strip().startswith('## '):
                                heading = line.strip()[3:]
                                method_name = heading.split(' ')[0].split('{')[0].strip()
                                current_method = method_name
                            if 'CodeGroup' in line and current_method is not None:
                                method = current_method
                                hash_link = self.slugify(method)
                                link = f"[{method}]({doc_path}/#{hash_link})"
                                methods_dict[section].append({
                                    "link": link,
                                    "method": method,
                                    "doc_url": doc_path
                                })
                                methods_list.append(method)
        methods_list = sorted(list(set(methods_list)))

        template_path = template_path or os.path.join(self.script_path, 'methods_table.template')
        output_path = output_path or f'{self.root_path}/src/pages/komodo-defi-framework/api/index.mdx'
        
        with open(template_path, 'r') as f:
            template = f.read()
            with open(output_path, 'w') as f2:
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
                    legacy = self.escape_underscores(legacy)
                    v20 = self.escape_underscores(v20)
                    v20_dev = self.escape_underscores(v20_dev)
                    line = "| {:^108} | {:^108} | {:^108} |".format(legacy, v20, v20_dev)
                    f2.write(f"{line}\n")
        self.pretty_print_md_table(output_path)

    @staticmethod
    def escape_underscores(s):
        return ''.join(['\\_' if letter == '_' else letter for letter in s])

    @staticmethod
    def slugify(text):
        text = text.split("{{")[0].strip()
        text = re.sub(r'[:_\s]+', '-', text)
        text = re.sub(r'[^a-zA-Z0-9\-]', '', text)
        return text.lower()

    @staticmethod
    def pretty_print_md_table(input_file):
        with open(input_file, 'r') as f:
            lines = f.readlines()
        # Find the start of the table (first line starting with |)
        table_start = next(i for i, l in enumerate(lines) if l.strip().startswith('|'))
        header = lines[:table_start]
        table = [l.rstrip('\n') for l in lines[table_start:] if l.strip().startswith('|')]
        # Split table into columns
        rows = [re.split(r'\s*\|\s*', row.strip())[1:-1] for row in table]
        # Calculate max width for each column
        widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
        def fmt(row):
            return '| ' + ' | '.join(row[i].ljust(widths[i]) for i in range(len(row))) + ' |'
        pretty_table = [fmt(row) for row in rows]
        with open(input_file, 'w') as f:
            f.writelines(header)
            for row in pretty_table:
                f.write(row + '\n')

if __name__ == '__main__':
    tm = TableManager()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'generate':
            tm.generate_api_methods_table()
        elif sys.argv[1] == 'pretty' and len(sys.argv) > 2:
            tm.pretty_print_md_table(sys.argv[2])
        else:
            print("Usage: python table_manager.py [generate|pretty <file>]")
    else:
        print("Usage: python table_manager.py [generate|pretty <file>]") 