#!/usr/bin/env python3
import re
import os
import sys

DOCS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'docs')

if len(sys.argv) > 1:
    INPUT_FILE = sys.argv[1]
else:
    INPUT_FILE = f'{DOCS_DIR}/style-update-progress.md'

with open(INPUT_FILE, 'r') as f:
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

with open(INPUT_FILE, 'w') as f:
    f.writelines(header)
    for row in pretty_table:
        f.write(row + '\n') 