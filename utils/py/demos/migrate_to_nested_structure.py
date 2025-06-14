#!/usr/bin/env python3
"""
Migration Script: Flat to Nested Directory Structure

This script migrates the existing flat directory structure to the new nested
structure while preserving backward compatibility and allowing gradual migration.

Usage:
    python migrate_to_nested_structure.py --dry-run    # See what would be done
    python migrate_to_nested_structure.py --migrate    # Perform migration
    python migrate_to_nested_structure.py --rollback   # Rollback to flat structure
"""

import sys
import os
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.path_utils import PathMapper
from lib.mapping import MethodMapper

class StructureMigrator:
    """Handles migration between flat and nested directory structures."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.path_mapper = PathMapper(base_path)
        self.method_mapper = MethodMapper(base_path)
        
    def analyze_current_structure(self) -> Dict[str, Dict[str, List[str]]]:
        """Analyze the current file structure."""
        print("🔍 Analyzing current structure...")
        
        structure = {
            "openapi": {"v1": [], "v2": []},
            "postman_json": {"v1": [], "v2": []},
            "postman_collections": {"v1": [], "v2": []}
        }
        
        # Analyze OpenAPI files
        for version in ["v1", "v2"]:
            version_config = self.path_mapper.version_configs.get(version)
            if version_config:
                openapi_dir = self.base_path / version_config.openapi_path
                if openapi_dir.exists():
                    for yaml_file in openapi_dir.glob("*.yaml"):
                        structure["openapi"][version].append(str(yaml_file.relative_to(self.base_path)))
                
                postman_dir = self.base_path / version_config.postman_path
                if postman_dir.exists():
                    for method_dir in postman_dir.iterdir():
                        if method_dir.is_dir():
                            structure["postman_json"][version].append(str(method_dir.relative_to(self.base_path)))
        
        return structure
    
    def plan_migration(self) -> List[Tuple[str, str, str]]:
        """Plan the migration from flat to nested structure."""
        print("📋 Planning migration...")
        
        migration_plan = []  # (source, destination, type)
        
        # Get unified mapping
        unified_mapping = self.method_mapper.create_unified_mapping()
        
        for version in ["v1", "v2"]:
            if version not in unified_mapping:
                continue
                
            methods = unified_mapping[version]
            print(f"Planning {len(methods)} methods for {version}...")
            
            for method_name, mapping in methods.items():
                if not mapping.has_mdx:
                    continue
                    
                # Get nested path mapping
                path_mapping = self.path_mapper.get_method_path_mapping(
                    method_name, mapping.mdx_path, version
                )
                
                # Plan OpenAPI migration
                if mapping.has_yaml:
                    old_openapi = self.base_path / mapping.yaml_path
                    new_openapi = self.base_path / path_mapping.openapi_path
                    if old_openapi.exists() and old_openapi != new_openapi:
                        migration_plan.append((str(old_openapi), str(new_openapi), "openapi"))
                
                # Plan Postman JSON migration
                if mapping.has_json:
                    # Current flat structure
                    version_config = self.path_mapper.version_configs.get(version)
                    if version_config:
                        old_json_dir = self.base_path / version_config.postman_path / method_name.replace("::", "-").lower()
                        new_json_dir = self.base_path / path_mapping.postman_json_path
                        if old_json_dir.exists() and old_json_dir != new_json_dir:
                            migration_plan.append((str(old_json_dir), str(new_json_dir), "postman_json"))
        
        print(f"📦 Migration plan: {len(migration_plan)} operations")
        return migration_plan
    
    def execute_migration(self, migration_plan: List[Tuple[str, str, str]], dry_run: bool = False) -> Dict[str, int]:
        """Execute the migration plan."""
        print(f"{'🔄 [DRY RUN]' if dry_run else '🚀'} Executing migration...")
        
        results = {"moved": 0, "created_dirs": 0, "errors": 0}
        
        for source, destination, operation_type in migration_plan:
            try:
                source_path = Path(source)
                dest_path = Path(destination)
                
                if not source_path.exists():
                    print(f"⚠️  Source not found: {source}")
                    continue
                
                if dry_run:
                    print(f"[DRY RUN] Would move: {source} → {destination}")
                else:
                    # Create destination directory
                    if operation_type == "openapi":
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source_path), str(dest_path))
                        print(f"📄 Moved OpenAPI: {source_path.name} → {dest_path}")
                    elif operation_type == "postman_json":
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source_path), str(dest_path))
                        print(f"📦 Moved JSON dir: {source_path.name} → {dest_path}")
                    
                    results["moved"] += 1
                    
            except Exception as e:
                print(f"❌ Error migrating {source}: {e}")
                results["errors"] += 1
        
        return results
    
    def create_backward_compatibility_links(self, dry_run: bool = False):
        """Create symlinks for backward compatibility (optional)."""
        print(f"🔗 {'[DRY RUN]' if dry_run else ''} Creating backward compatibility links...")
        
        # This is optional - create symlinks from old flat structure to new nested structure
        # Implementation depends on requirements
        pass
    
    def validate_migration(self) -> bool:
        """Validate that the migration was successful."""
        print("✅ Validating migration...")
        
        # Check if files are in expected nested locations
        unified_mapping = self.method_mapper.create_unified_mapping()
        validation_passed = True
        
        for version in ["v1", "v2"]:
            if version not in unified_mapping:
                continue
                
            methods = unified_mapping[version]
            for method_name, mapping in methods.items():
                if not mapping.has_mdx:
                    continue
                    
                path_mapping = self.path_mapper.get_method_path_mapping(
                    method_name, mapping.mdx_path, version
                )
                
                # Check if OpenAPI file exists in nested location
                if mapping.has_yaml:
                    nested_openapi = self.base_path / path_mapping.openapi_path
                    if not nested_openapi.exists():
                        print(f"❌ Missing OpenAPI: {path_mapping.openapi_path}")
                        validation_passed = False
                
                # Check if JSON directory exists in nested location
                if mapping.has_json:
                    nested_json = self.base_path / path_mapping.postman_json_path
                    if not nested_json.exists():
                        print(f"❌ Missing JSON: {path_mapping.postman_json_path}")
                        validation_passed = False
        
        if validation_passed:
            print("✅ Migration validation passed!")
        else:
            print("❌ Migration validation failed!")
            
        return validation_passed
    
    def rollback_migration(self, dry_run: bool = False) -> bool:
        """Rollback to flat structure if needed."""
        print(f"⏪ {'[DRY RUN]' if dry_run else ''} Rolling back to flat structure...")
        
        # This would reverse the migration
        # Implementation depends on backup strategy
        print("⚠️  Rollback not implemented - use git to restore previous state")
        return False

def main():
    parser = argparse.ArgumentParser(description="Migrate KDF structure from flat to nested")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--analyze', action='store_true', help='Analyze current structure')
    group.add_argument('--plan', action='store_true', help='Plan migration (dry run)')
    group.add_argument('--migrate', action='store_true', help='Execute migration')
    group.add_argument('--validate', action='store_true', help='Validate migration results')
    group.add_argument('--rollback', action='store_true', help='Rollback migration')
    
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    
    args = parser.parse_args()
    
    migrator = StructureMigrator()
    
    if args.analyze:
        structure = migrator.analyze_current_structure()
        print("\n📊 Current Structure Analysis:")
        for category, versions in structure.items():
            print(f"\n{category.upper()}:")
            for version, files in versions.items():
                print(f"  {version}: {len(files)} files")
                if files and len(files) <= 5:  # Show first few files as examples
                    for file in files[:3]:
                        print(f"    - {file}")
                    if len(files) > 3:
                        print(f"    ... and {len(files) - 3} more")
    
    elif args.plan:
        migration_plan = migrator.plan_migration()
        print(f"\n📋 Migration Plan ({len(migration_plan)} operations):")
        for source, dest, op_type in migration_plan[:10]:  # Show first 10
            print(f"  {op_type}: {Path(source).name} → {Path(dest)}")
        if len(migration_plan) > 10:
            print(f"  ... and {len(migration_plan) - 10} more operations")
    
    elif args.migrate:
        migration_plan = migrator.plan_migration()
        results = migrator.execute_migration(migration_plan, dry_run=args.dry_run)
        print(f"\n📊 Migration Results:")
        print(f"  ✅ Moved: {results['moved']}")
        print(f"  📁 Created directories: {results['created_dirs']}")
        print(f"  ❌ Errors: {results['errors']}")
        
        if not args.dry_run and results['errors'] == 0:
            migrator.validate_migration()
    
    elif args.validate:
        migrator.validate_migration()
    
    elif args.rollback:
        migrator.rollback_migration(dry_run=args.dry_run)

if __name__ == "__main__":
    main() 