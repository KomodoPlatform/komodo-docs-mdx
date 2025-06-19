from typing import Dict

def sort_version_method_counts(version_counts: Dict[str, int]) -> Dict[str, int]:
    """
    Sorts a dictionary of version method counts alphabetically by version 
    and ensures the 'all' key is present and calculated.

    Args:
        version_counts: A dictionary where keys are version strings and 
                        values are method counts.

    Returns:
        A new dictionary with sorted version counts and a calculated 'all' key.
    """
    if 'all' not in version_counts:
        version_counts['all'] = sum(v for k, v in version_counts.items() if k != 'all')
    
    return dict(sorted(version_counts.items())) 