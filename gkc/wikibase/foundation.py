"""Foundation ontology profile loading and Wikibase audit utilities.

This module provides label-first auditing and initialization support for
Data Distillery foundation entities/properties. QID/PID identifiers are
optional in profile definitions.
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests
import yaml

from gkc.auth import WikiverseAuth
from gkc.mash import WikibaseApiClient
from gkc.shipper import WikibaseShipper

_ID_PATTERN = re.compile(r"^[PQ]\d+$", flags=re.IGNORECASE)


class FoundationProfileError(Exception):
    """Raised when foundation profile files are invalid or missing."""


class FoundationAuditError(Exception):
    """Raised when Wikibase audit operations fail."""


class FoundationInitError(Exception):
    """Raised when Wikibase init operations fail."""


@dataclass(slots=True)
class ClaimRequirement:
    """Required claim definition for an entity audit rule."""

    property_ref: str
    value_ref: Optional[str] = None


@dataclass(slots=True)
class FoundationEntitySpec:
    """Expected foundation item definition."""

    label: str
    identifier: Optional[str] = None
    description: Optional[str] = None
    required_claims: list[ClaimRequirement] = field(default_factory=list)


@dataclass(slots=True)
class FoundationPropertySpec:
    """Expected foundation property definition."""

    label: str
    identifier: Optional[str] = None
    description: Optional[str] = None
    datatype: Optional[str] = None


@dataclass(slots=True)
class FoundationProfiles:
    """Container for loaded foundation ontology profile definitions."""

    entities: list[FoundationEntitySpec]
    properties: list[FoundationPropertySpec]
    source_dir: str


@dataclass(slots=True)
class AuditRecord:
    """Detailed result for one audited definition."""

    kind: str
    label: str
    expected_id: Optional[str]
    resolved_id: Optional[str]
    status: str
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FoundationAuditReport:
    """Aggregated result from a foundation audit run."""

    ok: bool
    summary: dict[str, int]
    records: list[AuditRecord]
    resolved_identifiers: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to JSON-safe dictionary."""
        return {
            "ok": self.ok,
            "summary": dict(self.summary),
            "records": [asdict(record) for record in self.records],
            "resolved_identifiers": dict(self.resolved_identifiers),
        }


@dataclass(slots=True)
class InitActionRecord:
    """Record of one init action performed."""

    kind: str
    label: str
    action: str
    entity_id: Optional[str]
    details: str
    request_payload: Optional[dict[str, Any]] = None


@dataclass(slots=True)
class FoundationInitReport:
    """Aggregated result from a foundation init run."""

    ok: bool
    summary: dict[str, int]
    actions: list[InitActionRecord]
    audit_report: FoundationAuditReport

    def to_dict(self) -> dict[str, Any]:
        """Convert report to JSON-safe dictionary."""
        return {
            "ok": self.ok,
            "summary": dict(self.summary),
            "actions": [asdict(action) for action in self.actions],
            "audit_report": self.audit_report.to_dict(),
        }


