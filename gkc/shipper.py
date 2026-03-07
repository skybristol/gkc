"""
Shipper: Deliver Bottled output to external systems.

This module defines shippers responsible for write operations to external
systems such as Wikibase instances, Wikimedia Commons, and OpenStreetMap.

Plain meaning: Send Bottled output to target APIs in a safe, testable way.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from gkc.auth import OpenStreetMapAuth, WikiverseAuth
from gkc.mash import WikibaseApiClient


class ShipperError(Exception):
    """Raised when a shipper operation fails.

    Plain meaning: A write or validation step failed.
    """


@dataclass
class WriteResult:
    """Result summary for write operations.

    Plain meaning: A stable summary of what happened during a write.
    """

    entity_id: Optional[str]
    revision_id: Optional[int]
    status: str
    warnings: list[str] = field(default_factory=list)
    api_response: dict = field(default_factory=dict)
    request_payload: Optional[dict] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary.

        Plain meaning: Convert the result into a simple dict.
        """

        return {
            "entity_id": self.entity_id,
            "revision_id": self.revision_id,
            "status": self.status,
            "warnings": list(self.warnings),
            "api_response": dict(self.api_response),
            "request_payload": copy.deepcopy(self.request_payload),
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        """Serialize the result to JSON.

        Plain meaning: Turn the result into a JSON string.
        """

        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass
class DiffOperation:
    """Planned diff operation for a Wikibase entity or property.

    Plain meaning: One create/update/no-op decision with payload details.
    """

    kind: str
    label: str
    status: str
    entity_id: Optional[str] = None
    reasons: list[str] = field(default_factory=list)
    request_payload: Optional[dict] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "entity_id": self.entity_id,
            "reasons": list(self.reasons),
            "request_payload": copy.deepcopy(self.request_payload),
            "metadata": dict(self.metadata),
        }


@dataclass
class DiffPlan:
    """Aggregated planning result for a batch write operation.

    Plain meaning: What will be created/updated/skipped before writing.
    """

    operations: list[DiffOperation]
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": dict(self.summary),
            "operations": [operation.to_dict() for operation in self.operations],
        }


class Shipper:
    """Base class for shippers.

    Plain meaning: A shared interface for writing Bottled output to targets.
    """

    def write(self, payload: dict, **kwargs: Any) -> WriteResult:
        """Write the payload to a target system.

        Plain meaning: Deliver Bottled output to an external API.
        """

        raise NotImplementedError("Shipper.write must be implemented by subclasses")


