"""Validation data models for normalized Wikidata statements.

Plain meaning: Typed containers for normalized statement data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ValueType = Literal["item", "url", "string", "quantity", "time"]


class StatementValue(BaseModel):
    """Normalized value for a statement, qualifier, or reference.

    Args:
        value: The extracted value.
        value_type: The datatype for the value.

    Example:
        >>> StatementValue(value="Q5", value_type="item")

    Plain meaning: A typed value pulled from a Wikidata statement.
    """

    value: str | int | float = Field(..., description="Extracted value")
    value_type: ValueType = Field(..., description="Value datatype")


class ReferenceData(BaseModel):
    """Normalized reference data for a statement.

    Args:
        snaks: Mapping of property IDs to lists of statement values.

    Example:
        >>> ReferenceData(
        ...     snaks={
        ...         "P854": [StatementValue(value="https://...", value_type="url")]
        ...     }
        ... )

    Plain meaning: A single reference block attached to a statement.
    """

    snaks: dict[str, list[StatementValue]] = Field(
        default_factory=dict, description="Reference snaks"
    )


class StatementData(BaseModel):
    """Normalized statement data including qualifiers and references.

    Args:
        value: Main statement value.
        qualifiers: Qualifier values keyed by property ID.
        references: Reference blocks for the statement.

    Example:
        >>> StatementData(value=StatementValue(value="Q5", value_type="item"))

    Plain meaning: One statement with its attached qualifiers and references.
    """

    value: StatementValue = Field(..., description="Main statement value")
    qualifiers: dict[str, list[StatementValue]] = Field(
        default_factory=dict, description="Qualifier values"
    )
    references: list[ReferenceData] = Field(
        default_factory=list, description="Statement references"
    )
