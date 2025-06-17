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
- compare: Compare repository methods with documentation
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

# Add the lib directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from lib.scanning.repository_scanner import KDFRepositoryScanner
from lib.scanning.postman_scanners import MDXExtractor, ExtractedExample
from lib.managers import MethodMappingManager
from lib.utils import safe_write_json, ensure_directory_exists
from lib import (
    UnifiedScanner,
    get_logger, setup_logging
)
from lib.constants.config import get_config
from lib.constants.enums import DeploymentEnvironment


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
        
        if level == "success":
            print(f"✅ {message}")
        elif level == "error":
            print(f"❌ {message}")
        elif level == "warning":
            print(f"⚠️  {message}")
        else:
            print(f"ℹ️  {message}")
    
    def openapi_command(self, args):
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        self.log("Starting MDX to OpenAPI conversion with enum/schema extraction...")
        
        try:
            # Auto-cleanup generated files if requested
            if args.clean_before:
                self.log("🧹 Cleaning up old OpenAPI files before generation...")
                if not self._cleanup_before_generation(['openapi'], args.dry_run):
                    self.log("Cleanup failed, continuing anyway...", "warning")
            
            # Initialize OpenAPI manager with enhanced enum/schema support
            from lib.managers.openapi_manager import OpenAPIManager
            manager = OpenAPIManager(
                base_path=self.config.workspace_root
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
                
                # Generate combined tracking files
                self.log("📋 Generating combined tracking files for both versions...")
                manager._generate_openapi_tracking_files(
                    version="all",
                    success_count=len(combined_methods),
                    error_count=0,
                    all_enums={},
                    structures_count=0,
                    enums_count=0,
                    source_dirs=["legacy", "v20", "v20-dev", "common_structures"]
                )
                
                result = f"✅ All versions processed successfully!\n   📊 V1 methods: {len(v1_methods)}\n   📊 V2 methods: {len(manager.all_methods) - len(v1_methods)}\n   📊 Total methods: {len(combined_methods)}"
            else:
                # Generate OpenAPI specs for single version
                result = manager.generate_openapi_spec(version=args.version)
            
            self.log(f"✅ {result}")
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.log(f"📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['total_methods']}")
            self.log(f"   • Methods with enums: {stats['methods_with_enums']}")
            self.log(f"   • Common schemas generated: {stats['common_schemas']}")
            
            if stats['enum_patterns']:
                self.log(f"   • Enum patterns found:")
                for enum_values, count in stats['enum_patterns'].items():
                    if count >= 2:  # Only show patterns used multiple times
                        enum_str = ', '.join(enum_values[:3])  # Show first 3 values
                        if len(enum_values) > 3:
                            enum_str += f" (and {len(enum_values) - 3} more)"
                        self.log(f"     - [{enum_str}] used in {count} methods")
            
            return 0
            
        except Exception as e:
            self.log(f"❌ OpenAPI conversion failed: {str(e)}", "error")
            if args.verbose:
                import traceback
                self.log(traceback.format_exc(), "error")
            return 1
    
    def scan_rust(self, args):
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        try:
            # Use default data directory from config
            data_dir = self._get_data_dir()
            
            scanner = KDFRepositoryScanner(
                base_directory=data_dir,
                default_branch=args.branch,
                verbose=self.verbose
            )
            
            if self.verbose:
                print(f"📋 Branch: {args.branch}")
                print(f"📁 Data directory: {data_dir}")
                print("💡 Using async processing for better performance")
                print()
            
            from lib.async_support import run_async
            # Use async scanning for better performance
            # Always do a fresh scan (caching removed for simplicity)
            repo_info = run_async(scanner.scan_repository_methods_async(args.branch, args.versions))
            saved_path = run_async(scanner.save_repository_methods_async(repo_info, args.output))
            
            # Display summary
            if self.verbose:
                total_methods = 0
                # Load repository methods once instead of for each version
                try:
                    data = run_async(scanner.load_repository_methods_async())
                except:
                    data = None
                
                for version in args.versions:
                    try:
                        count = len(data.get(version, {}).methods) if data else 0
                    except:
                        count = 0
                    
                    total_methods += count
                    print(f"✅ {version.upper()}: {count} methods")
                
                print(f"\n📊 Total: {total_methods} methods across {len(args.versions)} versions")
                print(f"📁 Saved to: {saved_path}")
            
            return 0
        except Exception as e:
            self.log(f"Repository scan failed: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def scan_mdx_command(self, args):
        """Handle MDX-only scanning - extract method names from MDX documentation files."""
        try:
            from datetime import datetime
            import glob
            
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
            from lib.async_support import run_async
            
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
                    
                    import json
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
            
            # STEP 1: Generate method paths file (primary data source)
            method_paths_data = self._generate_mdx_method_paths_data(
                doc_results, rust_data, versions, current_branch
            )
            
            # Save method paths file first
            paths_filename = f"kdf_mdx_method_paths_{timestamp}.json"
            paths_output_path = Path(data_dir) / paths_filename
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
            methods_output_path = Path(data_dir) / methods_filename
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
                import traceback
                traceback.print_exc()
            return 1
    
    def _generate_mdx_method_paths_data(self, doc_results, rust_data, versions, current_branch):
        """Generate the method paths data structure (primary data source)."""
        from datetime import datetime
        
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
        from datetime import datetime
        import json
        
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
                    from lib.async_support import run_async
                    run_async(mapper.remove_method_files_async(args.remove, dry_run=args.dry_run))
                else:
                    mapper.remove_method_files(args.remove, dry_run=args.dry_run)
                return 0
            
            if args.debug:
                # Use async version for debugging if available 
                if hasattr(mapper, 'debug_method_matching_async'):
                    from lib.async_support import run_async
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
                from lib.async_support import run_async
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
                if not self._cleanup_before_generation(['postman_collections'], args.dry_run):
                    self.log("Cleanup failed, continuing anyway...", "warning")
            
            # Handle "all" version by converting to actual supported versions
            versions = args.versions if args.versions != ["all"] else ["v1", "v2"]
            
            # Step 1: Generate method paths file first (like other commands)
            self.log("🗺️ Generating method mapping with Postman hotlinks...")
            from lib.managers.method_mapping_manager import MethodMappingManager
            mapper = MethodMappingManager(verbose=self.verbose)
            
            # Use async mapping for better performance and generate paths file
            from lib.async_support import run_async
            run_async(mapper.save_unified_mapping_async())
            
            # Step 2: Generate Postman collections
            self.log("📮 Generating Postman collections...")
            from lib.managers.postman_manager import PostmanManager
            
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
                import traceback
                self.log(f"Full traceback: {traceback.format_exc()}", "error")
    
    def compare_command(self, args):
        """Handle compare subcommand - Compare repository methods with documentation."""
        if args.simple:
            return self.compare_simple(args)
        else:
            return self.compare_live(args)
    
    def compare_simple(self, args):
        """Handle simple comparison using pre-generated JSON files."""
        self.log("Running simple comparison using JSON files...")
        
        try:
            from lib.managers.simple_comparator import SimpleComparator
            
            # Use default data directory from config
            data_dir = self._get_data_dir()
            
            comparator = SimpleComparator(verbose=self.verbose)
            
            if args.repo_file and args.docs_file:
                # Use specific files
                comparison = comparator.compare_from_files(
                    args.repo_file, args.docs_file, args.versions, args.output
                )
            else:
                # Find latest files automatically
                comparison = comparator.compare_latest(
                    data_dir, args.branch, args.versions, args.output
                )
            
            # Auto-cleanup old comparison files
            from lib.utils import cleanup_kdf_temp_files
            cleanup_kdf_temp_files(data_dir, keep_count=3, verbose=self.verbose)
            
            return 0
        except Exception as e:
            self.log(f"Simple comparison failed: {e}", "error")
            return 1
    
    def compare_live(self, args):
        """Handle live comparison using real-time scanning (original complex approach)."""
        self.log("Comparing repository methods with documentation using live scanning...")
        
        try:
            # Use default data directory from config
            data_dir = self._get_data_dir()
            
            # Initialize scanners
            scanner = KDFRepositoryScanner(
                base_directory=data_dir,
                default_branch=args.branch,
                verbose=self.verbose
            )
            
            if self.verbose:
                print("📚 Scanning documentation for comparison with async processing...")
                print(f"📁 Data directory: {data_dir}")
            
            # Use async scanning for better performance
            from lib.async_support import run_async
            
            # Scan documentation using async methods
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
            
            doc_results = run_async(doc_scanner.scan_all_files_async(args.versions))
            
            # Extract method names from documentation
            doc_methods = {}
            for version in args.versions:
                if version in doc_results:
                    mdx_methods = set(doc_results[version].get('mdx_files', {}).keys())
                    yaml_methods = set(doc_results[version].get('yaml_files', {}).keys())
                    json_methods = set()
                    
                    # Extract methods from JSON examples
                    json_examples = doc_results[version].get('json_examples', {})
                    for method_name in json_examples.keys():
                        json_methods.add(method_name)
                    
                    # Combine all documented methods
                    all_doc_methods = mdx_methods | yaml_methods | json_methods
                    doc_methods[version] = sorted(list(all_doc_methods))
            
            if self.verbose:
                print("🔍 Scanning repository asynchronously...")
            
            # Scan repository using async methods
            repo_info = run_async(scanner.scan_repository_methods_async(args.branch, args.versions))
            
            # Generate unified method mappings to include file paths
            if self.verbose:
                print("🗺️  Generating method mappings for file path resolution...")
            
            mapping_manager = MethodMappingManager(verbose=self.verbose)
            unified_mappings = run_async(mapping_manager.create_unified_mapping_async())
            
            # Compare (this is still synchronous as it's just data processing)
            comparison = scanner.compare_with_documentation(repo_info, doc_methods)
            
            # Generate and display report with method mappings for file paths
            report = scanner.generate_comparison_report(comparison, unified_mappings)
            print(report)
            
            # Save comparison results
            comparison_filename = f"kdf_repo_vs_docs_comparison_{args.branch}.json"
            comparison_path = Path(data_dir) / comparison_filename
            
            safe_write_json(comparison_path, comparison, indent=2)
            
            if self.verbose:
                print(f"💾 Comparison saved to: {comparison_path}")
            
            # Auto-cleanup old comparison files
            from lib.utils import cleanup_kdf_temp_files
            cleanup_kdf_temp_files(data_dir, keep_count=3, verbose=self.verbose)
            
            return 0
        except Exception as e:
            self.log(f"Live comparison failed: {e}", "error")
            return 1
    
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
            
            from lib.async_support import run_async
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
        self.log("Starting cleanup of old temporary files...")
        
        try:
            from lib.utils import cleanup_kdf_temp_files
            
            # Use default data directory from config
            data_dir = self._get_data_dir()
            
            results = cleanup_kdf_temp_files(
                data_dir=data_dir, 
                keep_count=args.keep, 
                verbose=self.verbose
            )
            
            total_removed = sum(results.values())
            if total_removed > 0:
                self.log(f"Cleanup completed: removed {total_removed} old files", "success")
                if self.verbose:
                    print(f"📁 Data directory: {data_dir}")
                    for file_type, count in results.items():
                        if count > 0:
                            print(f"  {file_type}: {count} files removed")
            else:
                self.log("No cleanup needed - all files are recent", "info")
            
            return 0
            
        except Exception as e:
            self.log(f"Cleanup failed: {e}", "error")
            return 1
    
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
            from datetime import datetime
            import json
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path(self._get_data_dir())
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate method paths tracking file
            self._generate_json_method_paths_file(timestamp, data_dir, all_extracted_methods)
            
            # Generate methods tracking file
            self._generate_json_methods_file(timestamp, data_dir, all_extracted_methods, extraction_stats)
            
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error generating JSON tracking files: {e}")
    
    def _generate_json_method_paths_file(self, timestamp: str, data_dir: Path, all_extracted_methods: Dict[str, Any]) -> None:
        """Generate kdf_json_method_paths_{timestamp}.json file."""
        try:
            from datetime import datetime
            import json
            
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
            from datetime import datetime
            import json
            
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
    
    def _cleanup_before_generation(self, categories: List[str], dry_run: bool = False) -> bool:
        """Clean up generated files before regeneration."""
        try:
            from lib.utils.cleanup_utils import GeneratedFilesCleaner
            
            # Use workspace root from config
            workspace_root = self.config.workspace_root
            cleaner = GeneratedFilesCleaner(workspace_root, verbose=True)
            
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
            from datetime import datetime
            import json
            import glob
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path(self._get_data_dir())
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Find the latest postman method paths file (should have been created by method mapping manager)
            method_paths_files = glob.glob(str(data_dir / "kdf_postman_method_paths_*.json"))
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
            filepath = data_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"📋 Generated Postman methods tracking: {filepath}")
            
        except Exception as e:
            self.log(f"❌ Error generating Postman tracking file: {e}", "error")

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
        scan_rust_parser = subparsers.add_parser('scan-rust',
                                          help='Scan KDF Rust repository for RPC methods')
        scan_rust_parser.add_argument('--branch', '-b', default='dev',
                                help='Git branch to scan (default: dev)')
        scan_rust_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'],
                                default=['v1', 'v2'],
                                help='API versions to scan (default: v1 v2)')
        scan_rust_parser.add_argument('--output', '-o',
                                help='Output filename (auto-generated if not specified)')
        
        # Scan MDX subcommand  
        scan_mdx_parser = subparsers.add_parser('scan-mdx',
                                              help='Scan MDX documentation files for method names')
        scan_mdx_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                    default=['all'],
                                    help='API versions to scan (default: all)')
        scan_mdx_parser.add_argument('--output', '-o',
                                    help='Output filename (auto-generated if not specified)')
        
        # Map subcommand
        map_parser = subparsers.add_parser('methods-map',
                                         help='Method mapping and OpenAPI management')
        map_parser.add_argument('--remove', type=str, metavar='METHOD',
                               help='Remove all files related to the specified method')
        map_parser.add_argument('--debug', type=str, metavar='METHOD',
                               help='Debug method name matching for the specified method')
        map_parser.add_argument('--debug-matching', action='store_true',
                               help='Enable verbose debug output for method matching process')
        
        # Postman subcommand
        postman_parser = subparsers.add_parser('postman',
                                             help='Generate Postman collections')
        postman_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                   default=['all'],
                                   help='API versions to process (default: all)')
        postman_parser.add_argument('--clean-before', action='store_true',
                                   help='Clean up old Postman collections before generation')
        
        # Compare subcommand
        compare_parser = subparsers.add_parser('compare',
                                             help='Compare repository methods with documentation')
        compare_parser.add_argument('--branch', '-b', default='dev',
                                   help='Git branch to scan (default: dev)')
        compare_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'],
                                   default=['v1', 'v2'],
                                   help='API versions to scan (default: v1 v2)')
        compare_parser.add_argument('--simple', '-s', action='store_true',
                                   help='Use simple comparison with pre-generated JSON files (faster)')
        compare_parser.add_argument('--repo-file', 
                                   help='Repository methods JSON file (for simple mode)')
        compare_parser.add_argument('--docs-file',
                                   help='Documentation methods JSON file (for simple mode)')
        compare_parser.add_argument('--output',
                                   help='Output file for comparison results')
        
        # JSON Extract subcommand
        extract_json_parser = subparsers.add_parser('json-extract',
                                                   help='Extract JSON examples from MDX files')
        extract_json_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                        default=['all'],
                                        help='API versions to process (default: all)')
        
        # Cleanup subcommand
        cleanup_parser = subparsers.add_parser('cleanup',
                                              help='Clean up old temporary files')
        cleanup_parser.add_argument('--keep', type=int, default=3,
                                   help='Number of recent files to keep (default: 3)')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return 1
        
        # Setup logging and verbosity
        verbose = args.verbose and not args.quiet
        self.quiet = args.quiet
        self.setup_logging(verbose)
        
        # Setup configuration with proper workspace root
        self.setup_config()
        
        # Route to appropriate command handler
        try:
            if args.command == 'openapi':
                return self.openapi_command(args)
            elif args.command == 'scan-rust':
                return self.scan_rust(args)
            elif args.command == 'scan-mdx':
                return self.scan_mdx_command(args)
            elif args.command == 'methods_map':
                return self.methods_map_command(args)
            elif args.command == 'postman':
                return self.postman_command(args)
            elif args.command == 'compare':
                return self.compare_command(args)
            elif args.command == 'json-extract':
                return self.json_extract_command(args)
            elif args.command == 'cleanup':
                return self.cleanup_command(args)
            else:
                self.log(f"Unknown command: {args.command}", "error")
                return 1
        
        except KeyboardInterrupt:
            self.log("Operation cancelled by user", "warning")
            return 1
        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            if verbose:
                import traceback
                traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    tools = KDFTools()
    return tools.main()


if __name__ == "__main__":
    sys.exit(main()) 