def load_foundation_profiles(profile_dir: str | Path) -> FoundationProfiles:
    """Load foundation entity/property definitions from YAML files.

    Expected files in ``profile_dir``:
      - ``foundation_entities.yaml``
      - ``foundation_properties.yaml``

    ID fields are optional; labels are required and used as the primary audit key.
    """
    base_dir = Path(profile_dir)
    if not base_dir.exists():
        raise FoundationProfileError(
            f"Foundation profile directory not found: {base_dir}"
        )

    entities_data = _read_yaml(base_dir / "foundation_entities.yaml")
    properties_data = _read_yaml(base_dir / "foundation_properties.yaml")

    entities_raw = entities_data.get("entities") or []
    properties_raw = properties_data.get("properties") or []

    if not isinstance(entities_raw, list):
        raise FoundationProfileError(
            "'entities' must be a list in foundation_entities.yaml"
        )
    if not isinstance(properties_raw, list):
        raise FoundationProfileError(
            "'properties' must be a list in foundation_properties.yaml"
        )

    entities: list[FoundationEntitySpec] = []
    for index, raw in enumerate(entities_raw):
        if not isinstance(raw, dict):
            raise FoundationProfileError(
                f"Invalid entity entry at index {index}: expected mapping"
            )

        label = _require_text(raw, "label", context=f"entity[{index}]")
        identifier = _optional_identifier(raw.get("qid") or raw.get("id"))
        description = _optional_text(raw.get("description"))

        required_claims: list[ClaimRequirement] = []
        claims_raw = raw.get("required_claims") or []
        if not isinstance(claims_raw, list):
            raise FoundationProfileError(
                f"entity[{index}].required_claims must be a list"
            )

        for claim_index, claim in enumerate(claims_raw):
            if not isinstance(claim, dict):
                raise FoundationProfileError(
                    f"entity[{index}].required_claims[{claim_index}] must be a mapping"
                )
            property_ref = _require_text(
                claim,
                "property",
                context=f"entity[{index}].required_claims[{claim_index}]",
            )
            value_ref = _optional_text(claim.get("value"))
            required_claims.append(
                ClaimRequirement(property_ref=property_ref, value_ref=value_ref)
            )

        entities.append(
            FoundationEntitySpec(
                label=label,
                identifier=identifier,
                description=description,
                required_claims=required_claims,
            )
        )

    properties: list[FoundationPropertySpec] = []
    for index, raw in enumerate(properties_raw):
        if not isinstance(raw, dict):
            raise FoundationProfileError(
                f"Invalid property entry at index {index}: expected mapping"
            )
        label = _require_text(raw, "label", context=f"property[{index}]")
        identifier = _optional_identifier(raw.get("pid") or raw.get("id"))
        description = _optional_text(raw.get("description"))
        datatype = _optional_text(raw.get("datatype"))

        properties.append(
            FoundationPropertySpec(
                label=label,
                identifier=identifier,
                description=description,
                datatype=datatype,
            )
        )

    return FoundationProfiles(
        entities=entities,
        properties=properties,
        source_dir=str(base_dir),
    )


def audit_wikibase_foundation(
    *,
    api_url: str,
    profile_dir: str | Path,
    language: str = "en",
    session: Optional[requests.Session] = None,
) -> FoundationAuditReport:
    """Audit a Wikibase instance against foundation profiles.

    The audit is label-first and tolerates profiles without fixed QID/PID values.
    """
    profiles = load_foundation_profiles(profile_dir)
    api = WikibaseApiClient(api_url=api_url, session=session, timeout=20)

    records: list[AuditRecord] = []
    resolved_identifiers: dict[str, str] = {}

    property_label_to_id: dict[str, str] = {}

    try:
        for spec in profiles.properties:
            record, resolved_id = _audit_property_spec(
                spec=spec,
                api=api,
                language=language,
            )
            records.append(record)
            if resolved_id:
                property_label_to_id[spec.label.casefold()] = resolved_id
                resolved_identifiers[f"property:{spec.label}"] = resolved_id

        for spec in profiles.entities:
            record, resolved_id = _audit_entity_spec(
                spec=spec,
                api=api,
                language=language,
                property_label_to_id=property_label_to_id,
            )
            records.append(record)
            if resolved_id:
                resolved_identifiers[f"entity:{spec.label}"] = resolved_id
    except RuntimeError as exc:
        raise FoundationAuditError(str(exc)) from exc

    summary = {
        "total": len(records),
        "conformant": sum(1 for record in records if record.status == "conformant"),
        "missing": sum(1 for record in records if record.status == "missing"),
        "ambiguous": sum(1 for record in records if record.status == "ambiguous"),
        "nonconforming": sum(
            1 for record in records if record.status == "nonconforming"
        ),
    }

    ok = (
        summary["missing"] == 0
        and summary["ambiguous"] == 0
        and summary["nonconforming"] == 0
    )
    return FoundationAuditReport(
        ok=ok,
        summary=summary,
        records=records,
        resolved_identifiers=resolved_identifiers,
    )


