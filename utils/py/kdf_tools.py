#!/usr/bin/env python3
"""
Komodo DeFi Framework Tools - Unified CLI

A comprehensive command-line interface for managing KDF documentation, OpenAPI specs,
Postman collections, and repository analysis. This tool consolidates functionality
from multiple specialized scripts into a single, easy-to-use interface.

Available Commands:
- openapi: Convert MDX documentation to OpenAPI specs (--clean-before for auto-cleanup)
- postman: Generate Postman collections (--clean-before for auto-cleanup)
- scan-rust: Scan KDF Rust repository for RPC methods
- scan-mdx: Scan MDX documentation files for method names
- gap-analysis: Compare Rust methods with MDX documentation
- map_methods: Method mapping and OpenAPI management
- json-extract: Extract JSON examples from MDX files
- cleanup: Clean up old temporary files

Recommended Workflows:
    # Generate with automatic cleanup
    kdf_tools.py openapi --version v2 --clean-before
    kdf_tools.py postman --versions v2 --clean-before

Examples:
    kdf_tools.py openapi --version v2 --clean-before # Generate OpenAPI with cleanup
    kdf_tools.py postman --clean-before              # Generate Postman with cleanup

Global Options:
    --dry-run: Show what would be done without making changes
    --quiet: Suppress verbose output
    --keep: Number of recent temporary files to keep during auto-cleanup (default: 3)
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
from utils.py.lib import (
    UnifiedScanner,
    get_logger, DraftsManager,
    MdxGenerator, ExistingDocsScanner
)
from utils.py.lib.constants.config import get_config
from utils.py.lib.rust.scanner import KDFScanner
from utils.py.lib.openapi.openapi_manager import OpenAPIManager
from utils.py.lib.postman.postman_manager import PostmanManager

from utils.py.lib.generation.cleanup_utils import GeneratedFilesCleaner
from utils.py.lib.async_support import run_async
from utils.py.lib.openapi.openapi_spec_generator import OpenApiSpecGenerator


class KDFTools:
    """Unified KDF Tools CLI."""
    CLEANUP_CATEGORIES = ["openapi", "postman", "rust", "all"]
    
    def __init__(self):
        self.verbose = True
        self.quiet = False
        self.config = get_config()
        self.logger = get_logger("kdf-tools")
        self.openapi_spec_generator = OpenApiSpecGenerator()
        self.cleaner = GeneratedFilesCleaner(
            config=self.config,
            verbose=self.verbose
        )
        if self.verbose:
            self.logger.folder(f"Workspace root: {self.config.workspace_root}")
            self.logger.folder(f"Data directory: {self.config.directories.data_dir}")
            self.logger.folder(f"Reports directory: {self.config.directories.reports_dir}")

    
    def log(self, message, level="info"):
        """Log a message with appropriate level."""
        if self.quiet:
            return
        
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
        
    def openapi_command(self, args):
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        command_title = "MDX to OpenAPI Conversion"
        config = [
            f"Version: {args.version}",
            f"Clean before: {args.clean_before}",
            f"Keep: {args.keep}"
        ]
        self._print_header(command_title, config)
        
        success = False
        report_paths = []
        try:
            # Auto-cleanup generated files if requested
            if args.clean_before:
                self.logger.clean("Cleaning up old OpenAPI files before generation...")
                if not self._cleanup_before_generation(['openapi', 'reports'], args.dry_run, args.keep):
                    self.log("Cleanup failed, continuing anyway...", "warning")
            
            # Initialize OpenAPI manager with enhanced enum/schema support
            manager = OpenAPIManager(
                config=self.config,
                verbose=self.verbose
            )
            
            # Handle "all" version by processing both v1 and v2
            if args.version == "all":
                self.log("🔄 Processing all versions (v1 and v2) in a single run...")
                
                # Process v1 first
                self.log("📂 Processing v1 (legacy methods)...")
                # Store pre-v1 counts
                v1_pre_count = manager.success_count
                result_v1 = manager.generate_openapi_specs(version="v1")
                # Calculate v1 count
                v1_post_count = manager.success_count
                v1_count = v1_post_count - v1_pre_count
                self.log(f"✅ V1: Processed {v1_count} methods.")
                
                # Process v2 
                self.log("📂 Processing v2 (current methods)...")
                # Store pre-v2 counts
                v2_pre_count = manager.success_count
                result_v2 = manager.generate_openapi_specs(version="v2")
                # Calculate v2 count
                v2_post_count = manager.success_count
                v2_count = v2_post_count - v2_pre_count
                self.log(f"✅ V2: Processed {v2_count} methods.")

                total_count = manager.success_count
                result = f"✅ All versions processed successfully!\n   📊 V1 methods: {v1_count}\n   📊 V2 methods: {v2_count}\n   📊 Total methods: {total_count}"
            else:
                # Generate OpenAPI specs for single version
                result = manager.generate_openapi_specs(version=args.version)
            
            self.log(f"✅ {result}")
            
            # NEW: Call tracking file generation when 'all' versions are processed
            if args.version == "all":
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
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.log(f"📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['files_processed']}")
            self.log(f"   • Enums found: {stats['enums_found']}")
            self.log(f"   • Structures found: {stats['structures_found']}")
            
            self.log("🔚 Finished MDX to OpenAPI conversion.")

            # Generate tracking files
            processed_versions = [args.version] if args.version != "all" else ["v1", "v2"]
            openapi_report_path = self._generate_openapi_tracking_files(manager, processed_versions)
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
        config = [
            f"Branch: {args.branch}",
            f"Versions: {args.versions}",
            f"Clean before: {args.clean_before}",
            f"Keep: {args.keep}"
        ]
        self._print_header(command_title, config)

        output_paths = []
        success = False

        async def main():
            nonlocal output_paths, success
            if args.clean_before:
                self.logger.clean("Cleaning up old Rust scan files before generation...")
                if not self._cleanup_before_generation(['rust'], args.dry_run, args.keep):
                    self.log("Cleanup failed, continuing anyway...", "warning")

            scanner = KDFScanner(
                config=self.config,
                branch=args.branch,
                verbose=self.verbose
            )
            
            versions_to_scan = args.versions
            if "all" in versions_to_scan:
                versions_to_scan = ["v1", "v2"]

            self.logger.info(f"Initialized KDFScanner in REMOTE mode.")
            self.logger.info(f"Remote repository branch: {scanner.branch}")
            
            repo_info = await scanner.scan_repository_methods_async(versions=versions_to_scan)
            
            # Save results to file
            output_file = await scanner.save_repository_methods_async(repo_info)
            output_paths.append(output_file)
            
            self.logger.save(f"Saved repository methods to: {output_file}")
            
            # Additional logic for processing/reporting on repo_info
            total_methods = sum(len(v.methods) for v in repo_info.values())
            self.logger.finish(f"Async scan completed: {total_methods} methods across {len(repo_info)} versions")
            success = True

        try:
            asyncio.run(main())
        except Exception as e:
            self.log(f"❌ An error occurred during Rust repository scan: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
    
    def scan_mdx_command(self, args):
        """Handle MDX-only scanning - extract method names from MDX documentation files."""
        command_title = "MDX Documentation Scan"
        versions = args.versions
        if 'all' in versions:
            versions = ['v1', 'v2']

        config_lines = [
            f"Versions: {versions}",
            f"Clean before: {args.clean_before}",
            f"Keep: {args.keep}"
        ]
        self._print_header(command_title, config_lines)
        
        success = False
        try:
            if args.clean_before:
                self.logger.clean("Cleaning up old MDX scan files before generation...")
                if not self._cleanup_before_generation(['mdx'], args.dry_run, args.keep):
                    self.log("Cleanup failed, continuing anyway...", "warning")

            # Use default data directory from config
            data_dir = self._get_data_dir()
            
            # Get current git branch of the repository
            try:
                result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                      capture_output=True, text=True, cwd=self.config.workspace_root, check=True)
                current_branch = result.stdout.strip()
                if self.verbose:
                    print(f"📋 Detected git branch: {current_branch}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                current_branch = "unknown"
                if self.verbose:
                    print("⚠️  Could not detect git branch, using 'unknown'")
            
            if self.verbose:
                print("💡 Using async processing for MDX file scanning")
                print("🗺️  Generating method-to-path mapping first, then deriving methods file")
                print(f"📋 Versions: {', '.join(versions)}")
                print(f"📁 Data directory: {data_dir}")
                print(f"📁 Reports directory: {self.config.directories.reports_dir}")
                print(f"📁 Workspace root: {self.config.workspace_root}")
                print()
            
            # Use async scanning for better performance
            
            # Initialize documentation scanner
            doc_scanner = UnifiedScanner(verbose=self.verbose)
            
            if self.verbose:
                self.logger.info("🔍 Scanning MDX documentation files asynchronously")
            
            # Scan documentation files
            doc_results = run_async(doc_scanner.scan_all_files_async(versions))
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # STEP 1: Generate method paths file (primary data source)
            method_paths_data = self._generate_mdx_method_paths_data(
                doc_results, versions, current_branch
            )
            
            # Save method paths file first
            paths_filename = f"report-kdf_mdx_method_paths.json"
            paths_output_path = Path(self.config.directories.reports_dir / paths_filename)
            safe_write_json(paths_output_path, method_paths_data, indent=2)
            
            if self.verbose:
                self.logger.success(f"💾 Saved method paths mapping to: {paths_output_path}")
            
            # STEP 2: Derive methods file from the paths file (eliminates duplication)
            methods_data = self._generate_mdx_methods_from_paths_file(
                paths_output_path, current_branch, versions
            )
            
            # Save methods file
            methods_filename = f"report-kdf_mdx_methods.json"
            methods_output_path = Path(self.config.directories.reports_dir / methods_filename)
            safe_write_json(methods_output_path, methods_data, indent=2)
            
            if self.verbose:
                self.logger.success(f"💾 Saved documentation methods to: {methods_output_path}")
                
                # Display summary from the paths data
                total_documented_methods = method_paths_data["scan_metadata"]["total_documented_methods"]
                
                print()
                print("📊 Summary:")
                for version in versions:
                    if version in method_paths_data["method_paths"]:
                        documented = len(method_paths_data["method_paths"][version])
                        print(f"✅ {version.upper()}: {documented} methods with paths")
                
                print(f"\n📄 Total documented: {total_documented_methods} methods across {len(versions)} versions")
            
            success = True
            
        except Exception as e:
            self.log(f"MDX documentation scan failed: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
        
        self._print_footer(command_title, success=success)
        return 0 if success else 1
    
    def _generate_mdx_method_paths_data(self, doc_results, versions, current_branch):
        """Generate the method paths data structure (primary data source)."""
        method_paths_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDFMethodPathMapper v1.5.0",
                "scanner_type": "MDX_METHOD_PATH_MAPPING",
                "total_versions": len(versions),
                "total_documented_methods": 0,
                "versions_processed": versions,
                "includes_gap_analysis": False,
                "generated_during_mdx_scan": True,
                "is_primary_data_source": True
            },
            "method_paths": {}
        }
        
        total_documented_methods = 0
        
        for version in versions:
            if version not in doc_results:
                if self.verbose:
                    print(f"⚠️  No documentation found for version {version}")
                continue
            
            # Extract method paths ONLY from MDX files (these are the documented methods)
            method_paths = {}
            version_data = doc_results[version]
            
            # Get methods from MDX files (with paths) - these are the only ones that count as "documented"
            if 'mdx_files' in version_data:
                for method_name, file_path in version_data['mdx_files'].items():
                    method_paths[method_name] = str(file_path)
            
            # Store method paths (only MDX files with actual paths)
            method_paths_data["method_paths"][version] = dict(sorted(method_paths.items()))
            total_documented_methods += len(method_paths)
            
            if self.verbose:
                print(f"🔍 Processing {version.upper()} documentation...")
                print(f"   📁 MDX files with paths: {len(method_paths)}")
        
        # Update total documented methods count
        method_paths_data["scan_metadata"]["total_documented_methods"] = total_documented_methods
        
        return method_paths_data
    
    def _generate_mdx_methods_from_paths_file(self, paths_file_path, current_branch, versions):
        """Generate the methods file by deriving method lists from the paths file."""
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
                
                if self.verbose:
                    print(f"✅ {version.upper()}: {len(method_list)} methods with MDX documentation")
            else:
                methods_by_version[version] = []
        
        # Create the methods data structure
        methods_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDFDocumentationScanner v2.3.0",
                "scanner_type": "MDX_DOCUMENTATION",
                "total_versions": len(versions),
                "total_methods": total_methods,
                "includes_path_mapping": False,
                "method_source": "derived_from_paths_file_mdx_only",
                "paths_file_reference": paths_file_path.name,
                "includes_only_documented_methods": True
            },
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
        
        if self.verbose:
            print(f"📖 Derived method lists from paths file: {paths_file_path.name}")
            print(f"📋 Only included methods with actual MDX documentation files")
        
        return methods_data
    
    def methods_map_command(self, args):
        """Handle map subcommand - Method mapping and OpenAPI management."""
        self.log("Starting method mapping and OpenAPI management...")
        
        try:
            mapper = MethodMappingManager(verbose=self.verbose)
            
            # Enable debug mode if requested
            if hasattr(args, 'debug_matching') and args.debug_matching:
                mapper.normalizer.enable_debug_mode(True)
                self.log("🔍 Debug mode enabled for method matching", "info")
            
            if args.remove:
                # Use async version for file removal if available
                if hasattr(mapper, 'remove_method_files_async'):
                    run_async(mapper.remove_method_files_async(args.remove, dry_run=args.dry_run))
                else:
                    mapper.remove_method_files(args.remove, dry_run=args.dry_run)
                return 0
            
            if args.debug:
                # Use async version for debugging if available 
                if hasattr(mapper, 'debug_method_matching_async'):
                    run_async(mapper.debug_method_matching_async(args.debug))
                else:
                    mapper.debug_method_matching(args.debug)
                return 0
            
            if not self.quiet:
                print("\n📋 Generating unified method mapping...")
                
                # Check if async processing is available and recommended
                if hasattr(mapper, 'create_unified_mapping_async'):
                    print("💡 Async processing is available for faster performance!")
                    print("   The mapping will now use concurrent file processing.")
            
            # Use async version for mapping generation
            if hasattr(mapper, 'save_unified_mapping_async'):
                if self.verbose:
                    print("💡 Using async processing for method mapping...")
                run_async(mapper.save_unified_mapping_async())
            else:
                mapper.save_unified_mapping()
            
            # Generate Postman methods tracking file from the latest method paths data
            self._generate_postman_tracking_file_from_latest_data(['v1', 'v2'])
            
            # Auto-cleanup old mapping files - REMOVED: Will be handled by Step 6 comprehensive cleanup
            # from lib.utils import cleanup_kdf_temp_files
            # cleanup_kdf_temp_files('data', keep_count=3, verbose=self.verbose)
            
            self.log("Method mapping completed successfully!", "success")
            return 0
        except Exception as e:
            self.log(f"Method mapping failed: {e}", "error")
            return 1
    
    def postman_command(self, args):
        """Handle postman subcommand - Generate Postman collections."""
        command_title = "Postman Collection Generation"
        versions = args.versions
        if "all" in versions:
            versions = ["v1", "v2"]
        
        config_lines = [
            f"Versions: {versions}",
            f"Clean before: {args.clean_before}",
            f"Keep: {args.keep}"
        ]
        self._print_header(command_title, config_lines)
        
        success = False
        try:
            # Auto-cleanup generated files if requested
            if args.clean_before:
                self.logger.clean("Cleaning up old Postman collections before generation...")
                if not self._cleanup_before_generation(['postman'], args.dry_run, args.keep):
                    self.log("Cleanup failed, continuing anyway...", "warning")
            
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
            
            self.logger.success("✅ Postman collection generation completed!")
            if not self.quiet:
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
                print("💡 Using async processing for method mapping...")
            
            unified_mapping = run_async(mapper.create_unified_mapping_async())

            # Handle "all" version by converting to actual supported versions
            versions = args.versions
            if 'all' in versions:
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
                        if self.verbose:
                            print(f"  ⏭️  Skipping {method_name}: No MDX file found")
                        continue
                    
                    # Extract examples from MDX
                    examples = extractor.extract_from_mdx_file(method_name, mapping, version)
                    
                    if not examples:
                        if self.verbose:
                            print(f"  ⚪ {method_name}: No JSON examples found")
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
                    
                    if self.verbose:
                        print(f"  🔍 {method_name}: Found {len(cleaned_examples)} examples")
                    
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
                            folder_name = example.method_name.replace("::", "_")
                            
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
                                self.logger.save(f"🔍 {method_name}: Saved example {i} to {self.config.directories.get_relative_path(str(output_path))}")
                    
                    version_examples += len(cleaned_examples)
                    version_methods_with_examples += 1
                
                self.log(f"✅ {version.upper()}: {version_count} examples extracted from {version_methods_with_examples} methods")
                
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
    
    def cleanup_command(self, args):
        """Handle cleanup subcommand - removes old generated files."""
        command_title = "Cleanup Old Files"
        config_lines = [
            f"Categories: {args.categories}",
            f"Keep: {args.keep}",
            f"Dry run: {args.dry_run}"
        ]
        self._print_header(command_title, config_lines)
        
        success = False
        try:
            categories_to_clean = args.categories
            if "all" in categories_to_clean:
                categories_to_clean = [c for c in self.CLEANUP_CATEGORIES if c != 'all']
            
            self._cleanup_before_generation(
                categories=categories_to_clean,
                dry_run=args.dry_run,
                keep_count=args.keep
            )
            success = True
        except Exception as e:
            self.log(f"An error occurred during cleanup: {e}", "error")

        self._print_footer(command_title, success=success)
        return 0 if success else 1


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
                        print(f"  {gen.name} <-> {live.relative_to(analyzer.live_docs_dir)}")
                    if len(pairs) > 10:
                        print(f"  ... and {len(pairs) - 10} more")
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
            
            print("\n" + "="*60)
            print("DRAFT QUALITY ANALYSIS SUMMARY")
            print("="*60)
            print(summary)
            print("="*60)
            
            if args.output:
                self.log(f"Full report saved to: {args.output}", "success")
            else:
                import glob
                latest_report_files = glob.glob(str(self.config.directories.reports_dir / "draft_quality_report_*.md"))
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
        
        self._generate_json_method_paths_file(all_extracted_methods)
        self._generate_json_methods_file(all_extracted_methods, extraction_stats)
    
    def _generate_openapi_tracking_files(self, openapi_manager: OpenAPIManager, versions: List[str]) -> str:
        """Generates all necessary tracking files for OpenAPI."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return self.openapi_spec_generator._generate_openapi_method_paths_file(
            timestamp=timestamp,
            all_methods=openapi_manager.all_methods,
            versions=versions,
            path_mapper=openapi_manager.path_mapper
        )  

    def _generate_json_method_paths_file(self, all_extracted_methods: Dict[str, Any]) -> None:
        """Creates a JSON file mapping each method to its JSON examples path."""
        self.logger.info("Generating JSON method paths file...")
        v1_methods = [data["method_name"] for data in all_extracted_methods.values() if data["version"] == "v1"]
        v2_methods = [data["method_name"] for data in all_extracted_methods.values() if data["version"] == "v2"]
        paths_data = {
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
            "method_paths": {
                "v1": v1_methods,
                "v2": v2_methods
            }
        }

        file_path = self.config.directories.reports_dir / "report-kdf_postman_json_method_paths.json"
        safe_write_json(file_path, paths_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.log(f"✅ 💾 Saved Postman method paths mapping to: {log_path}")
        self.log(f"📊 V1: {len(paths_data['method_paths']['v1'])} methods")
        self.log(f"📊 V2: {len(paths_data['method_paths']['v2'])} methods")

    def _generate_json_methods_file(self, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generates a JSON file that maps each method to its extracted JSON examples."""
        self.log("Generating JSON methods file...")
        v1_methods_data = [data for data in all_extracted_methods.values() if data["version"] == "v1"]
        v2_methods_data = [data for data in all_extracted_methods.values() if data["version"] == "v2"]
        v1_methods = [data["method_name"] for data in v1_methods_data]
        v2_methods = [data["method_name"] for data in v2_methods_data]
        methods_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDF-JSON-Extractor v1.0.0",
                "scanner_type": "JSON_EXTRACTOR",
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
        file_path = self.config.directories.reports_dir / "report-kdf_postman_json_methods.json"
        safe_write_json(file_path, methods_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.log(f"✅ 💾 Saved JSON extraction examples summary to: {log_path}")
        self.log(f"📊 V1: {extraction_stats['v1']['total_examples_found']} examples from {extraction_stats['v1']['methods_with_examples']} methods")
        self.log(f"📊 V2: {extraction_stats['v2']['total_examples_found']} examples from {extraction_stats['v2']['methods_with_examples']} methods")

    def _cleanup_before_generation(self, categories: List[str], dry_run: bool = False, keep_count: int = 0) -> bool:
        """
        Cleanup old generated files based on category.

        NEW: Added 'rust' category for scan-rust cleanup.
        """
        self.logger.clean(f"Starting cleanup for categories: {categories} (keeping {keep_count} recent files)...")
        
        base_dirs = {
            "openapi": self.config.directories.openapi_main.parent,
            "postman": self.config.directories.postman_collections,
            "reports": self.config.directories.reports_dir,
            "rust": self.config.directories.reports_dir,
            "mdx": self.config.directories.reports_dir
        }
        
        file_patterns = {
            "openapi": "report-mdx_kdf_*_*.json",
            "reports": "report-*.json",
            "rust": "report-kdf_rust_method*.json",
            "postman": "report-kdf_postman_method*.json",
            "mdx": "report-kdf_mdx_method*.json"
        }
        
        all_cleaned = True
        
        for category in categories:
            if category not in base_dirs:
                self.log(f"Unknown cleanup category: {category}", "warning")
                continue

            dir_path = base_dirs[category]
            pattern = file_patterns[category]
            
            if not dir_path.exists():
                self.logger.clean(f"Directory not found for category '{category}': {dir_path}")
                continue

            self.logger.clean(f"Scanning for '{pattern}' in '{dir_path}'...")
            
            try:
                # Find all matching files and sort them by modification time
                files = sorted(
                    [p for p in dir_path.glob(pattern) if p.is_file()],
                    key=os.path.getmtime,
                    reverse=True
                )
                
                if not files:
                    self.logger.clean(f"No files to clean for category '{category}'.")
                    continue
                
                files_to_delete = files[keep_count:]
                
                if not files_to_delete:
                    self.log(f"No old files to delete for category '{category}'.")
                    continue

                self.log(f"Found {len(files_to_delete)} file(s) to delete for category '{category}':")
                for f in files_to_delete:
                    relative_path = self.config.directories.get_relative_path(f)
                    self.log(f"  - Deleting {relative_path}")
                    if not dry_run:
                        try:
                            f.unlink()
                            self.logger.info(f"🗑️ File delete completed: {relative_path}")
                        except Exception as e:
                            self.log(f"    -> Failed to delete: {e}", "error")
                            all_cleaned = False
            except Exception as e:
                self.log(f"Error while cleaning category '{category}': {e}", "error")
                all_cleaned = False
        
        if dry_run:
            self.log("Dry run complete. No files were deleted.", "info")
        
        return all_cleaned

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
        parser.add_argument(
            '--clean-before', action='store_true',
            help='Clean up old Postman files before running.'
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep during cleanup.'
        )
        parser.set_defaults(func=self.postman_command)

    def setup_openapi_parser(self, subparsers):
        """Setup parser for the openapi command."""
        parser = subparsers.add_parser(
            'openapi',
            help='Generate OpenAPI specs from MDX documentation.',
            description='Processes MDX documentation files to create OpenAPI specifications.'
        )
        parser.add_argument(
            '--version', type=str, default='v2',
            help='Specify the API version to process.'
        )
        parser.add_argument(
            '--clean-before', action='store_true',
            help='Clean up old OpenAPI files before running.'
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep during cleanup.'
        )
        parser.set_defaults(func=self.openapi_command)

    def setup_scan_mdx_parser(self, subparsers):
        """Setup parser for the scan-mdx command."""
        parser = subparsers.add_parser(
            'scan-mdx',
            help='Scan MDX files for method names.',
            description='Scans local MDX documentation to extract API method names and paths.'
        )
        parser.add_argument(
            '--versions', nargs='+', default=['all'],
            help="List of versions to process (e.g., v1 v2 all). Default: ['all']"
        )
        parser.add_argument(
            '--clean-before', action='store_true',
            help='Clean up old scan files before running.'
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep during cleanup.'
        )
        parser.set_defaults(func=self.scan_mdx_command)

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
        parser.add_argument(
            '--versions', nargs='+', default=['all'],
            help="List of versions to process (e.g., v1 v2 all). Default: ['all']"
        )
        parser.add_argument(
            '--clean-before', action='store_true',
            help='Clean up old JSON example files before running.'
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep during cleanup.'
        )
        parser.set_defaults(func=self.json_extract_command)

    def setup_cleanup_parser(self, subparsers):
        """Setup parser for the cleanup command."""
        parser = subparsers.add_parser(
            'cleanup',
            help='Clean up old temporary files.',
            description='Removes old generated files from various tool operations.'
        )
        parser.add_argument(
            '--categories', nargs='+', choices=self.CLEANUP_CATEGORIES, default=['all'],
            help=f"Categories to clean. Choices: {self.CLEANUP_CATEGORIES}"
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep for each category.'
        )
        parser.set_defaults(func=self.cleanup_command)

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
        """Setup parser for the generate-docs command."""
        parser = subparsers.add_parser(
            'generate-docs',
            help='Generate documentation for missing KDF methods.',
            description='Generates documentation for missing KDF methods.'
        )
        parser.add_argument(
            '--branch', type=str,
            help='Branch of the repository to generate documentation for.'
        )
        parser.add_argument(
            '--repo-path', type=Path,
            help='Path to the repository containing the KDF code.'
        )
        parser.add_argument(
            '--method', type=str,
            help='Specific method to generate documentation for.'
        )
        parser.add_argument(
            '--version', type=str,
            help='Version of the API to generate documentation for.'
        )
        parser.add_argument(
            '--methods-file', type=Path,
            help='Path to a file containing methods to generate documentation for.'
        )
        parser.add_argument(
            '--interactive', action='store_true',
            help='Interactively select methods to generate documentation for.'
        )
        parser.add_argument(
            '--output-dir', type=Path,
            help='Directory to save generated documentation files.'
        )
        parser.add_argument(
            '--generate-summary', action='store_true',
            help='Generate a summary report of the documentation generation process.'
        )
        parser.set_defaults(func=self.generate_docs_command)

    def setup_gap_analysis_parser(self, subparsers):
        """Setup parser for the gap-analysis command."""
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

    def _generate_postman_tracking_file_from_latest_data(self, versions: List[str]) -> None:
        """Placeholder for generating Postman tracking file."""
        pass

    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for the scan-rust command."""
        parser = subparsers.add_parser(
            'scan-rust', 
            help='Scan KDF Rust repository for RPC methods.',
            description='Scans the Komodo DeFi Framework Rust repository to find RPC methods.'
        )
        parser.add_argument(
            '--branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan.'
        )
        parser.add_argument(
            '--versions', nargs='+', default=['v2', 'v1'],
            help="List of versions to scan (e.g., v1 v2). Default: ['v2', 'v1']"
        )
        parser.add_argument(
            '--clean-before', action='store_true',
            help='Clean up old scan files before running.'
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Number of recent files to keep during cleanup.'
        )
        parser.set_defaults(func=self.scan_rust)

    def gap_analysis_command(self, args):
        """Handle gap-analysis subcommand."""
        command_title = "Documentation Gap Analysis"
        config = [
            f"Versions: {args.versions}"
        ]
        self._print_header(command_title, config)
        success = False
        try:
            # Load latest Rust scan data
            rust_data = {}
            rust_scan_files = glob.glob(os.path.join(str(self.config.directories.reports_dir), "report-kdf_rust_methods_*.json"))
            if rust_scan_files:
                latest_rust_scan = max(rust_scan_files, key=os.path.getctime)
                self.log(f"Found latest Rust methods file: {os.path.basename(latest_rust_scan)}")
                with open(latest_rust_scan, 'r') as f:
                    rust_methods_data = json.load(f).get("repository_data", {})
                    for v in args.versions:
                        if v in rust_methods_data:
                            rust_data[v] = rust_methods_data[v].get("methods", [])
            else:
                self.log(f"⚠️  No 'report-kdf_rust_methods_*.json' file found.", "warning")
                self.log(f"   Run 'python py/kdf_tools.py scan-rust' first", "warning")
                return

            # Load latest MDX methods data
            mdx_methods = {}
            mdx_scan_files = glob.glob(os.path.join(str(self.config.directories.reports_dir), "report-kdf_mdx_methods_*.json"))
            if mdx_scan_files:
                latest_mdx_scan = max(mdx_scan_files, key=os.path.getctime)
                self.log(f"Found latest MDX methods file: {os.path.basename(latest_mdx_scan)}")
                with open(latest_mdx_scan, 'r') as f:
                    mdx_methods_data = json.load(f).get("repository_data", {})
                    for v in args.versions:
                        if v in mdx_methods_data:
                            mdx_methods[v] = mdx_methods_data[v].get("methods", [])
            else:
                self.log(f"⚠️  No 'report-kdf_mdx_methods_*.json' file found.", "warning")
                self.log(f"   Run 'python py/kdf_tools.py scan-mdx' first", "warning")
                return

            # Perform Gap Analysis
            self.log("📊 Performing Gap Analysis...")
            gap_analysis_data = {
                "rust_methods_without_mdx": {v: [] for v in args.versions},
                "mdx_methods_without_rust": {v: [] for v in args.versions},
                "statistics": {}
            }

            for v in args.versions:
                if v not in rust_data or v not in mdx_methods:
                    continue
                self.log(f"🔍 Processing {v.upper()}...")
                rust_method_set = set(rust_data.get(v, []))
                doc_method_set = set(mdx_methods.get(v, []))

                missing_in_docs = sorted(list(rust_method_set - doc_method_set))
                extra_in_docs = sorted(list(doc_method_set - rust_method_set))

                gap_analysis_data["rust_methods_without_mdx"][v] = missing_in_docs
                gap_analysis_data["mdx_methods_without_rust"][v] = extra_in_docs
                
                total_rust_methods = len(rust_method_set)
                total_doc_methods = len(doc_method_set)
                
                coverage = (total_doc_methods / total_rust_methods * 100) if total_rust_methods > 0 else 0

                gap_analysis_data["statistics"][v] = {
                    "total_rust_methods": total_rust_methods,
                    "documented_methods": total_doc_methods,
                    "undocumented_methods": len(missing_in_docs),
                    "extra_methods_in_docs": len(extra_in_docs),
                    "documentation_coverage_percent": f"{coverage:.2f}%"
                }

                self.log(f"   - Total methods in Rust: {total_rust_methods}")
                self.log(f"   - Total methods in MDX: {total_doc_methods}")
                self.log(f"   - Coverage: {coverage:.2f}%")
                if missing_in_docs:
                    self.log(f"   - 🚨 Undocumented methods: {len(missing_in_docs)}")
                if extra_in_docs:
                    self.log(f"   - ⚠️  Extra methods in docs: {len(extra_in_docs)}")

            # Save report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.config.directories.reports_dir / "report-kdf_gap_analysis.json"
            safe_write_json(report_path, gap_analysis_data, indent=2)
            self.log(f"✅ 💾 Gap analysis report saved to: {report_path}")

            success = True

        except Exception as e:
            self.logger.error(f"Error during gap analysis: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self._print_footer(command_title, success=success)

    def main(self):
        """Main entry point for CLI."""
        parser = argparse.ArgumentParser(
            description='Komodo DeFi Framework Tools - Unified CLI',
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes.')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
        parser.add_argument('-q', '--quiet', action='store_true', help='Suppress all output except errors.')

        subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

        # Setup parsers for all commands
        self.setup_openapi_parser(subparsers)
        self.setup_postman_parser(subparsers)
        self.setup_scan_rust_parser(subparsers)
        self.setup_scan_mdx_parser(subparsers)
        self.setup_gap_analysis_parser(subparsers)
        self.setup_map_methods_parser(subparsers)
        self.setup_json_extract_parser(subparsers)
        self.setup_cleanup_parser(subparsers)
        self.setup_review_draft_quality_parser(subparsers)
        self.setup_scan_existing_docs_parser(subparsers)
        self.setup_generate_docs_parser(subparsers)
        
        args = parser.parse_args()

        # Setup logging and config
        self.quiet = args.quiet
        is_verbose = args.verbose or not args.quiet
        
        # Add dry_run to args if not present (for commands that dont have it)
        if not hasattr(args, 'dry_run'):
            args.dry_run = False
        if not hasattr(args, 'keep'):
            args.keep = 3

        # Execute command
        if hasattr(args, 'func'):
            return args.func(args)
        else:
            self.log("No function associated with command.", "error")
            return 1

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
