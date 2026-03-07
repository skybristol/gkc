"""Tests for Wikibase foundation profile loading and label-first auditing."""

import json

from gkc.wikibase.foundation import (
    FoundationProfileError,
    audit_wikibase_foundation,
    init_wikibase_foundation,
    load_foundation_profiles,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, search_results=None, entities=None):
        self.search_results = search_results or {}
        self.entities = entities or {}

    def get(self, api_url, params=None, timeout=20):
        action = (params or {}).get("action")
        if action == "wbsearchentities":
            label = params.get("search")
            entity_type = params.get("type")
            key = (entity_type, label)
            return _FakeResponse({"search": self.search_results.get(key, [])})

        if action == "wbgetentities":
            entity_id = params.get("ids")
            return _FakeResponse({"entities": {entity_id: self.entities[entity_id]}})

        raise AssertionError(f"Unexpected action: {action}")


def test_load_foundation_profiles_label_first(tmp_path):
    """Profiles can omit IDs and still load successfully."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: entity
  - label: GKC Entity Profile
    required_claims:
      - property: subclass of
        value: entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: subclass of
    datatype: wikibase-item
""".strip(),
        encoding="utf-8",
    )

    profiles = load_foundation_profiles(tmp_path)

    assert len(profiles.entities) == 2
    assert profiles.entities[0].identifier is None
    assert profiles.entities[1].required_claims[0].property_ref == "subclass of"
    assert len(profiles.properties) == 1


def test_load_foundation_profiles_invalid_identifier(tmp_path):
    """Invalid IDs are rejected when present."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: entity
    qid: X1
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: instance of
""".strip(),
        encoding="utf-8",
    )

    try:
        load_foundation_profiles(tmp_path)
    except FoundationProfileError as exc:
        assert "must match Q<number> or P<number>" in str(exc)
    else:
        raise AssertionError("Expected FoundationProfileError")


def test_audit_wikibase_foundation_resolves_ids_from_labels(tmp_path):
    """Audit resolves IDs by exact label and validates required claims."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: GKC Entity Profile
    required_claims:
      - property: subclass of
        value: entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: subclass of
    datatype: wikibase-item
""".strip(),
        encoding="utf-8",
    )

    search_results = {
        ("property", "subclass of"): [{"id": "P2", "label": "subclass of"}],
        ("item", "GKC Entity Profile"): [{"id": "Q3", "label": "GKC Entity Profile"}],
        ("item", "entity"): [{"id": "Q1", "label": "entity"}],
    }

    entities = {
        "P2": {
            "id": "P2",
            "datatype": "wikibase-item",
            "descriptions": {},
            "claims": {},
        },
        "Q3": {
            "id": "Q3",
            "descriptions": {},
            "claims": {
                "P2": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"id": "Q1"},
                            }
                        }
                    }
                ]
            },
        },
        "Q1": {
            "id": "Q1",
            "descriptions": {},
            "claims": {},
        },
    }

    report = audit_wikibase_foundation(
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        session=_FakeSession(search_results=search_results, entities=entities),
    )

    assert report.ok is True
    assert report.summary["conformant"] == 2
    assert report.resolved_identifiers["property:subclass of"] == "P2"
    assert report.resolved_identifiers["entity:GKC Entity Profile"] == "Q3"


def test_audit_wikibase_foundation_reports_missing(tmp_path):
    """Missing entities are surfaced in summary and records."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: Missing Entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: subclass of
""".strip(),
        encoding="utf-8",
    )

    report = audit_wikibase_foundation(
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        session=_FakeSession(search_results={}, entities={}),
    )

    assert report.ok is False
    assert report.summary["missing"] == 2
    serialized = json.dumps(report.to_dict())
    assert "Missing Entity" in serialized


def test_init_wikibase_foundation_creates_missing_property(tmp_path):
    """Init creates a missing property with correct datatype."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities: []
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: test property
    description: a test property
    datatype: string
""".strip(),
        encoding="utf-8",
    )

    class FakeUnifiedSession:
        """Fake session supporting both GET (audit/API client) and POST (shipper)."""

        def __init__(self):
            self.writes = []

        def get(self, url, params=None, timeout=20):
            # Return empty search results for audit label lookups
            if params and params.get("action") == "wbsearchentities":
                return _FakeResponse({"search": []})
            return _FakeResponse({})

        def post(self, url, data):
            self.writes.append(data)
            return _FakeResponse(
                {
                    "entity": {
                        "id": "P1",
                        "lastrevid": 100,
                    }
                }
            )

    class FakeAuth:
        api_url = "https://example.org/w/api.php"

        def __init__(self):
            self.session = FakeUnifiedSession()

        def is_logged_in(self):
            return True

        def get_csrf_token(self):
            return "fake-token"

    fake_auth = FakeAuth()

    report = init_wikibase_foundation(
        auth=fake_auth,
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        dry_run=False,
    )

    assert report.ok is True
    assert report.summary["created"] == 1
    assert len(report.actions) == 1
    assert report.actions[0].action == "created"
    assert report.actions[0].label == "test property"
    assert report.actions[0].entity_id == "P1"
    assert len(fake_auth.session.writes) == 1
    write_data = fake_auth.session.writes[0]
    assert write_data["new"] == "property"
    posted_entity_data = json.loads(write_data["data"])
    assert posted_entity_data["datatype"] == "string"


