#!/usr/bin/env python3
"""
Komodo DeFi Framework Tools - Unified CLI

A comprehensive command-line interface for managing KDF documentation, OpenAPI specs,
Postman collections, and repository analysis. This tool consolidates functionality
from multiple specialized scripts into a single, easy-to-use interface.

Available Commands:
- openapi: Convert MDX documentation to OpenAPI specs
- postman: Generate Postman collections
- scan-rust: Scan KDF Rust repository for RPC methods
- scan-mdx: Scan MDX documentation files for method names
- gap-analysis: Compare Rust methods with MDX documentation
- map_methods: Method mapping and OpenAPI management
- json-extract: Extract JSON examples from MDX files

Recommended Workflows:
    kdf_tools.py openapi --version v2
    kdf_tools.py postman --versions v2

Examples:
    kdf_tools.py openapi --version v2 # Generate OpenAPI
    kdf_tools.py postman              # Generate Postman

Global Options:
    --dry-run: Show what would be done without making changes
"""

import sys
import argparse
import os
from pathlib import Path
import subprocess
from typing import List, Dict, Any
import traceback
import argparse
import asyncio
import glob
import json
from datetime import datetime
import time
from collections import defaultdict
import re

# To solve relative import issues, we add the project root to the python path.
_script_dir = Path(__file__).parent.absolute()
_workspace_root = _script_dir.parent.parent
if not (_workspace_root / "src" / "pages").exists():
    _current = Path.cwd()
    for _parent in [_current] + list(_current.parents):
        if (_parent / "src" / "pages").exists() and (_parent / "utils" / "py").exists():
            _workspace_root = _parent
            break
sys.path.insert(0, str(_workspace_root))
from utils.py.lib.mdx.mdx_generator import MdxGenerator


from utils.py.lib.postman.postman_scanner import MdxJsonExampleExtractor, ExtractedExample
from utils.py.lib.managers import MethodMappingManager
from utils.py.lib.utils import safe_write_json, ensure_directory_exists
from utils.py.lib.utils.path_utils import get_method_path
from utils.py.lib import (
    UnifiedScanner,
    get_logger, DraftsManager,
    MdxGenerator, ExistingDocsScanner
)
from utils.py.lib.constants import UnifiedRepositoryInfo
from utils.py.lib.constants.config import get_config
from utils.py.lib.constants.data_structures import ScanMetadata
from utils.py.lib.rust.scanner import KDFScanner
from utils.py.lib.openapi.openapi_manager import OpenAPIManager
from utils.py.lib.postman.postman_manager import PostmanManager
from utils.py.lib.utils.data_utils import sort_version_method_counts

from utils.py.lib.async_support import run_async
from utils.py.lib.openapi.openapi_spec_generator import OpenApiSpecGenerator
from utils.py.lib.api_client.kdf_api_processor import ApiRequestProcessor


class MdxScanner:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.workspace_root = Path(self.config.workspace_root)
        self.mdx_docs_path = self.workspace_root / 'src' / 'pages'

    def scan(self, versions: List[str]):
        # The existing scan logic can remain here
        pass

    def generate_api_methods_table(self):
        self.logger.info("Generating API methods table for index.mdx...")
        paths_file = self.config.directories.mdx_method_paths_report
        template_file = self.workspace_root / 'templates' / 'methods_table.template'
        output_file = self.workspace_root / 'src' / 'pages' / 'komodo-defi-framework' / 'api' / 'index.mdx'

        if not paths_file.exists():
            self.logger.error(f"Method paths file not found: {paths_file}")
            self.logger.error("Please run the 'scan-mdx' command first to generate the report.")
            return

        with open(paths_file, 'r') as f:
            paths_data = json.load(f)

        methods = defaultdict(lambda: {"legacy": "", "v20": "", "v20-dev": ""})
        
        for method_name, file_path_str in paths_data['method_paths']['v1'].items():
            link = self._create_link(method_name, file_path_str)
            methods[method_name]['legacy'] = link

        for method_name, file_path_str in paths_data['method_paths']['v2'].items():
            link = self._create_link(method_name, file_path_str)
            if '/api/v20-dev/' in file_path_str:
                methods[method_name]['v20-dev'] = link
            elif '/api/v20/' in file_path_str:
                methods[method_name]['v20'] = link
        
        sorted_methods = sorted(methods.keys())

        table_rows = []
        for method_name in sorted_methods:
            row = f"| {methods[method_name]['legacy']} | {methods[method_name]['v20']} | {methods[method_name]['v20-dev']} |"
            table_rows.append(row)

        with open(template_file, 'r') as f:
            template_content = f.read()

        final_content = template_content + "\n" + "\n".join(table_rows)

        with open(output_file, 'w') as f:
            f.write(final_content)
        
        self.logger.save(f"Successfully generated API methods table at: {output_file}")

    def _create_link(self, method_name, file_path_str):
        doc_path_obj = Path(file_path_str).relative_to(self.mdx_docs_path)
        doc_path = "/" + doc_path_obj.parent.as_posix()
        slug = self._slugify(method_name)
        escaped_name = method_name.replace('_', '\\_')
        return f"[{escaped_name}]({doc_path}/#{slug})"

    @staticmethod
    def _slugify(text):
        text = text.split("{{")[0].strip()
        text = re.sub(r'[:_\\s]+', '-', text)
        text = re.sub(r'[^a-zA-Z0-9\\-]', '', text)
        return text.lower()


