"""
GKC Entity Profiles: Canonical entity structures for the Global Knowledge Commons.

A GKC Entity Profile defines the canonical structure and meaning of an entity type
within the Global Knowledge Commons, independent of specific platform constraints.
It combines structure from Wikidata EntitySchemas (ShEx), Wikidata property definitions,
and cross-platform entity concepts into a unified, well-documented model.

Plain meaning: The canonical definition of what a particular kind of entity is.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class GKCEntityProfile(BaseModel):
    """
    GKC Entity Profile: Canonical entity structure for Global Knowledge Commons.

    Represents a single, unified type of entity across multiple Commons platforms.
    (E.g., "office held by head of government" in Wikidata, OSM, etc.).

    Plain meaning: The canonical shape and requirements for a particular kind of entity.

    Attributes:
        id: Unique identifier for this entity type in the GKC namespace
           (e.g., "office-held-by-head-of-government")
        source_eid: Optional Wikidata EntitySchema ID that inspired this profile
           (e.g., "E502" for tribe schemas)
        labels: Multilingual labels for this entity type
        descriptions: Multilingual descriptions
        aliases: Multilingual alternative names
        properties: List of property IDs (e.g., ["P1313", "P380", "P585"])
           that are valid/expected for this entity type
        classification_constraints: P31 and P279 constraints extracted from ShEx
        target_systems: List of target systems this entity maps to
           (e.g., ["wikidata", "osm", "wikipedia"])
    """

    id: str = Field(
        ...,
        description="Unique GKC entity identifier "
        "(e.g., 'office-held-by-head-of-government')",
        pattern=r"^[a-z0-9-]+$",
    )
    source_eid: Optional[str] = Field(
        None,
        description="Source Wikidata EntitySchema ID (e.g., 'E502')",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Multilingual labels for this entity type",
    )
    descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Multilingual descriptions",
    )
    aliases: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Multilingual aliases (lists of alternative names)",
    )
    properties: list[str] = Field(
        default_factory=list,
        description="Property IDs valid for this entity type (e.g., ['P31', 'P1313'])",
    )
    classification_constraints: dict[str, list[str]] = Field(
        default_factory=dict,
        description="P31 (instance of) and P279 (subclass of) constraints from ShEx",
    )
    target_systems: list[str] = Field(
        default_factory=lambda: ["wikidata"],
        description="Target systems this entity type maps to",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "office-held-by-head-of-government",
                "source_eid": "E502",
                "labels": {
                    "en": "Office held by head of government",
                },
                "descriptions": {
                    "en": "Political office held by the head of government"
                },
                "aliases": {"en": ["head of government position", "chief executive"]},
                "properties": ["P31", "P1313", "P580", "P582", "P585"],
                "classification_constraints": {
                    "p31": ["Q4173029"],  # political office
                    "p279": [],
                },
                "target_systems": ["wikidata", "osm"],
            }
        }

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize to dictionary (alias for model_dump for compatibility)."""
        return self.model_dump(**kwargs)  # type: ignore[return-value]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GKCEntityProfile":
        """Deserialize from dictionary (alias for model_validate for compatibility)."""
        return cls.model_validate(data)  # type: ignore[return-value]
