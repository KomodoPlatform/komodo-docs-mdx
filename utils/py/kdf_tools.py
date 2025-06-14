#!/usr/bin/env python3
"""
Komodo DeFi Framework Tools - Unified CLI

A comprehensive command-line interface for managing KDF documentation, OpenAPI specs,
Postman collections, and repository analysis. This tool consolidates functionality
from multiple specialized scripts into a single, easy-to-use interface.

Available Commands:
- openapi: Convert MDX documentation to OpenAPI specs
- scan: Scan KDF repository for RPC methods
- map: Method mapping and OpenAPI management
- postman: Generate Postman collections
- compare: Compare repository methods with documentation
- json-extract: Extract JSON examples from MDX files

Examples:
    kdf_tools.py openapi --version v2 --output-dir ./output
    kdf_tools.py scan --branch dev --versions v1 v2 --force-refresh
    kdf_tools.py map --include-postman
    kdf_tools.py json-extract --versions v2 --nested-structure

Global Options:
    --dry-run: Show what would be done without making changes
    --quiet: Suppress verbose output
    --nested-structure: Use nested directory structure based on MDX organization (default: True)
    --flat-structure: Use legacy flat directory structure for backward compatibility
"""

import sys
import argparse
import os
from pathlib import Path

# Add the lib directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from lib.mapping import MethodMapper
from lib.openapi.converter import MDXToOpenAPIConverter
from lib.scanning.repository_scanner import KDFRepositoryScanner
from lib.scanning.extractors import MDXExtractor
from lib.postman.postman_consolidated import PostmanCollectionGenerator
from lib.utils import safe_write_json, ensure_directory_exists
from lib import (
    UnifiedScanner,
    get_logger, setup_logging
)


class KDFTools:
    """Unified KDF Tools CLI."""
    
    def __init__(self):
        self.verbose = True
        self.quiet = False
        self.logger = None
        self.events_enabled = False
    
    def setup_logging(self, verbose=True, events=False):
        """Setup logging configuration."""
        setup_logging(verbose=verbose, events=events)
        self.logger = get_logger("kdf-tools")
        self.verbose = verbose
        self.events_enabled = events
    
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
        self.log("Starting MDX to OpenAPI conversion...")
        
        try:
            converter = MDXToOpenAPIConverter(base_path=".", use_nested_structure=args.nested_structure)
            converter.convert_methods(
                version=args.version,
                output_dir=args.output_dir,
                dry_run=args.dry_run
            )
            self.log("OpenAPI conversion completed successfully!", "success")
            return 0
        except Exception as e:
            self.log(f"OpenAPI conversion failed: {e}", "error")
            return 1
    
    def scan_command(self, args):
        """Handle scan subcommand - KDF repository scanning."""
        self.log(f"Scanning KDF repository (branch: {args.branch})...")
        
        try:
            scanner = KDFRepositoryScanner(
                base_directory=args.data_dir,
                default_branch=args.branch,
                verbose=self.verbose
            )
            
            if self.verbose:
                print(f"📋 Branch: {args.branch}")
                print(f"📋 Versions: {', '.join(args.versions)}")
                print()
            
            # Scan repository
            if args.force_refresh:
                repo_info = scanner.scan_repository_methods(args.branch, args.versions)
                saved_path = scanner.save_repository_methods(repo_info, args.output)
            else:
                methods = scanner.get_latest_methods(args.branch, args.force_refresh)
                
                # Convert to output format
                output_data = {
                    "scan_metadata": {
                        "branch": args.branch,
                        "versions": args.versions,
                        "scanner": "KDFRepositoryScanner v2.0.0"
                    }
                }
                output_data.update(methods)
                
                if args.output:
                    output_path = Path(args.data_dir) / args.output
                    safe_write_json(output_path, output_data, indent=2)
                    saved_path = str(output_path)
                else:
                    repo_info = scanner.scan_repository_methods(args.branch, args.versions)
                    saved_path = scanner.save_repository_methods(repo_info)
            
            # Display summary
            if self.verbose:
                total_methods = 0
                # Load repository methods once instead of for each version
                try:
                    data = scanner.load_repository_methods()
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
                print(f"💾 Saved to: {saved_path}")
            
            return 0
        except Exception as e:
            self.log(f"Repository scan failed: {e}", "error")
            return 1
    
    def map_command(self, args):
        """Handle map subcommand - Method mapping and OpenAPI management."""
        self.log("Starting method mapping and OpenAPI management...")
        
        try:
            mapper = MethodMapper(verbose=self.verbose)
            
            # Enable debug mode if requested
            if hasattr(args, 'debug_matching') and args.debug_matching:
                mapper.normalizer.enable_debug_mode(True)
                self.log("🔍 Debug mode enabled for method matching", "info")
            
            if args.remove:
                mapper.remove_method_files(args.remove, dry_run=args.dry_run)
                return 0
            
            if args.debug:
                mapper.debug_method_matching(args.debug)
                return 0
            
            if not self.quiet:
                print("\n📋 Generating unified method mapping...")
            
            mapper.save_unified_mapping()
            self.log("Method mapping completed successfully!", "success")
            return 0
        except Exception as e:
            self.log(f"Method mapping failed: {e}", "error")
            return 1
    
    def postman_command(self, args):
        """Handle postman subcommand - Generate Postman collections."""
        self.log("Starting Postman collection generation...")
        
        try:
            # Handle "all" version by converting to actual supported versions
            versions = args.versions
            if 'all' in versions:
                versions = ['v1', 'v2']
            
            generator = PostmanCollectionGenerator(verbose=self.verbose)
            results = generator.generate_collections(versions)
            summary = generator.generate_summary_report(results)
            
            self.log("Collection generation completed successfully!", "success")
            if not self.quiet:
                print(summary)
            
            return 0
        except Exception as e:
            self.log(f"Collection generation failed: {e}", "error")
            return 1
    
    def compare_command(self, args):
        """Handle compare subcommand - Compare repository with documentation."""
        self.log("Comparing repository methods with documentation...")
        
        try:
            # Initialize scanners
            scanner = KDFRepositoryScanner(
                base_directory=args.data_dir,
                default_branch=args.branch,
                verbose=self.verbose
            )
            
            if self.verbose:
                print("📚 Scanning documentation for comparison...")
            
            # Scan documentation
            doc_scanner = UnifiedScanner(verbose=self.verbose)
            doc_results = doc_scanner.scan_all_files(args.versions)
            
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
                print("🔍 Scanning repository...")
            
            # Scan repository
            repo_info = scanner.scan_repository_methods(args.branch, args.versions)
            
            # Compare
            comparison = scanner.compare_with_documentation(repo_info, doc_methods)
            
            # Generate and display report
            report = scanner.generate_comparison_report(comparison)
            print(report)
            
            # Save comparison results
            comparison_filename = f"kdf_repo_vs_docs_comparison_{args.branch}.json"
            comparison_path = Path(args.data_dir) / comparison_filename
            
            safe_write_json(comparison_path, comparison, indent=2)
            
            if self.verbose:
                print(f"💾 Comparison saved to: {comparison_path}")
            
            return 0
        except Exception as e:
            self.log(f"Comparison failed: {e}", "error")
            return 1
    
    def json_extract_command(self, args):
        """Handle json-extract subcommand - Extract JSON examples from MDX files."""
        self.log("Starting JSON example extraction from MDX files...")
        
        try:
            # Initialize components
            mapper = MethodMapper(base_path=".", verbose=self.verbose)
            extractor = MDXExtractor(verbose=self.verbose, use_nested_structure=args.nested_structure, base_path=".")
            
            # Get unified mapping
            unified_mapping = mapper.create_unified_mapping()
            
            # Handle "all" version by converting to actual supported versions
            versions = args.versions
            if 'all' in versions:
                versions = ['v1', 'v2']
            
            total_extracted = 0
            
            for version in versions:
                if version not in unified_mapping:
                    self.log(f"No methods found for version {version}", "warning")
                    continue
                
                methods = unified_mapping[version]
                version_count = 0
                
                self.log(f"Processing {len(methods)} methods for {version.upper()}")
                
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
                        continue
                    
                    if self.verbose:
                        print(f"  🔍 {method_name}: Found {len(examples)} examples")
                    
                    # Save each example
                    for i, example in enumerate(examples, 1):
                        if self._save_json_example(example, version, i, args.dry_run):
                            version_count += 1
                
                self.log(f"✅ {version.upper()}: {version_count} examples extracted")
                total_extracted += version_count
            
            self.log(f"🎯 Total: {total_extracted} JSON examples extracted", "success")
            return 0
            
        except Exception as e:
            self.log(f"JSON extraction failed: {e}", "error")
            return 1
    
    def _save_json_example(self, example, version: str, example_num: int, dry_run: bool = False) -> bool:
        """Save a JSON example to the appropriate directory."""
        # Convert method name to directory format
        dir_name = example.method_name.replace('::', '-')
        
        # Create directory path
        base_dir = Path("../../postman/json/kdf") / version
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
        parser.add_argument('--events', action='store_true',
                           help='Enable event system logging (default: False)')
        parser.add_argument('--dry-run', action='store_true',
                           help='Show what would be changed without making changes')
        parser.add_argument('--data-dir', default='data',
                           help='Directory to store data files (default: data)')
        parser.add_argument('--nested-structure', action='store_true', default=True,
                           help='Use nested directory structure based on MDX organization (default)')
        parser.add_argument('--flat-structure', dest='nested_structure', action='store_false',
                           help='Use legacy flat directory structure for backward compatibility')
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # OpenAPI subcommand
        openapi_parser = subparsers.add_parser('openapi', 
                                             help='Convert MDX documentation to OpenAPI specs')
        openapi_parser.add_argument('--version', choices=['v1', 'v2', 'all'], default='all',
                                   help='API version to process (default: all)')
        openapi_parser.add_argument('--output-dir', 
                                   help='Output directory for OpenAPI files')
        
        # Scan subcommand
        scan_parser = subparsers.add_parser('scan',
                                          help='Scan KDF repository for RPC methods')
        scan_parser.add_argument('--branch', '-b', default='dev',
                                help='Git branch to scan (default: dev)')
        scan_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'],
                                default=['v1', 'v2'],
                                help='API versions to scan (default: v1 v2)')
        scan_parser.add_argument('--output', '-o',
                                help='Output filename (auto-generated if not specified)')
        scan_parser.add_argument('--force-refresh', '-f', action='store_true',
                                help='Force refresh even if cache is valid')
        
        # Map subcommand
        map_parser = subparsers.add_parser('map',
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
        
        # Compare subcommand
        compare_parser = subparsers.add_parser('compare',
                                             help='Compare repository methods with documentation')
        compare_parser.add_argument('--branch', '-b', default='dev',
                                   help='Git branch to scan (default: dev)')
        compare_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'],
                                   default=['v1', 'v2'],
                                   help='API versions to scan (default: v1 v2)')
        
        # JSON Extract subcommand
        json_extract_parser = subparsers.add_parser('json-extract',
                                                   help='Extract JSON examples from MDX files')
        json_extract_parser.add_argument('--versions', nargs='+', choices=['v1', 'v2', 'all'],
                                        default=['all'],
                                        help='API versions to process (default: all)')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return 1
        
        # Setup logging and verbosity
        verbose = args.verbose and not args.quiet
        self.quiet = args.quiet
        self.events_enabled = args.events
        self.setup_logging(verbose, args.events)
        
        # Change to script directory for relative paths
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Route to appropriate command handler
        try:
            if args.command == 'openapi':
                return self.openapi_command(args)
            elif args.command == 'scan':
                return self.scan_command(args)
            elif args.command == 'map':
                return self.map_command(args)
            elif args.command == 'postman':
                return self.postman_command(args)
            elif args.command == 'compare':
                return self.compare_command(args)
            elif args.command == 'json-extract':
                return self.json_extract_command(args)
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