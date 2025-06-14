#!/usr/bin/env python3
"""
Method Name Normalizer

Simplified method name normalizer that delegates to centralized functions.
This provides backward compatibility while using the consolidated utilities.
"""

from typing import List, Optional, Dict
from functools import lru_cache

from ..core.logging_utils import get_logger
from ..utils.string_utils import (
    normalize_method_name, normalize_method_name_variations,
    convert_filesystem_to_api_format, convert_api_to_filesystem_format,
    extract_base_method, extract_operation, is_valid_method_name,
    clean_method_name
)


class MethodNameNormalizer:
    """
    Simplified method name normalizer using centralized utilities.
    
    Provides backward compatibility for existing code while delegating
    to the consolidated normalization functions in utils.string_utils.
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
    
    def generate_method_variations(self, method_name: str) -> List[str]:
        """
        Generate normalized variations of a method name for matching.
        
        Args:
            method_name: The method name to normalize
            
        Returns:
            List of normalized variations
        """
        return normalize_method_name_variations(method_name)
    
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
            self._match_stats['direct_matches'] += 1
            return mapping_dict[method_name]
        
        # Try variations
        variations = self.generate_method_variations(method_name)
        for variation in variations:
            if variation in mapping_dict:
                self._match_stats['variation_matches'] += 1
                return mapping_dict[variation]
        
        # Fuzzy matching as last resort
        fuzzy_match = self._fuzzy_match(method_name, mapping_dict)
        if fuzzy_match:
            self._match_stats['fuzzy_matches'] += 1
            return mapping_dict[fuzzy_match]
        
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
    
    # Delegate to centralized functions
    def convert_filesystem_to_api_format(self, method_name: str) -> str:
        """Convert filesystem-safe method name to API format."""
        return convert_filesystem_to_api_format(method_name)
    
    def convert_api_to_filesystem_format(self, method_name: str) -> str:
        """Convert API format method name to filesystem-safe format."""
        return convert_api_to_filesystem_format(method_name)
    
    def convert_filesystem_to_canonical_format(self, method_name: str) -> str:
        """Convert filesystem-safe method name back to canonical API format."""
        # This is the same as convert_filesystem_to_api_format
        return convert_filesystem_to_api_format(method_name)
    
    def is_valid_method_name(self, method_name: str) -> bool:
        """Validate method name using centralized validation."""
        return is_valid_method_name(method_name)
    
    def extract_base_method(self, method_name: str) -> str:
        """Extract the base method name (without operation suffix)."""
        return extract_base_method(method_name)
    
    def extract_operation(self, method_name: str) -> Optional[str]:
        """Extract the operation suffix from a method name."""
        return extract_operation(method_name)
    
    def get_normalization_stats(self) -> Dict[str, int]:
        """Get statistics about normalization cache usage."""
        # Return empty stats since we don't have caching at this level
        return {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_size': 0,
            'cache_max_size': 0
        }
    
    def clear_cache(self) -> None:
        """Clear the normalization cache (no-op in simplified version)."""
        self.logger.debug("Method normalization cache cleared (no-op)")
    
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