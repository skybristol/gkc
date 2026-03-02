"""
Entity JSON Schema validators and completeness checkers.

This package provides validation infrastructure for GKC Entity JSON objects,
including schema compliance checking and completeness calculation.
"""

from gkc.profiles.validators.entity_json_validator import (
    CompletenessInfo,
    EntityJSONValidationResult,
    EntityJSONValidator,
    ValidationIssue,
)

__all__ = [
    "EntityJSONValidator",
    "EntityJSONValidationResult",
    "CompletenessInfo",
    "ValidationIssue",
]
