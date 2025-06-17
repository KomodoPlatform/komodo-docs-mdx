#!/usr/bin/env python3
"""
KDF Documentation Auto-Generator

A comprehensive tool that generates documentation for missing KDF API methods by:
1. Loading missing methods from unified_method_mapping.json
2. Allowing user selection of methods to generate docs for
3. Analyzing the local KDF repository for method details with branch switching
4. Populating a comprehensive MDX template with the analysis
5. Outputting generated documentation to the generated_docs directory

Usage:
    python kdf_docs_autogen.py
    python kdf_docs_autogen.py --method task::enable_bch::cancel
    python kdf_docs_autogen.py --list-missing
    python kdf_docs_autogen.py --generate-all
    python kdf_docs_autogen.py --branch main
    python kdf_docs_autogen.py --pull-latest
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Import the library components
from lib.async_support.async_utils import AsyncFileProcessor
from lib.scanning.repository_scanner import KDFRepositoryScanner
from lib.scanning.enhanced_analyzer import EnhancedRepositoryAnalyzer, EnhancedMethodInfo
from lib.utils.logging_utils import get_logger, ProgressTracker


class KDFDocsAutoGenerator:
    """
    Main documentation auto-generation class that orchestrates the entire process.
    """
    
    def __init__(self, branch: str = "dev", repo_path: Optional[str] = None, verbose: bool = True):
        self.verbose = verbose
        self.branch = branch
        self.logger = get_logger("kdf-docs-autogen")
        
        # Initialize components
        self.file_processor = AsyncFileProcessor()
        self.repo_scanner = KDFRepositoryScanner(verbose=verbose)
        
        # Initialize enhanced analyzer with local repository
        try:
            self.enhanced_analyzer = EnhancedRepositoryAnalyzer(
                repo_path=repo_path, 
                default_branch=branch, 
                verbose=verbose
            )
            
            # Show current repository status
            current_branch = self.enhanced_analyzer.get_current_branch()
            if current_branch:
                self.logger.info(f"🌿 Repository currently on branch: {current_branch}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced analyzer: {e}")
            self.logger.info("Falling back to basic repository scanner")
            self.enhanced_analyzer = None
        
        # Define paths
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.unified_mapping_path = self.data_dir / "unified_method_mapping.json"
        self.template_path = self.base_dir.parent.parent / "docs" / "templates" / "komodefi_method_comprehensive.mdx"
        self.generated_docs_dir = self.data_dir / "generated_docs"
        
        # Ensure directories exist
        self.generated_docs_dir.mkdir(parents=True, exist_ok=True)
        
        if self.verbose:
            self.logger.info("🚀 KDF Documentation Auto-Generator initialized")
            self.logger.info(f"   🌿 Target branch: {self.branch}")
            self.logger.info(f"   📁 Data directory: {self.data_dir}")
            self.logger.info(f"   📄 Template: {self.template_path}")
            self.logger.info(f"   📂 Output directory: {self.generated_docs_dir}")
    
    def switch_branch(self, branch: str) -> bool:
        """Switch the repository to a different branch."""
        if self.enhanced_analyzer:
            success = self.enhanced_analyzer.switch_branch(branch)
            if success:
                self.branch = branch
                self.logger.info(f"✅ Switched to branch: {branch}")
            return success
        else:
            self.logger.warning("Enhanced analyzer not available for branch switching")
            return False
    
    def pull_latest(self) -> bool:
        """Pull the latest changes from the repository."""
        if self.enhanced_analyzer:
            return self.enhanced_analyzer.pull_latest(self.branch)
        else:
            self.logger.warning("Enhanced analyzer not available for pulling updates")
            return False
    
    async def load_missing_methods(self) -> Dict[str, List[str]]:
        """Load the list of missing methods from unified mapping."""
        try:
            if not self.unified_mapping_path.exists():
                self.logger.error(f"Unified mapping file not found: {self.unified_mapping_path}")
                return {}
            
            data = await self.file_processor.read_json_async(self.unified_mapping_path)
            
            if "missing" not in data or "methods_lacking_coverage" not in data["missing"]:
                self.logger.error("Invalid unified mapping format: missing 'missing.methods_lacking_coverage'")
                return {}
            
            missing_methods = data["missing"]["methods_lacking_coverage"]
            
            if self.verbose:
                total_missing = sum(len(methods) for methods in missing_methods.values())
                self.logger.info(f"📋 Loaded {total_missing} missing methods across {len(missing_methods)} versions")
                for version, methods in missing_methods.items():
                    self.logger.info(f"   {version}: {len(methods)} methods")
            
            return missing_methods
            
        except Exception as e:
            self.logger.error(f"Failed to load missing methods: {e}")
            return {}
    
    async def load_template(self) -> str:
        """Load the comprehensive MDX template."""
        try:
            if not self.template_path.exists():
                self.logger.error(f"Template file not found: {self.template_path}")
                return ""
            
            template_content = await self.file_processor.read_file_async(self.template_path)
            
            if self.verbose:
                self.logger.info(f"📄 Loaded template ({len(template_content):,} characters)")
            
            return template_content
            
        except Exception as e:
            self.logger.error(f"Failed to load template: {e}")
            return ""
    
    def display_missing_methods(self, missing_methods: Dict[str, List[str]]) -> None:
        """Display the missing methods in a user-friendly format."""
        print("\n" + "="*80)
        print("MISSING METHODS REQUIRING DOCUMENTATION")
        print("="*80)
        
        for version, methods in missing_methods.items():
            print(f"\n{version.upper()} ({len(methods)} methods):")
            print("-" * 40)
            
            for i, method in enumerate(sorted(methods), 1):
                print(f"  {i:2d}. {method}")
        
        total_missing = sum(len(methods) for methods in missing_methods.values())
        print(f"\nTotal missing methods: {total_missing}")
        print("="*80)
    
    def select_methods_interactive(self, missing_methods: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """Interactive method selection interface."""
        # Flatten methods with version info
        all_methods = []
        for version, methods in missing_methods.items():
            for method in sorted(methods):
                all_methods.append((method, version))
        
        if not all_methods:
            print("No missing methods found.")
            return []
        
        print(f"\nFound {len(all_methods)} missing methods. Please select:")
        print("1. Enter method numbers (e.g., '1,3,5' or '1-5')")
        print("2. Enter 'all' to generate docs for all methods")
        print("3. Enter 'quit' to exit")
        
        while True:
            try:
                user_input = input("\nYour selection: ").strip().lower()
                
                if user_input == 'quit':
                    return []
                
                if user_input == 'all':
                    return all_methods
                
                # Parse number ranges and individual numbers
                selected_indices = set()
                parts = user_input.split(',')
                
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Handle ranges like "1-5"
                        start, end = part.split('-', 1)
                        start, end = int(start.strip()), int(end.strip())
                        selected_indices.update(range(start, end + 1))
                    else:
                        # Handle individual numbers
                        selected_indices.add(int(part))
                
                # Validate indices and convert to methods
                selected_methods = []
                for idx in sorted(selected_indices):
                    if 1 <= idx <= len(all_methods):
                        selected_methods.append(all_methods[idx - 1])
                    else:
                        print(f"Warning: Index {idx} is out of range (1-{len(all_methods)})")
                
                if selected_methods:
                    print(f"\nSelected {len(selected_methods)} methods:")
                    for method, version in selected_methods:
                        print(f"  - {method} ({version})")
                    
                    confirm = input("\nProceed with these selections? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        return selected_methods
                    else:
                        continue
                else:
                    print("No valid methods selected. Please try again.")
                    
            except ValueError:
                print("Invalid input format. Please use numbers, ranges, or 'all'.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return []
    
    async def analyze_method(self, method_name: str, version: str) -> Dict[str, Any]:
        """
        Perform enhanced analysis of a method using the local repository analyzer.
        
        This uses the enhanced analyzer to extract detailed information from
        the local KDF repository including parameters, examples, errors, etc.
        """
        if self.verbose:
            self.logger.info(f"🔍 Analyzing method: {method_name} ({version})")
        
        try:
            if self.enhanced_analyzer:
                # Use the enhanced analyzer for comprehensive analysis
                enhanced_info = await self.enhanced_analyzer.analyze_method_comprehensive(
                    method_name, version, self.branch
                )
                
                # Convert enhanced info to the format expected by the template
                analysis = self._convert_enhanced_info_to_analysis(enhanced_info)
                
                if self.verbose:
                    param_count = len(analysis.get("parameters", []))
                    error_count = len(analysis.get("error_types", []))
                    example_count = len(analysis.get("examples", []))
                    self.logger.info(f"   📊 Found: {param_count} params, {error_count} errors, {example_count} examples")
                
                return analysis
            else:
                # Fallback to enhanced analysis if enhanced analyzer not available
                return await self._fallback_enhanced_analysis(method_name, version)
                
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Enhanced analysis failed for {method_name}: {e}")
            
            # Fallback to basic analysis
            return await self._fallback_enhanced_analysis(method_name, version)
    
    def _convert_enhanced_info_to_analysis(self, enhanced_info: EnhancedMethodInfo) -> Dict[str, Any]:
        """Convert EnhancedMethodInfo to the analysis format expected by the template."""
        return enhanced_info.to_dict()
    
    def _generate_basic_example_dict(self, method_name: str, version: str) -> Dict[str, Any]:
        """Generate a basic example in dictionary format."""
        if version == "v1":
            request = {
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD"
            }
        else:  # v2
            request = {
                "mmrpc": "2.0",
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD",
                "params": {},
                "id": 0
            }
        
        return {
            "title": f"Basic {method_name} Example",
            "request": request,
            "response": {"result": "success"},
            "description": "Basic example for method usage"
        }
    
    async def _fallback_enhanced_analysis(self, method_name: str, version: str) -> Dict[str, Any]:
        """Fallback to enhanced inference-based analysis if direct analysis fails."""
        from lib.scanning.enhanced_analyzer import EnhancedMethodInfo, ParameterInfo, ErrorInfo, ExampleInfo
        
        # Generate enhanced parameter info based on method patterns
        parameters = self.infer_enhanced_parameters(method_name, version)
        errors = self.infer_enhanced_errors(method_name, version)
        examples = [self.generate_enhanced_example(method_name, version)]
        
        enhanced_info = EnhancedMethodInfo(
            method_name=method_name,
            api_version=version,
            handler_file=None,
            description=self.generate_description(method_name),
            parameters=parameters,
            response=None,
            errors=errors,
            examples=examples,
            related_methods=self.find_related_methods(method_name),
            tags=self.extract_method_tags(method_name)
        )
        
        return enhanced_info.to_dict()
    
    def infer_enhanced_parameters(self, method_name: str, version: str) -> List:
        """Generate enhanced parameter information with better inference."""
        from lib.scanning.enhanced_analyzer import ParameterInfo
        
        parameters = []
        
        # Always include userpass for all methods
        parameters.append(ParameterInfo(
            name="userpass",
            type="string",
            required=True,
            default=None,
            description="Password for authentication",
            example='"RPC_UserP@SSW0RD"'
        ))
        
        # Method-specific parameters based on patterns
        if "enable" in method_name and "task::" in method_name:
            parameters.extend([
                ParameterInfo(
                    name="coin",
                    type="string", 
                    required=True,
                    default=None,
                    description="Coin ticker symbol",
                    example='"BTC"'
                ),
                ParameterInfo(
                    name="activation_params",
                    type="object",
                    required=True,
                    default=None,
                    description="Coin activation parameters",
                    example='{"mode": {"rpc": "Electrum", "rpc_data": {...}}}'
                )
            ])
        
        elif "cancel" in method_name and "task::" in method_name:
            parameters.append(ParameterInfo(
                name="task_id",
                type="number",
                required=True,
                default=None,
                description="Task ID to cancel",
                example="12345"
            ))
        
        elif "status" in method_name and "task::" in method_name:
            parameters.append(ParameterInfo(
                name="task_id",
                type="number",
                required=True, 
                default=None,
                description="Task ID to check status",
                example="12345"
            ))
        
        return parameters
    
    def generate_human_title(self, method_name: str) -> str:
        """Convert API method name to human-readable title."""
        if "::" in method_name:
            parts = method_name.split("::")
            
            if parts[0] == "task":
                if len(parts) >= 3:
                    action = parts[2].replace("_", " ").title()
                    target = parts[1].replace("_", " ").title()
                    return f"{action} {target} Task"
                else:
                    target = parts[1].replace("_", " ").title()
                    return f"{target} Task"
            
            elif parts[0] == "stream":
                if len(parts) >= 3:
                    action = parts[2].replace("_", " ").title()
                    target = parts[1].replace("_", " ").title()
                    return f"{action} {target} Stream"
                else:
                    target = parts[1].replace("_", " ").title()
                    return f"{target} Stream"
            
            elif parts[0] == "lightning":
                if len(parts) >= 3:
                    category = parts[1].replace("_", " ").title()
                    action = parts[2].replace("_", " ").title()
                    return f"{action} Lightning {category[:-1] if category.endswith('s') else category}"
                else:
                    target = parts[1].replace("_", " ").title()
                    return f"Lightning {target}"
            
            elif parts[0] == "gui_storage":
                action = parts[1].replace("_", " ").title()
                return f"{action} GUI Storage"
            
            elif parts[0] == "experimental":
                if len(parts) >= 3:
                    action = parts[-1].replace("_", " ").title()
                    category = parts[-2].replace("_", " ").title()
                    return f"{action} {category}"
                else:
                    target = parts[1].replace("_", " ").title()
                    return f"Experimental {target}"
            
            else:
                # Generic namespaced methods
                action = parts[-1].replace("_", " ").title()
                namespace = "::".join(parts[:-1]).replace("_", " ").title()
                return f"{action} {namespace}"
        
        # Simple methods
        return method_name.replace("_", " ").title()
    
    def generate_description(self, method_name: str) -> str:
        """Generate a descriptive summary for the method."""
        if "::" in method_name:
            parts = method_name.split("::")
            
            if parts[0] == "task":
                if "init" in method_name:
                    return f"Initializes the {parts[1].replace('_', ' ')} task operation in the Komodo DeFi Framework."
                elif "cancel" in method_name:
                    return f"Cancels the {parts[1].replace('_', ' ')} task operation in the Komodo DeFi Framework."
                elif "status" in method_name:
                    return f"Retrieves the status of the {parts[1].replace('_', ' ')} task operation."
                elif "user_action" in method_name:
                    return f"Handles user action for the {parts[1].replace('_', ' ')} task operation."
                else:
                    return f"Manages the {parts[1].replace('_', ' ')} task operation in the Komodo DeFi Framework."
            
            elif parts[0] == "stream":
                return f"Manages the {parts[1].replace('_', ' ')} streaming functionality in the Komodo DeFi Framework."
            
            elif parts[0] == "lightning":
                return f"Handles Lightning Network {parts[1].replace('_', ' ')} operations in the Komodo DeFi Framework."
            
            elif parts[0] == "gui_storage":
                return f"Manages GUI storage operations for {parts[1].replace('_', ' ')} in the Komodo DeFi Framework."
            
            elif parts[0] == "experimental":
                return f"Provides experimental functionality for {parts[-1].replace('_', ' ')} operations in the Komodo DeFi Framework."
        
        # Default description
        return f"The {method_name} method provides functionality for {method_name.replace('_', ' ')} operations in the Komodo DeFi Framework."
    
    def classify_method_type(self, method_name: str) -> str:
        """Classify the method type for better template population."""
        if "::" in method_name:
            parts = method_name.split("::")
            return parts[0]  # task, stream, lightning, etc.
        return "direct"
    
    def infer_basic_parameters(self, method_name: str) -> List[Dict[str, Any]]:
        """Infer basic parameters based on method name patterns."""
        params = []
        
        # Add userpass for all methods
        params.append({
            "name": "userpass",
            "type": "string",
            "required": True,
            "default": None,
            "description": "The user's password for RPC authorization."
        })
        
        # Method-specific parameter inference
        if "task::" in method_name:
            if "init" in method_name:
                if "enable_" in method_name:
                    # Enable tasks typically need coin parameter
                    params.append({
                        "name": "coin",
                        "type": "string",
                        "required": True,
                        "default": None,
                        "description": "The ticker symbol of the coin to enable."
                    })
            elif "status" in method_name or "cancel" in method_name:
                # Status and cancel operations need task_id
                params.append({
                    "name": "task_id",
                    "type": "number",
                    "required": True,
                    "default": None,
                    "description": "The identifier of the task to query or cancel."
                })
            elif "user_action" in method_name:
                # User action operations need task_id
                params.append({
                    "name": "task_id",
                    "type": "number",
                    "required": True,
                    "default": None,
                    "description": "The identifier of the task requiring user action."
                })
        
        elif "stream::" in method_name:
            # Stream methods might need different parameters
            if "enable" in method_name:
                params.append({
                    "name": "stream_id",
                    "type": "string",
                    "required": False,
                    "default": None,
                    "description": "Optional identifier for the stream."
                })
        
        elif "lightning::" in method_name:
            # Lightning methods typically involve coin
            params.append({
                "name": "coin",
                "type": "string",
                "required": True,
                "default": None,
                "description": "The ticker symbol of the Lightning-enabled coin."
            })
        
        elif "gui_storage::" in method_name:
            # GUI storage methods might need account parameters
            if "account" in method_name:
                params.append({
                    "name": "account_id",
                    "type": "string",
                    "required": True,
                    "default": None,
                    "description": "The identifier of the account."
                })
        
        return params
    
    def infer_basic_response(self, method_name: str) -> Dict[str, Any]:
        """Infer basic response structure based on method patterns."""
        response = {}
        
        if "task::" in method_name:
            if "init" in method_name:
                response = {
                    "task_id": "number - The identifier of the initialized task",
                    "result": "string - Result status of the initialization"
                }
            elif "status" in method_name:
                response = {
                    "status": "string - Current status of the task",
                    "details": "object - Detailed information about the task state"
                }
            elif "cancel" in method_name:
                response = {
                    "result": "string - Result of the cancellation operation"
                }
        
        elif "stream::" in method_name:
            response = {
                "stream_id": "string - Identifier of the stream",
                "status": "string - Status of the stream operation"
            }
        
        elif "lightning::" in method_name:
            response = {
                "result": "object - Lightning operation result",
                "coin": "string - The coin ticker involved in the operation"
            }
        
        elif "gui_storage::" in method_name:
            response = {
                "result": "string - Result of the GUI storage operation"
            }
        
        else:
            # Default response structure
            response = {
                "result": "object - The method response data"
            }
        
        return response
    
    def infer_basic_errors(self, method_name: str) -> List[Dict[str, str]]:
        """Infer common error types for the method."""
        errors = [
            {
                "name": "InvalidRequest",
                "description": "Request is missing required parameters or has invalid format"
            },
            {
                "name": "InternalError",
                "description": "An internal error occurred processing the request"
            }
        ]
        
        # Method-specific errors
        if "enable" in method_name or "coin" in method_name.lower():
            errors.append({
                "name": "NoSuchCoin",
                "description": "The specified coin is not supported or not activated"
            })
        
        if "task::" in method_name:
            errors.append({
                "name": "NoSuchTask",
                "description": "The specified task ID does not exist"
            })
        
        if "lightning::" in method_name:
            errors.append({
                "name": "LightningError",
                "description": "Lightning network operation failed"
            })
        
        return errors
    
    def populate_template(self, template: str, analysis: Dict[str, Any]) -> str:
        """Populate template with enhanced analysis data."""
        content = template
        
        # Basic replacements
        method_name = analysis.get("method_name", "")
        human_title = self.generate_human_title(method_name)
        content = content.replace("[Human-Readable Title]", human_title)
        content = content.replace("[Human-Readable, Title-Cased Method Name]", human_title)
        content = content.replace("[exact::api::method::name]", method_name)
        
        # Determine API tag
        version = analysis.get("api_version", "v2")
        api_tag = "API-v1" if version == "v1" else "API-v2"
        content = content.replace("API-v2", api_tag)
        
        # Description
        description = analysis.get("description", self.generate_description(method_name))
        content = content.replace("[Concise description of the method's purpose and functionality.]", description)
        content = content.replace("[Brief introduction to the method explaining its purpose, use case, and any relevant context.]", description)
        
        # Populate parameters table
        parameters = analysis.get("parameters", [])
        content = self.populate_parameters_table(content, parameters, version)
        
        # Populate response parameters
        content = self.populate_response_parameters(content, method_name, analysis)
        
        # Populate examples
        examples = analysis.get("examples", [])
        if examples:
            content = self.populate_examples(content, examples[0], method_name)
        
        # Populate error types
        errors = analysis.get("errors", [])
        content = self.populate_error_types(content, errors)
        
        # Note: Using custom table generation instead of table manager
        # to properly handle long content like structure links
        # content = self.prettify_tables(content)
        
        return content
    
    def populate_parameters_table(self, content: str, parameters: List[Dict[str, Any]], version: str) -> str:
        """Generate parameters table from structured parameter data."""
        if not parameters:
            return content
        
        # Check if we need Default column
        has_defaults = any(
            not param.get("required", True) and param.get("default") is not None
            for param in parameters
        )
        
        # Prepare table data
        if has_defaults:
            headers = ["Parameter", "Type", "Required", "Default", "Description"]
            alignments = ['left', 'left', 'center', 'center', 'left']
        else:
            headers = ["Parameter", "Type", "Required", "Description"]
            alignments = ['left', 'left', 'center', 'left']
        
        # Build table rows
        rows = []
        for param in parameters:
            name = param.get("name", "")
            param_type = param.get("type", "")
            required = param.get("required", True)
            default = param.get("default")
            description = param.get("description", "")
            
            required_mark = "✓" if required else "✗"
            
            if has_defaults:
                default_val = default if default is not None else "-"
                rows.append([name, param_type, required_mark, default_val, description])
            else:
                rows.append([name, param_type, required_mark, description])
        
        # Generate the new table
        new_table = self.generate_markdown_table(headers, rows, alignments)
        
        # Use more precise replacement targeting the exact template table structure
        template_request_table = """| Parameter | Type | Required | Description |
