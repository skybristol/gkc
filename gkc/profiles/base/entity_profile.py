"""Entity Profile: Canonical representation of entities across platforms.

This module defines the base EntityProfile class that all concrete entity profiles
inherit from. Entity profiles represent the canonical, validated form of entities
like tribal governments, government offices, people, etc.

Plain meaning: The blueprint for what a validated entity looks like.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .barrel_profile import BarrelProfile
    from .modulation_profile import ModulationProfile


class EntityProfile(BaseModel):
    """Base class for all entity profiles.

    EntityProfile represents the canonical, validated form of an entity, patterned
    after the Wikibase model with labels, descriptions, and aliases as core
    components. Concrete profiles (e.g., TribalGovernmentProfile) inherit from this
    and add domain-specific fields and validation logic.

    All profiles must define:
    - profile_name: Unique identifier for this profile type
    - profile_version: Semantic version for tracking changes
    - description: Human-readable explanation of what this profile represents

    Core fields (inherited from Wikibase model):
    - labels: Language-keyed labels (e.g., {"en": "Apache Tribe"})
    - descriptions: Language-keyed descriptions
    - aliases: Language-keyed lists of alternative names

    Concrete profiles may add:
    - Domain-specific fields (e.g., headquarters_location for governments)
    - Custom validators for naming conventions
    - Transformation logic for platform-specific outputs

    Plain meaning: The template that all entity types follow.

    Example:
        >>> class TribalGovernmentProfile(EntityProfile):
        ...     profile_name: ClassVar[str] = "tribal_government_us"
        ...     profile_version: ClassVar[str] = "1.0"
        ...     description: ClassVar[str] = "US Tribal Government"
        ...     headquarters_location: str | None = None
    """

    # Required metadata - concrete profiles must define these as ClassVars
    profile_name: ClassVar[str]
    profile_version: ClassVar[str] = "1.0"
    description: ClassVar[str] = ""

    # Core Wikibase-patterned fields
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Language-keyed labels (e.g., {'en': 'Apache Tribe'})",
    )
    descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Language-keyed descriptions of the entity",
    )
    aliases: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Language-keyed lists of alternative names",
    )

    # Optional: raw source item identifier (QID/EID/PID)
    source_id: str | None = Field(
        default=None,
        description="Source identifier (e.g., 'Q42' for Wikidata items)",
    )

    # Optional: provenance metadata about where this profile came from
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about profile generation (timestamps, sources, etc.)",
    )

    def validate_profile(self) -> None:
        """Hook for profile-specific validation rules.

        Concrete profiles can override this to add custom validation logic
        that goes beyond Pydantic's built-in field validation. For example,
        checking that certain fields are mutually required or validating
        cross-field constraints.

        Plain meaning: Extra checks specific to this entity type.
        """
        return

    def to_dict(self) -> dict[str, Any]:
        """Export profile as a dictionary.

        Returns:
            Dict representation of the profile, suitable for serialization.

        Plain meaning: Convert the profile to a plain dictionary.
        """
        return self.model_dump()

    def to_modulation_profile(self) -> ModulationProfile:
        """Generate a ModulationProfile from this EntityProfile.

        ModulationProfiles define what can be input/edited for this entity type.
        Concrete profiles should override this to return a properly configured
        modulation profile with input validation rules and field specifications.

        Returns:
            ModulationProfile defining input schema for this entity type.

        Raises:
            NotImplementedError: If concrete profile hasn't implemented this.

        Plain meaning: Generate the input form schema for this entity type.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_modulation_profile()"
        )

    def to_barrel_profile(self, platform: str) -> BarrelProfile:
        """Generate a platform-specific BarrelProfile from this EntityProfile.

        BarrelProfiles transform the canonical entity representation into
        platform-specific payloads ready for shipping to Wikidata, OSM, Commons, etc.

        Args:
            platform: Target platform identifier ("wikidata", "osm", "commons", etc.)

        Returns:
            BarrelProfile configured for the specified platform.

        Raises:
            NotImplementedError: If concrete profile hasn't implemented this.
            ValueError: If platform is not supported for this entity type.

        Plain meaning: Convert this entity to the format needed by a specific platform.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_barrel_profile()"
        )

    @classmethod
    def from_raw(cls, raw: Any) -> EntityProfile:
        """Transform a raw platform item into this profile.

        Args:
            raw: Raw data from a platform (e.g., Wikidata JSON, OSM XML)

        Returns:
            Validated EntityProfile instance.

        Raises:
            NotImplementedError: If concrete profile hasn't implemented this.

        Plain meaning: Parse raw data into a validated profile.
        """
        raise NotImplementedError(f"{cls.__name__} must implement from_raw()")
