"""Still Charger: Fill curation packets with concrete entity data.

This module provides the "charge the still" stage of the workflow:
profile-generated curation packets are populated with real input values before
barreling/transformation for shipping.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChargeIssue:
    """Represents a non-fatal charging issue."""

    severity: str
    entity_id: str
    field: str
    message: str


@dataclass
class ChargeReport:
    """Summary of a charge operation."""

    entities_charged: int = 0
    entities_skipped: int = 0
    issues: list[ChargeIssue] = field(default_factory=list)


def _extract_statement_ids(profile_structure: dict[str, Any]) -> set[str]:
    statements = profile_structure.get("statements", [])
    if isinstance(statements, list):
        return {
            str(stmt.get("id"))
            for stmt in statements
            if isinstance(stmt, dict) and stmt.get("id")
        }
    if isinstance(statements, dict):
        return set(statements.keys())
    return set()


def _entity_payload_for(
    entity: dict[str, Any],
    source_values: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    entity_id = entity.get("id")
    profile_id = entity.get("profile")

    if entity_id in source_values:
        return source_values[entity_id]
    if profile_id in source_values:
        return source_values[profile_id]
    return None


def charge_curation_packet(
    packet: dict[str, Any],
    source_values: dict[str, dict[str, Any]],
    *,
    specificationless: bool = True,
) -> tuple[dict[str, Any], ChargeReport]:
    """Fill packet entities with real source values.

    Args:
        packet: Curation packet generated from profile scaffolds.
        source_values: Mapping keyed by entity ID or profile ID. Each value is
            expected to include a ``statements`` mapping and optional metadata
            (labels/descriptions/aliases).
        specificationless: When ``True``, allows unknown statements and records
            warnings instead of blocking charging.

    Returns:
        Tuple of (charged_packet, report).
    """
    charged = deepcopy(packet)
    report = ChargeReport()

    entities = charged.get("entities", [])
    for entity in entities:
        entity_id = str(entity.get("id", ""))
        payload = _entity_payload_for(entity, source_values)
        if not payload:
            report.entities_skipped += 1
            continue

        entity.setdefault("data", {})
        entity_data = entity["data"]
        profile_structure = entity.get("profile_structure", {})
        allowed_statement_ids = _extract_statement_ids(profile_structure)

        payload_statements = payload.get("statements", {})
        if not isinstance(payload_statements, dict):
            report.issues.append(
                ChargeIssue(
                    severity="error",
                    entity_id=entity_id,
                    field="statements",
                    message="Expected 'statements' payload to be a mapping.",
                )
            )
            report.entities_skipped += 1
            continue

        unknown_statement_ids = [
            statement_id
            for statement_id in payload_statements
            if allowed_statement_ids and statement_id not in allowed_statement_ids
        ]

        if unknown_statement_ids and not specificationless:
            report.issues.append(
                ChargeIssue(
                    severity="error",
                    entity_id=entity_id,
                    field="statements",
                    message=(
                        "Unknown statements for profile scaffold: "
                        + ", ".join(sorted(unknown_statement_ids))
                    ),
                )
            )
            report.entities_skipped += 1
            continue

        if unknown_statement_ids and specificationless:
            report.issues.append(
                ChargeIssue(
                    severity="warning",
                    entity_id=entity_id,
                    field="statements",
                    message=(
                        "Specificationless charging accepted unknown statements: "
                        + ", ".join(sorted(unknown_statement_ids))
                    ),
                )
            )

        for key in ("labels", "descriptions", "aliases", "sitelinks"):
            if key in payload:
                entity_data[key] = payload[key]

        entity_data.setdefault("statements", {})
        entity_data["statements"].update(payload_statements)
        report.entities_charged += 1

    return charged, report
