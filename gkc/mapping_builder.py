"""
Deprecated: This module has been renamed to 'recipe'.

This file provides backwards compatibility during terminology refactoring.
Please update imports to use gkc.recipe instead.

Example:
    Old: from gkc.mapping_builder import ClaimsMapBuilder
    New: from gkc.recipe import RecipeBuilder
"""

# Re-export everything from recipe
from gkc.recipe import (
    PropertyCatalog,
    PropertyProfile,
    RecipeBuilder,
    SpecificationExtractor,
)

# Deprecated aliases
ClaimsMapBuilder = RecipeBuilder
PropertyInfo = PropertyProfile
ShExPropertyExtractor = SpecificationExtractor
WikidataPropertyFetcher = PropertyCatalog

__all__ = [
    "ClaimsMapBuilder",
    "PropertyInfo",
    "ShExPropertyExtractor",
    "WikidataPropertyFetcher",
    "RecipeBuilder",
    "PropertyProfile",
    "SpecificationExtractor",
    "PropertyCatalog",
]
