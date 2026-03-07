"""Tests for Wikidata shipper."""

import json
from unittest.mock import Mock

import gkc.shipper as shipper_module
from gkc.shipper import WikidataShipper


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


def _basic_payload() -> dict:
    return {
        "labels": {"en": {"language": "en", "value": "Test"}},
        "descriptions": {"en": {"language": "en", "value": "Desc"}},
    }


def test_write_item_dry_run_does_not_post():
    """Dry run returns payload and skips network."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth)

    result = shipper.write_item(
        _basic_payload(),
        summary="Dry run",
        dry_run=True,
    )

    assert result.status == "dry_run"
    auth.session.post.assert_not_called()


def test_write_item_validate_only_blocks_missing_labels():
    """Validation-only blocks writes without labels."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth)

    result = shipper.write_item(
        {"descriptions": {"en": {"language": "en", "value": "Desc"}}},
        summary="Validate only",
        validate_only=True,
    )

    assert result.status == "blocked"
    assert any("labels" in warning for warning in result.warnings)
    auth.session.post.assert_not_called()


def test_write_item_submit_posts_request():
    """Submit sends a wbeditentity request."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth, dry_run_default=False)

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


def test_write_property_submit_embeds_datatype_in_data_json():
    """Property create sends datatype inside the wbeditentity data JSON payload."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth, dry_run_default=False)

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


def test_plan_batch_create_when_no_exact_match(monkeypatch):
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
    shipper = WikidataShipper(auth=auth)
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


def test_plan_batch_ambiguous_on_multiple_exact_matches(monkeypatch):
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
    shipper = WikidataShipper(auth=auth)
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


def test_plan_batch_update_and_noop(monkeypatch):
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
    shipper = WikidataShipper(auth=auth)
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


def test_plan_batch_property_create_requires_datatype(monkeypatch):
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
    shipper = WikidataShipper(auth=auth)
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
