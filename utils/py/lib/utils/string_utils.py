"""
String Utilities

Consolidated string manipulation and method name conversion functions.
These utilities handle method name normalization, formatting, and path generation.
"""

import re
from typing import Tuple, Optional, List, Dict, Pattern
from functools import lru_cache


# =============================================================================
# METHOD NAME CONVERSIONS
# =============================================================================

def convert_dir_to_method_name(directory_name: str) -> str:
    """
    Convert directory name to method name format.
    
    Args:
        directory_name: Directory name (e.g., "task-enable-eth-init")
        
    Returns:
        Method name (e.g., "task::enable_eth::init")
    """
    # Replace hyphens with double colons, but handle underscores specially
    if "task-enable-" in directory_name:
        # Special handling for task methods
        parts = directory_name.split("-")
        if len(parts) >= 3:
            # Convert task-enable-eth-init to task::enable_eth::init
            method_parts = [parts[0], f"{parts[1]}_{parts[2]}"]
            if len(parts) > 3:
                method_parts.extend(parts[3:])
            return "::".join(method_parts)
    
    return directory_name.replace("-", "::")


def convert_method_to_dir_name(method_name: str) -> str:
    """
    Convert method name to directory name format.
    
    Args:
        method_name: Method name (e.g., "task::enable_eth::init")
        
    Returns:
        Directory name (e.g., "task-enable-eth-init")
    """
    # Handle special cases first
    if method_name == "task::enable_z_coin":
        return "task-enable-z-coin"
    elif method_name.startswith("task::enable_"):
        # Convert task::enable_eth to task-enable-eth
        return method_name.replace("::", "-").replace("_", "-")
    
    return method_name.replace("::", "-")


def format_method_name_for_display(method_name: str) -> str:
    """
    Format method name for human-readable display.
    
    Args:
        method_name: Raw method name
        
    Returns:
        Formatted method name for display
    """
    # Split on :: and capitalize each part
    parts = method_name.split("::")
    formatted_parts = []
    
    for part in parts:
        # Handle underscores
        if "_" in part:
            words = part.split("_")
            formatted_part = " ".join(word.capitalize() for word in words)
        else:
            formatted_part = part.capitalize()
        
        formatted_parts.append(formatted_part)
    
    return " → ".join(formatted_parts)


# =============================================================================
# NORMALIZATION FUNCTIONS (CONSOLIDATED)
# =============================================================================

def normalize_method_name(method_name: str) -> str:
    """
    Normalize method name to consistent format (simple version).
    
    Args:
        method_name: Method name in any format
        
    Returns:
        Normalized method name
    """
    # Remove extra whitespace and convert to lowercase
    normalized = method_name.strip().lower()
    
    # Convert various separators to double colon
    normalized = normalized.replace("-", "::")
    normalized = normalized.replace("_", "::")
    normalized = normalized.replace("/", "::")
    
    # Handle multiple colons
    while "::::" in normalized:
        normalized = normalized.replace("::::", "::")
    
    return normalized


def normalize_method_name_variations(method_name: str) -> List[str]:
    """
    Generate multiple normalized variations of a method name for matching.
    
    Args:
        method_name: The method name to normalize
        
    Returns:
        List of normalized variations
    """
    if not method_name:
        return []
    
    variations = {method_name}  # Always include original
    
    # Clean the method name
    cleaned = clean_method_name(method_name)
    if cleaned and cleaned != method_name:
        variations.add(cleaned)
    
    # Generate format variations (:: vs -)
    variations.update(_generate_format_variations(cleaned))
    
    # Generate prefix variations
    variations.update(_generate_prefix_variations(cleaned))
    
    # Generate special case variations
    variations.update(_generate_special_variations(cleaned))
    
    return list(variations)


def _generate_format_variations(method_name: str) -> set:
    """Generate format variations (:: vs -)."""
    variations = set()
    
    # Convert :: to -
    if '::' in method_name:
        dash_version = method_name.replace('::', '-')
        variations.add(dash_version)
        
        # Also try single colon
        single_colon = method_name.replace('::', ':')
        variations.add(single_colon)
    
    # Convert - to ::
    elif '-' in method_name and not method_name.startswith(('http-', 'https-')):
        colon_version = method_name.replace('-', '::')
        variations.add(colon_version)
        
        # Also try single colon
        single_colon = method_name.replace('-', ':')
        variations.add(single_colon)
    
    return variations


def _generate_prefix_variations(method_name: str) -> set:
    """Generate variations for known prefixes."""
    variations = set()
    
    prefix_mappings = {
        'task': ['task', 'task::'],
        'lightning': ['lightning', 'lightning::'],
        'stream': ['stream', 'stream::'],
        'gui_storage': ['gui_storage', 'gui_storage::'],
        'experimental': ['experimental', 'experimental::']
    }
    
    for prefix, formats in prefix_mappings.items():
        if method_name.startswith(prefix):
            base_name = method_name[len(prefix):].lstrip('-:')
            
            for fmt in formats:
                if fmt.endswith(('-', '::')):
                    variations.add(f"{fmt}{base_name}")
                else:
                    variations.add(f"{fmt}::{base_name}")
                    variations.add(f"{fmt}-{base_name}")
    
    return variations


