#!/usr/bin/env python3
"""Test script for table prettification."""

import re

def prettify_tables(content: str) -> str:
    """Prettify markdown tables by aligning columns and ensuring consistent spacing."""
    
    # Find all markdown tables - improved regex pattern
    table_pattern = r'(\| *[^\n|]+ *\|[^\n]*\n)(\| *[-:]+[-| :]*\|\n)((?:\| *[^\n|]+ *\|[^\n]*\n?)*)'
    
    def format_table(match):
        print(f"Found table match:")
        print(f"Header: {repr(match.group(1))}")
        print(f"Separator: {repr(match.group(2))}")
        print(f"Rows: {repr(match.group(3))}")
        
        header = match.group(1).strip()
        separator = match.group(2).strip()
        rows = match.group(3).strip()
        
        # Parse all rows including header
        all_rows = [header]
        if rows:
            all_rows.extend([row.strip() for row in rows.split('\n') if row.strip()])
        
        # Parse cells for each row
        parsed_rows = []
        for row in all_rows:
            if row.strip() and '|' in row:
                cells = [cell.strip() for cell in row.split('|')]
                # Remove empty first and last cells (from leading/trailing |)
                if cells and cells[0] == '':
                    cells = cells[1:]
                if cells and cells[-1] == '':
                    cells = cells[:-1]
                if cells:  # Only add non-empty rows
                    parsed_rows.append(cells)
        
        if not parsed_rows:
            return match.group(0)
        
        print(f"Parsed rows: {parsed_rows}")
        
        # Calculate maximum width for each column, with reasonable limits
        num_cols = len(parsed_rows[0])
        col_widths = [0] * num_cols
        max_width_per_col = 80  # Reasonable maximum width per column
        
        for row in parsed_rows:
            for i, cell in enumerate(row):
                if i < num_cols:
                    # For the description column (usually last), limit width to prevent unwieldy tables
                    if i == num_cols - 1:  # Last column (usually description)
                        col_widths[i] = max(col_widths[i], min(len(cell), max_width_per_col))
                    else:
                        col_widths[i] = max(col_widths[i], len(cell))
        
        print(f"Column widths: {col_widths}")
        
        # Format the table
        formatted_rows = []
        
        # Format header
        header_cells = parsed_rows[0]
        formatted_header = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(header_cells)) + " |"
        formatted_rows.append(formatted_header)
        
        # Format separator with proper alignment
        sep_cells = []
        separator_parts = separator.split('|')
        for i, width in enumerate(col_widths):
            if i + 1 < len(separator_parts):  # Check if alignment specified
                original_sep = separator_parts[i + 1].strip()
                if original_sep.startswith(':') and original_sep.endswith(':'):
                    # Center alignment
                    sep_cells.append(':' + '-' * (width - 2) + ':')
                elif original_sep.endswith(':'):
                    # Right alignment
                    sep_cells.append('-' * (width - 1) + ':')
                else:
                    # Left alignment (default)
                    sep_cells.append('-' * width)
            else:
                sep_cells.append('-' * width)
        
        formatted_separator = "| " + " | ".join(sep_cells) + " |"
        formatted_rows.append(formatted_separator)
        
        # Format data rows
        for row in parsed_rows[1:]:
            if len(row) == num_cols:
                formatted_row = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
                formatted_rows.append(formatted_row)
        
        result = '\n'.join(formatted_rows) + '\n'
        print(f"Formatted result:\n{result}")
        return result
    
    # Apply formatting to all tables
    prettified_content = re.sub(table_pattern, format_table, content, flags=re.MULTILINE)
    
    return prettified_content


# Test with sample content
test_content = """
### Request Parameters

| Parameter | Type | Required | Default | Description |
| --------- | ---- | :------: | :-----: | ----------- |
| userpass | string | ✓ | - | Password for authentication |
| ticker | string | ✓ | - | The ticker symbol of the coin to activate |
| activation_params | object | ✓ | - | A standard [ActivationParams](/komodo-defi-framework/api/common_structures/activation/#activation-params) object containing activation configuration parameters |
| priv_key_policy | string | ✗ | `ContextPrivKey` | Value can be [PrivKeyActivationPolicyEnum](/komodo-defi-framework/api/common_structures/enums/#priv-key-activation-policy-enum) for coin activation |

### Response Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| task_id | integer | The identifier of the initialized task |
"""

if __name__ == "__main__":
    print("Original content:")
    print(test_content)
    print("\n" + "="*50 + "\n")
    
    result = prettify_tables(test_content)
    
    print("Final result:")
    print(result) 