class KDFTools:
    """Unified KDF Tools CLI."""
    
    def __init__(self):
        self.verbose = True
        self.config = get_config()
        self.logger = get_logger("kdf-tools")
        self.processor = ApiRequestProcessor(
            config=self.config,
            logger=self.logger
        )
        self.processor._load_dotenv()
        self.openapi_spec_generator = OpenApiSpecGenerator()
        if self.verbose:
            self.logger.folder(f"Workspace root: {self.config.workspace_root}")
            self.logger.folder(f"Data directory: {self.config.directories.data_dir}")
            self.logger.folder(f"KDF repository: {self.config.directories.kdf_repo_path}")
            self.logger.folder(f"Reports directory: {self.config.directories.reports_dir}")
            self.logger.folder(f"Branched reports directory: {self.config.directories.branched_reports_dir}")



    def log(self, message, level="info"):
        """Log a message with appropriate level."""
        
        # Map simple levels to logger methods
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)
    
    def _print_header(self, title, config_lines=None):
        """Prints a standardized command header."""
        self.log(f"")
        self.logger.start(f"============== Starting: {title} ==============")
        if config_lines:
            self.logger.config("Config:")
            for line in config_lines:
                self.logger.config(f"    - {line}")
        self.log("")

    def _print_footer(self, title, success=True, output_paths=None, report_paths=None):
        """Prints a standardized command footer."""
        self.log("")
        if success:
            self.logger.finish(f"✅ Success: {title}")
        else:
            self.logger.finish(f"❌ Failed: {title}")

        if output_paths:
            self.log("  Output data paths:")
            for path in output_paths:
                self.log(f"    - {path}")
        if report_paths:
            self.log("  Output report paths:")
            for path in report_paths:
                self.log(f"    - {path}")
        self.log("")
        
    def report_error_responses(self):
        """Generates a report of method requests that have error responses."""
        command_title = "Generate Error Response Report"
        self._print_header(command_title)

        methods_with_errors = {
            "v1": {},
            "v2": {}
        }

        postman_dirs = {
            "v1": self.config.directories.postman_json_v1,
            "v2": self.config.directories.postman_json_v2
        }

        for version, version_dir in postman_dirs.items():
            self.logger.info(f"Scanning {version} directory: {version_dir}")
            for method_dir in version_dir.iterdir():
                if not method_dir.is_dir():
                    continue

                method_name = method_dir.name
                error_files = sorted(list(method_dir.glob("error_*.json")))
                request_files = sorted(list(method_dir.glob("request_*.json")))

                if not error_files or not request_files:
                    continue

                self.logger.info(f"Found {len(error_files)} error responses for method: {method_name}")

                requests = []
                for req_file in request_files:
                    try:
                        with open(req_file, 'r') as f:
                            requests.append(json.load(f))
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not decode JSON from {req_file}")
                    except Exception as e:
                        self.logger.error(f"Error reading {req_file}: {e}")

                if not requests:
                    self.logger.warning(f"No valid request files found for {method_name}, skipping.")
                    continue

                for i, error_file in enumerate(error_files):
                    try:
                        with open(error_file, 'r') as f:
                            error_content_str = f.read()
                            error_response = json.loads(error_content_str)

                        request_body = requests[i % len(requests)]
                        report_method_name = f"{method_name}_{i+1}"

                        methods_with_errors[version][report_method_name] = {
                            "request": request_body,
                            "error_response": error_response
                        }

                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not decode JSON from error file {error_file}")
                    except Exception as e:
                        self.logger.error(f"Error processing {error_file}: {e}")

        v1_count = len(methods_with_errors["v1"])
        v2_count = len(methods_with_errors["v2"])
        all_count = v1_count + v2_count

        scan_metadata = {
            "scanner_type": "ERROR_RESPONSE_SCAN",
            "scanner_version": "KDFTools v1.0.0",
            "generated_at": datetime.now().isoformat(),
            "generated_during": "error_report_scan",
            "method_source": "Postman JSON examples (dev branch)",
            "is_primary_data_source": False,
            "total_error_responses_found": {
                "all": all_count,
                "v1": v1_count,
                "v2": v2_count
            }
        }
        
        report = {
            "scan_metadata": scan_metadata,
            "kdf_branch": "dev",
            "methods": methods_with_errors
        }

        report_path = self.config.directories.methods_error_responses_report
        safe_write_json(report_path, report)
        self.logger.save(f"Saved error responses report to: {report_path}")
        self._print_footer(command_title, success=True, report_paths=[str(report_path)])

    def openapi_command(self, args):
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        command_title = "MDX to OpenAPI Conversion"
        config = [
        ]
        self._print_header(command_title, config)
        
        success = False
        report_paths = []
        try:
            manager = OpenAPIManager(
                config=self.config,
                verbose=self.verbose
            )
            manager.openapi_command()
            
            v1_count = len([m for m in manager.all_methods.values() if m['version'] == 'v1'])
            v2_count = len([m for m in manager.all_methods.values() if m['version'] == 'v2'])
            total_count = v1_count + v2_count

            result = f"✅ All versions processed successfully!\n   📊 V1 methods: {v1_count}\n   📊 V2 methods: {v2_count}\n   📊 Total methods: {total_count}"
            
            self.log(f"{result}")
            
            # NEW: Call tracking file generat
            self.log("📊 Generating OpenAPI tracking files...")
            enums_count = len(manager.mdx_parser.enum_patterns)
            structures_count = len(manager.mdx_parser.common_structures)
            source_dirs = [str(Path(self.config.workspace_root) / self.config.directories.mdx_v1),
                            str(Path(self.config.workspace_root) / self.config.directories.mdx_v2)]
            
            manager.spec_generator.generate_tracking_files(
                "all", manager.success_count, manager.error_count,
                manager.mdx_parser.enum_patterns, structures_count,
                enums_count, source_dirs, manager.all_methods
            )
            
            # Generate review files
            self.log("📊 Generating review files...")
            manager.common_schema_generator.generate_review_files(manager.mdx_parser.enum_patterns)
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.log(f"📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['files_processed']}")
            self.log(f"   • Enums found: {stats['enums_found']}")
            self.log(f"   • Structures found: {stats['structures_found']}")
            
            self.log("🔚 Finished MDX to OpenAPI conversion.")

            v1_methods = [m for m, d in manager.all_methods.items() if d['version'] == 'v1']
            v2_methods = [m for m, d in manager.all_methods.items() if d['version'] == 'v2']
            version_method_counts = {
                'v1': len(v1_methods),
                'v2': len(v2_methods),
                'all': len(v1_methods) + len(v2_methods)
            }
            version_method_counts = sort_version_method_counts(version_method_counts)

            # Generate tracking files
            processed_versions = [args.version] if args.version != "all" else ["v1", "v2"]
            openapi_report_path = self._generate_openapi_tracking_files(manager, processed_versions, version_method_counts)
            if openapi_report_path:
                report_paths.append(openapi_report_path)
            
            success = True
        except Exception as e:
            self.log(f"An error occurred during OpenAPI generation: {e}", "error")
            self.log(traceback.format_exc(), "error")
            success = False
        finally:
            self._print_footer(command_title, success=success, report_paths=report_paths)
            
    def scan_rust(self, args):
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        command_title = "KDF Repository Scan"
        versions = args.versions
        if 'all' in versions:
            versions = ['v1', 'v2']
            
        config = [
            f"Branch: {args.kdf_branch}",
            f"Versions: {versions}",
        ]
        self._print_header(command_title, config)

        if args.kdf_branch:
            if not self._switch_kdf_branch(args.kdf_branch):
                self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting rust-scan.")
                self._print_footer(command_title, success=False)
                return

        report_paths = []
        success = False

        async def main():
            nonlocal report_paths, success
            scanner = KDFScanner(
                config=self.config,
                repo_path=self.config.directories.kdf_repo_path,
                branch=args.kdf_branch,
                verbose=self.verbose
            )
            
            repo_info = await scanner.scan_repository_methods_async(versions)
            if repo_info:
                version_method_counts = self._calc_version_method_counts(repo_info)
                # Save results to file
                output_file = await scanner.save_repository_methods_async(repo_info, version_method_counts)
                report_paths.append(output_file)
            
            # Additional logic for processing/reporting on repo_info
            self.logger.finish(f"Async KDF Repository scan completed:")
            self.log(f"📊 Rust Repository Scan Statistics:")
            self.log(f"   • V1 methods processed: {version_method_counts['v1']}")
            self.log(f"   • V2 methods processed: {version_method_counts['v2']}")
            self.log(f"   • Total methods processed: {version_method_counts['all']}")
            self.log("🔚 Finished Rust repository scan.")
            success = True

        try:
            asyncio.run(main())
        except Exception as e:
            self.log(f"❌ An error occurred during Rust repository scan: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
        self._print_footer(command_title, success=success, output_paths=report_paths)

        
    def _calc_version_method_counts(self, repo_info: Dict[str, UnifiedRepositoryInfo]) -> Dict[str, int]:
        version_method_counts = {version: len(info.methods) for version, info in repo_info.items()}
        return sort_version_method_counts(version_method_counts)
    
    def scan_mdx_command(self, args):
        """Scans MDX files for Komodo DeFi Framework methods."""
        command_title = "Scan MDX Documentation"
        config_lines = [
            f"Versions to scan: {args.versions}",
            f"Repo branch: {args.branch}"
        ]
        self._print_header(command_title, config_lines)
        
        versions = args.versions.split(',') if args.versions and args.versions != 'all' else ['v1', 'v2']
        
        doc_scanner = UnifiedScanner(
            config=self.config,
            verbose=self.verbose 
        )
        doc_results = run_async(doc_scanner.scan_all_files_async(versions))
        self._generate_mdx_method_paths_data(doc_results, versions, args.branch)
        self._generate_mdx_methods_from_paths_file(self.config.directories.mdx_method_paths_report, args.branch, versions)
        
        scanner = MdxScanner(self.config, self.logger)
        scanner.generate_api_methods_table()
        self._print_footer(command_title, success=True, output_paths=[self.config.directories.mdx_method_paths_report, self.config.directories.mdx_methods_report])
    

    def _generate_mdx_method_paths_data(self, doc_results, versions, current_branch):
        """
        Generate the method paths data structure (primary data source).
        This version uses the ScanMetadata dataclass for standardized metadata.
        """
        method_paths = {}
        version_method_counts = {}

        for version in versions:
            if version not in doc_results:
                if self.verbose:
                    self.logger.warning(f"No documentation found for version {version}")
                version_method_counts[version] = 0
                method_paths[version] = {}
                continue

            version_data = doc_results[version]
            current_version_paths = {}
            if 'mdx_files' in version_data:
                for method_name, file_path in version_data['mdx_files'].items():
                    current_version_paths[method_name] = str(file_path)
            
            method_paths[version] = dict(sorted(current_version_paths.items()))
            version_method_counts[version] = len(current_version_paths)

            if self.verbose:
                self.logger.scan(f"Processing {version.upper()} documentation...")
                self.logger.folder(f"MDX files with paths: {len(current_version_paths)}")

        total_documented_methods = sum(version_method_counts.values())
        version_method_counts.update({"all": total_documented_methods})
        version_method_counts = sort_version_method_counts(version_method_counts)

        metadata = ScanMetadata(
            scanner_type="MDX_METHOD_PATH_MAPPING",
            scanner_version="KDFMethodPathMapper v2.0.0",
            generated_during="mdx_scan",
            method_source="mdx",
            is_primary_data_source=True,
            version_method_counts=version_method_counts
        )

        method_paths_data = {
            "scan_metadata": metadata.to_dict(),
            "method_paths": method_paths
        }
        
        safe_write_json(self.config.directories.mdx_method_paths_report, method_paths_data)
        self.logger.save(f"Saved documentation paths to: {self.config.directories.mdx_method_paths_report}")
        return method_paths_data

    def _generate_mdx_methods_from_paths_file(self, paths_file_path, current_branch, versions):
        """Generates a JSON report of methods from a paths file."""
        # Read the paths file that was just generated
        with open(paths_file_path, 'r', encoding='utf-8') as f:
            paths_data = json.load(f)
        
        # Extract method names ONLY from the method_paths keys (methods with actual MDX files)
        methods_by_version = {}
        method_paths = paths_data.get("method_paths", {})
        total_methods = 0
        
        for version in versions:
            if version in method_paths:
                # Only include methods that have actual MDX documentation files
                methods_with_mdx_files = list(method_paths[version].keys())
                method_list = sorted(methods_with_mdx_files)
                
                methods_by_version[version] = method_list
                total_methods += len(method_list)
                
                self.logger.info(f"{version.upper()}: {len(method_list)} methods with MDX documentation")
            else:
                methods_by_version[version] = []
        
        version_method_counts = {v: len(m) for v, m in methods_by_version.items()}
        version_method_counts = sort_version_method_counts(version_method_counts)

        # Create the methods data structure
        metadata = ScanMetadata(
            scanner_type="MDX_METHOD_PATH_MAPPING",
            scanner_version="KDFMethodPathMapper v2.0.0",
            generated_during="mdx_scan",
            method_source="mdx",
            is_primary_data_source=True,
            version_method_counts=version_method_counts
        )

        methods_data = {
            "scan_metadata": metadata.to_dict(),
            "repository_data": {}
        }
        
        # Add version-specific data
        for version in versions:
            methods_data["repository_data"][version] = {
                "branch": current_branch,
                "version": version,
                "source_type": "MDX_DOCUMENTATION",
                "methods": methods_by_version.get(version, []),
                "last_updated": datetime.now().isoformat(),
                "extraction_patterns_used": [
                    "MDX file parsing with path verification",
                    "Derived from method paths file",
                    "Only includes methods with actual MDX files"
                ]
            }
        
        safe_write_json(self.config.directories.mdx_methods_report, methods_data)
        self.logger.save(f"Saved documentation paths to: {self.config.directories.mdx_methods_report}")
        return methods_data
    
    def methods_map_command(self, args):
        """Handle methods-map subcommand."""
        command_title = "Method Mapping and OpenAPI Management"
        config_lines = [
            f"Command: {args.subcommand}",
            f"Versions: {args.versions}"
        ]
        self._print_header(command_title, config_lines)
        success = False
        try:
            # Load latest Rust scan data
            rust_data = {}
            rust_scan_files = glob.glob(str(self.config.directories.rust_methods_report))
            if rust_scan_files:
                with open(rust_scan_files[0], 'r') as f:
                    rust_methods_data = json.load(f).get("repository_data", {})
                    for v in args.versions:
                        if v in rust_methods_data:
                            rust_data[v] = rust_methods_data[v].get("methods", [])
            else:
                self.logger.warning(f"No '{os.path.basename(str(self.config.directories.rust_methods_report))}' file found.")
                self.logger.warning(f"Run 'python py/kdf_tools.py scan-rust' first")
                return

            # Load latest MDX methods data
            mdx_methods = {}
            mdx_scan_files = glob.glob(str(self.config.directories.mdx_methods_report))
            if mdx_scan_files:
                with open(mdx_scan_files[0], 'r') as f:
                    mdx_methods_data = json.load(f).get("repository_data", {})
                    for v in args.versions:
                        if v in mdx_methods_data:
                            mdx_methods[v] = mdx_methods_data[v].get("methods", [])
            else:
                self.logger.warning(f"No '{os.path.basename(str(self.config.directories.mdx_methods_report))}' file found.")
                self.logger.warning(f"Run 'python py/kdf_tools.py scan-mdx' first")
                return

            # Initialize the MethodMappingManager
            manager = MethodMappingManager(
                config=self.config,
                rust_methods=rust_data,
                mdx_methods=mdx_methods,
                verbose=self.verbose
            )

            if args.subcommand == 'generate':
                manager.generate_mapping_file()
            elif args.subcommand == 'update':
                manager.update_mapping_file()
            elif args.subcommand == 'validate':
                manager.validate_mapping_file()
            elif args.subcommand == 'create-drafts':
                manager.create_draft_files()
            
            success = True
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self._print_footer(command_title, success=success)

    def postman_command(self, args):
        """Handle postman subcommand - Postman collection generation."""
        command_title = "Postman Collection Generation"
        versions = args.versions
        if "all" in versions:
            versions = ["v1", "v2"]
        
        config_lines = [
            f"Versions: {versions}",
        ]
        self._print_header(command_title, config_lines)
        
        success = False
        try:
            # Step 1: Generate method paths file first (like other commands)
            self.logger.info("🗺️ Generating method mapping with Postman hotlinks...")
            mapper = MethodMappingManager(config=self.config, verbose=self.verbose)
            
            # Use async mapping for better performance and generate paths file
            run_async(mapper.save_unified_mapping_async())
            
            # Step 2: Generate Postman collections
            self.logger.info("📮 Generating Postman collections...")
            # Initialize manager
            manager = PostmanManager(config=self.config, verbose=self.verbose)
            
            # Generate collections
            results = manager.generate_collections(versions)
            summary = manager.generate_summary_report(results)
            
            # Step 3: Generate tracking file - read from the method paths file we just created
            self._generate_postman_tracking_file_from_latest_data(versions)
            
            self.logger.success("Postman collection generation completed!")
            print(summary)
            success = True
            
        except Exception as e:
            self.log(f"❌ Error in postman command: {e}", "error")
            if self.verbose:
                self.log(f"Full traceback: {traceback.format_exc()}", "error")
        
        self._print_footer(command_title, success=success)
        return 0 if success else 1
    
    def json_extract_command(self, args):
        """Handle json-extract subcommand - Extract JSON examples from MDX files."""
        self.log("Starting JSON example extraction from MDX files...")
        
        try:
            # Initialize components
            mapper = MethodMappingManager(verbose=self.verbose)
            extractor = MdxJsonExampleExtractor(verbose=self.verbose)
            
            # Get unified mapping using async for better performance (consistent with other commands)
            if self.verbose:
                self.logger.info("Using async processing for method mapping...")
            
            unified_mapping = run_async(mapper.create_unified_mapping_async())

            versions = ['v1', 'v2']
            
            # Initialize tracking data
            all_extracted_methods = {}
            extraction_stats = {
                'total_extracted': 0,
                'total_methods_processed': 0,
                'total_examples_found': 0,
                'methods_with_examples': 0,
                'methods_without_examples': 0,
                'versions_processed': versions,
                'v1': {'total_extracted': 0, 'total_examples_found': 0, 'methods_with_examples': 0},
                'v2': {'total_extracted': 0, 'total_examples_found': 0, 'methods_with_examples': 0}
            }
            
            for version in versions:
                if version not in unified_mapping:
                    self.log(f"No methods found for version {version}", "warning")
                    continue
                
                methods = unified_mapping[version]
                version_count = 0
                version_examples = 0
                version_methods_with_examples = 0
                
                self.log(f"Processing {len(methods)} methods for {version.upper()}")
                extraction_stats['total_methods_processed'] += len(methods)
                
                for method_name, mapping in methods.items():
                    if not mapping.has_mdx:
                        self.logger.warning(f"Skipping {method_name}: No MDX file found")
                        continue
                    
                    # Extract examples from MDX
                    examples = extractor.extract_from_mdx_file(method_name, mapping, version)
                    
                    if not examples:
                        self.logger.warning(f"{method_name}: No JSON examples found")
                        extraction_stats['methods_without_examples'] += 1
                        continue
                    
                    # Clean method names from examples (fix escaped underscores)
                    cleaned_examples = []
                    for example in examples:
                        # Clean the method name in the example
                        cleaned_method_name = example.method_name.replace('\\_', '_')
                        # Create a new example with cleaned method name
                        cleaned_example = ExtractedExample(
                            method_name=cleaned_method_name,
                            version=example.version,
                            example_type=example.example_type,
                            content=example.content,
                            source_file=example.source_file,
                            line_number=example.line_number,
                            description=example.description
                        )
                        cleaned_examples.append(cleaned_example)                    

                    self.logger.info(f"{method_name:64} Found {len(cleaned_examples)} examples")
                    
                    # Store method info for tracking
                    if method_name not in all_extracted_methods:
                        all_extracted_methods[method_name] = {
                            'method_name': method_name.replace('\\_', '_'),  # Clean method name
                            'version': version,
                            'mdx_path': mapping.mdx_path if hasattr(mapping, 'mdx_path') else str(mapping.get('mdx_path', '')),
                            'examples_count': len(cleaned_examples),
                            'examples': []
                        }
                    if not args.dry_run:
                    # Save each example
                        for i, example in enumerate(cleaned_examples, 1):

                            # Clean method name for folder creation
                            # The canonical method name (e.g., 'task::enable_utxo::init') is converted to
                            # a directory-safe format by replacing '::' with hyphens.
                            # Underscores within method parts are preserved (e.g., 'task-enable_utxo-init').
                            folder_name = example.method_name.replace("::", "-")
                            
                            # Define output directory based on version
                            output_dir = self.config.directories.postman_json_v1 if version == 'v1' else self.config.directories.postman_json_v2
                            
                            # Create full path for the example file
                            example_dir = output_dir / folder_name
                            
                            ensure_directory_exists(example_dir)

                            # Generate filename
                            filename = f"{example.example_type}_{i}.json"
                            output_path = example_dir / filename
                            all_extracted_methods[method_name].update({
                                'json_examples_path': str(example_dir),
                            })
                            if self._save_json_example(output_path, example):
                                version_count += 1
                                # Track example info
                                all_extracted_methods[method_name]['examples'].append({
                                    'example_num': i,
                                    'description': example.description,
                                    'example_type': example.example_type,
                                    'line_number': example.line_number
                                })
                                # self.logger.save(f"{method_name}: Saved example {i} to {self.config.directories.get_relative_path(str(output_path))}")
                    
                    version_examples += len(cleaned_examples)
                    version_methods_with_examples += 1
                
                self.logger.finish(f"{version.upper()}: {version_count} examples extracted from {version_methods_with_examples} methods")
                
                # Update global stats
                extraction_stats['total_extracted'] += version_count
                extraction_stats['total_examples_found'] += version_examples
                extraction_stats['methods_with_examples'] += version_methods_with_examples

                # Update version-specific stats
                if version in extraction_stats:
                    extraction_stats[version]['total_extracted'] = version_count
                    extraction_stats[version]['total_examples_found'] = version_examples
                    extraction_stats[version]['methods_with_examples'] = version_methods_with_examples
            
            # Generate tracking files
            if not args.dry_run:
                self._generate_json_tracking_files(all_extracted_methods, extraction_stats)
            
            self.log(f"🎯 Total: {extraction_stats['total_extracted']} JSON examples extracted from {extraction_stats['methods_with_examples']} methods", "success")
            return 0
            
        except Exception as e:
            self.log(f"JSON extraction failed: {e}", "error")
            return 1
    
    def review_draft_quality_command(self, args):
        """Handle review-draft-quality subcommand - Compare generated docs with live versions."""
        self.log("Starting draft quality analysis...")
        
        # Validate arguments
        if bool(args.generated) != bool(args.live):
            self.log("❌ Error: Both --generated and --live must be specified together, or neither", "error")
            return 1
        
        if args.generated and args.live:
            if not args.generated.exists():
                self.log(f"❌ Generated file not found: {args.generated}", "error")
                return 1
            if not args.live.exists():
                self.log(f"❌ Live file not found: {args.live}", "error")
                return 1
        
        try:
            # Create analyzer with custom directories if provided
            analyzer = DraftsManager(
                generated_docs_dir=args.generated_dir,
                live_docs_dir=args.live_dir
            )
            
            if args.dry_run:
                # Show what would be analyzed
                if args.generated and args.live:
                    self.log(f"Would analyze:\n  Generated: {args.generated}\n  Live: {args.live}")
                else:
                    pairs = analyzer.find_corresponding_files()
                    self.log(f"Would analyze {len(pairs)} document pairs:")
                    for gen, live in pairs[:10]:  # Show first 10
                        self.logger.info(f"  {gen.name} <-> {live.relative_to(analyzer.live_docs_dir)}")
                    if len(pairs) > 10:
                        self.logger.info(f"  ... and {len(pairs) - 10} more")
                return 0
            
            # Run analysis
            self.log("🔍 Analyzing documentation quality...")
            
            if args.format == 'json':
                # TODO: Implement JSON output
                self.log("JSON format not yet implemented, using markdown", "warning")
            
            report = analyzer.review_draft_quality(
                generated_path=args.generated,
                live_path=args.live,
                output_file=args.output
            )
            
            # Print summary to console
            lines = report.split('\n')
            summary_end = next((i for i, line in enumerate(lines) if line.startswith('## Top Improvement')), len(lines))
            summary = '\n'.join(lines[:summary_end + 10])  # Include a bit of the improvements section
            
            self.logger.separator("DRAFT QUALITY ANALYSIS SUMMARY")
            self.logger.separator("="*60)
            self.logger.info(summary)
            self.logger.separator("="*60)
            
            if args.output:
                self.log(f"Full report saved to: {args.output}", "success")
            else:
                import glob
                latest_report_files = glob.glob(str(self.config.directories.branched_reports_dir / "draft_quality_report.md"))
                if latest_report_files:
                    latest_report = max(latest_report_files, key=lambda p: Path(p).stat().st_mtime)
                    self.log(f"Full report saved to: {latest_report}", "success")
            
            self.log("Draft quality analysis completed successfully!", "success")
            return 0
            
        except Exception as e:
            self.log(f"❌ Draft quality analysis failed: {e}", "error")
            return 1
    
    def scan_existing_docs_command(self, args):
        """Handle scan-existing-docs subcommand - Scan existing KDF documentation to extract method patterns."""
        self.log("Starting existing documentation scan...")
        
        try:
            # Create scanner instance
            scanner = ExistingDocsScanner(
                docs_base_path=Path(args.docs_path) if args.docs_path else None,
                verbose=self.verbose
            )
            
            # Perform the scan
            if args.async_scan:
                # Use async scanning for better performance
                patterns = asyncio.run(scanner.scan_all_methods_async())
            else:
                patterns = scanner.scan_all_methods()
            
            if not patterns:
                self.log("⚠️  No documentation patterns found", "warning")
                return 1
            
            # Save patterns to file
            output_file = Path(args.output) if args.output else None
            saved_file = scanner.save_patterns(output_file)
            
            # Generate analysis report if requested
            if args.generate_report:
                report = scanner.generate_analysis_report()
                report_file = saved_file.parent / f"{saved_file.stem}_analysis_report.md"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                self.log(f"📊 Analysis report saved: {report_file}", "success")
            
            # Show summary
            if self.verbose:
                analysis = scanner.analyze_patterns()
                self.log(f"✅ Scan completed successfully:", "success")
                self.log(f"   📄 Patterns saved: {saved_file}")
                self.log(f"   📊 Total methods: {analysis['total_methods']}")
                self.log(f"   📂 Categories: {len(analysis['method_categories'])}")
                self.log(f"   🔧 Common parameters: {len(analysis['common_parameters'])}")
                
                if args.show_categories:
                    self.log("📂 Method categories:")
                    for category, methods in analysis['method_categories'].items():
                        self.log(f"   {category}: {len(methods)} methods")
            
            return 0
            
        except Exception as e:
            self.log(f"❌ Existing docs scan failed: {e}", "error")
            return 1
    
    def generate_docs_command(self, args):
        """Handle generate-docs subcommand - Generate documentation for missing KDF methods."""
        self.log("Starting comprehensive documentation generation...")
        
        try:
            # Create generator instance
            generator = MdxGenerator(
                branch=args.branch or "dev",
                repo_path=args.repo_path,
                verbose=self.verbose
            )
            
            # Determine which methods to generate
            selected_methods = []
            
            if args.method:
                # Generate specific method
                version = args.version or "v2"
                selected_methods = [(args.method, version)]
                self.log(f"🎯 Generating documentation for specific method: {args.method} ({version})")
            
            elif args.methods_file:
                # Load methods from file
                import json
                with open(args.methods_file, 'r') as f:
                    methods_data = json.load(f)
                
                if isinstance(methods_data, dict):
                    # Format: {"v2": ["method1", "method2"], "v1": ["method3"]}
                    for version, methods in methods_data.items():
                        for method in methods:
                            selected_methods.append((method, version))
                elif isinstance(methods_data, list):
                    # Format: [{"method": "method1", "version": "v2"}, ...]
                    for item in methods_data:
                        if isinstance(item, dict):
                            method = item.get("method", "")
                            version = item.get("version", "v2")
                            if method:
                                selected_methods.append((method, version))
                        elif isinstance(item, str):
                            # Just method names, assume v2
                            selected_methods.append((item, "v2"))
                
                self.log(f"📋 Loaded {len(selected_methods)} methods from file")
            
            else:
                # Load all missing methods from unified mapping
                import asyncio
                missing_methods = asyncio.run(generator.load_missing_methods())
                
                if not missing_methods:
                    self.log("⚠️  No missing methods found in unified mapping", "warning")
                    return 1
                
                # Convert to list of tuples
                for version, methods in missing_methods.items():
                    for method in methods:
                        selected_methods.append((method, version))
                
                # Show options and let user select (if interactive)
                if args.interactive and selected_methods:
                    selected_methods = self._select_methods_interactively(selected_methods)
                
                self.log(f"📋 Found {len(selected_methods)} missing methods to generate")
            
            if not selected_methods:
                self.log("❌ No methods selected for generation", "error")
                return 1
            
            # Generate the documentation
            import asyncio
            generated_files = asyncio.run(
                generator.generate_documentation_for_methods(selected_methods)
            )
            
            if generated_files:
                # Show results
                self.log(f"✅ Documentation generation completed!", "success")
                self.log(f"   📄 Generated: {len(generated_files)} method documentation files")
                
                if self.verbose:
                    for method, file_path in generated_files.items():
                        self.log(f"   📄 {method}: {file_path}")
                
                # Create summary report if requested
                if args.generate_summary:
                    summary_file = Path(args.output_dir or "data") / "generation_summary.md"
                    self._create_generation_summary(selected_methods, generated_files, summary_file)
                    self.log(f"📊 Generation summary saved: {summary_file}")
                
                return 0
            else:
                self.log("❌ No documentation was generated", "error")
                return 1
                
        except Exception as e:
            self.log(f"❌ Documentation generation failed: {e}", "error")
            if self.verbose:
                self.log(traceback.format_exc(), "error")
            return 1
    
    def _select_methods_interactively(self, methods_list):
        """Placeholder for interactive method selection."""
        pass

    def _create_generation_summary(self, selected_methods, generated_files, summary_file):
        with open(summary_file, "w") as f:
            f.write(f"Generated {len(generated_files)} files for {len(selected_methods)} methods.\n\n")
            f.write("Generated Files:\n" + "\n".join(f"- {Path(p).name}" for p in generated_files) + "\n\n")
            f.write("Selected Methods:\n" + "\n".join(f"- {m}" for m in selected_methods) + "\n")

    async def _save_json_example_async(self, output_path: Path, example: ExtractedExample) -> bool:
        """Asynchronously save a single JSON example to the correct file path."""
        safe_write_json(output_path, example.content, indent=2)
        return True

    def _save_json_example(self, output_path: Path, example: ExtractedExample) -> bool:
        return run_async(self._save_json_example_async(output_path, example))

    def _generate_json_tracking_files(self, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Top-level function to generate all JSON-related tracking files."""
        self.log("Generating JSON tracking files...", "info")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        method_paths_file = self._generate_json_method_paths_file(all_extracted_methods)
        methods_file = self._generate_json_methods_file(method_paths_file, extraction_stats)
        return method_paths_file, methods_file
    
    def _generate_openapi_tracking_files(self, openapi_manager: OpenAPIManager, versions: List[str], version_method_counts: Dict[str, int]) -> str:
        """Generates all necessary tracking files for OpenAPI."""

        return self.openapi_spec_generator._generate_openapi_method_paths_file(
            all_methods=openapi_manager.all_methods,
            path_mapper=openapi_manager.path_mapper,
            versions=versions,
            version_method_counts=version_method_counts
        )  

    def _generate_json_method_paths_file(self, all_extracted_methods: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a JSON file mapping each method to its JSON examples path."""
        self.logger.info("Generating JSON method paths file...")
        v1_methods = {data["method_name"]: data["json_examples_path"] for data in all_extracted_methods.values() if data["version"] == "v1"}
        v2_methods = {data["method_name"]: data["json_examples_path"] for data in all_extracted_methods.values() if data["version"] == "v2"}
        paths_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDF-MDX-JSON-Example-Extractor v1.0.0",
                "scanner_type": "MDX_JSON_EXAMPLE_EXTRACTOR",
                "total_methods": {
                    "all": len(v1_methods) + len(v2_methods),
                    "v1": len(v1_methods),
                    "v2": len(v2_methods)
                },
                "versions_processed": ["v1", "v2"],
                "is_primary_data_source": False
            },
            "method_paths": {
                "v1": v1_methods,
                "v2": v2_methods
            }
        }

        file_path = self.config.directories.mdx_json_example_method_paths_report
        safe_write_json(file_path, paths_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.logger.save(f"Saved Postman method paths mapping to: {log_path}")
        self.log(f"📊 V1: {len(paths_data['method_paths']['v1'])} methods")
        self.log(f"📊 V2: {len(paths_data['method_paths']['v2'])} methods")
        return paths_data

    def _generate_json_methods_file(self, method_paths_data: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generates a JSON file that maps each method to its extracted JSON examples."""
        self.log("Generating JSON methods file...")
        v1_methods = list(method_paths_data["method_paths"]["v1"].keys())
        v2_methods = list(method_paths_data["method_paths"]["v2"].keys())
        methods_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDF-MDX-JSON-Example-Extractor v1.0.0",
                "scanner_type": "MDX_JSON_EXAMPLE_EXTRACTOR",
                "total_versions": 2,
                "total_methods": {
                    "all": len(v1_methods) + len(v2_methods),
                    "v1": len(v1_methods),
                    "v2": len(v2_methods)
                },
                "versions_processed": ["v1", "v2"],
                "is_primary_data_source": False
            },
            "repository_data": {
                "v1": {
                    "methods": v1_methods,
                    "extraction_patterns_used": ["JSON extraction from MDX files"],
                    "total_extracted": extraction_stats['v1']['total_extracted'],
                    "total_methods_processed": len(v1_methods),
                    "total_examples_found": extraction_stats['v1']['total_examples_found']
                },
                "v2": {
                    "methods": v2_methods,
                    "extraction_patterns_used": ["JSON extraction from MDX files"],
                    "total_extracted": extraction_stats['v2']['total_extracted'],
                    "total_methods_processed": len(v2_methods),
                    "total_examples_found": extraction_stats['v2']['total_examples_found']
                }
            }
        }
        file_path = self.config.directories.mdx_json_example_methods_report
        safe_write_json(file_path, methods_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.logger.save(f"Saved JSON extraction examples summary to: {log_path}")
        self.log(f"📊 V1: {extraction_stats['v1']['total_examples_found']} examples from {extraction_stats['v1']['methods_with_examples']} methods")
        self.log(f"📊 V2: {extraction_stats['v2']['total_examples_found']} examples from {extraction_stats['v2']['methods_with_examples']} methods")

    def _generate_postman_tracking_file_from_latest_data(self, versions: List[str]) -> None:
        """Placeholder for generating Postman tracking file."""
        pass

    def setup_postman_parser(self, subparsers):
        """Setup parser for the postman command."""
        parser = subparsers.add_parser(
            'postman',
            help='Generate Postman collections from OpenAPI specs.',
            description='Converts OpenAPI specifications into Postman collections for easier API testing and integration.'
        )
        parser.add_argument(
            '--versions', nargs='+', default=['all'],
            help="List of versions to process (e.g., v1 v2 all). Default: ['all']"
        )
        parser.set_defaults(func=self.postman_command)

    def setup_openapi_parser(self, subparsers):
        """Setup parser for the openapi command."""
        parser = subparsers.add_parser(
            'openapi',
            help='Generate OpenAPI specs from MDX documentation.',
            description='Processes MDX documentation files to create OpenAPI specifications'
        )
        parser.add_argument(
            '--version', type=str, default='v2',
            help='Specify the API version to process.'
        )
        parser.set_defaults(func=self.openapi_command)

    def setup_scan_mdx_parser(self, subparsers):
        """Sets up argument parser for the mdx_scan command."""
        parser = subparsers.add_parser('scan-mdx', help='Scan MDX files for method info.')
        parser.add_argument(
            '--versions', 
            default='all',
            help='Comma-separated KDF versions to scan (e.g., v1,v2). Default: all'
        )
        parser.add_argument(
            '--branch', 
            default='dev',
            help='The git branch of the repo being scanned. Default: dev'
        )
        parser.set_defaults(func=self.scan_mdx_command)

    
    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for the scan-rust command."""
        parser = subparsers.add_parser(
            'scan-rust', 
            help='Scan KDF Rust repository for RPC methods.',
            description='Scans the Komodo DeFi Framework Rust repository to find RPC methods.'
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.add_argument(
            '--versions', nargs='+', default=['v2', 'v1'],
            help="List of versions to scan (e.g., v1 v2). Default: ['v2', 'v1']"
        )
        parser.set_defaults(func=self.scan_rust)


    def setup_map_methods_parser(self, subparsers):
        """Setup parser for the map-methods command."""
        parser = subparsers.add_parser(
            'map_methods',
            help='Generate a unified mapping of all method-related files.',
            description='Creates a comprehensive JSON file that maps each method to its corresponding MDX, OpenAPI, and Postman files.'
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='Remove all files associated with a specific method.'
        )
        parser.add_argument(
            '--debug',
            type=str,
            help='Debug method matching for a specific method.'
        )
        parser.set_defaults(func=self.methods_map_command)

    def setup_json_extract_parser(self, subparsers):
        """Setup parser for the json-extract command."""
        parser = subparsers.add_parser(
            'json-extract',
            help='Extract JSON examples from MDX files.',
            description='Extracts JSON request/response examples from MDX documentation.'
        )
        parser.set_defaults(func=self.json_extract_command)

    def setup_review_draft_quality_parser(self, subparsers):
        """Setup parser for the review-draft-quality command."""
        parser = subparsers.add_parser(
            'review-draft-quality',
            help='Compare generated documentation with live versions.',
            description='Compares generated documentation with live versions to assess quality.'
        )
        parser.add_argument(
            '--generated', type=Path, required=True,
            help='Path to the generated documentation file.'
        )
        parser.add_argument(
            '--live', type=Path, required=True,
            help='Path to the live documentation file.'
        )
        parser.add_argument(
            '--generated-dir', type=Path,
            help='Directory containing generated documentation files.'
        )
        parser.add_argument(
            '--live-dir', type=Path,
            help='Directory containing live documentation files.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the review report.'
        )
        parser.add_argument(
            '--format', choices=['json', 'markdown'], default='markdown',
            help='Format of the review report.'
        )
        parser.set_defaults(func=self.review_draft_quality_command)

    def setup_scan_existing_docs_parser(self, subparsers):
        """Setup parser for the scan-existing-docs command."""
        parser = subparsers.add_parser(
            'scan-existing-docs',
            help='Scan existing KDF documentation to extract method patterns.',
            description='Scans existing KDF documentation to extract method patterns.'
        )
        parser.add_argument(
            '--docs-path', type=Path,
            help='Path to the directory containing existing documentation files.'
        )
        parser.add_argument(
            '--async-scan', action='store_true',
            help='Use asynchronous scanning for better performance.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the extracted method patterns.'
        )
        parser.add_argument(
            '--generate-report', action='store_true',
            help='Generate an analysis report of the extracted method patterns.'
        )
        parser.add_argument(
            '--show-categories', action='store_true',
            help='Show method categories in the analysis report.'
        )
        parser.set_defaults(func=self.scan_existing_docs_command)

    def setup_generate_docs_parser(self, subparsers):
        """Sets up the argument parser for the `generate-docs` command."""
        parser = subparsers.add_parser(
            "generate-docs",
            help="Generate MDX documentation from templates for specified methods.",
            description="This command automates the creation of MDX documentation files from pre-defined templates. It can use a list of methods from a file or allow interactive selection.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "-m", "--methods",
            nargs='+',
            help="A list of one or more method names to generate documentation for."
        )
        parser.add_argument(
            "-f", "--methods-file",
            type=str,
            help="Path to a file containing a list of method names (one per line)."
        )
        parser.add_argument(
            "-i", "--interactive",
            action="store_true",
            help="Use interactive mode to select methods from a list."
        )
        parser.add_argument(
            "-t", "--template",
            type=str,
            default="default",
            help="The template to use for generation (e.g., 'default', 'comprehensive')."
        )
        parser.add_argument(
            "-o", "--output-dir",
            type=str,
            default=str(self.config.directories.data_dir / "generated_docs"),
            help="The directory to save the generated MDX files."
        )
        parser.set_defaults(func=self.generate_docs_command)

    def setup_gap_analysis_parser(self, subparsers):
        """Sets up the argument parser for the `gap-analysis` command."""
        parser = subparsers.add_parser(
            "gap-analysis",
            help="Perform gap analysis between Rust and MDX methods.",
            description="Compares methods found in the Rust repository against those documented in MDX files."
        )
        parser.add_argument(
            "--versions",
            nargs="+",
            default=["v1", "v2"],
            help="List of API versions to process (e.g., v1 v2)."
        )
        parser.set_defaults(func=self.gap_analysis_command)

    def gap_analysis_command(self, args):
        """Compares Rust methods with MDX documentation and generates a report."""
        command_title = "Gap Analysis"
        config = [
        ]
        self._print_header(command_title, config)
        
        # Load Rust methods
        rust_methods = {}
        rust_scan_files = glob.glob(str(self.config.directories.rust_methods_report))
        if rust_scan_files:
            with open(rust_scan_files[0], 'r') as f:
                rust_data = json.load(f)
            for version in args.versions:
                if version in rust_data['repository_data']:
                    rust_methods[version] = set(rust_data['repository_data'][version]['methods'])
        else:
            self.logger.warning(f"No '{os.path.basename(str(self.config.directories.rust_methods_report))}' file found.")
            self.logger.warning("Please run 'scan-rust' first.")
            return
        
        # Load MDX methods
        mdx_methods = {}
        mdx_scan_files = glob.glob(str(self.config.directories.mdx_methods_report))
        if mdx_scan_files:
            with open(mdx_scan_files[0], 'r') as f:
                mdx_data = json.load(f)
            for version in args.versions:
                if version in mdx_data['repository_data']:
                    mdx_methods[version] = set(mdx_data['repository_data'][version]['methods'])
        else:
            self.logger.warning(f"No '{os.path.basename(str(self.config.directories.mdx_methods_report))}' file found.")
            self.logger.warning("Please run 'scan-mdx' first.")
            return

        # Perform gap analysis
        gap_report = {}
        for v in args.versions:
            if v not in rust_methods or v not in mdx_methods:
                continue
            self.log(f"🔍 Processing {v.upper()}...")
            rust_method_set = rust_methods[v]
            doc_method_set = mdx_methods[v]

            missing_in_docs = sorted(list(rust_method_set - doc_method_set))
            extra_in_docs = sorted(list(doc_method_set - rust_method_set))

            gap_report[v] = {
                "missing_in_docs": missing_in_docs,
                "extra_in_docs": extra_in_docs,
                "total_rust_methods": len(rust_method_set),
                "total_doc_methods": len(doc_method_set),
                "undocumented_methods": len(missing_in_docs),
                "extra_methods_in_docs": len(extra_in_docs),
                "coverage": f"{len(doc_method_set) / len(rust_method_set) * 100:.2f}%"
            }

            self.log(f"   - Total methods in Rust: {len(rust_method_set)}")
            self.log(f"   - Total methods in MDX: {len(doc_method_set)}")
            self.log(f"   - Coverage: {gap_report[v]['coverage']}")
            if missing_in_docs:
                self.log(f"   - 🚨 Undocumented methods: {len(missing_in_docs)}")
            if extra_in_docs:
                self.log(f"   - ⚠️  Extra methods in docs: {len(extra_in_docs)}")

        # Save report
        report_path = self.config.directories.kdf_gap_analysis_report
        safe_write_json(report_path, gap_report, indent=2)
        self.logger.save(f"Gap analysis report saved to: {report_path}")

        success = True
        self._print_footer(command_title, success=success)

    def generate_common_schemas_command(self, args):
        """Generates OpenAPI schemas for common structures and enums."""
        command_title = "Generate Common Schemas"
        self._print_header(command_title)
        success = False
        try:
            manager = OpenAPIManager(config=self.config, verbose=self.verbose)
            manager.generate_common_schemas_only()
            success = True
        except Exception as e:
            self.log(f"An error occurred during common schema generation: {e}", "error")
            self.log(traceback.format_exc(), "error")
        finally:
            self._print_footer(command_title, success=success)

    def clean_json_files(self):
        """Removes all request, response, and error JSON files from Postman directories."""
        self.logger.info("Cleaning existing JSON files...")

        postman_dirs = [
            self.config.directories.postman_json_v1,
            self.config.directories.postman_json_v2
        ]

        patterns = ["request_*.json", "response_*.json", "error_*.json"]
        deleted_count = 0

        for p_dir in postman_dirs:
            if not p_dir.exists():
                self.logger.warning(f"Directory not found, skipping clean: {p_dir}")
                continue

            self.logger.info(f"Cleaning files in {p_dir}...")
            # Use rglob to recursively find files in subdirectories
            for pattern in patterns:
                for file_path in p_dir.rglob(pattern):
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except OSError as e:
                        self.logger.error(f"Error deleting file {file_path}: {e}")

        if deleted_count > 0:
            self.logger.success(f"Successfully deleted {deleted_count} JSON files.")
        else:
            self.logger.info("No JSON files found to clean.")

    def get_kdf_responses_command(self, args):
        try:
            """Gets API responses for a given method and version."""
            command_title = "Get KDF API Responses"
            config_lines = [
                f"Method: {args.method if args.method else None}",
                f"KDF Branch: {args.kdf_branch}",
            ]
            self._print_header(command_title, config_lines=config_lines)

            if args.kdf_branch:
                if not self._switch_kdf_branch(args.kdf_branch):
                    self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting.")
                    self._print_footer(command_title, success=False)
                    return

            if args.clean:
                self.clean_json_files()
                self.json_extract_command(args)

            self.start_container_command(args)
            time.sleep(5)
            
            if args.method:
                # Process a single method if specified
                versions_to_process = [args.version] if args.version != 'all' else ['v1', 'v2']
                for version in versions_to_process:
                    self.logger.info(f"Processing single method: {args.method}, version: {version}")
                    self.processor.process_method_request(
                        method=args.method,
                        version=version
                    )
            else:
                # Process all methods with sequencing
                self.logger.info("Processing all methods with sequencing...")
                examples = self.get_json_example_method_paths()
                
                for version, method_paths in examples.items():
                    self.logger.info(f"--- Processing version: {version.upper()} ---")
                    
                    all_methods_in_version = set(method_paths.keys())
                    
                    # Create an ordered execution plan
                    execution_plan = self._create_execution_plan(all_methods_in_version)
                    
                    self.logger.info(f"Execution plan for {version.upper()} created with {len(execution_plan)} methods.")

                    delayed_methods = []
                    for method in execution_plan:
                        validator = MethodValidator(method, version, self.processor)
                        
                        if not validator.validate_method_for_testing():
                            self.logger.info(f"Skipping {method}, not valid for test case: [{version} HD: {self.processor.enable_hd}]")
                            continue

                        if not validator.is_method_ready():
                            # Delays methods which need a prior method to be completed
                            self.logger.info(f"Skipping not ready method: {method}")
                            delayed_methods.append(method)
                            continue
                            
                        if method == "stop":
                            self.logger.info(f"Skipping stop method: {method}")
                            continue

                        mdx_path = get_method_path("mdx", method, version)
                        json_path = get_method_path("json", method, version)
                        if mdx_path is None:
                            self.logger.error(f"Method path not found for method: {method}, version: {version}")
                            continue
                        self.logger.info(f"MDX method path: {mdx_path}")
                        self.logger.info(f"JSON method path: {json_path}")
                        self.logger.info(f"Processing method: {method}, version: {version}")
                        self.logger.info(f"--------------------------------")

                        try:
                            self.processor.process_method_request(
                                method=method,
                                version=version
                            )
                        except Exception as e:
                            self.logger.error(f"An error occurred while processing {method}: {e}")
                            self.logger.error(traceback.format_exc())
                            # Save the error to a file so it can be reported
                            error_content = {
                                "error": f"Failed to process method '{method}': {str(e)}",
                                "error_type": "PROCESSOR_EXECUTION_ERROR",
                                "traceback": traceback.format_exc()
                            }
                            error_filename = f"error_processor_failed.json"
                            folder_name = method.replace("::", "-")
                            output_dir = self.config.directories.postman_json_v1 if version == 'v1' else self.config.directories.postman_json_v2
                            example_dir = output_dir / folder_name
                            ensure_directory_exists(example_dir)
                            error_path = example_dir / error_filename
                            safe_write_json(error_path, error_content)
                        time.sleep(1)

        except KeyboardInterrupt:
            self.logger.error("Keyboard interrupt detected. Stopping container...")
        finally:
            self.stop_container_command()
            self.report_error_responses()
            self._print_footer(command_title, success=False)


    def _create_execution_plan(self, all_methods: set) -> List[str]:
        """Creates an ordered list of methods to execute, prioritizing sequences."""
        
        # Get activation methods from the processor
        activation_methods = self.processor.activation_methods

        # Define method sequences here. This could be moved to a config file later.
        method_sequences = [
            # Pubkey banning sequence
            ["ban_pubkey", "list_banned_pubkeys", "unban_pubkeys"],
            # Swap sequence
            ["buy", "my_swap_status"],
            ["sell", "my_swap_status"],
            # KMD rewards
            ["kmd_rewards_info"],
            # Non-task activation sequences
            ["enable_eth_with_tokens", "enable_erc20"],
            ["enable_tendermint_with_assets", "enable_tendermint_token"],
            # Generic task sequences
            *[
                [f"task::{group}::{suffix}" for suffix in ["init", "status", "cancel"]]
                for group in [
                    "withdraw",
                    "enable_bch",
                    "enable_utxo",
                    "enable_eth",
                    "enable_qtum",
                    "enable_sia",
                    "enable_tendermint",
                    "enable_z_coin",
                    "get_new_address",
                    "scan_for_new_addresses",
                ]
            ],
            # Message signing sequence
            ["sign_message", "verify_message"],
            # Send raw tx sequence
            ["get_unsigned_transaction", "send_raw_transaction"],
        ]

        execution_plan = []
        processed_in_sequence = set()

        # 1. Add activation methods first, if they exist in the set of methods to run
        for method in sorted(list(activation_methods)):
            if method in all_methods:
                execution_plan.append(method)
                processed_in_sequence.add(method)
        
        self.logger.info(f"Prioritized {len(processed_in_sequence)} activation methods.")

        # 2. Add methods from defined sequences to the plan
        for sequence in method_sequences:
            for method_in_seq in sequence:
                if method_in_seq in all_methods and method_in_seq not in processed_in_sequence:
                    execution_plan.append(method_in_seq)
                    processed_in_sequence.add(method_in_seq)
        
        # 3. Add all other methods that are not part of any sequence, sorted alphabetically
        remaining_methods = sorted(list(all_methods - processed_in_sequence))
        execution_plan.extend(remaining_methods)
        
        return execution_plan

    def setup_get_kdf_responses_parser(self, subparsers):
        """Sets up the parser for the get-kdf-responses command."""
        parser = subparsers.add_parser('get-kdf-responses', help='Get API responses from a running KDF container.')
        parser.add_argument('--method', type=str, required=False, default=None, help='The API method to get responses for.')
        parser.add_argument('--version', type=str, required=False, default='all', help='The API version (e.g., v1, v2).')
        parser.add_argument('--kdf-branch', type=str, default='dev', help='The KDF branch to use for the container.')
        parser.add_argument('--commit', type=str, help='The commit hash to use. Defaults to the latest commit on the branch.')
        parser.add_argument('--clean', action='store_true', help='Remove all existing request/response/error json files in postman/json/kdf before running.')
        parser.set_defaults(func=self.get_kdf_responses_command)

    def build_container_command(self, args):
        """Builds the KDF container image."""
        self.logger.warning("The 'build-container' command is deprecated. The container is now built automatically when started.")
        self.start_container_command(args)

    def start_container_command(self, args):
        """Starts the KDF container."""
        command_title = "Start KDF Container"
        config_lines = [f"KDF Branch (from local repo): {args.kdf_branch}"]
        self._print_header(command_title, config_lines)

        kdf_repo_path = self.config.directories.kdf_repo_path
        if not kdf_repo_path.exists():
            self.logger.error(f"KDF repository not found at '{kdf_repo_path}'.")
            self.logger.error("Please run 'git clone <kdf_repo_url>' to clone it.")
            self._print_footer(command_title, success=False)
            return

        current_branch = self._switch_kdf_branch(args.kdf_branch)
        if not current_branch:
            self._print_footer(command_title, success=False)
            return
            
        self._print_header(command_title, config_lines=[
            f"KDF Branch (from local repo): {current_branch}"
        ])

        # Path to the docker-compose.yml file in the 'utils/docker' directory
        compose_file_path = self.config.directories.docker_dir / "docker-compose.yml"
        
        if not compose_file_path.exists():
            self.logger.error(f"docker-compose.yml not found at: {compose_file_path}")
            self._print_footer(command_title, success=False)
            return

        try:            
            # Run docker-compose
            subprocess.run(
                ['docker', 'compose', '--file', str(compose_file_path), 'up', '--build', '-d'],
                check=True,
                cwd=self.config.directories.docker_dir
            )
            self.logger.success(f"Container started successfully.")
            success = True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start container: {e}")
            success = False
        finally:
            self._print_footer(command_title, success=success)
        
        if success:
            time.sleep(5)  # Give the container a moment to initialize
            self.processor._update_enabled_coins()
        
        return 0 if success else 1

    def stop_container_command(self):
        """Stops the KDF container."""
        command_title = "Stop KDF Container"
        self._print_header(command_title)
        result = self.processor.stop_container()
        self._print_footer(command_title, success=result)

    def _switch_kdf_branch(self, branch_name: str):
        """Checks out the specified branch in the local KDF repository."""
        kdf_repo_path = self.config.directories.kdf_repo_path
        if not kdf_repo_path.exists() or not (kdf_repo_path / ".git").exists():
            self.logger.error(f"KDF repository not found at {kdf_repo_path}. Please clone it first.")
            return False

        self.logger.info(f"Switching local KDF repository to branch '{branch_name}'...")

        try:
            # Fetch the latest changes from origin
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=kdf_repo_path, check=True, capture_output=True, text=True
            )

            # Checkout the branch
            checkout_result = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=kdf_repo_path, check=True, capture_output=True, text=True
            )
            if self.verbose:
                if checkout_result.stdout: self.logger.info(checkout_result.stdout.strip())
                if checkout_result.stderr: self.logger.info(checkout_result.stderr.strip())

            # Pull the latest changes for that branch
            pull_result = subprocess.run(
                ["git", "pull", "origin", branch_name],
                cwd=kdf_repo_path, check=True, capture_output=True, text=True
            )
            if self.verbose and pull_result.stdout:
                self.logger.info(pull_result.stdout.strip())
            
            self.logger.success(f"Successfully switched to and updated branch '{branch_name}'.")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to switch to branch '{branch_name}': {e}")
            self.logger.error(f"Stderr: {e.stderr}")
            return False

    def get_json_example_method_paths(self):
        """Loads method and version data from the kdf_mdx_json_example_method_paths.json report."""
        report_path = self.config.directories.mdx_json_example_method_paths_report

        if not report_path.exists():
            self.logger.error(f"Method paths report not found at: {report_path}")
            self.logger.error("Please run 'json-extract' first to generate it.")
            return {}

        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.logger.error(f"Error decoding JSON from {report_path}")
            return {}

        return data.get("method_paths", {})

    def generate_v2_no_param_methods_report(self, args):
        """Generates a report of V2 methods that have no request parameters."""
        command_title = "Generate V2 No-Parameter Methods Report"
        self._print_header(command_title)
        
        try:
            v2_methods_with_no_params = {}
            v2_json_path = self.config.directories.postman_json_v2
            
            # Use kdf_mdx_method_paths.json to get the list of v2 methods
            mdx_method_paths_file = self.config.directories.mdx_method_paths_report
            with open(mdx_method_paths_file, 'r') as f:
                mdx_method_paths = json.load(f)
            
            v2_methods = mdx_method_paths.get("method_paths", {}).get("v2", {})

            for method_name, _ in v2_methods.items():
                # Correctly format the method name for path lookup
                folder_name = method_name.replace("::", "-")
                method_folder = Path(v2_json_path) / folder_name
                
                if method_folder.is_dir():
                    request_files = list(method_folder.glob("request_*.json"))
                    if not request_files:
                        continue

                    # Check the first request file
                    with open(request_files[0], 'r') as f:
                        try:
                            data = json.load(f)
                            if "params" in data and not data["params"]:
                                relative_path = self.config.directories.get_relative_path(str(request_files[0]))
                                v2_methods_with_no_params[method_name] = relative_path
                        except json.JSONDecodeError:
                            self.logger.warning(f"Could not parse JSON for {request_files[0]}")

            # Save the report
            report_path = self.config.directories.v2_no_param_methods_report
            report_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "report_name": "v2_methods_with_no_parameters"
                },
                "methods": dict(sorted(v2_methods_with_no_params.items())),
                "count": len(v2_methods_with_no_params)
            }
            safe_write_json(report_path, report_data)
            self.logger.success(f"Report generated at: {report_path}")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.logger.error(traceback.format_exc())

    def setup_v2_no_param_report_parser(self, subparsers):
        parser = subparsers.add_parser(
            "v2-no-param-report",
            help="Generate a report of V2 methods that do not require any parameters.",
            description="Scans V2 MDX files and identifies methods with no request parameters."
        )
        parser.set_defaults(func=self.generate_v2_no_param_methods_report)

    def main(self):
        """Main entry point for the KDF Tools CLI."""
        parser = argparse.ArgumentParser(
            description="Unified KDF Tools CLI",
            formatter_class=argparse.RawTextHelpFormatter
        )
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        self.setup_scan_rust_parser(subparsers)
        self.setup_scan_mdx_parser(subparsers)
        self.setup_openapi_parser(subparsers)
        self.setup_postman_parser(subparsers)
        self.setup_map_methods_parser(subparsers)
        self.setup_json_extract_parser(subparsers)
        self.setup_review_draft_quality_parser(subparsers)
        self.setup_scan_existing_docs_parser(subparsers)
        self.setup_generate_docs_parser(subparsers)
        self.setup_gap_analysis_parser(subparsers)
        self.setup_get_kdf_responses_parser(subparsers)
        self.setup_v2_no_param_report_parser(subparsers)


        # Container management commands
        build_parser = subparsers.add_parser('build-container', help='Build KDF container image.')
        build_parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to build.')
        build_parser.add_argument('--commit', type=str, help='Commit hash to build.')
        build_parser.set_defaults(func=self.build_container_command)

        start_parser = subparsers.add_parser('start-container', help='Start KDF container.')
        start_parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to use.')
        start_parser.add_argument('--commit', type=str, help='Commit hash to use.')
        start_parser.set_defaults(func=self.start_container_command)

        stop_parser = subparsers.add_parser('stop-container', help='Stop KDF container.')
        stop_parser.set_defaults(func=self.stop_container_command)

        # New parser for generate-common-schemas
        common_schemas_parser = subparsers.add_parser(
            "generate-common-schemas",
            help="Generate OpenAPI schemas for common structures and enums.",
            description="This command scans the common_structures directory and generates a corresponding OpenAPI schema file for each enum and structure."
        )
        common_schemas_parser.set_defaults(func=self.generate_common_schemas_command)

        args = parser.parse_args()
        
        
        # Add dry_run to args if not present (for commands that dont have it)
        if not hasattr(args, 'dry_run'):
            args.dry_run = False

        # Execute command
        if hasattr(args, 'func'):
            return args.func(args)
        elif args.command == "gap-analysis":
            self.gap_analysis_command(args)
        elif args.command == "generate-common-schemas":
            self.generate_common_schemas_command(args)
        else:
            parser.print_help()
            return 1