class WikibaseShipper(Shipper):
    """Shipper for Wikibase write operations.

    Plain meaning: Submit Bottled output to any Wikibase instance API.
    """

    def __init__(
        self,
        auth: WikiverseAuth,
        api_url: Optional[str] = None,
        dry_run_default: bool = True,
    ):
        """Initialize the Wikibase shipper.

        Plain meaning: Store auth details and default write behavior.
        """

        self.auth = auth
        self.api_url = api_url or auth.api_url
        self.dry_run_default = dry_run_default

    def plan_batch(
        self,
        operations: list[dict[str, Any]],
        *,
        language: str = "en",
    ) -> DiffPlan:
        """Build a create/update/no-op plan for a batch of Wikibase writes.

        Each operation supports:
          - kind: "item" or "property"
          - label: string label used for matching when entity_id not provided
          - payload: desired wbeditentity JSON fragment
          - entity_id: optional explicit target ID
          - datatype: optional for property creation checks

        Plain meaning: Preview what will be created or changed before writing.
        """

        api = WikibaseApiClient(
            api_url=self.api_url,
            session=self.auth.session if self.auth.is_logged_in() else None,
            timeout=20,
        )

        planned: list[DiffOperation] = []
        for raw in operations:
            planned.append(
                self._plan_single_operation(
                    raw,
                    api=api,
                    language=language,
                )
            )

        summary = {
            "total": len(planned),
            "create": sum(1 for op in planned if op.status == "create"),
            "update": sum(1 for op in planned if op.status == "update"),
            "noop": sum(1 for op in planned if op.status == "noop"),
            "ambiguous": sum(1 for op in planned if op.status == "ambiguous"),
            "blocked": sum(1 for op in planned if op.status == "blocked"),
        }
        return DiffPlan(operations=planned, summary=summary)

    def write_item(
        self,
        payload: dict,
        summary: str,
        entity_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        validate_only: bool = False,
        tags: Optional[list[str]] = None,
        bot: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> WriteResult:
        """Create or update a Wikibase item.

        Plain meaning: Build a request for wbeditentity, optionally submit it,
        and return a stable result summary.
        """

        if not summary or not summary.strip():
            raise ValueError("summary is required for Wikibase write operations")

        effective_dry_run = self.dry_run_default if dry_run is None else dry_run
        normalized_payload = self._normalize_payload(payload)

        is_valid, warnings = self._validate_payload(normalized_payload)
        result_metadata = metadata or {}

        if validate_only:
            status = "validated" if is_valid else "blocked"
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status=status,
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        if not is_valid:
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="blocked",
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        if effective_dry_run:
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="dry_run",
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        self._ensure_authenticated()
        csrf_token = self.auth.get_csrf_token()

        request_data = self._build_request_data(
            payload=normalized_payload,
            summary=summary,
            entity_id=entity_id,
            csrf_token=csrf_token,
            tags=tags,
            bot=bot,
        )

        response = self.auth.session.post(self.api_url, data=request_data)
        response.raise_for_status()
        response_json = response.json()

        if "error" in response_json:
            warnings.append(self._format_api_error(response_json["error"]))
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="error",
                warnings=warnings,
                api_response=response_json,
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        response_entity = response_json.get("entity", {})
        response_entity_id = response_entity.get("id") or entity_id
        revision_id = response_entity.get("lastrevid")

        return WriteResult(
            entity_id=response_entity_id,
            revision_id=revision_id,
            status="submitted",
            warnings=warnings,
            api_response=response_json,
            request_payload=normalized_payload,
            metadata=result_metadata,
        )

    def write_property(
        self,
        payload: dict,
        summary: str,
        datatype: str,
        entity_id: Optional[str] = None,
        dry_run: Optional[bool] = None,
        validate_only: bool = False,
        tags: Optional[list[str]] = None,
        bot: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> WriteResult:
        """Create or update a Wikibase property.

        Plain meaning: Build a request for wbeditentity (property variant),
        optionally submit it, and return a stable result summary.
        """

        if not summary or not summary.strip():
            raise ValueError("summary is required for Wikibase write operations")

        if not entity_id and not datatype:
            raise ValueError("datatype is required when creating a new property")

        effective_dry_run = self.dry_run_default if dry_run is None else dry_run
        normalized_payload = self._normalize_payload(payload)

        is_valid, warnings = self._validate_payload(normalized_payload)
        result_metadata = metadata or {}

        if validate_only:
            status = "validated" if is_valid else "blocked"
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status=status,
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        if not is_valid:
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="blocked",
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        if effective_dry_run:
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="dry_run",
                warnings=warnings,
                api_response={},
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        self._ensure_authenticated()
        csrf_token = self.auth.get_csrf_token()

        request_data = self._build_property_request_data(
            payload=normalized_payload,
            summary=summary,
            datatype=datatype,
            entity_id=entity_id,
            csrf_token=csrf_token,
            tags=tags,
            bot=bot,
        )

        response = self.auth.session.post(self.api_url, data=request_data)
        response.raise_for_status()
        response_json = response.json()

        if "error" in response_json:
            warnings.append(self._format_api_error(response_json["error"]))
            return WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="error",
                warnings=warnings,
                api_response=response_json,
                request_payload=normalized_payload,
                metadata=result_metadata,
            )

        response_entity = response_json.get("entity", {})
        response_entity_id = response_entity.get("id") or entity_id
        revision_id = response_entity.get("lastrevid")

        return WriteResult(
            entity_id=response_entity_id,
            revision_id=revision_id,
            status="submitted",
            warnings=warnings,
            api_response=response_json,
            request_payload=normalized_payload,
            metadata=result_metadata,
        )

    def _ensure_authenticated(self) -> None:
        if not self.auth.is_logged_in():
            self.auth.login()

    def _plan_single_operation(
        self,
        operation: dict[str, Any],
        *,
        api: WikibaseApiClient,
        language: str,
    ) -> DiffOperation:
        kind = str(operation.get("kind") or "item").strip().lower()
        label = str(operation.get("label") or "").strip()
        payload = operation.get("payload") or {}
        entity_id = operation.get("entity_id")
        datatype = operation.get("datatype")

        if kind not in {"item", "property"}:
            return DiffOperation(
                kind=kind,
                label=label,
                status="blocked",
                reasons=["Unsupported kind; expected 'item' or 'property'"],
                request_payload=None,
            )

        if not isinstance(payload, dict):
            return DiffOperation(
                kind=kind,
                label=label,
                status="blocked",
                reasons=["payload must be a mapping"],
                request_payload=None,
            )

        is_valid, warnings = self._validate_payload(payload)
        if not is_valid:
            return DiffOperation(
                kind=kind,
                label=label,
                status="blocked",
                reasons=warnings,
                request_payload=copy.deepcopy(payload),
            )

        entity_type = "property" if kind == "property" else "item"
        target_id = entity_id

        if not target_id:
            if not label:
                return DiffOperation(
                    kind=kind,
                    label=label,
                    status="blocked",
                    reasons=["label is required when entity_id is not provided"],
                    request_payload=copy.deepcopy(payload),
                )

            matches = self._search_exact_label(
                api=api,
                label=label,
                entity_type=entity_type,
                language=language,
            )
            if len(matches) > 1:
                return DiffOperation(
                    kind=kind,
                    label=label,
                    status="ambiguous",
                    reasons=[
                        "Multiple exact label matches found: "
                        + ", ".join(match["id"] for match in matches)
                    ],
                    request_payload=None,
                )

            if len(matches) == 1:
                target_id = matches[0]["id"]

        if not target_id:
            create_reasons: list[str] = []
            if kind == "property" and not datatype:
                return DiffOperation(
                    kind=kind,
                    label=label,
                    status="blocked",
                    reasons=["datatype is required to create a property"],
                    request_payload=copy.deepcopy(payload),
                )

            create_reasons.append("No matching entity found by exact label")
            return DiffOperation(
                kind=kind,
                label=label,
                status="create",
                entity_id=None,
                reasons=create_reasons,
                request_payload=copy.deepcopy(payload),
                metadata={"datatype": datatype} if datatype else {},
            )

        existing = api.get_entity(target_id)
        patch, diff_reasons = self._build_patch_payload(
            existing=existing,
            desired=payload,
            language=language,
            kind=kind,
            desired_datatype=datatype,
        )

        if not patch:
            return DiffOperation(
                kind=kind,
                label=label,
                status="noop",
                entity_id=target_id,
                reasons=["No differences detected"],
                request_payload=None,
            )

        return DiffOperation(
            kind=kind,
            label=label,
            status="update",
            entity_id=target_id,
            reasons=diff_reasons,
            request_payload=patch,
            metadata={"datatype": datatype} if datatype else {},
        )

    def _search_exact_label(
        self,
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

    def _build_patch_payload(
        self,
        *,
        existing: dict[str, Any],
        desired: dict[str, Any],
        language: str,
        kind: str,
        desired_datatype: Optional[str],
    ) -> tuple[dict[str, Any], list[str]]:
        patch: dict[str, Any] = {}
        reasons: list[str] = []

        desired_labels = desired.get("labels")
        if isinstance(desired_labels, dict):
            labels_patch: dict[str, Any] = {}
            existing_labels = existing.get("labels", {})
            for lang, entry in desired_labels.items():
                desired_value = (
                    (entry or {}).get("value") if isinstance(entry, dict) else None
                )
                existing_value = (existing_labels.get(lang) or {}).get("value")
                if desired_value is not None and desired_value != existing_value:
                    labels_patch[lang] = entry

            if labels_patch:
                patch["labels"] = labels_patch
                reasons.append("labels differ")

        desired_descriptions = desired.get("descriptions")
        if isinstance(desired_descriptions, dict):
            descriptions_patch: dict[str, Any] = {}
            existing_descriptions = existing.get("descriptions", {})
            for lang, entry in desired_descriptions.items():
                desired_value = (
                    (entry or {}).get("value") if isinstance(entry, dict) else None
                )
                existing_value = (existing_descriptions.get(lang) or {}).get("value")
                if desired_value is not None and desired_value != existing_value:
                    descriptions_patch[lang] = entry

            if descriptions_patch:
                patch["descriptions"] = descriptions_patch
                reasons.append("descriptions differ")

        desired_claims = desired.get("claims")
        if isinstance(desired_claims, list) and desired_claims:
            existing_claims = existing.get("claims", {})
            missing_claims = [
                claim
                for claim in desired_claims
                if not self._entity_has_matching_claim(existing_claims, claim)
            ]
            if missing_claims:
                patch["claims"] = missing_claims
                reasons.append("claims differ")

        if kind == "property" and desired_datatype:
            existing_datatype = existing.get("datatype")
            if existing_datatype != desired_datatype:
                reasons.append(
                    "datatype differs "
                    f"(existing={existing_datatype}, desired={desired_datatype})"
                )

        return patch, reasons

    def _entity_has_matching_claim(
        self,
        existing_claims: dict[str, Any],
        desired_claim: dict[str, Any],
    ) -> bool:
        desired_mainsnak = desired_claim.get("mainsnak", {})
        desired_property = desired_mainsnak.get("property")
        desired_datavalue = desired_mainsnak.get("datavalue", {})
        desired_value = desired_datavalue.get("value")

        if not desired_property:
            return False

        existing_property_claims = existing_claims.get(desired_property) or []
        for existing_claim in existing_property_claims:
            existing_value = (
                existing_claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            )
            if existing_value == desired_value:
                return True

        return False

    def _normalize_payload(self, payload: dict) -> dict:
        return copy.deepcopy(payload)

    def _validate_payload(self, payload: dict) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        is_valid = True

        claims = payload.get("claims")
        if claims is not None:
            if not isinstance(claims, list):
                warnings.append("Claims payload must be a list when provided")
                is_valid = False
            # Claims-only update payloads are valid for wbeditentity updates.
            return is_valid, warnings

        labels = payload.get("labels")
        if not labels or not isinstance(labels, dict):
            warnings.append("Missing labels in payload")
            is_valid = False

        return is_valid, warnings

    def _build_request_data(
        self,
        payload: dict,
        summary: str,
        entity_id: Optional[str],
        csrf_token: str,
        tags: Optional[list[str]],
        bot: bool,
    ) -> dict:
        request_data = {
            "action": "wbeditentity",
            "format": "json",
            "token": csrf_token,
            "data": json.dumps(payload),
            "summary": summary,
        }

        if entity_id:
            request_data["id"] = entity_id
        else:
            request_data["new"] = "item"

        if tags:
            request_data["tags"] = "|".join(tags)

        if bot:
            request_data["bot"] = "1"

        return request_data

    def _build_property_request_data(
        self,
        payload: dict,
        summary: str,
        datatype: str,
        entity_id: Optional[str],
        csrf_token: str,
        tags: Optional[list[str]],
        bot: bool,
    ) -> dict:
        request_data = {
            "action": "wbeditentity",
            "format": "json",
            "token": csrf_token,
            "summary": summary,
        }

        if entity_id:
            request_data["data"] = json.dumps(payload)
            request_data["id"] = entity_id
        else:
            property_payload = copy.deepcopy(payload)
            property_payload["datatype"] = datatype
            request_data["data"] = json.dumps(property_payload)
            request_data["new"] = "property"

        if tags:
            request_data["tags"] = "|".join(tags)

        if bot:
            request_data["bot"] = "1"

        return request_data

    def _format_api_error(self, error: dict) -> str:
        code = error.get("code", "unknown")
        info = error.get("info", "Unknown API error")
        return f"API error {code}: {info}"


class CommonsShipper(Shipper):
    """Shipper scaffold for Wikimedia Commons.

    Plain meaning: Reserved for future Commons write support.
    """

    def __init__(self, auth: WikiverseAuth, api_url: Optional[str] = None):
        """Initialize the Commons shipper.

        Plain meaning: Store auth details for future Commons writes.
        """

        self.auth = auth
        self.api_url = api_url or auth.api_url

    def write(self, payload: dict, **kwargs: Any) -> WriteResult:
        """Write payload to Wikimedia Commons.

        Plain meaning: Placeholder for future Commons write support.
        """

        raise NotImplementedError("CommonsShipper.write is not implemented yet")


class OpenStreetMapShipper(Shipper):
    """Shipper scaffold for OpenStreetMap.

    Plain meaning: Reserved for future OpenStreetMap write support.
    """

    def __init__(self, auth: OpenStreetMapAuth):
        """Initialize the OpenStreetMap shipper.

        Plain meaning: Store auth details for future OpenStreetMap writes.
        """

        self.auth = auth

    def write(self, payload: dict, **kwargs: Any) -> WriteResult:
        """Write payload to OpenStreetMap.

        Plain meaning: Placeholder for future OpenStreetMap write support.
        """

        raise NotImplementedError("OpenStreetMapShipper.write is not implemented yet")


class WikidataShipper(WikibaseShipper):
    """Backward-compatible alias for WikibaseShipper.

    Plain meaning: Existing imports using WikidataShipper keep working.
    """
