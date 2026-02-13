"""
Deprecated: This module has been renamed to 'spirit_safe'.

Please update imports to use gkc.spirit_safe instead.
"""

# Re-export from spirit_safe for backwards compatibility during migration
from gkc.spirit_safe import (
    SpiritSafeValidationError,
    SpiritSafeValidator,
)

__all__ = [
    "SpiritSafeValidator",
    "SpiritSafeValidationError",
]