| --------- | ---- | :------: | ----------- |
| userpass  | string | ✓ | Password for authentication |"""
        
        content = content.replace(template_request_table, new_table)
        
        return content
    
    def populate_response_parameters(self, content: str, method_name: str, analysis: Dict[str, Any]) -> str:
        """Generate response parameters table based on method type."""
        # Generate realistic response parameters based on method patterns
        response_params = []
        
        if "init" in method_name and "task::" in method_name:
            response_params = [
                {"name": "task_id", "type": "integer", "description": "The identifier of the initialized task"}
            ]
        elif "status" in method_name and "task::" in method_name:
            response_params = [
                {"name": "status", "type": "string", "description": "Current status of the task"},
                {"name": "details", "type": "object", "description": "Detailed information about the task state"}
            ]
        elif "cancel" in method_name and "task::" in method_name:
            response_params = [
                {"name": "result", "type": "string", "description": "Result of the cancellation operation"}
            ]
        elif "get_new_address" in method_name:
            response_params = [
                {"name": "address", "type": "string", "description": "The newly generated address"},
                {"name": "derivation_path", "type": "string", "description": "BIP44 derivation path of the address"}
            ]
        elif "get_public_key" in method_name:
            response_params = [
                {"name": "public_key", "type": "string", "description": "The user's public key"}
            ]
        else:
            response_params = [
                {"name": "result", "type": "string", "description": "The outcome of the request"}
            ]
        
        # Prepare table data
        headers = ["Parameter", "Type", "Description"]
        alignments = ['left', 'left', 'left']
        
        rows = []
        for param in response_params:
            rows.append([param['name'], param['type'], param['description']])
        
        # Generate the new table
        new_table = self.generate_markdown_table(headers, rows, alignments)
        
        # Use precise replacement targeting the exact template response table
        template_response_table = """| Parameter | Type | Description |