def test_init_wikibase_foundation_creates_missing_entity(tmp_path):
    """Init creates a missing entity."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: test entity
    description: a test entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties: []
""".strip(),
        encoding="utf-8",
    )

    class FakeUnifiedSession:
        """Fake session supporting both GET (audit/API client) and POST (shipper)."""

        def __init__(self):
            self.writes = []

        def get(self, url, params=None, timeout=20):
            # Return empty search results for audit label lookups
            if params and params.get("action") == "wbsearchentities":
                return _FakeResponse({"search": []})
            return _FakeResponse({})

        def post(self, url, data):
            self.writes.append(data)
            return _FakeResponse(
                {
                    "entity": {
                        "id": "Q1",
                        "lastrevid": 100,
                    }
                }
            )

    class FakeAuth:
        api_url = "https://example.org/w/api.php"

        def __init__(self):
            self.session = FakeUnifiedSession()

        def is_logged_in(self):
            return True

        def get_csrf_token(self):
            return "fake-token"

    fake_auth = FakeAuth()

    report = init_wikibase_foundation(
        auth=fake_auth,
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        dry_run=False,
    )

    assert report.ok is True
    assert report.summary["created"] == 1
    assert len(report.actions) == 1
    assert report.actions[0].action == "created"
    assert report.actions[0].label == "test entity"
    assert report.actions[0].entity_id == "Q1"
    assert len(fake_auth.session.writes) == 1
    write_data = fake_auth.session.writes[0]
    assert write_data["new"] == "item"


def test_init_wikibase_foundation_dry_run(tmp_path):
    """Init in dry-run mode does not submit writes."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: test entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: test property
    datatype: string
""".strip(),
        encoding="utf-8",
    )

    class FakeUnifiedSession:
        """Fake session supporting both GET (audit/API client) and POST (shipper)."""

        def __init__(self):
            self.writes = []

        def get(self, url, params=None, timeout=20):
            # Return empty search results for audit label lookups
            if params and params.get("action") == "wbsearchentities":
                return _FakeResponse({"search": []})
            return _FakeResponse({})

        def post(self, url, data):
            self.writes.append(data)
            raise AssertionError("Should not submit writes in dry-run mode")

    class FakeAuth:
        api_url = "https://example.org/w/api.php"

        def __init__(self):
            self.session = FakeUnifiedSession()

        def is_logged_in(self):
            return True

    fake_auth = FakeAuth()

    report = init_wikibase_foundation(
        auth=fake_auth,
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        dry_run=True,
    )

    assert report.summary["dry_run"] == 2
    assert report.summary["created"] == 0
    assert len(report.actions) == 2
    assert all(action.action == "dry_run" for action in report.actions)
    assert len(fake_auth.session.writes) == 0


def test_init_wikibase_foundation_dependency_order_and_claim_enrichment(tmp_path):
    """Init creates dependencies first, then enriches dependent entities with claims."""
    (tmp_path / "foundation_entities.yaml").write_text(
        """
entities:
  - label: entity
    description: root
  - label: child entity
    description: child
    required_claims:
      - property: subclass of
        value: entity
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "foundation_properties.yaml").write_text(
        """
properties:
  - label: subclass of
    description: subclass relation
    datatype: wikibase-item
""".strip(),
        encoding="utf-8",
    )

    class FakeUnifiedSession:
        """Fake session supporting audit reads and ordered write responses."""

        def __init__(self):
            self.writes = []

        def get(self, url, params=None, timeout=20):
            if params and params.get("action") == "wbsearchentities":
                return _FakeResponse({"search": []})
            return _FakeResponse({})

        def post(self, url, data):
            self.writes.append(data)
            write_index = len(self.writes)
            if write_index == 1:
                entity_id = "P2"
            elif write_index == 2:
                entity_id = "Q1"
            elif write_index == 3:
                entity_id = "Q2"
            else:
                entity_id = data.get("id", "Q2")

            return _FakeResponse(
                {
                    "entity": {
                        "id": entity_id,
                        "lastrevid": 100 + write_index,
                    }
                }
            )

    class FakeAuth:
        api_url = "https://example.org/w/api.php"

        def __init__(self):
            self.session = FakeUnifiedSession()

        def is_logged_in(self):
            return True

        def get_csrf_token(self):
            return "fake-token"

    fake_auth = FakeAuth()

    report = init_wikibase_foundation(
        auth=fake_auth,
        api_url="https://example.org/w/api.php",
        profile_dir=tmp_path,
        dry_run=False,
    )

    assert report.ok is True
    assert report.summary["created"] == 3
    assert report.summary["updated"] == 1

    # Write order: property create -> root entity create -> child entity create -> child claims update
    assert len(fake_auth.session.writes) == 4

    property_create = fake_auth.session.writes[0]
    root_entity_create = fake_auth.session.writes[1]
    child_entity_create = fake_auth.session.writes[2]
    child_claim_update = fake_auth.session.writes[3]

    assert property_create.get("new") == "property"
    assert root_entity_create.get("new") == "item"
    assert child_entity_create.get("new") == "item"
    assert child_claim_update.get("id") == "Q2"
    assert child_claim_update.get("new") is None

    claim_update_data = json.loads(child_claim_update["data"])
    claims = claim_update_data["claims"]
    assert len(claims) == 1
    mainsnak = claims[0]["mainsnak"]
    assert mainsnak["property"] == "P2"
    assert mainsnak["datavalue"]["value"]["id"] == "Q1"
    assert mainsnak["datavalue"]["value"]["entity-type"] == "item"