def init_wikibase_foundation(
    *,
    auth: WikiverseAuth,
    api_url: str,
    profile_dir: str | Path,
    language: str = "en",
    dry_run: bool = True,
    bot: bool = False,
    summary: str = "initiating Data Distillery wikibase with items and properties",
) -> FoundationInitReport:
    """Initialize a Wikibase instance by creating missing foundation entities/properties.

    Runs audit first, then acts on the results:
      - missing: creates the entity/property
      - ambiguous: skips (requires manual disambiguation)
      - nonconforming: skips (may add auto-fix in future)
    """
    if not summary or not summary.strip():
        raise FoundationInitError("summary is required for wbeditentity operations")

    audit_report = audit_wikibase_foundation(
        api_url=api_url,
        profile_dir=profile_dir,
        language=language,
        session=auth.session if auth.is_logged_in() else None,
    )

    profiles = load_foundation_profiles(profile_dir)
    api = WikibaseApiClient(
        api_url=api_url,
        session=auth.session if auth.is_logged_in() else None,
        timeout=20,
    )
    shipper = WikibaseShipper(auth=auth, api_url=api_url, dry_run_default=dry_run)

    actions: list[InitActionRecord] = []
    property_specs_by_label = {
        spec.label.casefold(): spec for spec in profiles.properties
    }
    entity_specs_by_label = {spec.label.casefold(): spec for spec in profiles.entities}

    existing_property_ids: dict[str, str] = {
        key.split(":", 1)[1].casefold(): value
        for key, value in audit_report.resolved_identifiers.items()
        if key.startswith("property:")
    }
    existing_entity_ids: dict[str, str] = {
        key.split(":", 1)[1].casefold(): value
        for key, value in audit_report.resolved_identifiers.items()
        if key.startswith("entity:")
    }

    created_property_ids: dict[str, str] = {}
    created_entity_ids: dict[str, str] = {}
    missing_property_specs: list[FoundationPropertySpec] = []
    missing_entity_specs: list[FoundationEntitySpec] = []

    for record in audit_report.records:
        if record.status == "missing" and record.kind == "property":
            spec = property_specs_by_label.get(record.label.casefold())
            if spec:
                missing_property_specs.append(spec)
            continue

        if record.status == "missing" and record.kind == "entity":
            spec = entity_specs_by_label.get(record.label.casefold())
            if spec:
                missing_entity_specs.append(spec)
            continue

        if record.status == "ambiguous":
            actions.append(
                InitActionRecord(
                    kind=record.kind,
                    label=record.label,
                    action="skipped",
                    entity_id=None,
                    details="Ambiguous label match; manual resolution required",
                )
            )
            continue

        if record.status == "nonconforming":
            actions.append(
                InitActionRecord(
                    kind=record.kind,
                    label=record.label,
                    action="skipped",
                    entity_id=record.resolved_id,
                    details="Existing entity nonconforming; manual review required",
                )
            )

    # Phase 1: create missing properties first (foundation dependency roots)
    for spec in missing_property_specs:
        payload = {
            "labels": {language: {"language": language, "value": spec.label}},
        }
        if spec.description:
            payload["descriptions"] = {
                language: {"language": language, "value": spec.description}
            }

        if not spec.datatype:
            actions.append(
                InitActionRecord(
                    kind="property",
                    label=spec.label,
                    action="skipped",
                    entity_id=None,
                    details="Missing datatype in profile",
                )
            )
            continue

        result = shipper.write_property(
            payload=payload,
            summary=f"{summary}: create property '{spec.label}'",
            datatype=spec.datatype,
            dry_run=dry_run,
            bot=bot,
        )

        if result.status == "submitted" and result.entity_id:
            created_property_ids[spec.label.casefold()] = result.entity_id

        action_status = result.status if result.status != "submitted" else "created"
        actions.append(
            InitActionRecord(
                kind="property",
                label=spec.label,
                action=action_status,
                entity_id=result.entity_id,
                details=(
                    f"Property created with datatype {spec.datatype}"
                    if result.status == "submitted"
                    else (
                        "; ".join(result.warnings) if result.warnings else result.status
                    )
                ),
                request_payload=copy.deepcopy(payload),
            )
        )

    # Phase 1: create missing entities with core identity fields
    for spec in missing_entity_specs:
        payload = {
            "labels": {language: {"language": language, "value": spec.label}},
        }
        if spec.description:
            payload["descriptions"] = {
                language: {"language": language, "value": spec.description}
            }

        result = shipper.write_item(
            payload=payload,
            summary=f"{summary}: create entity '{spec.label}'",
            dry_run=dry_run,
            bot=bot,
        )

        if result.status == "submitted" and result.entity_id:
            created_entity_ids[spec.label.casefold()] = result.entity_id

        action_status = result.status if result.status != "submitted" else "created"
        actions.append(
            InitActionRecord(
                kind="entity",
                label=spec.label,
                action=action_status,
                entity_id=result.entity_id,
                details=(
                    "Entity created"
                    if result.status == "submitted"
                    else (
                        "; ".join(result.warnings) if result.warnings else result.status
                    )
                ),
                request_payload=copy.deepcopy(payload),
            )
        )

    # Phase 2: apply required-claim enrichments for created entities now that IDs exist.
    property_ids = {**existing_property_ids, **created_property_ids}
    entity_ids = {**existing_entity_ids, **created_entity_ids}

    for spec in missing_entity_specs:
        if not spec.required_claims:
            continue

        entity_id = created_entity_ids.get(spec.label.casefold())

        claim_statements: list[dict[str, Any]] = []
        unresolved_references: list[str] = []

        for requirement in spec.required_claims:
            property_id = _resolve_property_id(
                requirement.property_ref,
                property_ids,
                api,
                language,
            )
            if not property_id:
                unresolved_references.append(f"property '{requirement.property_ref}'")
                continue

            if not requirement.value_ref:
                continue

            value_id = _resolve_entity_or_property_id_with_maps(
                requirement.value_ref,
                entity_ids,
                property_ids,
                api,
                language,
            )
            if not value_id:
                unresolved_references.append(f"value '{requirement.value_ref}'")
                continue

            claim_statements.append(
                _build_entity_id_claim_statement(property_id, value_id)
            )

        if unresolved_references:
            actions.append(
                InitActionRecord(
                    kind="entity",
                    label=spec.label,
                    action="skipped",
                    entity_id=entity_id,
                    details=(
                        "Claim enrichment skipped: unresolved "
                        + ", ".join(unresolved_references)
                    ),
                )
            )
            continue

        if not claim_statements:
            continue

        if not entity_id:
            if dry_run:
                actions.append(
                    InitActionRecord(
                        kind="entity",
                        label=spec.label,
                        action="dry_run",
                        entity_id=None,
                        details=(
                            f"Would apply {len(claim_statements)} required claims "
                            "after create"
                        ),
                        request_payload=copy.deepcopy({"claims": claim_statements}),
                    )
                )
            else:
                actions.append(
                    InitActionRecord(
                        kind="entity",
                        label=spec.label,
                        action="skipped",
                        entity_id=None,
                        details="Claim enrichment skipped: created entity ID unavailable",
                    )
                )
            continue

        enrichment_payload = {
            "claims": claim_statements,
        }
        result = shipper.write_item(
            payload=enrichment_payload,
            summary=f"{summary}: enrich entity '{spec.label}'",
            entity_id=entity_id,
            dry_run=dry_run,
            bot=bot,
        )

        action_status = "updated" if result.status == "submitted" else result.status
        actions.append(
            InitActionRecord(
                kind="entity",
                label=spec.label,
                action=action_status,
                entity_id=entity_id,
                details=(
                    f"Applied {len(claim_statements)} required claims"
                    if result.status == "submitted"
                    else (
                        "; ".join(result.warnings) if result.warnings else result.status
                    )
                ),
                request_payload=copy.deepcopy(enrichment_payload),
            )
        )

    summary = {
        "total_actions": len(actions),
        "created": sum(1 for action in actions if action.action == "created"),
        "updated": sum(1 for action in actions if action.action == "updated"),
        "skipped": sum(1 for action in actions if action.action == "skipped"),
        "dry_run": sum(1 for action in actions if action.action == "dry_run"),
    }

    ok = summary["skipped"] == 0 and (dry_run or summary["created"] > 0)
    return FoundationInitReport(
        ok=ok,
        summary=summary,
        actions=actions,
        audit_report=audit_report,
    )


