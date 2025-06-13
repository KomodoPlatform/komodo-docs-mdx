#!/usr/bin/env python3
"""
Repository Integration Example

Demonstrates how to use the new KDFRepositoryScanner with other library components
to create comprehensive documentation validation and reporting.
"""

import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from lib import (
    KDFRepositoryScanner, UnifiedScanner, MethodMapper, PostmanCollectionGenerator,
    get_logger, setup_logging
)


def main():
    """Demonstrate repository scanner integration."""
    # Setup logging
    setup_logging(verbose=True)
    logger = get_logger("repo-integration-example")
    
    print("🚀 Repository Integration Example")
    print("=" * 50)
    print()
    
    # 1. Scan repository for latest methods
    print("1️⃣ Scanning KDF repository...")
    repo_scanner = KDFRepositoryScanner(verbose=True)
    repo_methods = repo_scanner.get_latest_methods(force_refresh=True)
    
    print(f"   Found methods in repository:")
    for version, methods in repo_methods.items():
        print(f"   {version.upper()}: {len(methods)} methods")
    print()
    
    # 2. Scan documentation
    print("2️⃣ Scanning documentation...")
    doc_scanner = UnifiedScanner(verbose=True)
    doc_results = doc_scanner.scan_all_files(['v1', 'v2'])
    
    # Extract documented methods
    doc_methods = {}
    for version, results in doc_results.items():
        mdx_methods = set(results.get('mdx_files', {}).keys())
        yaml_methods = set(results.get('yaml_files', {}).keys())
        json_methods = set(results.get('json_examples', {}).keys())
        
        all_methods = mdx_methods | yaml_methods | json_methods
        doc_methods[version] = sorted(list(all_methods))
        
        print(f"   {version.upper()}: {len(all_methods)} documented methods")
    print()
    
    # 3. Compare repository with documentation
    print("3️⃣ Comparing repository with documentation...")
    repo_info = repo_scanner.scan_repository_methods()
    comparison = repo_scanner.compare_with_documentation(repo_info, doc_methods)
    
    for version, results in comparison.items():
        coverage = results['coverage_percentage']
        print(f"   {version.upper()}: {coverage:.1f}% coverage")
        print(f"      Repository: {results['repo_count']} methods")
        print(f"      Documented: {results['doc_count']} methods")
        print(f"      Missing docs: {len(results['repo_only'])} methods")
        print(f"      Extra docs: {len(results['doc_only'])} methods")
    print()
    
    # 4. Generate detailed comparison report
    print("4️⃣ Generating detailed comparison report...")
    report = repo_scanner.generate_comparison_report(comparison)
    print(report)
    
    # 5. Check Postman collection coverage
    print("5️⃣ Checking Postman collection coverage...")
    postman_generator = PostmanCollectionGenerator(verbose=True)
    
    for version in ['v1', 'v2']:
        try:
            categorized_requests = postman_generator.scan_json_examples(version)
            postman_methods = set()
            
            for category_requests in categorized_requests.values():
                for request in category_requests:
                    postman_methods.add(request.method_name)
            
            repo_set = set(repo_methods.get(version, []))
            postman_coverage = (len(postman_methods & repo_set) / max(1, len(repo_set))) * 100
            
            print(f"   {version.upper()}: {postman_coverage:.1f}% Postman coverage")
            print(f"      Repository: {len(repo_set)} methods")
            print(f"      Postman examples: {len(postman_methods)} methods")
            
        except Exception as e:
            print(f"   {version.upper()}: Error checking Postman coverage: {e}")
    print()
    
    # 6. Create unified mapping with repository data
    print("6️⃣ Creating unified mapping with repository data...")
    try:
        mapper = MethodMapper(verbose=True)
        unified_mapping = mapper.create_unified_mapping()
        
        # Enhance mapping with repository information
        enhanced_mapping = {}
        for version, mapping in unified_mapping.items():
            enhanced_mapping[version] = {}
            repo_set = set(repo_methods.get(version, []))
            
            for method, info in mapping.items():
                enhanced_info = info.copy()
                enhanced_info['in_repository'] = method in repo_set
                enhanced_info['repository_verified'] = method in repo_set
                enhanced_mapping[version][method] = enhanced_info
            
            # Add repository-only methods
            for method in repo_set:
                if method not in mapping:
                    enhanced_mapping[version][method] = {
                        'in_repository': True,
                        'repository_verified': True,
                        'has_mdx': False,
                        'has_yaml': False,
                        'has_json': False,
                        'status': 'repository_only'
                    }
        
        # Save enhanced mapping
        output_file = Path("data") / "enhanced_method_mapping.json"
        from lib.shared_utils import safe_write_json, ensure_directory_exists
        ensure_directory_exists(output_file.parent)
        safe_write_json(output_file, enhanced_mapping, indent=2)
        
        print(f"   ✅ Enhanced mapping saved to: {output_file}")
        
    except Exception as e:
        print(f"   ❌ Error creating enhanced mapping: {e}")
    print()
    
    # 7. Summary and recommendations
    print("7️⃣ Summary and Recommendations")
    print("-" * 30)
    
    total_repo_methods = sum(len(methods) for methods in repo_methods.values())
    total_doc_methods = sum(len(methods) for methods in doc_methods.values())
    
    print(f"📊 Overall Statistics:")
    print(f"   Repository methods: {total_repo_methods}")
    print(f"   Documented methods: {total_doc_methods}")
    print(f"   Documentation coverage: {(total_doc_methods/max(1,total_repo_methods)*100):.1f}%")
    print()
    
    print("🎯 Recommendations:")
    
    # Find methods that need documentation
    for version, results in comparison.items():
        if results['repo_only']:
            print(f"   📝 {version.upper()}: Document {len(results['repo_only'])} missing methods")
            for method in results['repo_only'][:5]:  # Show first 5
                print(f"      - {method}")
            if len(results['repo_only']) > 5:
                print(f"      ... and {len(results['repo_only']) - 5} more")
    
    print()
    print("✅ Integration example completed!")


if __name__ == "__main__":
    main() 