"""Base classes for the GKC profile system.

This module exports the foundational classes for the 4-profile architecture:

- EntityProfile: Canonical representation of entities
- ModulationProfile: Input schemas for data contribution workflows
- BarrelProfile: Platform-specific output transformers
- PropertyDefinition: Metadata about properties/claims/tags
- MashBill: (Legacy) Extract structured facts from sources

Plain meaning: The building blocks for profile-based data workflows.
"""

from .barrel_profile import BarrelProfile
from .entity_profile import EntityProfile
from .mash_bill import MashBill
from .modulation_profile import ModulationProfile
from .property_definition import PropertyDefinition

__all__ = [
    "BarrelProfile",
    "EntityProfile",
    "MashBill",
    "ModulationProfile",
    "PropertyDefinition",
]
