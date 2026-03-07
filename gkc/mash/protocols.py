"""Mash protocol contracts.

Defines source adapter interfaces used by mash loaders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from gkc.mash.core import DataTemplate


@runtime_checkable
class MashSourceAdapter(Protocol):
    """Contract for mash source adapters.

    A source adapter handles loading one or more source references and returning
    templates that satisfy the ``DataTemplate`` protocol.
    """

    source_name: str

    def can_load(self, source_ref: str) -> bool:
        """Return True when this adapter can load the provided source reference."""

    def load(self, source_ref: str) -> DataTemplate:
        """Load one source reference into a template."""

    def load_many(self, source_refs: list[str]) -> dict[str, DataTemplate]:
        """Load multiple source references into templates keyed by source ref."""