def _generate_special_variations(method_name: str) -> set:
    """Generate special case variations."""
    variations = set()
    
    # Add enable-specific variations
    variations.update(_generate_enable_variations(method_name))
    
    # Add version-specific variations
    if 'v1' in method_name or 'v2' in method_name:
        base = method_name.replace('v1', '').replace('v2', '').strip('-:')
        if base:
            variations.add(base)
    
    return variations


def _generate_enable_variations(method_name: str) -> set:
    """Generate variations for enable methods."""
    variations = set()
    
    enable_patterns = [
        'enable_', 'enable-', 'enable::'
    ]
    
    for pattern in enable_patterns:
        if pattern in method_name:
            # Create variations with different separators
            base = method_name.replace(pattern, '')
            variations.add(f"enable::{base}")
            variations.add(f"enable-{base}")
            variations.add(f"enable_{base}")
    
    return variations


# =============================================================================
# CONVERSION FUNCTIONS
# =============================================================================

def convert_filesystem_to_api_format(method_name: str) -> str:
    """
    Convert filesystem-safe method name to API format.
    
    Args:
        method_name: Filesystem-safe method name
        
    Returns:
        API format method name
    """
    if not method_name:
        return method_name
    
    # Convert hyphens to double colons for API format
    return method_name.replace('-', '::')


def convert_api_to_filesystem_format(method_name: str) -> str:
    """
    Convert API format method name to filesystem-safe format.
    
    Args:
        method_name: API format method name
        
    Returns:
        Filesystem-safe method name
    """
    if not method_name:
        return method_name
    
    # Convert double colons to hyphens for filesystem safety
    return method_name.replace('::', '-')


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_method_parts(method_name: str) -> List[str]:
    """
    Extract method name parts split by double colon.
    
    Args:
        method_name: Method name with :: separators
        
    Returns:
        List of method parts
    """
    if not method_name:
        return []
    
    return [part.strip() for part in method_name.split('::') if part.strip()]


def join_method_parts(parts: List[str]) -> str:
    """
    Join method parts with double colon separator.
    
    Args:
        parts: List of method parts
        
    Returns:
        Joined method name
    """
    return '::'.join(part.strip() for part in parts if part.strip())