def _audit_property_spec(
    *,
    spec: FoundationPropertySpec,
    api: WikibaseApiClient,
    language: str,
) -> tuple[AuditRecord, Optional[str]]:
    candidates = _search_exact_label(
        api=api,
        label=spec.label,
        entity_type="property",
        language=language,
    )

    if not candidates:
        return (
            AuditRecord(
                kind="property",
                label=spec.label,
                expected_id=spec.identifier,
                resolved_id=None,
                status="missing",
                issues=["No property found by exact label"],
            ),
            None,
        )

    if len(candidates) > 1:
        return (
            AuditRecord(
                kind="property",
                label=spec.label,
                expected_id=spec.identifier,
                resolved_id=None,
                status="ambiguous",
                issues=[
                    "Multiple properties found by exact label: "
                    + ", ".join(candidate["id"] for candidate in candidates)
                ],
            ),
            None,
        )

    candidate = candidates[0]
    resolved_id = candidate["id"]
    entity = api.get_entity(resolved_id)

    issues: list[str] = []

    if spec.identifier and resolved_id.upper() != spec.identifier.upper():
        issues.append(
            f"Identifier mismatch: expected {spec.identifier}, found {resolved_id}"
        )

    if spec.description:
        actual_description = _extract_lang_value(
            entity.get("descriptions", {}), language
        )
        if actual_description != spec.description:
            issues.append(
                "Description mismatch: "
                f"expected '{spec.description}', found '{actual_description or ''}'"
            )

    if spec.datatype:
        actual_datatype = entity.get("datatype")
        if actual_datatype != spec.datatype:
            issues.append(
                f"Datatype mismatch: expected '{spec.datatype}', found '{actual_datatype}'"
            )

    status = "conformant" if not issues else "nonconforming"
    return (
        AuditRecord(
            kind="property",
            label=spec.label,
            expected_id=spec.identifier,
            resolved_id=resolved_id,
            status=status,
            issues=issues,
        ),
        resolved_id,
    )


