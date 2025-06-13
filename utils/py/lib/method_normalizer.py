#!/usr/bin/env python3
"""
Method Name Normalizer

Enhanced method name normalization with regex patterns for better performance.
Handles conversion between different naming formats with improved pattern matching.
"""

import re
from typing import List, Optional, Dict, Pattern
from functools import lru_cache

from .logging_utils import get_logger


class MethodNameNormalizer:
    """
    Enhanced method name normalizer using compiled regex patterns.
    
    Provides fast, consistent normalization and variation generation
    for API method names across different formats.
    """
    
    def __init__(self):
        self.logger = get_logger("method-normalizer")
        self._debug_mode = False
        self._match_stats = {
            'direct_matches': 0,
            'variation_matches': 0,
            'fuzzy_matches': 0,
            'no_matches': 0
        }
        
        # Compile regex patterns for performance
        self._patterns = self._compile_patterns()
        
        # Define prefix mappings for different method types
        self.prefix_mappings = {
            'task': ['task', 'task::'],
            'lightning': ['lightning', 'lightning::'],
            'stream': ['stream', 'stream::'],
            'gui_storage': ['gui_storage', 'gui_storage::'],
            'experimental': ['experimental', 'experimental::']
        }
    
    def _compile_patterns(self) -> Dict[str, Pattern]:
        """Compile regex patterns for method name processing."""
        return {
            # Basic format patterns
            'colon_notation': re.compile(r'::'),
            'dash_notation': re.compile(r'-'),
            
            # Method structure patterns
            'task_pattern': re.compile(r'^task[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
            'stream_pattern': re.compile(r'^stream[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
            'lightning_pattern': re.compile(r'^lightning[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
            'experimental_pattern': re.compile(r'^experimental[-:]?:?([^-:]+)[-:]?:?(.+)?$', re.IGNORECASE),
            
            # Validation patterns
            'valid_method': re.compile(r'^[a-zA-Z0-9_:.-]+$'),
            'invalid_chars': re.compile(r'[^a-zA-Z0-9_:.-]'),
            
            # Cleanup patterns
            'multiple_separators': re.compile(r'[-:]{2,}'),
            'leading_trailing': re.compile(r'^[-:]+|[-:]+$'),
            
            # Special cases
            'duplicate_segments': re.compile(r'\b(\w+)[-:]\1\b'),
            'version_suffix': re.compile(r'[-:]?v?\d+$', re.IGNORECASE)
        }
    
    @lru_cache(maxsize=1000)
    def normalize_method_name(self, method_name: str) -> List[str]:
        """
        Generate normalized variations of a method name for matching.
        
        Args:
            method_name: The method name to normalize
            
        Returns:
            List of normalized variations
        """
        if not method_name:
            return []
        
        variations = {method_name}  # Always include original
        
        # Clean the method name
        cleaned = self._clean_method_name(method_name)
        if cleaned and cleaned != method_name:
            variations.add(cleaned)
        
        # Generate format variations (:: vs -)
        variations.update(self._generate_format_variations(cleaned))
        
        # Generate prefix variations
        variations.update(self._generate_prefix_variations(cleaned))
        
        # Generate special case variations
        variations.update(self._generate_special_variations(cleaned))
        
        result = list(variations)
        # Only log debug info if explicitly requested (not during normal operations)
        if hasattr(self, '_debug_mode') and self._debug_mode:
            self.logger.debug(f"Generated {len(result)} variations for '{method_name}'")
        return result
    
    def _clean_method_name(self, method_name: str) -> str:
        """Clean and standardize method name format."""
        if not method_name:
            return ""
        
        # Remove invalid characters
        cleaned = self._patterns['invalid_chars'].sub('', method_name.strip())
        
        # Normalize multiple separators
        cleaned = self._patterns['multiple_separators'].sub('::', cleaned)
        
        # Remove leading/trailing separators
        cleaned = self._patterns['leading_trailing'].sub('', cleaned)
        
        return cleaned.lower()
    
    def _generate_format_variations(self, method_name: str) -> set:
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
    
    def _generate_prefix_variations(self, method_name: str) -> set:
        """Generate variations for known prefixes."""
        variations = set()
        
        for prefix, formats in self.prefix_mappings.items():
            if method_name.startswith(prefix):
                base_name = method_name[len(prefix):].lstrip('-:')
                
                for fmt in formats:
                    if fmt.endswith(('-', '::')):
                        variations.add(f"{fmt}{base_name}")
                    else:
                        variations.add(f"{fmt}::{base_name}")
                        variations.add(f"{fmt}-{base_name}")
        
        return variations
    
    def _generate_special_variations(self, method_name: str) -> set:
        """Generate special case variations."""
        variations = set()
        
        # Handle duplicate segments (e.g., "method::method" -> "method")
        deduplicated = self._patterns['duplicate_segments'].sub(r'\1', method_name)
        if deduplicated != method_name:
            variations.add(deduplicated)
        
        # Handle version suffixes
        without_version = self._patterns['version_suffix'].sub('', method_name)
        if without_version != method_name:
            variations.add(without_version)
        
        # Handle enable patterns specifically
        variations.update(self._generate_enable_variations(method_name))
        
        return variations
    
    def _generate_enable_variations(self, method_name: str) -> set:
        """Generate variations for enable-related methods."""
        variations = set()
        
        # Task enable patterns
        task_match = self._patterns['task_pattern'].match(method_name)
        if task_match and task_match.group(1) and 'enable' in task_match.group(1):
            groups = task_match.groups()
            base = groups[0] if groups[0] else ''
            suffix = groups[1] if len(groups) > 1 and groups[1] else ''
            
            # Generate different combinations
            if suffix:
                variations.add(f"task::enable_{base}::{suffix}")
                variations.add(f"task-enable-{base}-{suffix}")
                variations.add(f"enable_{base}::{suffix}")
            else:
                variations.add(f"task::enable_{base}")
                variations.add(f"task-enable-{base}")
                variations.add(f"enable_{base}")
        
        return variations
    
    def find_best_match(self, method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
        """
        Find the best match for a method name in a mapping dictionary.
        
        Args:
            method_name: The method name to search for
            mapping_dict: Dictionary to search in
            
        Returns:
            The matched value or None if no match found
        """
        if not method_name or not mapping_dict:
            return None
        
        # Direct match first (fastest)
        if method_name in mapping_dict:
            # Only log debug info if explicitly requested
            if hasattr(self, '_debug_mode') and self._debug_mode:
                self.logger.debug(f"Direct match found for '{method_name}'")
            self._match_stats['direct_matches'] += 1
            return mapping_dict[method_name]
        
        # Try variations
        variations = self.normalize_method_name(method_name)
        for variation in variations:
            if variation in mapping_dict:
                # Only log debug info if explicitly requested
                if hasattr(self, '_debug_mode') and self._debug_mode:
                    self.logger.debug(f"Variation match: '{method_name}' -> '{variation}'")
                self._match_stats['variation_matches'] += 1
                return mapping_dict[variation]
        
        # Fuzzy matching as last resort
        fuzzy_match = self._fuzzy_match(method_name, mapping_dict)
        if fuzzy_match:
            # Only log debug info if explicitly requested
            if hasattr(self, '_debug_mode') and self._debug_mode:
                self.logger.debug(f"Fuzzy match: '{method_name}' -> '{fuzzy_match}'")
            self._match_stats['fuzzy_matches'] += 1
            return mapping_dict[fuzzy_match]
        
        # Only log debug info if explicitly requested
        if hasattr(self, '_debug_mode') and self._debug_mode:
            self.logger.debug(f"No match found for '{method_name}'")
        self._match_stats['no_matches'] += 1
        return None
    
    def _fuzzy_match(self, method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
        """Perform fuzzy matching using edit distance."""
        if not method_name:
            return None
        
        best_match = None
        best_score = float('inf')
        threshold = len(method_name) // 3  # Allow up to 1/3 character differences
        
        for key in mapping_dict.keys():
            if abs(len(key) - len(method_name)) > threshold:
                continue
            
            score = self._levenshtein_distance(method_name.lower(), key.lower())
            if score < best_score and score <= threshold:
                best_score = score
                best_match = key
        
        return best_match
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def convert_filesystem_to_api_format(self, method_name: str) -> str:
        """Convert filesystem-safe method name to API format."""
        if not method_name:
            return method_name
        
        # Use regex patterns for conversion
        if self._patterns['colon_notation'].search(method_name):
            return method_name  # Already in API format
        
        # Convert dashes to double colons for known patterns
        for prefix in self.prefix_mappings.keys():
            if method_name.startswith(f"{prefix}-"):
                return method_name.replace('-', '::')
        
        # General conversion for multi-segment names
        if method_name.count('-') >= 2:
            return method_name.replace('-', '::')
        
        return method_name
    
    def convert_api_to_filesystem_format(self, method_name: str) -> str:
        """Convert API format method name to filesystem-safe format."""
        if not method_name:
            return method_name
        
        return self._patterns['colon_notation'].sub('-', method_name)
    
    def convert_filesystem_to_canonical_format(self, method_name: str) -> str:
        """Convert filesystem-safe method name back to canonical API format."""
        if not method_name:
            return method_name
        
        # If it already contains double colons, it's already in canonical format
        if '::' in method_name:
            return method_name
        
        # Convert dashes to double colons for known structured patterns
        for prefix in self.prefix_mappings.keys():
            if method_name.startswith(f"{prefix}-"):
                return method_name.replace('-', '::')
        
        # General conversion for multi-segment names (3+ segments with dashes)
        if method_name.count('-') >= 2:
            return method_name.replace('-', '::')
        
        return method_name
    
    def is_valid_method_name(self, method_name: str) -> bool:
        """Validate method name using regex patterns."""
        if not method_name or len(method_name.strip()) < 2:
            return False
        
        method_name = method_name.strip()
        
        # Check for valid characters
        if not self._patterns['valid_method'].match(method_name):
            return False
        
        # Check for reasonable structure
        if (method_name.startswith(('::', '--', '__')) or 
            method_name.endswith(('::', '--', '__')) or
            not any(c.isalpha() for c in method_name)):
            return False
        
        return True
    
    def extract_base_method(self, method_name: str) -> str:
        """Extract the base method name (without operation suffix)."""
        if not method_name:
            return ""
        
        # Try structured patterns first
        for pattern_name in ['task_pattern', 'stream_pattern', 'lightning_pattern']:
            match = self._patterns[pattern_name].match(method_name)
            if match and match.group(1):
                return f"{pattern_name.split('_')[0]}::{match.group(1)}"
        
        # Fallback to simple splitting
        parts = re.split(r'[::-]', method_name)
        if len(parts) > 2:
            return '::'.join(parts[:-1])
        
        return method_name
    
    def extract_operation(self, method_name: str) -> Optional[str]:
        """Extract the operation suffix from a method name."""
        if not method_name:
            return None
        
        # Try structured patterns first
        for pattern_name in ['task_pattern', 'stream_pattern', 'lightning_pattern']:
            match = self._patterns[pattern_name].match(method_name)
            if match and len(match.groups()) > 1 and match.group(2):
                return match.group(2)
        
        # Fallback to simple splitting
        parts = re.split(r'[::-]', method_name)
        if len(parts) > 2:
            return parts[-1]
        
        return None
    
    def get_normalization_stats(self) -> Dict[str, int]:
        """Get statistics about normalization cache usage."""
        cache_info = self.normalize_method_name.cache_info()
        return {
            'cache_hits': cache_info.hits,
            'cache_misses': cache_info.misses,
            'cache_size': cache_info.currsize,
            'cache_max_size': cache_info.maxsize
        }
    
    def clear_cache(self) -> None:
        """Clear the normalization cache."""
        self.normalize_method_name.cache_clear()
        self.logger.debug("Method normalization cache cleared")
    
    def enable_debug_mode(self, enabled: bool = True):
        """Enable or disable debug mode for verbose logging."""
        self._debug_mode = enabled
        if enabled:
            self.logger.info("🔍 Method normalizer debug mode enabled")
    
    def get_match_stats(self) -> Dict[str, int]:
        """Get statistics about matching operations."""
        return self._match_stats.copy()
    
    def reset_stats(self):
        """Reset match statistics."""
        self._match_stats = {
            'direct_matches': 0,
            'variation_matches': 0,
            'fuzzy_matches': 0,
            'no_matches': 0
        } 