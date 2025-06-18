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
- map: Method mapping and OpenAPI management
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


from utils.py.lib.postman.postman_scanner import MDXExtractor, ExtractedExample
from utils.py.lib.managers import MethodMappingManager
from utils.py.lib.utils import safe_write_json, ensure_directory_exists
from utils.py.lib import (
    UnifiedScanner,
    get_logger, setup_logging, DraftsManager,
    MdxGenerator, ExistingDocsScanner
)
from utils.py.lib.constants.config import get_config
from utils.py.lib.constants.enums import DeploymentEnvironment
from utils.py.lib.rust.scanner import KDFScanner
from utils.py.lib.openapi.openapi_manager import OpenAPIManager
from utils.py.lib.postman.postman_manager import PostmanManager

from utils.py.lib.generation.cleanup_utils import GeneratedFilesCleaner
from utils.py.lib.async_support import run_async


class KDFTools:
    """Unified KDF Tools CLI."""
    
    def __init__(self):
        self.verbose = True
        self.quiet = False
        self.logger = None
        self.config = None
    
    def setup_logging(self, verbose=True):
        """Setup logging configuration."""
        setup_logging(verbose=verbose)
        self.logger = get_logger("kdf-tools")
        self.verbose = verbose
    
    def setup_config(self):
        """Setup configuration with proper workspace root."""

        # Auto-detect workspace root from current script location
        script_dir = Path(__file__).parent.absolute()
        # Go up from utils/py/ to workspace root
        workspace_root = script_dir.parent.parent
        
        # Verify this is correct by checking for characteristic files
        if not (workspace_root / "src" / "pages").exists():
            # If not found, try searching upward from current working directory
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                if (parent / "src" / "pages").exists() and (parent / "utils" / "py").exists():
                    workspace_root = parent
                    break
            else:
                # Still not found, use the script-based detection as fallback
                if self.verbose:
                    self.log("⚠️ Could not find workspace root with src/pages directory, using script location", "warning")
        
        self.config = get_config(
            base_path=str(workspace_root),
            environment=DeploymentEnvironment.DEVELOPMENT
        )
        
        if self.verbose:
            self.log(f"📁 Workspace root: {workspace_root}")
            self.log(f"📁 Data directory: {self._get_data_dir()}")
    
    def _get_data_dir(self) -> str:
        """Get absolute path to data directory using config constants."""
        if self.config:
            # Use config to resolve data directory path
            return self._resolve_data_directory_path(self.config.directories.data_dir)
        else:
            # Fallback to relative path
            return os.path.join(os.path.dirname(__file__), self.config.directories.data_dir if self.config else "data")
    
    def _resolve_data_directory_path(self, data_dir: str) -> str:
        """
        Resolve data directory path using config constants.
        
        Args:
            data_dir: The data directory name or path
            
        Returns:
            Absolute path to the data directory
        """
        if os.path.isabs(data_dir):
            return data_dir
        
        # Use config's _resolve_path method directly
        return self.config._resolve_path(data_dir)
    
    def log(self, message, level="info"):
        """Log a message with appropriate level."""
        if self.quiet:
            return
        
        # Map simple levels to logger methods
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)
    
    def openapi_command(self, args):
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        self.log("Starting MDX to OpenAPI conversion with enum/schema extraction...")
        
        try:
            # Auto-cleanup generated files if requested
            if args.clean_before:
                self.log("🧹 Cleaning up old OpenAPI files before generation...")
                if not self._cleanup_before_generation(['openapi'], args.dry_run, args.keep):
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
                result_v1 = manager.generate_openapi_spec(version="v1")
                self.log(f"✅ V1: {result_v1}")
                
                # Store v1 methods for combined tracking
                v1_methods = dict(manager.all_methods)
                
                # Process v2 
                self.log("📂 Processing v2 (current methods)...")
                result_v2 = manager.generate_openapi_spec(version="v2")
                self.log(f"✅ V2: {result_v2}")
                
                # Combine methods from both versions for comprehensive tracking
                combined_methods = {**v1_methods, **manager.all_methods}
                manager.all_methods = combined_methods
                
                result = f"✅ All versions processed successfully!\n   📊 V1 methods: {len(v1_methods)}\n   📊 V2 methods: {len(manager.all_methods) - len(v1_methods)}\n   📊 Total methods: {len(combined_methods)}"
            else:
                # Generate OpenAPI specs for single version
                result = manager.generate_openapi_spec(version=args.version)
            
            self.log(f"✅ {result}")
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.log(f"📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['files_processed']}")
            self.log(f"   • Enums found: {stats['enums_found']}")
            self.log(f"   • Structures found: {stats['structures_found']}")
            
            # Additional logic for displaying enum patterns can be added here
            
            return 0
            
        except Exception as e:
            self.log(f"❌ OpenAPI conversion failed: {e}", "error")
            self.log(f"❌ {traceback.format_exc()}", "error")
        finally:
            self.log("🔚 Finished MDX to OpenAPI conversion.", "success" if 'result' in locals() and 'Successfully' in result else "info")
    
    def scan_rust(self, args):
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        try:
            data_dir = self._get_data_dir()
            local_repo_path = Path(data_dir) / "kdf_repo"

            scanner = None
            if local_repo_path.exists() and not args.force_remote:
                self.log(f"Local KDF repository found at: {local_repo_path}", "info")
                scanner = KDFScanner(
                    repo_path=local_repo_path,
                    branch=args.branch,
                    verbose=self.verbose
                )
            else:
                if not local_repo_path.exists():
                    self.log("Local KDF repository not found.", "warning")
                self.log("Falling back to remote GitHub scan.", "info")
                scanner = KDFScanner(
                    branch=args.branch,
                    data_dir=data_dir,
                    verbose=self.verbose
                )

            if self.verbose:
                print(f"📋 Branch: {args.branch}")
                print(f"📁 Data directory: {data_dir}")
                print("💡 Using async processing for better performance")
                print()
            
            # Use async scanning for better performance
            # Always do a fresh scan (caching removed for simplicity)
            repo_info = run_async(scanner.scan_repository_methods_async(args.versions))
            saved_path = run_async(scanner.save_repository_methods_async(repo_info, args.output))
            
            # Display summary
            if self.verbose:
                total_methods = 0
                # The 'repo_info' variable already contains the scanned data.
                # No need to reload from the file.
                for version in args.versions:
                    count = 0
                    if version in repo_info and hasattr(repo_info[version], 'methods'):
                        count = len(repo_info[version].methods)
                    total_methods += count
                    print(f"✅ {version.upper()}: {count} methods")
                
                print(f"\n📊 Total: {total_methods} methods across {len(args.versions)} versions")
                print(f"📁 Saved to: {saved_path}")
            
            return 0
        except Exception as e:
            self.log(f"Repository scan failed: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
    
    def scan_mdx_command(self, args):
        """Handle MDX-only scanning - extract method names from MDX documentation files."""
        try:
            # Handle "all" version by converting to actual supported versions
            versions = args.versions
            if 'all' in versions:
                versions = ['v1', 'v2']
            
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
                print()
            
            # Use async scanning for better performance
            
            # Initialize documentation scanner
            base_directories = {
                'mdx_v1': os.path.join(self.config.workspace_root, 'src/pages/komodo-defi-framework/api/legacy'),
                'mdx_v2': os.path.join(self.config.workspace_root, 'src/pages/komodo-defi-framework/api/v20'),
                'mdx_v2_dev': os.path.join(self.config.workspace_root, 'src/pages/komodo-defi-framework/api/v20-dev'),
                'yaml_v1': os.path.join(self.config.workspace_root, 'openapi/paths/v1'),
                'yaml_v2': os.path.join(self.config.workspace_root, 'openapi/paths/v2'),
                'json_v1': os.path.join(self.config.workspace_root, 'postman/json/kdf/v1'),
                'json_v2': os.path.join(self.config.workspace_root, 'postman/json/kdf/v2'),
            }
            doc_scanner = UnifiedScanner(base_directories=base_directories, verbose=self.verbose)
            
            if self.verbose:
                self.logger.info("🔍 Scanning MDX documentation files asynchronously")
            
            # Scan documentation files
            doc_results = run_async(doc_scanner.scan_all_files_async(versions))
            
            # Load Rust repository methods for comparison (if available)
            rust_data = None
            try:
                # Load the latest kdf_rust_methods file from Step 1A
                rust_files = glob.glob(str(Path(data_dir) / "kdf_rust_methods_*.json"))
                if rust_files:
                    # Get the most recent file
                    latest_rust_file = max(rust_files, key=lambda x: Path(x).stat().st_mtime)
                    if self.verbose:
                        print(f"📊 Loading Rust methods from: {Path(latest_rust_file).name}")
                    
                    with open(latest_rust_file, 'r', encoding='utf-8') as f:
                        rust_file_data = json.load(f)
                    
                    # Extract repository data in the expected format
                    if "repository_data" in rust_file_data:
                        rust_data = {}
                        for version in versions:
                            if version in rust_file_data["repository_data"]:
                                # Create a simple object with methods attribute
                                class RustVersionData:
                                    def __init__(self, methods):
                                        self.methods = methods
                                
                                methods = rust_file_data["repository_data"][version].get("methods", [])
                                rust_data[version] = RustVersionData(methods)
                                
                                if self.verbose:
                                    print(f"   📋 {version.upper()}: {len(methods)} Rust methods loaded")
                    
                    if self.verbose and rust_data:
                        print("📊 Loaded Rust repository methods for gap analysis")
                else:
                    if self.verbose:
                        print("⚠️  No kdf_rust_methods_*.json file found from Step 1A")
                        print("   Run 'python py/kdf_tools.py scan-rust --branch dev --versions v1 v2' first")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Could not load Rust repository methods: {e}")
                    print("   Run 'python py/kdf_tools.py scan-rust --branch dev --versions v1 v2' first")
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = Path(self._resolve_data_directory_path(self.config.directories.reports_dir))
            reports_dir.mkdir(exist_ok=True, parents=True)
            
            # STEP 1: Generate method paths file (primary data source)
            method_paths_data = self._generate_mdx_method_paths_data(
                doc_results, rust_data, versions, current_branch
            )
            
            # Save method paths file first
            paths_filename = f"kdf_mdx_method_paths_{timestamp}.json"
            paths_output_path = reports_dir / paths_filename
            safe_write_json(paths_output_path, method_paths_data, indent=2)
            
            if self.verbose:
                self.logger.success(f"💾 Saved method paths mapping to: {paths_output_path}")
            
            # STEP 2: Derive methods file from the paths file (eliminates duplication)
            methods_data = self._generate_mdx_methods_from_paths_file(
                paths_output_path, current_branch, versions
            )
            
            # Save methods file
            if args.output:
                methods_filename = args.output
            else:
                methods_filename = f"kdf_mdx_methods_{timestamp}.json"
            methods_output_path = reports_dir / methods_filename
            safe_write_json(methods_output_path, methods_data, indent=2)
            
            if self.verbose:
                self.logger.success(f"💾 Saved documentation methods to: {methods_output_path}")
                
                # Display summary from the paths data
                total_documented_methods = method_paths_data["scan_metadata"]["total_documented_methods"]
                total_methods = methods_data["scan_metadata"]["total_methods"]
                
                print()
                print("📊 Summary:")
                for version in versions:
                    if version in method_paths_data["method_paths"]:
                        documented = len(method_paths_data["method_paths"][version])
                        total = len(methods_data["repository_data"].get(version, {}).get("methods", []))
                        print(f"✅ {version.upper()}: {total} total methods, {documented} with paths")
                
                print(f"\n📄 Total: {total_methods} methods across {len(versions)} versions")
                print(f"📁 Documented: {total_documented_methods} methods with file paths")
                
                # Show gap analysis summary
                gap_analysis = method_paths_data.get("gap_analysis", {})
                total_rust_gaps = sum(len(gap_analysis.get("rust_methods_without_mdx", {}).get(v, [])) for v in versions)
                
                if total_rust_gaps > 0:
                    print(f"\n⚠️  Gap Analysis:")
                    print(f"   🔧 Rust methods without MDX: {total_rust_gaps} (documentation needed)")
                    print(f"   📋 See detailed analysis in: {paths_output_path}")
                else:
                    # Check if we had Rust data to compare against
                    total_rust_methods = sum(method_paths_data.get("gap_analysis", {}).get("statistics", {}).get(v, {}).get("total_rust_methods", 0) for v in versions)
                    if total_rust_methods > 0:
                        print(f"\n✅ Gap Analysis: All {total_rust_methods} Rust methods have MDX documentation!")
                    else:
                        print(f"\n📋 Gap Analysis: No Rust methods data available for comparison")
            
            return 0
            
        except Exception as e:
            self.log(f"MDX documentation scan failed: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
    
    def _generate_mdx_method_paths_data(self, doc_results, rust_data, versions, current_branch):
        """Generate the method paths data structure (primary data source)."""
        method_paths_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDFMethodPathMapper v1.4.0",
                "scanner_type": "METHOD_PATH_MAPPING",
                "total_versions": len(versions),
                "total_documented_methods": 0,
                "versions_processed": versions,
                "includes_gap_analysis": True,
                "generated_during_mdx_scan": True,
                "is_primary_data_source": True
            },
            "method_paths": {},
            "gap_analysis": {
                "rust_methods_without_mdx": {},
                "statistics": {}
            }
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
            
            # Get Rust methods for gap analysis (canonical methods from source code)
            rust_methods = set()
            if rust_data and version in rust_data:
                rust_methods = set(rust_data[version].methods)
            
            # Gap analysis: Compare Rust methods vs documented methods
            documented_methods = set(method_paths.keys())
            
            # rust_methods_without_mdx: Canonical Rust methods that don't have MDX documentation
            rust_methods_without_mdx = [
                method for method in rust_methods 
                if method not in documented_methods
            ]
            
            # Store method paths (only MDX files with actual paths)
            method_paths_data["method_paths"][version] = dict(sorted(method_paths.items()))
            total_documented_methods += len(method_paths)
            
            # Store gap analysis
            method_paths_data["gap_analysis"]["rust_methods_without_mdx"][version] = rust_methods_without_mdx
            
            # Calculate statistics
            documented_count = len(method_paths)
            rust_count = len(rust_methods)
            coverage_vs_rust = (documented_count / rust_count * 100) if rust_count > 0 else 0
            
            method_paths_data["gap_analysis"]["statistics"][version] = {
                "documented_methods": documented_count,
                "total_rust_methods": rust_count,
                "rust_methods_without_mdx": len(rust_methods_without_mdx),
                "coverage_vs_rust": coverage_vs_rust
            }
            
            if self.verbose:
                print(f"🔍 Processing {version.upper()} documentation...")
                print(f"   📁 MDX files with paths: {documented_count}")
                if rust_count > 0:
                    print(f"   📊 Rust coverage: {documented_count}/{rust_count} ({coverage_vs_rust:.1f}%)")
                    if rust_methods_without_mdx:
                        print(f"   📝 Rust methods without MDX: {len(rust_methods_without_mdx)}")
                else:
                    print(f"   ⚠️  No Rust methods data available for gap analysis")
        
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
        self.log("Starting Postman collection generation...")
        
        try:
            # Auto-cleanup generated files if requested
            if args.clean_before:
                self.log("🧹 Cleaning up old Postman collections before generation...")
                if not self._cleanup_before_generation(['postman_collections'], args.dry_run, args.keep):
                    self.log("Cleanup failed, continuing anyway...", "warning")
            
            # Handle "all" version by converting to actual supported versions
            versions = args.versions if args.versions != ["all"] else ["v1", "v2"]
            
            # Step 1: Generate method paths file first (like other commands)
            self.log("🗺️ Generating method mapping with Postman hotlinks...")
            mapper = MethodMappingManager(verbose=self.verbose)
            
            # Use async mapping for better performance and generate paths file
            run_async(mapper.save_unified_mapping_async())
            
            # Step 2: Generate Postman collections
            self.log("📮 Generating Postman collections...")
            # Initialize manager
            manager = PostmanManager(verbose=self.verbose)
            
            # Generate collections
            results = manager.generate_collections(versions)
            summary = manager.generate_summary_report(results)
            
            # Step 3: Generate tracking file - read from the method paths file we just created
            self._generate_postman_tracking_file_from_latest_data(versions)
            
            self.log("✅ Postman collection generation completed!")
            if not self.quiet:
                print(summary)
            
        except Exception as e:
            self.log(f"❌ Error in postman command: {e}", "error")
            if self.verbose:
                self.log(f"Full traceback: {traceback.format_exc()}", "error")
    
 
    def json_extract_command(self, args):
        """Handle json-extract subcommand - Extract JSON examples from MDX files."""
        self.log("Starting JSON example extraction from MDX files...")
        
        try:
            # Initialize components
            mapper = MethodMappingManager(verbose=self.verbose)
            extractor = MDXExtractor(verbose=self.verbose)
            
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
                'versions_processed': versions
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
                    
                    # Save each example
                    for i, example in enumerate(cleaned_examples, 1):
                        if self._save_json_example(example, version, i, args.dry_run):
                            version_count += 1
                            # Track example info
                            all_extracted_methods[method_name]['examples'].append({
                                'example_num': i,
                                'description': example.description,
                                'example_type': example.example_type,
                                'line_number': example.line_number
                            })
                    
                    version_examples += len(cleaned_examples)
                    version_methods_with_examples += 1
                
                self.log(f"✅ {version.upper()}: {version_count} examples extracted from {version_methods_with_examples} methods")
                extraction_stats['total_extracted'] += version_count
                extraction_stats['total_examples_found'] += version_examples
                extraction_stats['methods_with_examples'] += version_methods_with_examples
            
            # Generate tracking files
            if not args.dry_run:
                self._generate_json_tracking_files(all_extracted_methods, extraction_stats)
            
            self.log(f"🎯 Total: {extraction_stats['total_extracted']} JSON examples extracted from {extraction_stats['methods_with_examples']} methods", "success")
            return 0
            
        except Exception as e:
            self.log(f"JSON extraction failed: {e}", "error")
            return 1
    
    def cleanup_command(self, args):
        """Handle cleanup subcommand - Clean up old temporary files."""
        self.log("Starting cleanup process for generated files...")
        
        try:
            cleaner = GeneratedFilesCleaner(
                keep_count=args.keep,
                verbose=self.verbose
            )

            # Default to cleaning timestamped report files if no categories are specified
            categories_to_clean = args.categories if args.categories else ['report_files']
            self.log(f"Targeting categories for cleanup: {', '.join(categories_to_clean)}")
            
            cleaned_files = cleaner.clean_files_by_category(
                categories=categories_to_clean,
                dry_run=args.dry_run,
                create_backup=False,
                max_age_days=None
            )
            
            total_removed = len(cleaned_files)
            if args.dry_run:
                self.log(f"Dry run: Would remove {total_removed} old files.", "info")
            elif total_removed > 0:
                self.log(f"Cleanup completed: removed {total_removed} old files", "success")
            else:
                self.log("No cleanup needed - no old files found to remove", "info")
            
            return 0
            
        except Exception as e:
            self.log(f"Cleanup failed: {e}", "error")
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
                # Find the generated report file
                reports_dir = analyzer.reports_dir
                import glob
                latest_report_files = glob.glob(str(reports_dir / "draft_quality_report_*.md"))
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
        """Allow user to interactively select methods for generation."""
        print("\n📋 Available methods for documentation generation:")
        print("=" * 60)
        
        # Group by version for better display
        by_version = {}
        for method, version in methods_list:
            if version not in by_version:
                by_version[version] = []
            by_version[version].append(method)
        
        # Show methods grouped by version
        for version, methods in by_version.items():
            print(f"\n🔹 {version} ({len(methods)} methods):")
            for i, method in enumerate(methods, 1):
                print(f"   {i:2d}. {method}")
        
        print(f"\n📊 Total: {len(methods_list)} methods")
        print("\nOptions:")
        print("  - Press Enter to generate ALL methods")
        print("  - Type 'q' to quit")
        print("  - Type version (e.g., 'v2') to generate all methods for that version")
        print("  - Type method name to generate specific method")
        
        try:
            choice = input("\nSelect option: ").strip()
            
            if not choice:
                # Generate all
                return methods_list
            elif choice.lower() == 'q':
                return []
            elif choice in by_version:
                # Generate all methods for specific version
                return [(method, choice) for method in by_version[choice]]
            else:
                # Try to find specific method
                matching_methods = []
                for method, version in methods_list:
                    if choice.lower() in method.lower():
                        matching_methods.append((method, version))
                
                if matching_methods:
                    if len(matching_methods) == 1:
                        return matching_methods
                    else:
                        print(f"\n🔍 Found {len(matching_methods)} matching methods:")
                        for i, (method, version) in enumerate(matching_methods, 1):
                            print(f"   {i}. {method} ({version})")
                        return matching_methods
                else:
                    print(f"❌ No methods found matching '{choice}'")
                    return []
                    
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return []
    
    def _create_generation_summary(self, selected_methods, generated_files, summary_file):
        """Create a summary report of the documentation generation."""
        lines = [
            "# Documentation Generation Summary",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Methods:** {len(selected_methods)}",
            f"**Successfully Generated:** {len(generated_files)}",
            f"**Failed:** {len(selected_methods) - len(generated_files)}\n"
        ]
        
        if generated_files:
            lines.extend([
                "## ✅ Successfully Generated\n"
            ])
            
            for method, file_path in generated_files.items():
                lines.append(f"- **{method}**: `{file_path}`")
        
        failed_methods = [method for method, version in selected_methods if method not in generated_files]
        if failed_methods:
            lines.extend([
                "\n## ❌ Failed to Generate\n"
            ])
            
            for method in failed_methods:
                lines.append(f"- {method}")
        
        # Ensure output directory exists
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _save_json_example(self, example, version: str, example_num: int, dry_run: bool = False) -> bool:
        """Save a JSON example to the appropriate directory."""
        # Convert method name to directory format
        dir_name = example.method_name.replace('::', '-')
        
        # Create directory path using workspace root from config
        base_dir = Path(self.config.workspace_root) / "postman" / "json" / "kdf" / version
        method_dir = base_dir / dir_name
        
        # Create filename
        filename = f"{dir_name}-{example.description}-{example.example_type}-{example_num}.json"
        file_path = method_dir / filename
        
        if dry_run:
            print(f"  [DRY RUN] Would save: {file_path}")
            return True
        
        try:
            # Ensure directory exists
            ensure_directory_exists(method_dir)
            
            # Save JSON file
            safe_write_json(file_path, example.content, indent=2)
            
            if self.verbose:
                print(f"    💾 Saved: {file_path}")
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"    ❌ Error saving {file_path}: {e}")
            return False

    def _generate_json_tracking_files(self, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generate tracking JSON files for the JSON extraction process."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = Path(self._resolve_data_directory_path(self.config.directories.reports_dir))
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate method paths tracking file
            self._generate_json_method_paths_file(timestamp, reports_dir, all_extracted_methods)
            
            # Generate methods tracking file
            self._generate_json_methods_file(timestamp, reports_dir, all_extracted_methods, extraction_stats)
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error generating JSON tracking files: {e}")
    
    def _generate_json_method_paths_file(self, timestamp: str, data_dir: Path, all_extracted_methods: Dict[str, Any]) -> None:
        """Generate kdf_json_method_paths_{timestamp}.json file."""
        try:
            # Collect method paths from all extracted methods
            method_paths = {"v1": {}, "v2": {}}
            
            for method_name, method_info in all_extracted_methods.items():
                version = method_info.get('version', 'v2')
                method_clean_name = method_info.get('method_name', method_name)
                
                # Determine version key
                version_key = "v1" if version == "v1" else "v2"
                
                # Create path to JSON output directory for this method using workspace root
                # Convert method name to directory format (same as _save_json_example)
                dir_name = method_clean_name.replace('::', '-')
                json_dir_path = str(Path(self.config.workspace_root) / "postman" / "json" / "kdf" / version / dir_name) + "/"
                
                method_paths[version_key][method_clean_name] = json_dir_path
            
            # Sort method paths alphabetically within each version
            for version_key in method_paths:
                method_paths[version_key] = dict(sorted(method_paths[version_key].items()))
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "KDFTools JSON Extractor v1.0.0",
                    "scanner_type": "JSON_METHOD_PATH_MAPPING",
                    "total_versions": 2,
                    "total_methods_with_json_examples": len(all_extracted_methods),
                    "versions_processed": ["v1", "v2"],
                    "includes_gap_analysis": False,
                    "generated_during_json_extraction": True
                },
                "method_paths": method_paths,
                "json_extraction_info": {
                    "output_format": "Individual JSON files per example",
                    "includes_request_examples": True,
                    "includes_response_examples": False,
                    "file_organization": "nested_by_method_and_example",
                    "paths_point_to": "JSON output directories (not MDX source files)"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_json_method_paths_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated JSON method paths tracking: {output_file}")
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error generating JSON method paths file: {e}")
    
    def _generate_json_methods_file(self, timestamp: str, data_dir: Path, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generate kdf_json_methods_{timestamp}.json file by deriving method lists from the paths file."""
        try:
            # Read the method paths file that was just generated to derive method lists
            paths_file = data_dir / f"kdf_json_method_paths_{timestamp}.json"
            
            if paths_file.exists():
                # Load the paths file and extract method names from the keys
                with open(paths_file, 'r', encoding='utf-8') as f:
                    paths_data = json.load(f)
                
                # Extract methods from the method_paths keys (single source of truth)
                methods_by_version = {"v1": [], "v2": []}
                method_paths = paths_data.get("method_paths", {})
                
                for version in ["v1", "v2"]:
                    if version in method_paths:
                        # Get method names from the keys and sort them
                        methods_by_version[version] = sorted(list(method_paths[version].keys()))
                
                if self.verbose:
                    print(f"📖 Derived method lists from paths file: {paths_file.name}")
            else:
                # Fallback to original logic if paths file doesn't exist
                if self.verbose:
                    print(f"⚠️  Paths file not found, using fallback method extraction")
                
                methods_by_version = {"v1": [], "v2": []}
                for method_name, method_info in all_extracted_methods.items():
                    version = method_info.get('version', 'v2')
                    clean_method_name = method_info.get('method_name', method_name)
                    version_key = "v1" if version == "v1" else "v2"
                    methods_by_version[version_key].append(clean_method_name)
                
                # Sort method lists
                for version_key in methods_by_version:
                    methods_by_version[version_key].sort()
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "KDFTools JSON Extractor v1.0.0",
                    "scanner_type": "JSON_METHODS",
                    "total_versions": 2,
                    "total_methods": sum(len(methods) for methods in methods_by_version.values()),
                    "includes_json_extraction_stats": True,
                    "method_source": "derived_from_paths_file" if paths_file.exists() else "extracted_directly"
                },
                "repository_data": {
                    "v1": {
                        "branch": "json_extraction",
                        "version": "v1",
                        "source_type": "JSON_EXTRACTED",
                        "methods": methods_by_version["v1"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "CodeGroup component parsing",
                            "JSON code block extraction",
                            "Method name cleaning (escaped underscores)",
                            "Example metadata extraction"
                        ]
                    },
                    "v2": {
                        "branch": "json_extraction", 
                        "version": "v2",
                        "source_type": "JSON_EXTRACTED",
                        "methods": methods_by_version["v2"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "CodeGroup component parsing",
                            "JSON code block extraction",
                            "Method name cleaning (escaped underscores)",
                            "Example metadata extraction"
                        ]
                    }
                },
                "extraction_statistics": {
                    "total_methods_processed": extraction_stats.get('total_methods_processed', 0),
                    "methods_with_examples": extraction_stats.get('methods_with_examples', 0),
                    "methods_without_examples": extraction_stats.get('methods_without_examples', 0),
                    "total_examples_found": extraction_stats.get('total_examples_found', 0),
                    "total_examples_extracted": extraction_stats.get('total_extracted', 0),
                    "versions_processed": extraction_stats.get('versions_processed', []),
                    "output_format": "Individual JSON files per example",
                    "file_organization": "nested_by_method_and_example"
                },
                "data_source_info": {
                    "method_lists_source": "derived_from_json_method_paths_file" if paths_file.exists() else "extracted_directly_from_mdx",
                    "ensures_consistency": True,
                    "eliminates_duplication": True,
                    "paths_file_reference": f"kdf_json_method_paths_{timestamp}.json"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_json_methods_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated JSON methods tracking: {output_file}")
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error generating JSON methods file: {e}")
    
    def _cleanup_before_generation(self, categories: List[str], dry_run: bool = False, keep_count: int = 0) -> bool:
        """Clean up generated files before regeneration."""
        try:
            # For pre-generation cleanup, we want to remove all files, so keep_count=0 unless specified
            cleaner = GeneratedFilesCleaner(keep_count=keep_count, verbose=True)

            # Clean files for specified categories
            cleaned_files = cleaner.clean_files_by_category(
                categories=categories,
                dry_run=dry_run,
                create_backup=False,
                max_age_days=None
            )

            self.log(f"Cleaned {len(cleaned_files)} files in categories: {categories}")
            return True

        except Exception as e:
            self.log(f"Cleanup helper failed: {e}", "error")
            return False

    def setup_openapi_parser(self, subparsers):
        """Set up OpenAPI conversion subcommand."""
        openapi_parser = subparsers.add_parser(
            'openapi',
            help='Convert MDX documentation to OpenAPI specifications',
            description='Convert MDX files to OpenAPI YAML specifications with enhanced parameter and enum detection'
        )
        
        openapi_parser.add_argument(
            '--version', '-v',
            choices=['v1', 'v2', 'v2-dev', 'v20-dev', 'all'],
            default='v2',
            help='API version to process (default: v2). Use v2-dev or v20-dev for development version. Use "all" to process both v1 and v2 in a single run.'
        )
        
        openapi_parser.add_argument(
            '--clean-before',
            action='store_true',
            help='Clean up old generated files before generation'
        )
        
        openapi_parser.add_argument(
            '--dry-run',
            action='store_true', 
            help='Show what would be done without making changes'
        )
        
        
        openapi_parser.set_defaults(func=self.openapi_command)
    
    def _generate_postman_tracking_file_from_latest_data(self, versions: List[str]) -> None:
        """Generate postman methods JSON file by deriving method lists from the latest postman method paths file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path(self._get_data_dir())
            reports_dir = Path(self._resolve_data_directory_path(self.config.directories.reports_dir))
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Find the latest postman method paths file (should have been created by method mapping manager)
            method_paths_files = glob.glob(str(reports_dir / "kdf_postman_method_paths_*.json"))
            if not method_paths_files:
                self.log("⚠️ No postman method paths file found - method mapping may not have run", "warning")
                # Create empty tracking file as fallback
                method_paths_data = {"method_paths": {"v1": {}, "v2": {}}}
            else:
                # Get the most recent file
                latest_file = max(method_paths_files, key=lambda x: Path(x).stat().st_mtime)
                self.log(f"📖 Reading method paths from: {Path(latest_file).name}")
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    method_paths_data = json.load(f)
            
            # STEP 1: Extract method names from the method_paths keys (single source of truth)
            methods_by_version = {"v1": [], "v2": []}
            method_paths = method_paths_data.get("method_paths", {})
            total_methods = 0
            total_collections = 0
            total_requests = 0
            collection_files = []
            
            for version in versions:
                if version in method_paths:
                    # Get method names from the keys and sort them
                    version_methods = sorted(list(method_paths[version].keys()))
                    methods_by_version[version] = version_methods
                    total_methods += len(version_methods)
                    
                    # Count requests and collections from the paths data
                    for method_name, method_data in method_paths[version].items():
                        if "postman_collection" in method_data:
                            postman_info = method_data["postman_collection"]
                            if "request_count" in postman_info:
                                total_requests += postman_info["request_count"]
                            
                            # Track collection files
                            if ("collection_info" in postman_info and 
                                "file" in postman_info["collection_info"]):
                                collection_file = postman_info["collection_info"]["file"]
                                if collection_file not in collection_files:
                                    collection_files.append(collection_file)
            
            total_collections = len(collection_files)
            
            if self.verbose:
                print(f"📖 Derived method lists from postman method paths file")
                for version in versions:
                    method_count = len(methods_by_version.get(version, []))
                    print(f"   📋 {version.upper()}: {method_count} methods with Postman integration")
            
            # STEP 2: Generate methods tracking file (derived from paths file)
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "KDFTools Postman Generator v1.0.0",
                    "scanner_type": "POSTMAN_COLLECTION_GENERATION",
                    "total_versions": len(versions),
                    "total_methods": total_methods,
                    "includes_postman_generation_stats": True,
                    "method_source": "derived_from_postman_method_paths_file"
                },
                "repository_data": {},
                "generation_statistics": {
                    "total_methods_processed": total_methods,
                    "total_collections_generated": total_collections,
                    "total_requests_generated": total_requests,
                    "versions_processed": versions,
                    "collection_files": sorted(collection_files),
                    "output_format": "Postman Collection JSON v2.1",
                    "file_organization": "separate_collections_per_version"
                },
                "data_source_info": {
                    "method_lists_source": "derived_from_postman_method_paths_file",
                    "ensures_consistency": True,
                    "eliminates_duplication": True,
                    "paths_file_reference": Path(latest_file).name if method_paths_files else "none"
                }
            }
            
            # Add version-specific data (derived from method paths keys)
            for version in versions:
                tracking_data["repository_data"][version] = {
                    "branch": "postman_generation",
                    "version": version,
                    "source_type": "POSTMAN_COLLECTION_GENERATED",
                    "methods": methods_by_version.get(version, []),
                    "last_updated": datetime.now().isoformat(),
                    "generation_patterns_used": [
                        "Method mapping integration",
                        "Postman collection structure generation",
                        "Hotlink integration with collections",
                        "Method paths file derivation"
                    ]
                }
            
            # Save methods tracking file
            filename = f"kdf_postman_methods_{timestamp}.json"
            filepath = reports_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"📋 Generated Postman methods tracking: {filepath}")
            
        except Exception as e:
            self.log(f"❌ Error generating Postman tracking file: {e}", "error")

    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for scan-rust subcommand."""
        scan_rust_parser = subparsers.add_parser(
            "scan-rust",
            help="Scan KDF Rust repository for RPC methods using async processing.",
            description="Scans the Komodo DeFi Framework Rust repository to extract all RPC method names. "
                        "It can operate on a local clone (if available) or fall back to the remote GitHub repository. "
                        "Results are saved to a timestamped JSON file in the data directory."
        )
        scan_rust_parser.add_argument(
            "--branch",
            default="dev",
            help="The git branch to scan in the remote repository (default: dev)."
        )
        scan_rust_parser.add_argument(
            "-v", "--versions",
            nargs='+',
            default=["v1", "v2"],
            help="A list of API versions to scan (e.g., v1 v2). Default is 'v1 v2'."
        )
        scan_rust_parser.add_argument(
            "-o", "--output",
            help="Output file name for the scan results. If not provided, a timestamped file will be generated."
        )
        scan_rust_parser.add_argument(
            "--force-remote",
            action="store_true",
            help="Force scanning the remote GitHub repository even if a local clone exists."
        )
        scan_rust_parser.set_defaults(func=self.scan_rust)

    def main(self):
        """Main CLI entry point."""
        parser = argparse.ArgumentParser(
            description='Komodo DeFi Framework Tools - Unified CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__doc__
        )
        
        # Global options
        parser.add_argument('--verbose', '-v', action='store_true', default=True,
                           help='Enable verbose output (default: True)')
        parser.add_argument('--quiet', '-q', action='store_true',
                           help='Suppress verbose output')
        parser.add_argument('--dry-run', action='store_true',
                           help='Show what would be done without making changes')
        parser.add_argument('--keep', type=int, default=3,
                           help='Number of recent temporary files to keep during auto-cleanup (default: 3)')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # OpenAPI subcommand
        self.setup_openapi_parser(subparsers)
        
        # Scan subcommand
        self.setup_scan_rust_parser(subparsers)
        
        # Scan MDX subcommand
        scan_mdx_parser = subparsers.add_parser('scan-mdx',
                                              help='Scan MDX documentation files for method names')
        scan_mdx_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                    default=['all'],
                                    help='API versions to scan (default: all)')
        scan_mdx_parser.add_argument('--output', '-o',
                                    help='Output filename (auto-generated if not specified)')
        scan_mdx_parser.set_defaults(func=self.scan_mdx_command)
        
        # Map subcommand
        map_parser = subparsers.add_parser('methods-map',
                                         help='Method mapping and OpenAPI management')
        map_parser.add_argument('--remove', type=str, metavar='METHOD',
                               help='Remove all files related to the specified method')
        map_parser.add_argument('--debug', type=str, metavar='METHOD',
                               help='Debug method name matching for the specified method')
        map_parser.add_argument('--debug-matching', action='store_true',
                               help='Enable verbose debug output for method matching process')
        map_parser.set_defaults(func=self.methods_map_command)
        
        # Postman subcommand
        postman_parser = subparsers.add_parser('postman',
                                             help='Generate Postman collections')
        postman_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                   default=['all'],
                                   help='API versions to process (default: all)')
        postman_parser.add_argument('--clean-before', action='store_true',
                                   help='Clean up old Postman collections before generation')
        postman_parser.set_defaults(func=self.postman_command)
        
        # JSON Extract subcommand
        extract_json_parser = subparsers.add_parser('json-extract',
                                                   help='Extract JSON examples from MDX files')
        extract_json_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                        default=['all'],
                                        help='API versions to process (default: all)')
        extract_json_parser.set_defaults(func=self.json_extract_command)
        
        # Cleanup subcommand
        cleanup_parser = subparsers.add_parser('cleanup',
                                              help='Clean up old temporary files. By default, cleans timestamped data files in utils/py/data.')
        cleanup_parser.add_argument('--keep', type=int, default=3,
                                   help='Number of recent files to keep for each pattern (default: 3)')
        cleanup_parser.add_argument('--categories', nargs='*',
                                   help='Specific categories to clean (e.g., openapi, postman_collections, json_examples). Overrides default.')
        cleanup_parser.add_argument('--dry-run', action='store_true',
                                   help='Show what would be done without making changes')
        cleanup_parser.set_defaults(func=self.cleanup_command)
        
        # Review Draft Quality subcommand
        review_quality_parser = subparsers.add_parser('review-draft-quality',
                                                      help='Compare generated docs with live versions')
        review_quality_parser.add_argument('--generated', type=Path,
                                           help='Path to specific generated document to analyze')
        review_quality_parser.add_argument('--live', type=Path,
                                           help='Path to specific live document to compare against')
        review_quality_parser.add_argument('--generated-dir', type=Path,
                                           help='Directory containing generated documents (default: utils/py/data/generated_docs)')
        review_quality_parser.add_argument('--live-dir', type=Path,
                                           help='Directory containing live documents (default: src/pages/komodo-defi-framework/api)')
        review_quality_parser.add_argument('--output', '-o', type=Path,
                                           help='Output file for the quality report (default: auto-generated timestamp)')
        review_quality_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                                           help='Output format (default: markdown)')
        review_quality_parser.add_argument('--similarity-threshold', type=float, default=0.8,
                                           help='Similarity threshold for flagging differences (default: 0.8)')
        review_quality_parser.add_argument('--verbose', '-v', action='store_true',
                                           help='Enable verbose logging')
        review_quality_parser.set_defaults(func=self.review_draft_quality_command)
        
        # Scan Existing Docs subcommand
        scan_existing_docs_parser = subparsers.add_parser('scan-existing-docs',
                                                         help='Scan existing KDF documentation to extract method patterns')
        scan_existing_docs_parser.add_argument('--docs-path', type=Path,
                                               help='Path to the directory containing existing documentation')
        scan_existing_docs_parser.add_argument('--async-scan', action='store_true',
                                               help='Use asynchronous scanning for better performance')
        scan_existing_docs_parser.add_argument('--generate-report', action='store_true',
                                               help='Generate an analysis report of the extracted patterns')
        scan_existing_docs_parser.add_argument('--show-categories', action='store_true',
                                               help='Show method categories in the analysis report')
        scan_existing_docs_parser.add_argument('--output', type=Path,
                                               help='Output file for the extracted patterns')
        scan_existing_docs_parser.set_defaults(func=self.scan_existing_docs_command)
        
        # Generate Docs subcommand
        generate_docs_parser = subparsers.add_parser('generate-docs',
                                                     help='Generate comprehensive documentation for missing KDF methods')
        generate_docs_parser.add_argument('--branch', '-b',
                                           help='Git branch to scan (default: dev)')
        generate_docs_parser.add_argument('--repo-path', type=Path,
                                           help='Path to the repository containing KDF methods')
        generate_docs_parser.add_argument('--methods-file', type=Path,
                                           help='Path to a JSON file containing methods to generate documentation for')
        generate_docs_parser.add_argument('--interactive', action='store_true',
                                           help='Allow interactive method selection')
        generate_docs_parser.add_argument('--output-dir', type=Path,
                                           help='Output directory for generated documentation')
        generate_docs_parser.add_argument('--method', 
                                           help='Generate documentation for a specific method')
        generate_docs_parser.add_argument('--version',
                                           help='API version for the specific method (default: v2)')
        generate_docs_parser.add_argument('--generate-summary', action='store_true',
                                           help='Generate a summary report of the documentation generation')
        generate_docs_parser.set_defaults(func=self.generate_docs_command)
        
        args = parser.parse_args()
        
        # Setup logging and verbosity
        verbose = args.verbose and not args.quiet
        self.quiet = args.quiet
        self.setup_logging(verbose=not args.quiet)
        
        # Setup configuration with proper workspace root
        self.setup_config()

        # Dispatch command
        try:
            if hasattr(args, 'func'):
                return args.func(args)
            else:
                parser.print_help()
                return 1
        
        except KeyboardInterrupt:
            self.log("Operation cancelled by user", "warning")
            return 1
        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            if verbose:
                traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    tools = KDFTools()
    return tools.main()


if __name__ == "__main__":
    sys.exit(main()) 