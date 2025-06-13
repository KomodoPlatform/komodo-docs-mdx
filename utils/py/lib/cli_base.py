#!/usr/bin/env python3
"""
CLI Base Classes

Common base classes and utilities for command-line interfaces.
Provides standardized argument parsing and logging functionality.
"""

import argparse
import os
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class CLIBase(ABC):
    """
    Base class for CLI applications providing common functionality.
    
    Features:
    - Standardized argument parsing
    - Verbosity control
    - Working directory management
    - Error handling
    """
    
    def __init__(self, description: str):
        self.description = description
        self.parser = self._create_base_parser()
        self.verbose = True
        self.quiet = False
        
    def _create_base_parser(self) -> argparse.ArgumentParser:
        """Create base argument parser with common options."""
        parser = argparse.ArgumentParser(description=self.description)
        
        # Common arguments for all CLI tools
        parser.add_argument('--verbose', '-v', action='store_true', default=True,
                           help='Enable verbose output')
        parser.add_argument('--quiet', '-q', action='store_true',
                           help='Minimal output')
        parser.add_argument('--dry-run', action='store_true',
                           help='Show what would be done without making changes')
        
        return parser
    
    def add_argument(self, *args, **kwargs):
        """Add argument to parser."""
        return self.parser.add_argument(*args, **kwargs)
    
    def add_argument_group(self, *args, **kwargs):
        """Add argument group to parser."""
        return self.parser.add_argument_group(*args, **kwargs)
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command line arguments."""
        parsed_args = self.parser.parse_args(args)
        
        # Set verbosity
        self.verbose = parsed_args.verbose and not parsed_args.quiet
        self.quiet = parsed_args.quiet
        
        return parsed_args
    
    def setup_working_directory(self):
        """Change to script directory for relative paths."""
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        os.chdir(script_dir)
        if self.verbose:
            print(f"Working directory: {os.getcwd()}")
    
    def log(self, message: str, level: str = "info"):
        """Log message based on verbosity settings."""
        if level == "error":
            print(f"❌ {message}", file=sys.stderr)
        elif level == "warning" and not self.quiet:
            print(f"⚠️ {message}")
        elif level == "info" and not self.quiet:
            print(f"ℹ️ {message}")
        elif level == "success" and not self.quiet:
            print(f"✅ {message}")
        elif level == "debug" and self.verbose:
            print(f"🔍 {message}")
    
    @abstractmethod
    def setup_arguments(self):
        """Setup command-specific arguments. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def run(self, args: argparse.Namespace) -> int:
        """Main execution logic. Must be implemented by subclasses."""
        pass
    
    def main(self, argv: Optional[List[str]] = None) -> int:
        """Main entry point."""
        try:
            self.setup_arguments()
            args = self.parse_args(argv)
            self.setup_working_directory()
            return self.run(args)
        except KeyboardInterrupt:
            self.log("Operation cancelled by user", "warning")
            return 130
        except Exception as e:
            self.log(f"Unexpected error: {e}", "error")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return 1


class VersionedCLI(CLIBase):
    """
    CLI base class for tools that work with API versions.
    Adds common version-related arguments.
    """
    
    def __init__(self, description: str, supported_versions: List[str] = ['v1', 'v2']):
        super().__init__(description)
        self.supported_versions = supported_versions
        
    def setup_arguments(self):
        """Setup version-related arguments."""
        self.add_argument('--versions', nargs='+', 
                         choices=self.supported_versions, 
                         default=self.supported_versions,
                         help='API versions to process')


class BatchProcessorCLI(VersionedCLI):
    """
    CLI base class for batch processing tools.
    Adds common batch processing arguments.
    """
    
    def setup_arguments(self):
        """Setup batch processing arguments."""
        super().setup_arguments()
        
        self.add_argument('--parallel', '-p', action='store_true',
                         help='Enable parallel processing')
        self.add_argument('--batch-size', type=int, default=50,
                         help='Batch size for processing')
        self.add_argument('--continue-on-error', action='store_true',
                         help='Continue processing even if errors occur')


def create_simple_cli(description: str, main_func) -> int:
    """
    Create a simple CLI wrapper for a main function.
    
    Args:
        description: CLI description
        main_func: Function to call with parsed arguments
        
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    
    try:
        return main_func(args)
    except KeyboardInterrupt:
        if not args.quiet:
            print("Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1 