def extract_base_method(method_name: str) -> str:
    """Extract the base method name (without operation suffix)."""
    if not method_name:
        return ""
    
    # Try structured patterns first
    patterns = [
        re.compile(r'^task[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^stream[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^lightning[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE)
    ]
    
    pattern_names = ['task', 'stream', 'lightning']
    
    for i, pattern in enumerate(patterns):
        match = pattern.match(method_name)
        if match and match.group(1):
            return f"{pattern_names[i]}::{match.group(1)}"
    
    # Fallback to simple splitting
    parts = re.split(r'[::-]', method_name)
    if len(parts) > 2:
        return '::'.join(parts[:-1])
    
    return method_name


def extract_operation(method_name: str) -> Optional[str]:
    """Extract the operation suffix from a method name."""
    if not method_name:
        return None
    
    # Try structured patterns first
    patterns = [
        re.compile(r'^task[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^stream[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
        re.compile(r'^lightning[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE)
    ]
    
    for pattern in patterns:
        match = pattern.match(method_name)
        if match and len(match.groups()) > 1 and match.group(2):
            return match.group(2)
    
    # Fallback to simple splitting
    parts = re.split(r'[::-]', method_name)
    if len(parts) > 2:
        return parts[-1]
    
    return None


# =============================================================================
# PATH AND CATEGORY FUNCTIONS
# =============================================================================

def generate_api_path(method_name: str, version: str = "v2") -> str:
    """
    Generate API path from method name.
    
    Args:
        method_name: Method name
        version: API version
        
    Returns:
        API path
    """
    return f"/{version}/{method_name.replace('::', '/')}"


def extract_category_from_method(method_name: str) -> Tuple[str, Optional[str]]:
    """
    Extract category and subcategory from method name.
    
    Args:
        method_name: Method name
        
    Returns:
        Tuple of (category, subcategory)
    """
    parts = extract_method_parts(method_name)
    
    if not parts:
        return "general", None
    
    if len(parts) == 1:
        return parts[0], None
    
    return parts[0], parts[1] if len(parts) > 1 else None


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def is_valid_method_name(method_name: str) -> bool:
    """
    Validate method name format.
    
    Args:
        method_name: Method name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not method_name:
        return False
    
    method_name = method_name.strip()
    
    # Basic validation rules
    if (len(method_name) < 2 or
        method_name in [':', '::', ':::', '', '/', '\\', '-', '_'] or
        method_name.startswith(':') or method_name.endswith(':') or
        not any(c.isalpha() for c in method_name)):
        return False
    
    # Check for valid characters (letters, numbers, colons, hyphens, underscores, dots)
    valid_chars = re.compile(r'^[a-zA-Z0-9_:.-]+$')
    if not valid_chars.match(method_name):
        return False
    
    return True


def clean_method_name(method_name: str) -> str:
    """
    Clean method name by removing invalid characters and formatting.
    
    Args:
        method_name: Raw method name
        
    Returns:
        Cleaned method name
    """
    if not method_name:
        return ""
    
    # Remove leading/trailing whitespace
    cleaned = method_name.strip()
    
    # Remove or replace invalid characters
    cleaned = re.sub(r'[^\w\s:.-]', '', cleaned)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', '_', cleaned)
    
    # Remove leading/trailing separators
    cleaned = re.sub(r'^[_:.-]+|[_:.-]+$', '', cleaned)
    
    # Normalize multiple separators
    cleaned = re.sub(r'[_:.-]{2,}', '::', cleaned)
    
    return cleaned


# =============================================================================
# MDX AND YAML EXTRACTION FUNCTIONS (CONSOLIDATED)
# =============================================================================

def extract_method_name_from_mdx_content(content: str) -> Optional[str]:
    """
    Extract method name from MDX content using standardized pattern.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        content: MDX file content
        
    Returns:
        Method name if found, None otherwise
    """
    # Look for method heading pattern (##\s+method_name\s*{{)
    method_pattern = r'##\s+([a-zA-Z0-9_:.-]+)\s*\{\{'
    match = re.search(method_pattern, content)
    
    if match:
        return match.group(1).strip()
    
    return None


def extract_method_name_from_yaml_filename(filename: str, version: str) -> Optional[str]:
    """
    Extract method name from YAML filename using standardized conversion.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        filename: YAML filename
        version: API version (v1 or v2)
        
    Returns:
        Method name if valid, None otherwise
    """
    # Remove extension
    name = filename.replace('.yaml', '').replace('.yml', '')
    
    # Convert to method format based on version
    if version == 'v1':
        return name
    elif version == 'v2':
        # Convert dashes to double colons for v2
        return name.replace('-', '::')
    
    return name


def extract_methods_from_mdx_codeblocks(content: str, is_legacy: bool = False) -> Tuple[List[str], List[str]]:
    """
    Extract method names from MDX CodeGroup blocks.
    
    This consolidates the duplicate implementations across the codebase.
    
    Args:
        content: MDX file content
        is_legacy: Whether this is a legacy API file
        
    Returns:
        Tuple of (v1_methods, v2_methods)
    """
    v1_methods = []
    v2_methods = []
    
    # Find all CodeGroup blocks
    codegroups = re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)
    
    for block in codegroups:
        # Extract code blocks from within CodeGroup
        code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
        
        for code in code_blocks:
            # Look for method field in JSON
            method_match = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
            if method_match:
                method = method_match.group(1)
                
                if is_legacy:
                    v1_methods.append(method)
                elif '"mmrpc": "2.0"' in code:
                    v2_methods.append(method)
                else:
                    v1_methods.append(method)
    
    return sorted(list(set(v1_methods))), sorted(list(set(v2_methods)))


# =============================================================================
# TEXT FORMATTING FUNCTIONS
# =============================================================================

def camel_case_to_snake_case(text: str) -> str:
    """
    Convert camelCase text to snake_case.
    
    Args:
        text: CamelCase text
        
    Returns:
        snake_case text
    """
    # Insert underscore before uppercase letters
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
    return snake_case.lower()


def snake_case_to_camel_case(text: str, capitalize_first: bool = False) -> str:
    """
    Convert snake_case text to camelCase.
    
    Args:
        text: snake_case text
        capitalize_first: Whether to capitalize the first letter
        
    Returns:
        camelCase text
    """
    components = text.split('_')
    if capitalize_first:
        return ''.join(word.capitalize() for word in components)
    else:
        return components[0] + ''.join(word.capitalize() for word in components[1:])


def title_case_with_exceptions(text: str, exceptions: List[str] = None) -> str:
    """
    Convert text to title case with exceptions for specific words.
    
    Args:
        text: Text to convert
        exceptions: List of words to keep lowercase
        
    Returns:
        Title-cased text
    """
    if exceptions is None:
        exceptions = ['and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'of', 'in']
    
    words = text.split()
    title_words = []
    
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in exceptions:
            title_words.append(word.capitalize())
        else:
            title_words.append(word.lower())
    
    return ' '.join(title_words)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix 