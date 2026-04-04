"""Tests for shipper module.

Covers base classes, result types, WikibaseShipper, and placeholder shippers.
"""

import json
from unittest.mock import Mock

import gkc.shipper as shipper_module
from gkc.shipper import (
    CommonsShipper,
    OpenStreetMapShipper,
    Shipper,
    WikibaseShipper,
    WriteResult,
)


class FakeAuth:
    """Minimal auth double for shipper tests."""

    def __init__(self):
        self.api_url = "https://www.wikidata.org/w/api.php"
        self.session = Mock()
        self._logged_in = False
        self.login_called = False

    def is_logged_in(self) -> bool:
        return self._logged_in

    def login(self) -> None:
        self._logged_in = True
        self.login_called = True

    def get_csrf_token(self) -> str:
        return "csrf_token"


class FakeOsmAuth:
    """Minimal OSM auth double."""

    pass


def _basic_payload() -> dict:
    return {
        "labels": {"en": {"language": "en", "value": "Test"}},
        "descriptions": {"en": {"language": "en", "value": "Desc"}},
    }


# ============================================================================
# Base Classes and Result Types
# ============================================================================


def test_write_result_to_dict_and_json():
    """Serialize write results to dict and JSON."""
    result = WriteResult(
        entity_id="Q1",
        revision_id=10,
        status="dry_run",
        warnings=["note"],
        api_response={"ok": True},
        request_payload={"labels": {}},
        metadata={"run_id": "test"},
    )

    as_dict = result.to_dict()
    assert as_dict["entity_id"] == "Q1"
    assert as_dict["revision_id"] == 10
    assert as_dict["status"] == "dry_run"
    assert as_dict["warnings"] == ["note"]
    assert as_dict["api_response"] == {"ok": True}
    assert as_dict["request_payload"] == {"labels": {}}
    assert as_dict["metadata"] == {"run_id": "test"}

    as_json = result.to_json()
    assert '"entity_id"' in as_json


def test_shipper_write_raises():
    """Ensure base shipper raises for unimplemented write."""
    shipper = Shipper()

    try:
        shipper.write({})
    except NotImplementedError as exc:
        assert "Shipper.write" in str(exc)
    else:
        raise AssertionError("Shipper.write should raise NotImplementedError")


# ============================================================================
# WikibaseShipper Core Functionality
# ============================================================================


def test_wikibase_shipper_write_item_dry_run():
    """Dry run returns payload and skips network."""
    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)

    result = shipper.write_item(
        _basic_payload(),
        summary="Dry run",
        dry_run=True,
    )

    assert result.status == "dry_run"
    auth.session.post.assert_not_called()


def test_wikibase_shipper_write_item_validate_only():
    """Validation-only blocks writes without labels."""
    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)

    result = shipper.write_item(
        {"descriptions": {"en": {"language": "en", "value": "Desc"}}},
        summary="Validate only",
        validate_only=True,
    )

    assert result.status == "blocked"
    assert any("labels" in warning for warning in result.warnings)
    auth.session.post.assert_not_called()


def test_wikibase_shipper_write_item_submit():
    """Submit sends a wbeditentity request."""
    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth, dry_run_default=False)

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "entity": {"id": "Q123", "lastrevid": 42},
    }
    auth.session.post.return_value = response

    result = shipper.write_item(
        _basic_payload(),
        summary="Submit",
        dry_run=False,
        tags=["gkc"],
        bot=True,
    )

    assert auth.login_called
    assert result.status == "submitted"
    assert result.entity_id == "Q123"
    assert result.revision_id == 42

    auth.session.post.assert_called_once()
    call_args = auth.session.post.call_args
    sent_data = call_args[1]["data"]
    assert sent_data["action"] == "wbeditentity"
    assert sent_data["summary"] == "Submit"
    assert sent_data["tags"] == "gkc"
    assert sent_data["bot"] == "1"
    assert "data" in sent_data


def test_wikibase_shipper_write_property_submit():
    """Property create sends datatype inside the wbeditentity data JSON payload."""
    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth, dry_run_default=False)

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "entity": {"id": "P123", "lastrevid": 77},
    }
    auth.session.post.return_value = response

    payload = {
        "labels": {"en": {"language": "en", "value": "Probe property"}},
        "descriptions": {"en": {"language": "en", "value": "Probe desc"}},
    }

    result = shipper.write_property(
        payload=payload,
        summary="Create property",
        datatype="wikibase-item",
        dry_run=False,
        bot=True,
    )

    assert auth.login_called
    assert result.status == "submitted"
    assert result.entity_id == "P123"

    auth.session.post.assert_called_once()
    call_args = auth.session.post.call_args
    sent_data = call_args[1]["data"]
    assert sent_data["action"] == "wbeditentity"
    assert sent_data["new"] == "property"
    assert "datatype" not in sent_data
    assert sent_data["bot"] == "1"

    posted_entity_data = json.loads(sent_data["data"])
    assert posted_entity_data["datatype"] == "wikibase-item"
    assert posted_entity_data["labels"]["en"]["value"] == "Probe property"


