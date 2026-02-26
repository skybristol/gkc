"""Barrel Profile: Transform entities to platform-specific payloads.

This module defines the BarrelProfile base class for transforming canonical entity
representations into platform-specific formats ready for shipping to Wikidata,
OpenStreetMap, Wikimedia Commons, Wikipedia, etc.

Each platform requires its own BarrelProfile implementation (e.g.,
WikidataBarrelProfile, OSMBarrelProfile) that knows how to transform an
EntityProfile into the correct JSON/XML/format for that platform.

Plain meaning: Convert entities to platform-ready formats for shipping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .entity_profile import EntityProfile


class BarrelProfile:
    """Transform an EntityProfile into a platform-specific payload.

    BarrelProfiles are platform-specific transformers that know how to convert
    a canonical EntityProfile into the exact format needed by a target platform.

    Concrete implementations (created in SpiritSafe repository) will:
    - Implement platform-specific transformation logic
    - Handle platform-specific validation
    - Provide shipping methods to send data to the platform
    - Manage platform-specific authentication/credentials

    Not all platforms apply to all entity types. For example, a tribal government
    entity might have Wikidata and OSM barrel profiles but not a Commons barrel.

    Plain meaning: Platform-specific converter and shipper.

    Example:
        >>> class WikidataTribalGovernmentBarrel(BarrelProfile):
        ...     platform = "wikidata"
        ...     def transform(self, entity):
        ...         # Convert to Wikidata JSON format
        ...         return {...}
    """

    platform: str = ""
    """Platform identifier (wikidata, osm, commons, wikipedia)."""

    def transform(self, entity: EntityProfile) -> dict[str, Any]:
        """Transform an EntityProfile to platform-specific format.

        Args:
            entity: The canonical EntityProfile to transform

        Returns:
            Platform-specific payload (e.g., Wikidata JSON, OSM XML as dict)

        Raises:
            NotImplementedError: If concrete class hasn't implemented this

        Plain meaning: Convert the entity to this platform's format.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement transform()"
        )

    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """Validate that the payload is ready for shipping.

        Args:
            payload: The transformed payload to validate

        Returns:
            True if payload is valid, False otherwise

        Raises:
            ValueError: If payload has validation errors

        Plain meaning: Check that the payload is correctly formatted.
        """
        # Base implementation - concrete classes can override
        return True

    def ship(self, payload: dict[str, Any]) -> Any:
        """Send the payload to the external platform.

        Args:
            payload: Platform-specific payload from transform()

        Returns:
            Platform-specific response (e.g., new item ID, edit result)

        Raises:
            NotImplementedError: If concrete class hasn't implemented this

        Plain meaning: Send the data to the platform.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement ship()")

    def to_dict(self) -> dict[str, Any]:
        """Export barrel profile metadata as a dictionary.

        Returns:
            Dict with platform identifier and metadata

        Plain meaning: Get info about this barrel profile.
        """
        return {
            "platform": self.platform,
            "class": self.__class__.__name__,
        }