def _audit_entity_spec(
    *,
    spec: FoundationEntitySpec,
    api: WikibaseApiClient,
    language: str,
    property_label_to_id: dict[str, str],
) -> tuple[AuditRecord, Optional[str]]:
    candidates = _search_exact_label(
        api=api,
        label=spec.label,
        entity_type="item",
        language=language,
    )

    if not candidates:
        return (
            AuditRecord(
                kind="entity",
                label=spec.label,
                expected_id=spec.identifier,
                resolved_id=None,
                status="missing",
                issues=["No entity found by exact label"],
            ),
            None,
        )

    if len(candidates) > 1:
        return (
            AuditRecord(
                kind="entity",
                label=spec.label,
                expected_id=spec.identifier,
                resolved_id=None,
                status="ambiguous",
                issues=[
                    "Multiple entities found by exact label: "
                    + ", ".join(candidate["id"] for candidate in candidates)
                ],
            ),
            None,
        )

    candidate = candidates[0]
    resolved_id = candidate["id"]
    entity = api.get_entity(resolved_id)

    issues: list[str] = []

    if spec.identifier and resolved_id.upper() != spec.identifier.upper():
        issues.append(
            f"Identifier mismatch: expected {spec.identifier}, found {resolved_id}"
        )

    if spec.description:
        actual_description = _extract_lang_value(
            entity.get("descriptions", {}), language
        )
        if actual_description != spec.description:
            issues.append(
                "Description mismatch: "
                f"expected '{spec.description}', found '{actual_description or ''}'"
            )

    for requirement in spec.required_claims:
        property_id = _resolve_property_id(
            requirement.property_ref,
            property_label_to_id,
            api,
            language,
        )
        if not property_id:
            issues.append(
                "Required claim property could not be resolved: "
                f"'{requirement.property_ref}'"
            )
            continue

        if property_id not in entity.get("claims", {}):
            issues.append(f"Missing required claim for property {property_id}")
            continue

        if requirement.value_ref:
            expected_value_id = _resolve_entity_or_property_id(
                requirement.value_ref,
                api,
                language,
            )
            if not expected_value_id:
                issues.append(
                    "Required claim value could not be resolved: "
                    f"'{requirement.value_ref}'"
                )
                continue

            if not _claim_has_value(entity["claims"][property_id], expected_value_id):
                issues.append(
                    "Required claim value mismatch for property "
                    f"{property_id}: expected {expected_value_id}"
                )

    status = "conformant" if not issues else "nonconforming"
    return (
        AuditRecord(
            kind="entity",
            label=spec.label,
            expected_id=spec.identifier,
            resolved_id=resolved_id,
            status=status,
            issues=issues,
        ),
        resolved_id,
    )


