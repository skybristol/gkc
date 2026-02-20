"""
Shipper: Deliver Bottled output to external systems.

This module defines shippers responsible for write operations to external
systems such as Wikidata, Wikimedia Commons, and OpenStreetMap.

Plain meaning: Send Bottled output to target APIs in a safe, testable way.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from gkc.auth import OpenStreetMapAuth, WikiverseAuth


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


class Shipper:
    """Base class for shippers.

    Plain meaning: A shared interface for writing Bottled output to targets.
    """

    def write(self, payload: dict, **kwargs: Any) -> WriteResult:
        """Write the payload to a target system.

        Plain meaning: Deliver Bottled output to an external API.
        """

        raise NotImplementedError("Shipper.write must be implemented by subclasses")


class WikidataShipper(Shipper):
    """Shipper for Wikidata write operations.

    Plain meaning: Submit Bottled output to the Wikidata API.
    """

    def __init__(
        self,
        auth: WikiverseAuth,
        api_url: Optional[str] = None,
        dry_run_default: bool = True,
    ):
        """Initialize the Wikidata shipper.

        Plain meaning: Store auth details and default write behavior.
        """

        self.auth = auth
        self.api_url = api_url or auth.api_url
        self.dry_run_default = dry_run_default

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
        """Create or update a Wikidata item.

        Plain meaning: Build a request for wbeditentity, optionally submit it,
        and return a stable result summary.
        """

        if not summary or not summary.strip():
            raise ValueError("summary is required for Wikidata write operations")

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

    def _ensure_authenticated(self) -> None:
        if not self.auth.is_logged_in():
            self.auth.login()

    def _normalize_payload(self, payload: dict) -> dict:
        return copy.deepcopy(payload)

    def _validate_payload(self, payload: dict) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        is_valid = True

        labels = payload.get("labels")
        if not labels or not isinstance(labels, dict):
            warnings.append("Missing labels in payload")
            is_valid = False

        descriptions = payload.get("descriptions")
        if not descriptions or not isinstance(descriptions, dict):
            warnings.append("Missing descriptions in payload")
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