| --------- | ---- | ----------- |
| result | string | The outcome of the request |"""
        
        content = content.replace(template_response_table, new_table)
        
        return content
    
    def populate_examples(self, content: str, example: Dict[str, Any], method_name: str) -> str:
        """Populate examples section with realistic data.""" 
        import json
        import re
        
        # Format the request and response JSON with 2-space indentation to match template
        request_json = json.dumps(example.get("request", {}), indent=2)
        response_json = json.dumps(example.get("response", {}), indent=2)
        
        # Replace method name in CodeGroup title
        title = example.get("title", method_name.replace("_", " ").title())
        content = content.replace("[Method Name]", title)
        
        # Replace method name placeholders in JSON
        content = content.replace("[exact::api::method::name]", method_name)
        
        # Replace the request JSON block using string replacement
        # The template format uses 2-space indentation
        old_request = '''  {
    "mmrpc": "2.0",
    "method": "''' + method_name + '''",
    "userpass": "RPC_UserP@SSW0RD",
    "params": {},
    "id": 0
  }'''
        
        # Create properly indented replacement (add 2 spaces to each line)
        indented_request = "\n".join("  " + line for line in request_json.split("\n"))
        content = content.replace(old_request, indented_request)
        
        # Replace the response JSON block
        old_response = '''  {
    "mmrpc": "2.0",
    "result": {
      "success": true
    },
    "id": 0
  }'''
        
        # Create properly indented replacement (add 2 spaces to each line)
        indented_response = "\n".join("  " + line for line in response_json.split("\n"))
        content = content.replace(old_response, indented_response)
        
        # Remove template comments
        comment_pattern = r'<!-- Template Usage Notes:.*?-->\s*'
        content = re.sub(comment_pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        return content
    
    def populate_error_types(self, content: str, errors: List[Dict[str, str]]) -> str:
        """Generate error types table and examples."""
        if not errors:
            # Use default errors if none provided
            errors = [
                {"name": "InvalidUserpass", "type": "string", "description": "The userpass provided is invalid"},
                {"name": "InternalError", "type": "string", "description": "An internal error occurred"},
                {"name": "InvalidRequest", "type": "string", "description": "The request parameters are invalid"},
                {"name": "NoSuchTask", "type": "string", "description": "The specified task was not found or has expired"}
            ]
        
        # Prepare table data
        headers = ["Parameter", "Type", "Description"]
        alignments = ['left', 'left', 'left']
        
        rows = []
        error_examples = []
        
        for i, error in enumerate(errors[:4]):  # Limit to 4 errors
            name = error.get("name", f"Error{i+1}")
            error_type = error.get("type", "string")
            description = error.get("description", "An error occurred")
            
            # Add to table
            rows.append([name, error_type, description])
            
            # Generate error example
            error_example = f'''##### {name}\n\n  ```json\n  {{\n    "mmrpc": "2.0",\n    "error": "{description}",\n    "error_path": "method_handler",\n    "error_trace": "method_handler:123]",\n    "error_type": "{name}",\n    "error_data": null,\n    "id": 0\n  }}\n  ```'''
            error_examples.append(error_example)
        
        # Generate the new table
        new_table = self.generate_markdown_table(headers, rows, alignments)
        
        # Use precise replacement targeting the exact template error table
        template_error_table = """| Parameter | Type | Description |