def _resolve_property_id(
    ref: str,
    property_label_to_id: dict[str, str],
    api: WikibaseApiClient,
    language: str,
) -> Optional[str]:
    if _looks_like_id(ref):
        return ref.upper()

    mapped = property_label_to_id.get(ref.casefold())
    if mapped:
        return mapped

    candidates = _search_exact_label(
        api=api,
        label=ref,
        entity_type="property",
        language=language,
    )
    if len(candidates) != 1:
        return None
    return candidates[0]["id"]


def _resolve_entity_or_property_id(
    ref: str,
    api: WikibaseApiClient,
    language: str,
) -> Optional[str]:
    if _looks_like_id(ref):
        return ref.upper()

    item_candidates = _search_exact_label(
        api=api,
        label=ref,
        entity_type="item",
        language=language,
    )
    if len(item_candidates) == 1:
        return item_candidates[0]["id"]

    property_candidates = _search_exact_label(
        api=api,
        label=ref,
        entity_type="property",
        language=language,
    )
    if len(property_candidates) == 1:
        return property_candidates[0]["id"]

    return None


def _resolve_entity_or_property_id_with_maps(
    ref: str,
    entity_label_to_id: dict[str, str],
    property_label_to_id: dict[str, str],
    api: WikibaseApiClient,
    language: str,
) -> Optional[str]:
    if _looks_like_id(ref):
        return ref.upper()

    mapped_entity = entity_label_to_id.get(ref.casefold())
    if mapped_entity:
        return mapped_entity

    mapped_property = property_label_to_id.get(ref.casefold())
    if mapped_property:
        return mapped_property

    return _resolve_entity_or_property_id(ref, api, language)


def _build_entity_id_claim_statement(property_id: str, value_id: str) -> dict[str, Any]:
    value_upper = value_id.upper()
    entity_type = "item" if value_upper.startswith("Q") else "property"
    numeric_id = int(value_upper[1:])

    return {
        "mainsnak": {
            "snaktype": "value",
            "property": property_id.upper(),
            "datavalue": {
                "type": "wikibase-entityid",
                "value": {
                    "entity-type": entity_type,
                    "id": value_upper,
                    "numeric-id": numeric_id,
                },
            },
        },
        "type": "statement",
        "rank": "normal",
    }


def _search_exact_label(
    *,
    api: WikibaseApiClient,
    label: str,
    entity_type: str,
    language: str,
) -> list[dict[str, Any]]:
    candidates = api.search_entities(
        label=label,
        entity_type=entity_type,
        language=language,
    )
    return [
        candidate
        for candidate in candidates
        if (candidate.get("label") or "").casefold() == label.casefold()
    ]


def _claim_has_value(claims: list[dict[str, Any]], expected_value_id: str) -> bool:
    expected_upper = expected_value_id.upper()
    for claim in claims:
        mainsnak = claim.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value")
        if isinstance(value, dict):
            found_id = value.get("id")
            if isinstance(found_id, str) and found_id.upper() == expected_upper:
                return True
    return False


def _extract_lang_value(multilang: dict[str, Any], language: str) -> Optional[str]:
    entry = multilang.get(language)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return value if isinstance(value, str) else None


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FoundationProfileError(
            f"Required foundation profile file not found: {path}"
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise FoundationProfileError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise FoundationProfileError(
            f"Top-level YAML structure must be a mapping: {path}"
        )
    return raw


def _require_text(container: dict[str, Any], key: str, *, context: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FoundationProfileError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FoundationProfileError("Expected string value")
    text = value.strip()
    return text if text else None


def _optional_identifier(value: Any) -> Optional[str]:
    text = _optional_text(value)
    if text is None:
        return None
    if not _looks_like_id(text):
        raise FoundationProfileError(
            f"Identifier '{text}' must match Q<number> or P<number>"
        )
    return text.upper()


def _looks_like_id(value: str) -> bool:
    return bool(_ID_PATTERN.match(value.strip()))
