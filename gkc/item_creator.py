"""
Deprecated: This module has been renamed to 'bottler'.

This file provides backwards compatibility during terminology refactoring.
Please update imports to use gkc.bottler instead.

Example:
    Old: from gkc.item_creator import PropertyMapper
    New: from gkc.bottler import Distillate
"""

# Re-export everything from bottler
from gkc.bottler import (
    ClaimBuilder,
    DataTypeTransformer,
    Distillate,
    SnakBuilder,
)

# Deprecated aliases
PropertyMapper = Distillate

__all__ = [
    "PropertyMapper",
    "DataTypeTransformer",
    "SnakBuilder",
    "ClaimBuilder",
    "Distillate",
]
