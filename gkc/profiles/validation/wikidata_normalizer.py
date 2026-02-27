"""Normalize Wikidata JSON into profile-friendly statements.

Plain meaning: Convert Wikidata item data into typed statement structures.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from gkc.profiles.models import ProfileDefinition
from gkc.profiles.validation.models import ReferenceData, StatementData, StatementValue


class NormalizationIssue(BaseModel):
    """Issue reported during normalization.

    Args:
        severity: "warning" or "error".
        message: Issue description.
        field_id: Optional profile field identifier.
        property_id: Optional Wikidata property ID.

    Example:
        >>> NormalizationIssue(severity="warning", message="Missing value")

    Plain meaning: A problem encountered while reading Wikidata data.
    """

    severity: Literal["warning", "error"] = Field(..., description="Issue severity")
    message: str = Field(..., description="Issue message")
    field_id: Optional[str] = Field(default=None, description="Profile field ID")
    property_id: Optional[str] = Field(default=None, description="Property ID")


class NormalizationResult(BaseModel):
    """Result of normalizing a Wikidata item.

    Args:
        data: Normalized statement data keyed by profile field id.
        issues: Normalization issues.

    Plain meaning: Parsed statements and any problems found.
    """

    data: Dict[str, List[StatementData]] = Field(
        default_factory=dict, description="Normalized statements"
    )
    issues: List[NormalizationIssue] = Field(
        default_factory=list, description="Normalization issues"
    )


class WikidataNormalizer:
    """Normalize Wikidata entity JSON to profile statement data.

    Example:
        >>> normalizer = WikidataNormalizer()
        >>> result = normalizer.normalize(entity_data, profile)

    Plain meaning: Extract statements from Wikidata JSON for validation.
    """

    def normalize(
        self, entity_data: dict, profile: ProfileDefinition
    ) -> NormalizationResult:
        """Normalize an entity JSON payload against a profile.

        Args:
            entity_data: Wikidata JSON entity data.
            profile: ProfileDefinition describing target fields.

        Returns:
            NormalizationResult with statement data and issues.

        Side effects:
            None.

        Example:
            >>> result = WikidataNormalizer().normalize(item, profile)

        Plain meaning: Convert raw Wikidata JSON into typed statements.
        """
        claims = entity_data.get("claims", {}) if isinstance(entity_data, dict) else {}
        result = NormalizationResult()

        for field in profile.fields:
            statements_raw = claims.get(field.wikidata_property, [])
            if not isinstance(statements_raw, list):
                result.issues.append(
                    NormalizationIssue(
                        severity="warning",
                        message="Claims entry is not a list",
                        field_id=field.id,
                        property_id=field.wikidata_property,
                    )
                )
                continue

            normalized_statements: List[StatementData] = []
            for statement in statements_raw:
                if isinstance(statement, dict):
                    mainsnak = statement.get("mainsnak", {})
                else:
                    mainsnak = {}
                value = _snak_to_value(mainsnak)
                if value is None:
                    result.issues.append(
                        NormalizationIssue(
                            severity="warning",
                            message="Statement missing value",
                            field_id=field.id,
                            property_id=field.wikidata_property,
                        )
                    )
                    continue

                qualifiers = _extract_qualifiers(statement.get("qualifiers", {}))
                references = _extract_references(statement.get("references", []))

                normalized_statements.append(
                    StatementData(
                        value=value,
                        qualifiers=qualifiers,
                        references=references,
                    )
                )

            result.data[field.id] = normalized_statements

        return result


def _extract_qualifiers(raw_qualifiers: dict) -> dict[str, list[StatementValue]]:
    qualifiers: Dict[str, List[StatementValue]] = {}
    if not isinstance(raw_qualifiers, dict):
        return qualifiers

    for prop_id, snaks in raw_qualifiers.items():
        if not isinstance(snaks, list):
            continue
        values = []
        for snak in snaks:
            value = _snak_to_value(snak)
            if value is not None:
                values.append(value)
        if values:
            qualifiers[prop_id] = values

    return qualifiers


def _extract_references(raw_references: list) -> list[ReferenceData]:
    references: List[ReferenceData] = []
    if not isinstance(raw_references, list):
        return references

    for reference in raw_references:
        if not isinstance(reference, dict):
            continue
        snaks = reference.get("snaks", {})
        reference_snaks: Dict[str, List[StatementValue]] = {}
        if isinstance(snaks, dict):
            for prop_id, snak_list in snaks.items():
                if not isinstance(snak_list, list):
                    continue
                values = []
                for snak in snak_list:
                    value = _snak_to_value(snak)
                    if value is not None:
                        values.append(value)
                if values:
                    reference_snaks[prop_id] = values
        references.append(ReferenceData(snaks=reference_snaks))

    return references


def _snak_to_value(snak: dict) -> Optional[StatementValue]:
    if not isinstance(snak, dict):
        return None
    if snak.get("snaktype") != "value":
        return None

    datavalue = snak.get("datavalue", {})
    if not isinstance(datavalue, dict):
        return None

    value_type = datavalue.get("type")
    raw_value = datavalue.get("value")
    datatype = snak.get("datatype")

    if value_type == "wikibase-entityid" and isinstance(raw_value, dict):
        entity_id = raw_value.get("id")
        if not entity_id:
            numeric_id = raw_value.get("numeric-id")
            if numeric_id is not None:
                entity_id = f"Q{numeric_id}"
        if entity_id:
            return StatementValue(value=str(entity_id), value_type="item")

    if value_type == "string" and isinstance(raw_value, str):
        if datatype == "url":
            return StatementValue(value=raw_value, value_type="url")
        return StatementValue(value=raw_value, value_type="string")

    if value_type == "quantity" and isinstance(raw_value, dict):
        amount = raw_value.get("amount")
        if isinstance(amount, str):
            amount = amount.replace("+", "")
        if amount is not None:
            try:
                numeric = float(amount)
                return StatementValue(value=numeric, value_type="quantity")
            except ValueError:
                return None

    if value_type == "time" and isinstance(raw_value, dict):
        time_value = raw_value.get("time")
        if isinstance(time_value, str):
            return StatementValue(value=time_value, value_type="time")

    return None