class MethodValidator:
    def __init__(self, method: str, version: str, processor: ApiRequestProcessor = None):
        self.processor = processor or ApiRequestProcessor()
        self.logger = get_logger("method-validator")
        self.method = method
        self.version = version
        self.enable_hd = self.processor._get_env_var_as_bool("ENABLE_HD", False)
        
    def validate_method_for_testing(self) -> bool:
        """Checks if a method is valid for the test case being run."""
        if self.enable_hd and self.is_legacy_only_method():
            return False
        if not self.enable_hd and self.is_hd_only_method():
            return False
        if self.is_method_interactive():
            return False
        if self.is_method_too_complex_for_now():
            return False
        if self.is_method_deprecated():
            return False
        return True
    
    def is_hd_only_method(self) -> bool:
        """Checks if a method is HD only."""
        hd_only_methods = {
            "v1": [],
            "v2": [
                "task::get_new_address::cancel",
                "task::get_new_address::init",
                "task::get_new_address::status",
                "task::get_new_address::user_action",
                "task::scan_for_new_addresses::cancel",
                "task::scan_for_new_addresses::init",
                "task::scan_for_new_addresses::status",
            ],
        }
        if self.method in hd_only_methods[self.version]:
            return True
        return False
    
    def is_legacy_only_method(self) -> bool:
        """Checks if a method is legacy only."""
        legacy_only_methods = {
            "v1": ["my_balance"],
            "v2": [],
        }
        if self.method in legacy_only_methods[self.version]:
            return True
        return False

    def is_method_interactive(self) -> bool:
        """Checks if a method is interactive."""
        if (
            self.method.find("trezor") != -1
            or self.method.find("user_action") != -1
            or self.method.find("metamask") != -1
            or self.method.startswith("wc")
        ):
            return True
        return False
    
    def is_method_too_complex_for_now(self) -> bool:
        """Checks if a method is too complex for now."""
        if self.method.startswith("lightning::"):
            return True
        if self.method.startswith("experimental::"):
            return True
        if self.method.find("nft") != -1:
            return True
        if self.method.find("1inch") != -1:
            return True
        if self.method.find("market_maker_bot") != -1:
            return True
        if self.method.find("stat_collection") != -1:
            return True
        return False

    def is_method_deprecated(self) -> bool:
        """Checks if a method is deprecated."""
        if self.method.find("enable_bch") != -1:
            return True
        deprecated_methods = {
            "v1": [],
            "v2": [
                "task::enable_bch::cancel",
                "task::enable_bch::init",
                "task::enable_bch::status",
                "task::enable_bch::user_action",
            ]
        }
        if self.method in deprecated_methods[self.version]:
            return True
        return False

    def is_method_ready(self) -> bool:
        """Checks if a method's prerequisites have been met."""
        method_prerequisites = {
            "unban_pubkeys": ["ban_pubkey"],
            "send_raw_transaction": ["get_unsigned_transaction"],
            "my_swap_status": ["buy", "sell"],  # Can depend on either
            "verify_message": ["sign_message"],
        }
        
        # Add task-based prerequisites dynamically
        if "::" in self.method and not self.method.endswith("::init"):
            parts = self.method.split("::")
            task_group = "::".join(parts[:-1])
            init_method = f"{task_group}::init"
            if self.method not in method_prerequisites:
                method_prerequisites[self.method] = []
            method_prerequisites[self.method].append(init_method)
            

        if self.method in method_prerequisites:
            prereqs = method_prerequisites[self.method]
            
            # For methods with multiple possible prerequisites (like my_swap_status)
            if self.method == "my_swap_status":
                if any(p in self.processor.completed_methods for p in prereqs):
                    return True
                else:
                    self.logger.warning(f"Prerequisites for {self.method} not met. Need one of: {prereqs}")
                    return False

            # For methods with specific prerequisites
            for prereq in prereqs:
                if prereq not in self.processor.completed_methods:
                    self.logger.warning(f"Prerequisite '{prereq}' for method '{self.method}' has not been completed.")
                    return False
        
        return True

    def _get_current_git_branch(self, repo_path):
        """Gets the current Git branch of a repository."""
        try:
            # The CWD needs to be the repo path for this command to work correctly.
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, check=True, cwd=repo_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get current branch for repo at '{repo_path}': {e}")
            return None

def main():
    """Script entry point."""
    try:
        cli = KDFTools()
        sys.exit(cli.main())
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        sys.exit(1)
if __name__ == '__main__':
    main()