def test_wikibase_shipper_write_property_canonicalizes_datatype_alias():
    """Property create normalizes known datatype aliases before submission."""
    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth, dry_run_default=False)

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "entity": {"id": "P124", "lastrevid": 78},
    }
    auth.session.post.return_value = response

    shipper.write_property(
        payload=_basic_payload(),
        summary="Create property alias datatype",
        datatype="item",
        dry_run=False,
    )

    sent_data = auth.session.post.call_args[1]["data"]
    posted_entity_data = json.loads(sent_data["data"])
    assert posted_entity_data["datatype"] == "wikibase-item"


# ============================================================================
# WikibaseShipper Planning (Batch Operations)
# ============================================================================


def test_wikibase_shipper_plan_batch_create(monkeypatch):
    """Plan reports create when no matching label exists."""

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            pass

        def search_entities(self, label, entity_type, language):
            return []

        def get_entity(self, entity_id):
            raise AssertionError("get_entity should not be called for create plan")

    monkeypatch.setattr(shipper_module, "WikibaseApiClient", FakeApiClient)

    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)
    plan = shipper.plan_batch(
        [
            {
                "kind": "item",
                "label": "New Entity",
                "payload": {
                    "labels": {"en": {"language": "en", "value": "New Entity"}},
                },
            }
        ]
    )

    assert plan.summary["create"] == 1
    assert plan.operations[0].status == "create"


def test_wikibase_shipper_plan_batch_ambiguous(monkeypatch):
    """Plan reports ambiguous when multiple exact labels are found."""

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            pass

        def search_entities(self, label, entity_type, language):
            return [
                {"id": "Q1", "label": label},
                {"id": "Q2", "label": label},
            ]

        def get_entity(self, entity_id):
            raise AssertionError("get_entity should not be called for ambiguous plan")

    monkeypatch.setattr(shipper_module, "WikibaseApiClient", FakeApiClient)

    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)
    plan = shipper.plan_batch(
        [
            {
                "kind": "item",
                "label": "Dup Entity",
                "payload": {
                    "labels": {"en": {"language": "en", "value": "Dup Entity"}},
                },
            }
        ]
    )

    assert plan.summary["ambiguous"] == 1
    assert plan.operations[0].status == "ambiguous"


def test_wikibase_shipper_plan_batch_update_and_noop(monkeypatch):
    """Plan reports update when data differs and noop when equal."""

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            pass

        def search_entities(self, label, entity_type, language):
            return [{"id": "Q10", "label": label}]

        def get_entity(self, entity_id):
            return {
                "id": entity_id,
                "labels": {"en": {"language": "en", "value": "Entity"}},
                "descriptions": {"en": {"language": "en", "value": "Old desc"}},
                "claims": {},
            }

    monkeypatch.setattr(shipper_module, "WikibaseApiClient", FakeApiClient)

    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)
    plan = shipper.plan_batch(
        [
            {
                "kind": "item",
                "label": "Entity",
                "payload": {
                    "labels": {"en": {"language": "en", "value": "Entity"}},
                    "descriptions": {"en": {"language": "en", "value": "New desc"}},
                },
            },
            {
                "kind": "item",
                "label": "Entity",
                "payload": {
                    "labels": {"en": {"language": "en", "value": "Entity"}},
                    "descriptions": {"en": {"language": "en", "value": "Old desc"}},
                },
            },
        ]
    )

    assert plan.summary["update"] == 1
    assert plan.summary["noop"] == 1
    assert plan.operations[0].status == "update"
    assert plan.operations[0].request_payload == {
        "descriptions": {"en": {"language": "en", "value": "New desc"}}
    }
    assert plan.operations[1].status == "noop"


def test_wikibase_shipper_plan_batch_property_requires_datatype(monkeypatch):
    """Plan blocks property creation when datatype is missing."""

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            pass

        def search_entities(self, label, entity_type, language):
            return []

        def get_entity(self, entity_id):
            raise AssertionError("get_entity should not be called")

    monkeypatch.setattr(shipper_module, "WikibaseApiClient", FakeApiClient)

    auth = FakeAuth()
    shipper = WikibaseShipper(auth=auth)
    plan = shipper.plan_batch(
        [
            {
                "kind": "property",
                "label": "new prop",
                "payload": {
                    "labels": {"en": {"language": "en", "value": "new prop"}},
                },
            }
        ]
    )

    assert plan.summary["blocked"] == 1
    assert plan.operations[0].status == "blocked"
    assert "datatype" in " ".join(plan.operations[0].reasons)


# ============================================================================
# Placeholder Shippers
# ============================================================================


def test_commons_shipper_not_implemented():
    """CommonsShipper.write raises NotImplementedError."""
    auth = FakeAuth()
    shipper = CommonsShipper(auth=auth)

    try:
        shipper.write({"filename": "test.jpg"})
    except NotImplementedError as exc:
        assert "CommonsShipper.write" in str(exc)
    else:
        raise AssertionError("CommonsShipper.write should raise NotImplementedError")


def test_osm_shipper_not_implemented():
    """OpenStreetMapShipper.write raises NotImplementedError."""
    auth = FakeOsmAuth()
    shipper = OpenStreetMapShipper(auth=auth)

    try:
        shipper.write({"type": "node"})
    except NotImplementedError as exc:
        assert "OpenStreetMapShipper.write" in str(exc)
    else:
        raise AssertionError(
            "OpenStreetMapShipper.write should raise NotImplementedError"
        )