| --------- | ---- | ----------- |
| InvalidUserpass | string | The userpass provided is invalid |
| InternalError | string | An internal error occurred |"""
        
        content = content.replace(template_error_table, new_table)
        
        # Replace error examples with precise targeting
        error_examples_section = "\n\n".join(error_examples)
        
        template_error_examples = """##### InvalidUserpass

  ```json
  {
    "mmrpc": "2.0",
    "error": "Userpass is invalid",
    "error_path": "dispatcher",
    "error_trace": "dispatcher:123]",
    "error_type": "InvalidUserpass",
    "error_data": null,
    "id": 0
  }
  ```

  ##### InternalError

  ```json
  {
    "mmrpc": "2.0",
    "error": "Internal error occurred",
    "error_path": "method_handler",
    "error_trace": "method_handler:456]",
    "error_type": "InternalError",
    "error_data": null,
    "id": 0
  }
  ```"""
        
        content = content.replace(template_error_examples, error_examples_section)
        
        return content
    
    async def save_generated_doc(self, method_name: str, version: str, content: str) -> str:
        """Save the generated documentation to the appropriate location."""
        try:
            # Create version-specific directory
            version_dir = self.generated_docs_dir / version
            
            # Create method-specific directory structure
            method_parts = method_name.split("::")
            if len(method_parts) > 1:
                # Handle namespaced methods
                method_dir = version_dir / "/".join(method_parts)
            else:
                # Handle simple methods
                method_dir = version_dir / method_name
            
            # Ensure directory exists
            method_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to index.mdx
            output_file = method_dir / "index.mdx"
            await self.file_processor.write_file_async(output_file, content)
            
            if self.verbose:
                self.logger.success(f"📄 Documentation saved: {output_file}")
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save documentation for {method_name}: {e}")
            raise
    
    async def generate_documentation_for_methods(self, selected_methods: List[Tuple[str, str]]) -> Dict[str, str]:
        """Generate documentation for the selected methods."""
        if not selected_methods:
            return {}
        
        template = await self.load_template()
        if not template:
            self.logger.error("Failed to load template - cannot proceed")
            return {}
        
        generated_files = {}
        progress = ProgressTracker(len(selected_methods), "Documentation Generation", self.logger)
        
        try:
            for method_name, version in selected_methods:
                try:
                    if self.verbose:
                        self.logger.info(f"🔄 Generating documentation for {method_name} ({version})")
                    
                    # Analyze the method
                    analysis = await self.analyze_method(method_name, version)
                    
                    # Populate template with analysis
                    populated_content = self.populate_template(template, analysis)
                    
                    # Save the generated documentation
                    output_file = await self.save_generated_doc(method_name, version, populated_content)
                    generated_files[method_name] = output_file
                    
                    progress.update()
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate docs for {method_name}: {e}")
                    progress.update()
                    continue
            
            progress.finish()
            
            if self.verbose:
                self.logger.success(f"✅ Generated documentation for {len(generated_files)} methods")
            
            return generated_files
            
        except Exception as e:
            self.logger.error(f"Documentation generation failed: {e}")
            return generated_files
    
    async def run(self, args: argparse.Namespace) -> None:
        """Main execution method."""
        try:
            # Load missing methods
            missing_methods = await self.load_missing_methods()
            if not missing_methods:
                self.logger.error("No missing methods found - nothing to generate")
                return
            
            # Handle different command modes
            if args.list_missing:
                self.display_missing_methods(missing_methods)
                return
            
            selected_methods = []
            
            if args.method:
                # Single method mode
                method_name = args.method
                version = None
                
                # Find the version for this method
                for v, methods in missing_methods.items():
                    if method_name in methods:
                        version = v
                        break
                
                if version:
                    selected_methods = [(method_name, version)]
                    print(f"Generating documentation for: {method_name} ({version})")
                else:
                    self.logger.error(f"Method '{method_name}' not found in missing methods list")
                    return
            
            elif args.generate_all:
                # Generate all missing methods
                for version, methods in missing_methods.items():
                    for method in methods:
                        selected_methods.append((method, version))
                print(f"Generating documentation for all {len(selected_methods)} missing methods")
            
            else:
                # Interactive mode
                self.display_missing_methods(missing_methods)
                selected_methods = self.select_methods_interactive(missing_methods)
            
            if not selected_methods:
                print("No methods selected for generation.")
                return
            
            # Generate documentation
            print(f"\n🚀 Starting documentation generation for {len(selected_methods)} methods...")
            
            generated_files = await self.generate_documentation_for_methods(selected_methods)
            
            # Display results
            print(f"\n✅ Documentation generation completed!")
            print(f"Generated {len(generated_files)} documentation files:")
            print("-" * 60)
            
            for method_name, file_path in generated_files.items():
                print(f"  📄 {method_name}")
                print(f"     → {file_path}")
            
            print(f"\n📂 All files saved to: {self.generated_docs_dir}")
            print("📝 Please review the generated documentation before integration.")
            
        except Exception as e:
            self.logger.error(f"Documentation generation failed: {e}")
            raise

    def infer_enhanced_errors(self, method_name: str, version: str) -> List:
        """Generate enhanced error information."""
        from lib.scanning.enhanced_analyzer import ErrorInfo
        
        errors = []
        
        # Common errors for all methods
        errors.extend([
            ErrorInfo(
                name="InvalidUserpass",
                type="string",
                description="The userpass provided is invalid"
            ),
            ErrorInfo(
                name="InternalError", 
                type="string",
                description="An internal error occurred"
            )
        ])
        
        # Method-specific errors
        if "enable" in method_name:
            errors.extend([
                ErrorInfo(
                    name="CoinAlreadyActivated",
                    type="string", 
                    description="The coin is already activated"
                ),
                ErrorInfo(
                    name="InvalidActivationParams",
                    type="string",
                    description="The activation parameters are invalid"
                )
            ])
        
        elif "task::" in method_name:
            errors.append(ErrorInfo(
                name="TaskNotFound",
                type="string",
                description="The specified task was not found"
            ))
        
        return errors
    
    def generate_enhanced_example(self, method_name: str, version: str):
        """Generate enhanced example information."""
        from lib.scanning.enhanced_analyzer import ExampleInfo
        
        if version == "v1":
            request = {
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD"
            }
        else:  # v2
            request = {
                "mmrpc": "2.0",
                "method": method_name,
                "userpass": "RPC_UserP@SSW0RD",
                "params": {},
                "id": 0
            }
        
        # Add method-specific parameters
        if "task::" in method_name and "init" in method_name and "enable" in method_name:
            if version == "v1":
                request.update({
                    "coin": "BTC",
                    "activation_params": {"mode": {"rpc": "Electrum"}}
                })
            else:
                request["params"].update({
                    "coin": "BTC", 
                    "activation_params": {"mode": {"rpc": "Electrum"}}
                })
        
        elif "task::" in method_name and ("cancel" in method_name or "status" in method_name):
            if version == "v1":
                request["task_id"] = 12345
            else:
                request["params"]["task_id"] = 12345
        
        return ExampleInfo(
            title=f"{method_name} Example",
            request=request,
            response={"result": "success"},
            description="Example request/response for this method"
        )
    
    def find_related_methods(self, method_name: str) -> List[str]:
        """Find related methods based on naming patterns."""
        related = []
        
        if "::" in method_name:
            parts = method_name.split("::")
            base = "::".join(parts[:-1])
            
            # For task methods, find the full lifecycle
            if method_name.endswith("::init"):
                related.extend([
                    f"{base}::status",
                    f"{base}::cancel", 
                    f"{base}::user_action"
                ])
            elif method_name.endswith("::status"):
                related.extend([
                    f"{base}::init",
                    f"{base}::cancel"
                ])
            elif method_name.endswith("::cancel"):
                related.extend([
                    f"{base}::init",
                    f"{base}::status"
                ])
        
        return related
    
    def extract_method_tags(self, method_name: str) -> List[str]:
        """Extract tags from method name."""
        tags = []
        
        if "::" in method_name:
            parts = method_name.split("::")
            if parts[0] in ["task", "lightning", "stream", "gui_storage", "experimental"]:
                tags.append(parts[0])
            if len(parts) > 2 and parts[1] in ["staking", "payments", "channels", "nodes"]:
                tags.append(parts[1])
        
        return tags

    def prettify_tables(self, content: str) -> str:
        """Prettify markdown tables using the table manager."""
        from lib.managers.table_manager import TableManager
        
        # Write content to a temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Use the table manager to prettify tables
            TableManager.pretty_print_md_table(temp_file_path)
            
            # Read the prettified content back
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                prettified_content = f.read()
            
            return prettified_content
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def generate_table_separator(self, headers: List[str], rows: List[List[str]], alignments: List[str] = None) -> str:
        """Generate proper table separator with adequate dash lengths for all alignment types."""
        if not alignments:
            alignments = ['left'] * len(headers)
        
        # Calculate minimum column widths based on content
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            # Check all rows for this column
            for row in rows:
                if i < len(row):
                    cell_content = str(row[i])
                    max_width = max(max_width, len(cell_content))
            # Minimum width of 3 for basic separators, but ensure adequate length
            col_widths.append(max(max_width, 3))
        
        # Generate separator row with proper alignment markers
        separator_parts = []
        for i, width in enumerate(col_widths):
            alignment = alignments[i] if i < len(alignments) else 'left'
            if alignment == 'center':
                # For center alignment: :-----: (minimum 3 dashes between colons)
                inner_dashes = max(width - 2, 3)
                separator_parts.append(f":{'-' * inner_dashes}:")
            elif alignment == 'right':
                # For right alignment: -----: (minimum 3 dashes before colon)
                dashes = max(width - 1, 3)
                separator_parts.append(f"{'-' * dashes}:")
            else:  # left alignment
                # For left alignment: ----- (minimum 3 dashes)
                dashes = max(width, 3)
                separator_parts.append('-' * dashes)
        
        return '| ' + ' | '.join(separator_parts) + ' |'
    
    def generate_markdown_table(self, headers: List[str], rows: List[List[str]], alignments: List[str] = None) -> str:
        """Generate a properly formatted markdown table with aligned column borders."""
        if not headers or not rows:
            return ""
        
        # Calculate column widths based on content
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            # Check all rows for this column
            for row in rows:
                if i < len(row):
                    cell_content = str(row[i])
                    max_width = max(max_width, len(cell_content))
            # Minimum width of 3 for readability
            col_widths.append(max(max_width, 3))
        
        # Generate padded header row
        padded_headers = []
        for i, header in enumerate(headers):
            padded_headers.append(header.ljust(col_widths[i]))
        header_row = '| ' + ' | '.join(padded_headers) + ' |'
        
        # Generate separator row
        separator_row = self.generate_table_separator(headers, rows, alignments)
        
        # Generate padded data rows
        data_rows = []
        for row in rows:
            padded_row = []
            for i in range(len(headers)):
                if i < len(row):
                    cell_content = str(row[i])
                    # Apply padding based on alignment
                    if alignments and i < len(alignments):
                        if alignments[i] == 'center':
                            padded_cell = cell_content.center(col_widths[i])
                        elif alignments[i] == 'right':
                            padded_cell = cell_content.rjust(col_widths[i])
                        else:  # left
                            padded_cell = cell_content.ljust(col_widths[i])
                    else:
                        padded_cell = cell_content.ljust(col_widths[i])
                else:
                    padded_cell = ''.ljust(col_widths[i])
                padded_row.append(padded_cell)
            
            data_rows.append('| ' + ' | '.join(padded_row) + ' |')
        
        return '\n'.join([header_row, separator_row] + data_rows)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="KDF Documentation Auto-Generator - Enhanced Local Repository Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kdf_docs_autogen.py                           # Interactive mode (default branch: dev, auto-pull enabled)
  python kdf_docs_autogen.py --list-missing             # List missing methods
  python kdf_docs_autogen.py --method task::enable_bch::cancel  # Generate single method
  python kdf_docs_autogen.py --generate-all             # Generate all missing methods
  python kdf_docs_autogen.py --branch main              # Use main branch instead of dev
  python kdf_docs_autogen.py --no-pull                  # Skip pulling latest changes from remote (default: auto-pull enabled)
  python kdf_docs_autogen.py --quiet                    # Run in quiet mode
  python kdf_docs_autogen.py --repo-path /path/to/kdf   # Use custom repository path
        """
    )
    
    parser.add_argument(
        "--method",
        help="Generate documentation for a specific method"
    )
    
    parser.add_argument(
        "--list-missing",
        action="store_true",
        help="List all missing methods and exit"
    )
    
    parser.add_argument(
        "--generate-all",
        action="store_true",
        help="Generate documentation for all missing methods"
    )
    
    parser.add_argument(
        "--branch",
        default="dev",
        help="Git branch to use for analysis (default: dev)"
    )
    
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip pulling latest changes from remote (default: auto-pull enabled)"
    )
    
    parser.add_argument(
        "--repo-path",
        help="Path to local KDF repository (default: utils/py/data/kdf_repo)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Run in quiet mode (minimal output)"
    )
    
    args = parser.parse_args()
    
    # Initialize the generator with branch and repo path
    verbose = not args.quiet
    generator = KDFDocsAutoGenerator(
        branch=args.branch,
        repo_path=args.repo_path,
        verbose=verbose
    )
    
    # Handle repository management commands (auto-pull by default)
    if not args.no_pull:
        print(f"📥 Pulling latest changes from {args.branch} branch...")
        if generator.pull_latest():
            print("✅ Repository updated successfully")
        else:
            print("⚠️ Failed to update repository")
            if not verbose:
                print("Use --verbose for more details")
    elif verbose:
        print(f"ℹ️ Skipping repository update (--no-pull specified)")
    
    # Run the generator
    try:
        asyncio.run(generator.run(args))
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 