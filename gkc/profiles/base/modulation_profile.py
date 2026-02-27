"""Modulation Profile: Define input schemas for entity modification workflows.

This module defines the ModulationProfile class that specifies what fields can be
input, created, or edited for one or more entities in a data contribution task.

A ModulationProfile represents a complete data curation workflow (e.g., "Document
a Tribal Government") and can orchestrate inputs for multiple related entities
(e.g., the tribe, its government office, and current leader).

Plain meaning: The input form blueprint for a data contribution task.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .barrel_profile import BarrelProfile


class ModulationProfile(BaseModel):
    """Define what can be input/modulated for a data contribution task.

    ModulationProfiles represent complete workflows for data curation, potentially
    spanning multiple entities and platforms. One ModulationProfile = one logical
    data contribution task from a curator's perspective.

    For example, documenting a tribal government might involve:
    - Creating/updating the Tribe entity in Wikidata
    - Creating the HeadOfGovernmentOffice entity
    - Adding the tribe headquarters to OpenStreetMap
    - Creating a Wikipedia infobox

    The ModulationProfile orchestrates all of this by defining:
    - Which entity types are involved
    - What fields can be input for each
    - Validation rules for each field
    - How inputs map to multiple platform outputs

    This is the foundation for future form generation (out of scope for initial
    implementation).

    Plain meaning: The blueprint for a complete data contribution workflow.

    Example:
        >>> modulation = ModulationProfile(
        ...     name="tribal_government_documentation",
        ...     description="Document a US tribal government",
        ...     entity_types=["tribal_government", "government_office"],
        ... )
    """

    name: str = Field(description="Unique identifier for this modulation task")

    description: str = Field(
        default="",
        description="Human-readable explanation of this workflow",
    )

    entity_types: List[str] = Field(
        default_factory=list,
        description="List of entity profile names involved in this workflow",
    )

    field_specs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Field specifications keyed by entity_type.field_name. "
            "Each spec defines validation rules, input types, help text, etc."
        ),
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about this modulation workflow",
    )

    def to_barrel_profiles(self) -> list[BarrelProfile]:
        """Generate platform-specific BarrelProfiles for all outputs.

        A single ModulationProfile may generate outputs for multiple platforms
        and multiple entities. This method returns all BarrelProfiles needed
        to ship the modulated data to the appropriate targets.

        Returns:
            List of BarrelProfiles for all platform outputs.

        Raises:
            NotImplementedError: If concrete profile hasn't implemented this.

        Plain meaning: Convert modulated inputs to platform-ready outputs.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement to_barrel_profiles()"
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user inputs against field specifications.

        Args:
            inputs: User-provided input data

        Returns:
            Validated and potentially coerced inputs

        Raises:
            ValueError: If validation fails

        Plain meaning: Check that inputs match requirements.
        """
        # Base implementation - concrete profiles can override
        # For now, just return inputs as-is
        return inputs

    def to_dict(self) -> dict[str, Any]:
        """Export modulation profile as a dictionary.

        Returns:
            Dict representation suitable for serialization.

        Plain meaning: Convert to a plain dictionary.
        """
        return self.model_dump()
