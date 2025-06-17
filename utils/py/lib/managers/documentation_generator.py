#!/usr/bin/env python3
"""
KDF Documentation Generator

This module generates comprehensive MDX documentation files from analysis data
using templates and detailed method information.

Integrates with the scanning infrastructure and managers.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ..utils.logging_utils import get_logger
from ..constants import get_config
from ..utils import safe_read_json, safe_write_json, ensure_directory_exists


class DocumentationGenerator:
    """
    Generates KDF method documentation from analysis data using templates.
    Integrates with the existing library infrastructure.
    """
    
    def __init__(self, 
                 template_file: Optional[Path] = None, 
                 output_base: Optional[Path] = None,
                 data_dir: Optional[Path] = None):
        self.logger = get_logger("doc-generator")
        self.script_dir = Path(__file__).parent.parent.parent
        
        # Set up paths
        self.data_dir = data_dir or (self.script_dir / "data")
        self.template_file = template_file or (self.script_dir.parent.parent / "docs" / "templates" / "komodefi_method.mdx")
        self.output_base = output_base or (self.script_dir.parent.parent)
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        
        # Load template
        self._load_template()
        
        # Set up output directories
        self.docs_dir = self.output_base / "src" / "pages" / "komodo-defi-framework" / "api"
        self.sidebar_file = self.output_base / "sidebar.json"
        
        # Load existing sidebar if available
        self.sidebar_data = {}
        if self.sidebar_file.exists():
            try:
                self.sidebar_data = safe_read_json(self.sidebar_file)
            except Exception as e:
                self.logger.warning(f"Could not load sidebar: {e}")
    
    def _load_template(self):
        """Load the MDX template."""
        try:
            if self.template_file.exists():
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    self.template_content = f.read()
                self.logger.info(f"Loaded template from {self.template_file}")
            else:
                self.logger.warning(f"Template file not found: {self.template_file}")
                self.template_content = self._get_default_template()
        except Exception as e:
            self.logger.error(f"Error loading template: {e}")
            self.template_content = self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Get a default template if none is available."""
        return '''export const title = "Komodo DeFi Framework Method: {human_title}";
export const description = "{description}";

# {human_title}

## {method_name} {{{{label : '{method_name}', tag : '{api_tag}'}}}}

{description}

### Request Parameters

{request_params_table}

### Response Parameters

{response_params_table}

#### 📌 Examples

<CodeGroup>
```json Request
{example_request}
```
</CodeGroup>

<CollapsibleSection expandedText="Hide Response" collapsedText="Show Response">
```json Response
{example_response}
```
</CollapsibleSection>
'''
    
    def humanize_method_name(self, method_name: str) -> str:
        """Convert API method name to human-readable title."""
        # Handle specific patterns first
        conversions = {
            "task::enable_bch::cancel": "Cancel Enable BCH Task",
            "task::enable_bch::init": "Initialize Enable BCH Task", 
            "task::enable_bch::status": "Enable BCH Task Status",
            "task::enable_bch::user_action": "Enable BCH Task User Action",
            "task::enable_eth::cancel": "Cancel Enable ETH Task",
            "task::enable_eth::init": "Initialize Enable ETH Task",
            "task::enable_eth::status": "Enable ETH Task Status", 
            "task::enable_eth::user_action": "Enable ETH Task User Action",
            "task::enable_utxo::cancel": "Cancel Enable UTXO Task",
            "task::enable_utxo::init": "Initialize Enable UTXO Task",
            "task::enable_utxo::status": "Enable UTXO Task Status",
            "task::enable_utxo::user_action": "Enable UTXO Task User Action",
            "task::create_new_account::cancel": "Cancel Create New Account Task",
            "task::create_new_account::init": "Initialize Create New Account Task",
            "task::create_new_account::status": "Create New Account Task Status",
            "task::create_new_account::user_action": "Create New Account Task User Action",
            "lightning::nodes::connect_to_node": "Connect to Lightning Node",
            "lightning::channels::open_channel": "Open Lightning Channel",
            "lightning::payments::send_payment": "Send Lightning Payment",
            "stream::swap_status::enable": "Enable Swap Status Stream",
            "stream::orderbook::enable": "Enable Orderbook Stream",
            "stream::disable": "Disable Stream"
        }
        
        if method_name in conversions:
            return conversions[method_name]
        
        # Generic conversion for other methods
        parts = method_name.split("::")
        
        # Handle task methods
        if method_name.startswith("task::"):
            if len(parts) >= 3:
                task_type = parts[1].replace("_", " ").title()
                action = parts[2].replace("_", " ").title()
                return f"{action} {task_type} Task"
        
        # Handle lightning methods
        elif method_name.startswith("lightning::"):
            if len(parts) >= 3:
                category = parts[1].replace("_", " ").title()
                action = parts[2].replace("_", " ").title()
                return f"{action} Lightning {category[:-1] if category.endswith('s') else category}"
        
        # Handle stream methods
        elif method_name.startswith("stream::"):
            if len(parts) >= 3:
                stream_type = parts[1].replace("_", " ").title()
                action = parts[2].replace("_", " ").title()
                return f"{action} {stream_type} Stream"
            elif method_name == "stream::disable":
                return "Disable Stream"
        
        # Handle GUI storage methods
        elif method_name.startswith("gui_storage::"):
            action = parts[1].replace("_", " ").title()
            return f"GUI Storage: {action}"
        
        # Generic title case conversion
        return " ".join(part.replace("_", " ").title() for part in parts)
    
    def create_method_description(self, method_name: str, method_info: Dict[str, Any]) -> str:
        """Create a concise description for the method."""
        if method_info.get("description"):
            # Clean up the description from code comments
            desc = method_info["description"]
            # Remove code artifacts and make it concise
            desc = re.sub(r'https?://[^\s]+', '', desc)  # Remove URLs
            desc = re.sub(r'\s+', ' ', desc)  # Normalize whitespace
            return desc.strip()[:200] + "..." if len(desc) > 200 else desc.strip()
        
        # Generate generic description based on method name
        if "cancel" in method_name:
            return f"Cancel the {method_name.replace('::cancel', '').replace('::', ' ')} operation in the Komodo DeFi Framework API."
        elif "init" in method_name:
            return f"Initialize the {method_name.replace('::init', '').replace('::', ' ')} operation in the Komodo DeFi Framework API."
        elif "status" in method_name:
            return f"Get status of the {method_name.replace('::status', '').replace('::', ' ')} operation in the Komodo DeFi Framework API."
        elif "enable" in method_name:
            return f"Enable the {method_name.replace('enable', '').replace('::', ' ')} feature in the Komodo DeFi Framework API."
        else:
            return f"Execute the {method_name.replace('::', ' ')} operation in the Komodo DeFi Framework API."
    
    def format_rust_type(self, rust_type: str) -> str:
        """Convert Rust types to documentation-friendly types."""
        type_mappings = {
            "String": "string",
            "u64": "integer", 
            "i64": "integer",
            "u32": "integer",
            "i32": "integer", 
            "f64": "number",
            "bool": "boolean",
            "Vec<String>": "array[string]",
            "HashMap<String, String>": "object",
            "BigDecimal": "string (decimal)",
            "MmNumber": "string (decimal)",
        }
        
        # Handle generic types
        for rust_pattern, doc_type in type_mappings.items():
            if rust_type == rust_pattern:
                return doc_type
        
        # Handle Vec<T> patterns
        if rust_type.startswith("Vec<") and rust_type.endswith(">"):
            inner_type = rust_type[4:-1]
            return f"array[{self.format_rust_type(inner_type)}]"
            
        # Handle Option<T> patterns (already handled in parsing, but just in case)
        if rust_type.startswith("Option<") and rust_type.endswith(">"):
            inner_type = rust_type[7:-1]
            return self.format_rust_type(inner_type)
        
        # Default to the original type if no mapping found
        return rust_type.lower()
    
    def format_parameters_table(self, parameters: List[Dict[str, Any]], include_default: bool = True) -> str:
        """Format parameters into a markdown table."""
        if not parameters:
            return """| Parameter | Type | Required | Description |
| --------- | ---- | :------: | ----------- |
| userpass  | string | ✓ | RPC user password |"""
        
        # Check if any parameter has a default value
        has_defaults = any(param.get("default") for param in parameters) if include_default else False
        
        if include_default and has_defaults:
            header = "| Parameter | Type | Required | Default | Description |\n"
            header += "| --------- | ---- | :------: | :-----: | ----------- |\n"
        else:
            header = "| Parameter | Type | Required | Description |\n" 
            header += "| --------- | ---- | :------: | ----------- |\n"
        
        # Add userpass parameter first
        if include_default and has_defaults:
            rows = ["| userpass | string | ✓ | - | RPC user password |"]
        else:
            rows = ["| userpass | string | ✓ | RPC user password |"]
        
        # Add method-specific parameters
        for param in parameters:
            name = param.get("name", "unknown")
            param_type = self.format_rust_type(param.get("type", "unknown"))
            required = "✓" if param.get("required", True) else "✗"
            description = param.get("description", "No description available")
            
            if include_default and has_defaults:
                default = f"`{param.get('default', '')}`" if param.get("default") else "-"
                rows.append(f"| {name} | {param_type} | {required} | {default} | {description} |")
            else:
                rows.append(f"| {name} | {param_type} | {required} | {description} |")
        
        return header + "\n".join(rows)
    
    def get_api_version_tag(self, method_name: str) -> str:
        """Determine the API version tag for the method."""
        # Most new methods are API-v2
        if any(keyword in method_name for keyword in ["task::", "lightning::", "stream::", "gui_storage::"]):
            return "API-v2"
        
        # Some specific v1 methods
        v1_methods = ["autoprice", "fundvalue", "inventory", "stats_swap_status", "my_swap_status"]
        if method_name in v1_methods:
            return "API-v1"
        
        # Default to v2 for newer methods
        return "API-v2"
    
    def create_method_path(self, method_name: str, version: str) -> Path:
        """Create the file path for the method documentation."""
        # Convert method name to path structure
        parts = method_name.split("::")
        
        # Create version-specific path
        version_path = self.docs_dir / f"v{version[-1]}" if version.startswith("API-v") else self.docs_dir / "v20"
        
        # Handle different method types
        if method_name.startswith("task::"):
            if "enable" in method_name and len(parts) >= 3:
                coin_type = parts[1].replace("enable_", "")
                action = parts[2]
                return version_path / "coin_activation" / "task_managed" / f"enable_{coin_type}" / action / "index.mdx"
            elif len(parts) >= 3:
                task_type = parts[1]
                action = parts[2]  
                return version_path / "wallet" / "task_managed" / task_type / action / "index.mdx"
        
        elif method_name.startswith("lightning::"):
            category = parts[1]  # nodes, channels, payments
            action = parts[2]
            return version_path / "lightning" / category / action / "index.mdx"
        
        elif method_name.startswith("stream::") or method_name.startswith("streaming::"):
            if method_name == "stream::disable":
                return version_path / "streaming" / "disable" / "index.mdx"
            else:
                stream_type = parts[1] if len(parts) > 1 else "unknown"
                return version_path / "streaming" / f"{stream_type}_enable" / "index.mdx"
        
        elif method_name.startswith("gui_storage::"):
            action = parts[1]
            return version_path / "gui_storage" / action / "index.mdx"
        
        else:
            # Simple method name, create basic path
            safe_name = method_name.replace("::", "_")
            return version_path / safe_name / "index.mdx"
    
    def generate_example_request(self, method_name: str, parameters: List[Dict[str, Any]]) -> str:
        """Generate example request JSON."""
        example_request = {
            "method": method_name,
            "userpass": "RPC_UserP@SSW0RD",
            "mmrpc": "2.0"
        }
        
        # Add method-specific parameters with example values
        for param in parameters:
            example_value = self._get_example_value(param["type"], param["name"])
            example_request[param["name"]] = example_value
        
        return json.dumps(example_request, indent=4)
    
    def _get_example_value(self, param_type: str, param_name: str) -> Any:
        """Get example value for a parameter based on its type and name."""
        
        # Name-based examples
        if "coin" in param_name.lower():
            return "KMD"
        elif "address" in param_name.lower():
            return "RRnMcSeKiLrNdbp91qNVQwwXx5azD4S4CD"
        elif "amount" in param_name.lower():
            return "1.0"
        elif "hash" in param_name.lower():
            return "7c6699c2c714d50ff7734bf87c1096e3b10b8d8d14c6f5c1d8cad7d5b8e9f2a1"
        
        # Type-based examples
        if param_type in ["String", "string"]:
            return "example_value"
        elif param_type in ["u64", "i64", "u32", "i32", "integer"]:
            return 10
        elif param_type in ["f64", "number"]:
            return 1.5
        elif param_type in ["bool", "boolean"]:
            return True
        elif param_type.startswith("Vec<") or param_type.startswith("array"):
            return ["item1", "item2"]
        elif param_type in ["HashMap<String, String>", "object"]:
            return {"key": "value"}
        else:
            return "example_value"
    
    def generate_method_documentation(self, method_name: str, method_info: Dict[str, Any], version: str) -> str:
        """Generate complete MDX documentation for a method."""
        
        # Prepare template variables
        human_title = self.humanize_method_name(method_name)
        description = self.create_method_description(method_name, method_info)
        api_tag = self.get_api_version_tag(method_name)
        
        # Format parameters
        parameters = method_info.get("parameters", [])
        request_params_table = self.format_parameters_table(parameters)
        
        # Create basic response structure
        response_table = """| Parameter | Type | Description |
| --------- | ---- | ----------- |
| result | object | The result of the operation |"""
        
        # Generate examples
        example_request = self.generate_example_request(method_name, parameters)
        example_response = json.dumps({
            "mmrpc": "2.0",
            "result": {"status": "success"},
            "id": None
        }, indent=4)
        
        # Fill in the template
        content = self.template_content.format(
            human_title=human_title,
            description=description,
            method_name=method_name,
            api_tag=api_tag,
            request_params_table=request_params_table,
            response_params_table=response_table,
            example_request=example_request,
            example_response=example_response
        )
        
        return content
    
    def generate_all_documentation(self, analysis_data: Dict[str, Any]) -> List[Path]:
        """Generate documentation for all methods in the analysis data."""
        generated_files = []
        
        for version, methods in analysis_data.items():
            self.logger.info(f"Generating documentation for {version.upper()} methods...")
            
            for method_name, method_info in methods.items():
                try:
                    self.logger.debug(f"Generating {method_name}...")
                    
                    # Generate content
                    content = self.generate_method_documentation(method_name, method_info, version)
                    
                    # Create file path
                    file_path = self.create_method_path(method_name, version)
                    
                    # Ensure directory exists
                    ensure_directory_exists(file_path.parent)
                    
                    # Write file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    generated_files.append(file_path)
                    self.logger.debug(f"Generated: {file_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error generating {method_name}: {e}")
                    continue
        
        return generated_files
    
    def generate_summary_report(self, generated_files: List[Path]) -> str:
        """Generate a summary report of what was created."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.script_dir / f"documentation_generation_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# KDF Documentation Generation Report\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total files generated: {len(generated_files)}\n\n")
            
            f.write("## Generated Files\n\n")
            for file_path in generated_files:
                f.write(f"- `{file_path}`\n")
            
            f.write("\n## Next Steps\n\n")
            f.write("1. Review generated documentation files\n")
            f.write("2. Update sidebar.json entries manually if needed\n")
            f.write("3. Test the documentation locally\n")
            f.write("4. Submit for review\n")
        
        self.logger.success(f"Summary report generated: {report_path}")
        return str(report_path)


# Convenience functions for backward compatibility
def generate_documentation_from_analysis(analysis_file: Union[str, Path], 
                                        template_file: Optional[Union[str, Path]] = None,
                                        output_base: Optional[Union[str, Path]] = None) -> List[Path]:
    """Convenience function to generate documentation from analysis file."""
    
    # Load analysis data
    analysis_data = safe_read_json(Path(analysis_file))
    
    # Create generator
    generator = DocumentationGenerator(
        template_file=Path(template_file) if template_file else None,
        output_base=Path(output_base) if output_base else None
    )
    
    # Generate documentation
    return generator.generate_all_documentation(analysis_data)


def generate_single_method_doc(method_name: str, method_info: Dict[str, Any], 
                              version: str = "v2", 
                              output_path: Optional[Union[str, Path]] = None) -> str:
    """Convenience function to generate documentation for a single method."""
    
    generator = DocumentationGenerator()
    content = generator.generate_method_documentation(method_name, method_info, version)
    
    if output_path:
        output_file = Path(output_path)
        ensure_directory_exists(output_file.parent)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(output_file)
    
    return content 