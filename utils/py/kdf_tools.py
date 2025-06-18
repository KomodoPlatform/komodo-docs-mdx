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
import os
from pathlib import Path
from typing import List, Dict, Any
import traceback
import argparse
import asyncio

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


from utils.py.lib import (
    get_logger, setup_logging
)
from utils.py.lib.constants.config import get_config
from utils.py.lib.constants.enums import DeploymentEnvironment
from utils.py.lib.openapi.openapi_manager import OpenAPIManager
from utils.py.lib.rust.scanner import KDFScanner


class KDFTools:
    """Unified KDF Tools CLI."""
    CLEANUP_CATEGORIES = ["openapi", "postman", "reports", "all"]

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

    def _print_header(self, title, config_lines=None):
        """Prints a standardized command header."""
        self.log(f"")
        self.log(f"============== 🚀 Starting: {title} ==============")
        if config_lines:
            self.log("Config:")
            for line in config_lines:
                self.log(f"    - {line}")
        self.log("")

    def _print_footer(self, title, success=True, output_paths=None, report_paths=None):
        """Prints a standardized command footer."""
        self.log("")
        if success:
            self.log(f"============== ✅ Success: {title} ==============")
        else:
            self.log(f"============== ❌ Failed: {title} ==============")

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
                manager.all_methods = {} # Reset for v2
                result_v2 = manager.generate_openapi_spec(version="v2")
                self.log(f"✅ V2: {result_v2}")
                
                # Combine methods from both versions for comprehensive tracking
                combined_methods = {**v1_methods, **manager.all_methods}
                
                result = f"✅ All versions processed successfully!\n   📊 V1 methods: {len(v1_methods)}\n   📊 V2 methods: {len(manager.all_methods)}\n   📊 Total methods: {len(combined_methods)}"
            else:
                # Generate OpenAPI specs for single version
                result = manager.generate_openapi_spec(version=args.version)
            
            self.log(f"✅ {result}")
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            enums_count = len(manager.mdx_parser.enum_patterns)
            structures_count = len(manager.mdx_parser.common_structures)
            
            self.log("📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['files_processed']}")
            self.log(f"   • Enums found: {enums_count}")
            self.log(f"   • Structures found: {structures_count}")
            
            self.log("🔚 Finished MDX to OpenAPI conversion.")
            
            success = True
            
        except Exception as e:
            self.log(f"❌ An error occurred during OpenAPI generation: {e}", "error")
            if self.verbose:
                traceback.print_exc()
        
        self._print_footer(command_title, success=success)
        return 0 if success else 1

    def scan_rust(self, args):
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        command_title = "KDF Repository Scan"
        config = [
            f"Branch: {args.branch}",
            f"Versions: {args.versions}"
        ]
        self._print_header(command_title, config)
        
        output_paths = []
        success = False

        async def main():
            nonlocal output_paths, success
            scanner = KDFScanner(
                branch=args.branch,
                data_dir=self._get_data_dir(),
                verbose=self.verbose
            )
            
            versions_to_scan = args.versions
            if "all" in versions_to_scan:
                versions_to_scan = ["v1", "v2"]
            
            repo_info = await scanner.scan_repository_methods_async(versions=versions_to_scan)
            
            if repo_info:
                output_file = await scanner.save_repository_methods_async(repo_info)
                print(f"💾 Saved repository method paths to: {output_file}")
                output_paths.append(output_file)
                success = True
            else:
                self.log("❌ Repository scan failed to return any information.", "error")
                success = False

        try:
            asyncio.run(main())
        except Exception as e:
            self.log(f"❌ An error occurred during Rust repository scan: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            success = False

        self._print_footer(command_title, success=success, output_paths=output_paths)
        return 0 if success else 1

    def scan_mdx_command(self, args):
        """Handle MDX-only scanning - extract method names from MDX documentation files."""
        command_title = "Scan MDX Documentation"
        config = [f"Versions: {args.versions}"]
        self._print_header(command_title, config)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def map_methods_command(self, args):
        """Handle map subcommand - Method mapping and OpenAPI management."""
        command_title = "Map Methods"
        config = [f"Version: {args.version}"]
        self._print_header(command_title, config)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def postman_command(self, args):
        """Handle postman subcommand - Generate Postman collections."""
        command_title = "Generate Postman Collections"
        config = [
            f"Versions: {args.versions}",
            f"Clean before: {args.clean_before}",
            f"Keep: {args.keep}"
        ]
        self._print_header(command_title, config)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def json_extract_command(self, args):
        """Handle json-extract subcommand - Extract JSON examples from MDX files."""
        command_title = "Extract JSON Examples"
        config = [f"Versions: {args.versions}"]
        self._print_header(command_title, config)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def cleanup_command(self, args):
        """Handle cleanup subcommand - Clean up old temporary files."""
        command_title = "Cleanup Old Temporary Files"
        config = [
            f"Categories: {args.categories}",
            f"Keep: {args.keep}",
            f"Dry run: {args.dry_run}"
        ]
        self._print_header(command_title, config)
        
        categories_to_clean = args.categories
        if "all" in categories_to_clean:
            categories_to_clean = [c for c in self.CLEANUP_CATEGORIES if c != 'all']

        self.log(f"Target categories: {', '.join(categories_to_clean)}")
        
        success = self._cleanup_before_generation(categories_to_clean, args.dry_run, args.keep)
        
        self._print_footer(command_title, success=success)
        return 0 if success else 1

    def review_draft_quality_command(self, args):
        """Handle review-draft-quality subcommand - Compare generated docs with live versions."""
        command_title = "Review Draft Quality"
        self._print_header(command_title)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def scan_existing_docs_command(self, args):
        """Handle scan-existing-docs subcommand - Scan existing KDF documentation to extract method patterns."""
        command_title = "Scan Existing Docs"
        self._print_header(command_title)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def generate_docs_command(self, args):
        """Handle generate-docs subcommand - Generate documentation for missing KDF methods."""
        command_title = "Generate Missing Docs"
        self._print_header(command_title)
        
        self.log("⚠️ This command is not yet implemented.", "warning")
        
        self._print_footer(command_title, success=False)
        return 1

    def _select_methods_interactively(self, methods_list):
        """Allow user to interactively select methods for generation."""
        pass

    def _create_generation_summary(self, selected_methods, generated_files, summary_file):
        """Create a summary report of the documentation generation."""
        pass

    def _save_json_example(self, example, version: str, example_num: int, dry_run: bool = False) -> bool:
        """Save a JSON example to the appropriate directory."""
        pass

    def _generate_json_tracking_files(self, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generate tracking JSON files for the JSON extraction process."""
        pass

    def _generate_json_method_paths_file(self, timestamp: str, data_dir: Path, all_extracted_methods: Dict[str, Any]) -> None:
        """Generate kdf_json_method_paths_{timestamp}.json file."""
        pass

    def _generate_json_methods_file(self, timestamp: str, data_dir: Path, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any]) -> None:
        """Generate kdf_json_methods_{timestamp}.json file by deriving method lists from the paths file."""
        pass

    def _cleanup_before_generation(self, categories: List[str], dry_run: bool = False, keep_count: int = 0) -> bool:
        """Clean up generated files before regeneration."""
        self.log(f"Starting cleanup for categories: {categories} (keeping {keep_count} recent files)...")
        
        base_dirs = {
            "openapi": getattr(self.config.directories, "openapi_dir", "openapi"),
            "postman": getattr(self.config.directories, "postman_collections_dir", "postman/collections/methods"),
            "reports": getattr(self.config.directories, "reports_dir", "utils/py/data/reports")
        }
        
        file_patterns = {
            "openapi": "kdf_*.yaml",
            "postman": "*.postman_collection.json",
            "reports": "*.json"
        }

        all_cleaned = True
        for category in categories:
            if category not in base_dirs or not base_dirs[category]:
                self.log(f"Unknown or unconfigured cleanup category: {category}", "warning")
                continue

            target_dir = Path(self.config._resolve_path(base_dirs[category]))
            pattern = file_patterns.get(category)
            
            if not target_dir.exists() or not pattern:
                self.log(f"Directory or pattern for category '{category}' not found.", "warning")
                continue

            files = sorted(
                target_dir.glob(f"**/{pattern}"), 
                key=lambda p: p.stat().st_mtime, 
                reverse=True
            )
            
            files_to_delete = files[keep_count:]
            
            if not files_to_delete:
                self.log(f"No old files to delete for category '{category}'.")
                continue

            self.log(f"Found {len(files_to_delete)} file(s) to delete for category '{category}':")
            for f in files_to_delete:
                self.log(f"  - Deleting {f.relative_to(self.config.workspace_root)}")
                if not dry_run:
                    try:
                        f.unlink()
                    except Exception as e:
                        self.log(f"    -> Failed to delete: {e}", "error")
                        all_cleaned = False
        
        if dry_run:
            self.log("Dry run complete. No files were deleted.", "info")
            
        return all_cleaned

    def setup_postman_parser(self, subparsers):
        """Setup parser for postman subcommand."""
        postman_parser = subparsers.add_parser(
            "postman",
            help="Generate Postman collections from OpenAPI specs",
            description="Processes OpenAPI specs to generate Postman collection files."
        )
        postman_parser.add_argument(
            "--versions",
            nargs='+',
            choices=["v1", "v2", "all"],
            default=["v2"],
            help="API versions to process (default: v2)"
        )
        postman_parser.add_argument(
            "--clean-before",
            action="store_true",
            help="Clean up old Postman files before generation"
        )
        postman_parser.add_argument(
            "--keep",
            type=int,
            default=3,
            help="Number of recent temporary files to keep during auto-cleanup (default: 3)"
        )
        postman_parser.set_defaults(func=self.postman_command)

    def setup_openapi_parser(self, subparsers):
        """Set up OpenAPI conversion subcommand."""
        openapi_parser = subparsers.add_parser(
            "openapi",
            help="Convert MDX documentation to OpenAPI specs",
            description="Processes MDX files to generate OpenAPI specification files."
        )
        openapi_parser.add_argument(
            "--version",
            choices=["v1", "v2", "all"],
            default="v2",
            help="API version to process (default: v2)"
        )
        openapi_parser.add_argument(
            "--clean-before",
            action="store_true",
            help="Clean up old OpenAPI files before generation"
        )
        openapi_parser.add_argument(
            "--keep",
            type=int,
            default=3,
            help="Number of recent temporary files to keep during auto-cleanup (default: 3)"
        )
        openapi_parser.set_defaults(func=self.openapi_command)

    def setup_scan_mdx_parser(self, subparsers):
        """Setup parser for scan-mdx subcommand."""
        scan_mdx_parser = subparsers.add_parser(
            "scan-mdx", help="Scan MDX documentation for method names"
        )
        scan_mdx_parser.add_argument(
            "--versions",
            nargs='+',
            choices=["v1", "v2", "all"],
            default=["all"],
            help="API versions to scan (default: all)"
        )
        scan_mdx_parser.set_defaults(func=self.scan_mdx_command)

    def setup_map_methods_parser(self, subparsers):
        """Setup parser for the map_methods subcommand."""
        map_methods_parser = subparsers.add_parser("map_methods", help="Method mapping and OpenAPI management")
        map_methods_parser.add_argument("--version", type=str, default="v2", help="Specify the API version (e.g., v2)")
        map_methods_parser.set_defaults(func=self.map_methods_command)

    def setup_json_extract_parser(self, subparsers):
        """Setup parser for the json-extract subcommand."""
        json_extract_parser = subparsers.add_parser(
            "json-extract", help="Extract JSON examples from MDX files"
        )
        json_extract_parser.add_argument(
            "--versions",
            nargs='+',
            choices=["v1", "v2", "all"],
            default=["all"],
            help="API versions to process (default: all)"
        )
        json_extract_parser.set_defaults(func=self.json_extract_command)

    def setup_cleanup_parser(self, subparsers):
        """Setup parser for cleanup subcommand."""
        description = (
            "Cleans up generated temporary files from various categories.\n\n"
            f"Available categories: {', '.join(self.CLEANUP_CATEGORIES)}"
        )
        cleanup_parser = subparsers.add_parser(
            "cleanup", 
            help="Clean up old temporary files.",
            description=description,
            formatter_class=argparse.RawTextHelpFormatter
        )
        cleanup_parser.add_argument(
            'categories',
            nargs='*',
            default=['reports'],
            help="The categories of files to clean. Defaults to 'reports'."
        )
        cleanup_parser.add_argument(
            "--keep",
            type=int,
            default=3,
            help="Number of recent temporary files to keep for each category (default: 3)."
        )
        cleanup_parser.set_defaults(func=self.cleanup_command)

    def setup_review_draft_quality_parser(self, subparsers):
        """Setup parser for review-draft-quality subcommand."""
        parser = subparsers.add_parser(
            "review-draft-quality", help="Compare generated docs with live versions"
        )
        parser.set_defaults(func=self.review_draft_quality_command)

    def setup_scan_existing_docs_parser(self, subparsers):
        """Setup parser for scan-existing-docs subcommand."""
        parser = subparsers.add_parser(
            "scan-existing-docs", help="Scan existing KDF documentation to extract method patterns"
        )
        parser.set_defaults(func=self.scan_existing_docs_command)

    def setup_generate_docs_parser(self, subparsers):
        """Setup parser for generate-docs subcommand."""
        parser = subparsers.add_parser(
            "generate-docs", help="Generate documentation for missing KDF methods"
        )
        parser.set_defaults(func=self.generate_docs_command)

    def _generate_postman_tracking_file_from_latest_data(self, versions: List[str]) -> None:
        """Generate postman methods JSON file by deriving method lists from the latest postman method paths file."""
        pass

    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for scan-rust subcommand."""
        scan_rust_parser = subparsers.add_parser(
            "scan-rust",
            help="Scan KDF Rust repository for RPC methods",
            description="Scans the Komodo DeFi Framework Rust source code to find RPC method definitions."
        )
        scan_rust_parser.add_argument(
            "--branch",
            type=str,
            default="dev",
            help="The KDF repository branch to scan (default: dev)"
        )
        scan_rust_parser.add_argument(
            "--versions",
            nargs='+',
            choices=["v1", "v2", "all"],
            default=["all"],
            help="API versions to scan (default: all)"
        )
        scan_rust_parser.set_defaults(func=self.scan_rust)

    def main(self):
        """Main CLI entry point."""
        parser = argparse.ArgumentParser(
            description="Komodo DeFi Framework Tools - Unified CLI",
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=__doc__
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be done without making changes"
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", default=True, help="Enable verbose output"
        )
        parser.add_argument(
            "-q", "--quiet", action="store_true", help="Suppress verbose output"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        self.setup_openapi_parser(subparsers)
        self.setup_postman_parser(subparsers)
        self.setup_scan_rust_parser(subparsers)
        self.setup_scan_mdx_parser(subparsers)
        self.setup_map_methods_parser(subparsers)
        self.setup_json_extract_parser(subparsers)
        self.setup_cleanup_parser(subparsers)
        self.setup_review_draft_quality_parser(subparsers)
        self.setup_scan_existing_docs_parser(subparsers)
        self.setup_generate_docs_parser(subparsers)

        args = parser.parse_args()

        self.verbose = args.verbose and not args.quiet
        self.quiet = args.quiet
        self.setup_logging(verbose=self.verbose)
        self.setup_config()

        if hasattr(args, 'func'):
            try:
                return args.func(args)
            except Exception as e:
                self.log(f"❌ An error occurred while executing command '{args.command}': {e}", "error")
                if self.verbose:
                    traceback.print_exc()
                return 1
        else:
            parser.print_help()
            return 0


def main():
    """Main entry point."""
    tools = KDFTools()
    return tools.main()


if __name__ == "__main__":
    sys.exit(main())