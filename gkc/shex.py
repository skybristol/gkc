"""
Deprecated: This module has been renamed to 'spirit_safe'.

This file provides backwards compatibility during the terminology refactoring.
Please update imports to use gkc.spirit_safe instead.

Example:
    Old: from gkc.shex import ShExValidator
    New: from gkc.spirit_safe import SpiritSafeValidator
"""

# Re-export everything from spirit_safe
from gkc.spirit_safe import (
    SpiritSafeValidationError,
    SpiritSafeValidator,
)

# Deprecated aliases
ShExValidationError = SpiritSafeValidationError
ShExValidator = SpiritSafeValidator

__all__ = [
    "ShExValidator",
    "ShExValidationError",
    "SpiritSafeValidator",
    "SpiritSafeValidationError",
]

