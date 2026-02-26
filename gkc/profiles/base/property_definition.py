"""Property Definition: Metadata about properties/claims/tags.

This module defines PropertyDefinition, which captures metadata about properties
across platforms (Wikidata properties, OSM tags, etc.) including validation rules,
required qualifiers, and references.

PropertyDefinitions are built pragmatically as we encounter properties in entity
introspection. They form the basis of a future property meta-registry.

Plain meaning: The blueprint for what a property looks like and how to use it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PropertyDefinition(BaseModel):
    """Define metadata and validation rules for a property/claim/tag.

    Properties in linked data platforms like Wikidata are compound structures
    that may have required qualifiers and references. The same property (e.g.,
    P31 "instance of") may have different requirements depending on the context
    of the entity profile it's used in.

    PropertyDefinition captures:
    - Basic metadata (ID, label, description, datatype)
    - Required and optional qualifiers
    - Reference requirements
    - Validation constraints
    - Platform-specific details

    This is built pragmatically as we introspect entities and will eventually
    form a property meta-registry for the Spirit Safe.

    Plain meaning: Everything you need to know about using a property correctly.

    Example:
        >>> prop = PropertyDefinition(
        ...     property_id="P31",
        ...     label="instance of",
        ...     datatype="wikibase-item",
        ...     required_qualifiers=["P580"],  # start time
        ... )
    """

    property_id: str = Field(
        description="Platform-specific property identifier (e.g., 'P31', 'amenity')"
    )

    label: str = Field(
        default="",
        description="Human-readable label for this property",
    )

    description: str = Field(
        default="",
        description="Explanation of what this property represents",
    )

    datatype: str = Field(
        default="",
        description="Property datatype (e.g., 'wikibase-item', 'string', 'time')",
    )

    platform: str = Field(
        default="wikidata",
        description="Platform this property belongs to (wikidata, osm, etc.)",
    )

    required_qualifiers: list[str] = Field(
        default_factory=list,
        description="Property IDs of qualifiers that must be present",
    )

    optional_qualifiers: list[str] = Field(
        default_factory=list,
        description="Property IDs of qualifiers that may be present",
    )

    requires_references: bool = Field(
        default=False,
        description="Whether this property requires source references",
    )

    validation_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation constraints (format patterns, value ranges, etc.)",
    )

    context_notes: str = Field(
        default="",
        description="Context-specific guidance for using this property in a profile",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific metadata",
    )

    def to_dict(self) -> dict[str, Any]:
        """Export property definition as a dictionary.

        Returns:
            Dict representation suitable for serialization.

        Plain meaning: Convert to a plain dictionary.
        """
        return self.model_dump()

    def validate_value(self, value: Any) -> bool:
        """Validate that a value conforms to this property's requirements.

        Args:
            value: The value to validate

        Returns:
            True if valid, False otherwise

        Plain meaning: Check if a value is acceptable for this property.
        """
        # Base implementation - can be enhanced with specific validation logic
        return True
