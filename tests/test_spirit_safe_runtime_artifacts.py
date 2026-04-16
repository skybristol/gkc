"""Tests for SpiritSafe JSON profile and semantic-anchor workflows."""

import json
from pathlib import Path
from shutil import copytree

import pytest

from gkc.shipper import WriteResult
from gkc.spirit_safe import (
    build_spiritsafe_semantic_anchor_document,
    build_spiritsafe_wikibase_conformance_report,
    export_spiritsafe_semantic_anchors,
    load_profile,
    load_profile_package,
    resolve_profile_link,
    set_spirit_safe_source,
    sync_spiritsafe_wikibase_seed,
    validate_packet_structure,
)
from gkc.still_charger import create_curation_packet
from gkc.wikibase import get_wikibase_init_contract_digest


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "spiritsafe"


@pytest.fixture(autouse=True)
def setup_local_source(fixture_root: Path):
    """Configure SpiritSafe access to use deterministic local fixture artifacts."""

    set_spirit_safe_source(mode="local", local_root=str(fixture_root))
    yield
    set_spirit_safe_source(mode="github")


def test_build_spiritsafe_semantic_anchor_document(tmp_path: Path, fixture_root: Path):
    """Semantic anchor builder should emit the richer artifact contract."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  id: datadistillery-wikibase
  label: Data Distillery Wikibase
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    entity_path = root / "still" / "entities" / "Q4.json"
    entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
    entity_doc["entity"]["claims"]["P214"] = [
        {
            "mainsnak": {
                "snaktype": "value",
                "property": "P214",
                "datavalue": {
                    "value": "_entity",
                    "type": "string",
                },
                "datatype": "string",
            },
            "type": "statement",
            "id": "Q4$P214",
            "rank": "normal",
        }
    ]
    entity_path.write_text(json.dumps(entity_doc, indent=2), encoding="utf-8")

    anchors = build_spiritsafe_semantic_anchor_document(root)

    assert anchors["metadata"]["property_count"] == 0
    assert anchors["metadata"]["item_count"] == 1
    assert isinstance(anchors["metadata"]["generated_at"], str)
    assert anchors["metadata"]["contract_digest"] == get_wikibase_init_contract_digest()
    assert anchors["validation"]["status"] in {"valid", "warning", "error"}
    assert (
        anchors["entities"]["_entity"]["id"]
        == "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert anchors["entities"]["_entity"]["kind"] == "item"
    assert isinstance(anchors["entities"]["_entity"]["required"], dict)
    assert isinstance(anchors["entities"]["_entity"]["resolved"], dict)
    assert isinstance(anchors["entities"]["_entity"]["validation"], dict)


def test_build_spiritsafe_semantic_anchor_document_includes_property_datatype(
    tmp_path: Path, fixture_root: Path
):
    """Semantic anchor builder should include datatype for properties only."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    property_path = root / "still" / "entities" / "P192.json"
    property_doc = {
        "entity_id": "P192",
        "entity": {
            "type": "property",
            "datatype": "time",
            "id": "P192",
            "claims": {
                "P214": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P214",
                            "datavalue": {
                                "value": "_time",
                                "type": "string",
                            },
                            "datatype": "string",
                        },
                        "type": "statement",
                        "id": "P192$P214-internal",
                        "rank": "normal",
                    }
                ]
            },
        },
    }
    property_path.write_text(json.dumps(property_doc, indent=2), encoding="utf-8")

    anchors = build_spiritsafe_semantic_anchor_document(root)

    assert anchors["metadata"]["property_count"] == 1
    assert anchors["metadata"]["item_count"] == 0
    assert (
        anchors["entities"]["_time"]["id"]
        == "https://datadistillery.wikibase.cloud/entity/P192"
    )
    assert anchors["entities"]["_time"]["kind"] == "property"
    assert anchors["entities"]["_time"]["datatype"] == "time"
    assert isinstance(anchors["entities"]["_time"]["required"], dict)
    assert isinstance(anchors["entities"]["_time"]["resolved"], dict)


def test_build_spiritsafe_wikibase_conformance_report_flags_missing_sparql_talk_page(
    tmp_path: Path, fixture_root: Path, monkeypatch
):
    """Conformance report should flag missing SPARQL talk-page content."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  api_url: https://example.test/w/api.php
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    item_path = root / "still" / "entities" / "Q43.json"
    item_doc = {
        "entity_id": "Q43",
        "entity": {
            "id": "Q43",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "List of World Countries"}},
            "descriptions": {
                "en": {
                    "language": "en",
                    "value": "SPARQL query returning list of countries of the world for country statements in items",
                }
            },
            "claims": {
                "P214": [
                    {
                        "id": "Q43$internal-name",
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P214",
                            "datavalue": {
                                "type": "string",
                                "value": "_world_countries",
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ]
            },
        },
    }
    item_path.write_text(json.dumps(item_doc, indent=2), encoding="utf-8")

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            self.api_url = api_url

        def request(self, params):
            return {
                "query": {"pages": [{"title": params.get("titles"), "missing": True}]}
            }

    monkeypatch.setattr("gkc.spirit_safe.WikibaseApiClient", FakeApiClient)

    report = build_spiritsafe_wikibase_conformance_report(root)
    row = next(
        action
        for action in report["actions"]
        if action["name_identifier"] == "_world_countries"
    )

    assert row["action"] == "update"
    assert "talk_page.sparql" in (row["changed_fields"] or [])
    assert row["talk_page"]["status"] == "missing"
    assert (
        row["differences"]["talk_page.sparql"]["expected"]["title"] == "Item_talk:Q43"
    )


def test_build_spiritsafe_wikibase_conformance_report_uses_materialized_cache_artifacts(
    tmp_path: Path, fixture_root: Path, monkeypatch
):
    """Conformance should compare against SpiritSafe files, not live talk pages."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  api_url: https://example.test/w/api.php
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    item_path = root / "still" / "entities" / "Q43.json"
    item_doc = {
        "entity_id": "Q43",
        "entity": {
            "id": "Q43",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "List of World Countries"}},
            "descriptions": {
                "en": {
                    "language": "en",
                    "value": "SPARQL query returning list of countries of the world for country statements in items",
                }
            },
            "claims": {
                "P1": [
                    {
                        "id": "Q43$instance-of",
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P1",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {"id": "Q7", "entity-type": "item"},
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ],
                "P214": [
                    {
                        "id": "Q43$internal-name",
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P214",
                            "datavalue": {
                                "type": "string",
                                "value": "_world_countries",
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ],
            },
        },
    }
    item_path.write_text(json.dumps(item_doc, indent=2), encoding="utf-8")

    queries_dir = root / "still" / "value_lists" / "queries"
    queries_dir.mkdir(parents=True, exist_ok=True)
    (queries_dir / "Q43.sparql").write_text(
        "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }\n",
        encoding="utf-8",
    )

    def _unexpected_fetch(*args, **kwargs):
        raise AssertionError("Conformance should not call the live talk-page API")

    monkeypatch.setattr(
        "gkc.spirit_safe.fetch_mediawiki_page_wikitext", _unexpected_fetch
    )

    report = build_spiritsafe_wikibase_conformance_report(root)
    row = next(
        action
        for action in report["actions"]
        if action["name_identifier"] == "_world_countries"
    )

    assert row["action"] == "update"
    assert "talk_page.sparql" in (row["changed_fields"] or [])
    assert row["talk_page"]["status"] == "drift"
    assert (
        "SELECT ?item WHERE"
        in row["differences"]["talk_page.sparql"]["current"]["content"]
    )


def test_sync_spiritsafe_wikibase_seed_routes_updates_through_shipper(
    tmp_path: Path, fixture_root: Path, monkeypatch
):
    """Sync helper should turn cache drift into shipper dry-run calls."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    property_path = root / "still" / "entities" / "P1.json"
    property_doc = {
        "entity_id": "P1",
        "entity": {
            "id": "P1",
            "type": "property",
            "datatype": "wikibase-item",
            "lastrevid": 321,
            "labels": {"en": {"language": "en", "value": "instance of"}},
            "descriptions": {"en": {"language": "en", "value": "wrong description"}},
            "claims": {
                "P214": [
                    {
                        "id": "P1$internal-name",
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P214",
                            "datavalue": {
                                "type": "string",
                                "value": "_instance_of",
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ]
            },
        },
    }
    property_path.write_text(json.dumps(property_doc, indent=2), encoding="utf-8")

    class FakeApiClient:
        def __init__(self, api_url, session=None, timeout=20):
            self.api_url = api_url

        def get_entity(self, entity_id):
            return json.loads(property_path.read_text(encoding="utf-8"))["entity"]

    monkeypatch.setattr("gkc.spirit_safe.WikibaseApiClient", FakeApiClient)

    class FakeShipper:
        def __init__(self):
            self.api_url = "https://example.test/w/api.php"
            self.auth = None
            self.calls = []

        def write_property(
            self,
            payload,
            summary,
            datatype,
            entity_id=None,
            dry_run=None,
            validate_only=False,
            tags=None,
            bot=False,
            metadata=None,
            base_revision_id=None,
        ):
            self.calls.append(
                {
                    "kind": "property",
                    "payload": payload,
                    "entity_id": entity_id,
                    "datatype": datatype,
                    "dry_run": dry_run,
                    "base_revision_id": base_revision_id,
                    "summary": summary,
                }
            )
            return WriteResult(
                entity_id=entity_id,
                revision_id=base_revision_id,
                status="dry_run" if dry_run else "submitted",
                request_payload=payload,
            )

        def write_item(
            self,
            payload,
            summary,
            entity_id=None,
            dry_run=None,
            validate_only=False,
            tags=None,
            bot=False,
            metadata=None,
            base_revision_id=None,
        ):
            self.calls.append(
                {
                    "kind": "item",
                    "payload": payload,
                    "entity_id": entity_id,
                    "dry_run": dry_run,
                    "base_revision_id": base_revision_id,
                    "summary": summary,
                }
            )
            return WriteResult(
                entity_id=entity_id,
                revision_id=base_revision_id,
                status="dry_run" if dry_run else "submitted",
                request_payload=payload,
            )

    fake_shipper = FakeShipper()
    result = sync_spiritsafe_wikibase_seed(root, shipper=fake_shipper, dry_run=True)

    assert result["summary"]["dry_run"] > 0
    assert any(call["entity_id"] == "P1" for call in fake_shipper.calls)
    assert any(
        call["base_revision_id"] == 321
        for call in fake_shipper.calls
        if call["entity_id"] == "P1"
    )
    assert any(
        action["write_status"] == "dry_run"
        for action in result["actions"]
        if action["action"] != "skip"
    )


def test_build_spiritsafe_semantic_anchor_document_marks_internal_entries(
    tmp_path: Path, fixture_root: Path
):
    """Semantic anchor builder should exclude non-underscore identifiers."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    entity_path = root / "still" / "entities" / "Q4.json"
    entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
    entity_doc["entity"]["claims"]["P214"] = [
        {
            "mainsnak": {
                "snaktype": "value",
                "property": "P214",
                "datavalue": {
                    "value": "tribal_government_profile",
                    "type": "string",
                },
                "datatype": "string",
            },
            "type": "statement",
            "id": "Q4$P214-internal",
            "rank": "normal",
        }
    ]
    entity_path.write_text(json.dumps(entity_doc, indent=2), encoding="utf-8")

    anchors = build_spiritsafe_semantic_anchor_document(root)

    assert anchors["metadata"]["property_count"] == 0
    assert anchors["metadata"]["item_count"] == 0
    assert anchors["entities"]["_entity"]["id"] is None
    assert anchors["entities"]["_entity"]["resolved"] is None


def test_build_spiritsafe_wikibase_conformance_report_uses_entity_cache(
    tmp_path: Path, fixture_root: Path
):
    """Cache report should compare current cached entities against the seed contract."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    entity_docs = {
        "P1": {
            "entity_id": "P1",
            "entity": {
                "id": "P1",
                "type": "property",
                "datatype": "wikibase-item",
                "labels": {"en": {"language": "en", "value": "instance of"}},
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "type to which this subject belongs or corresponds",
                    }
                },
                "claims": {
                    "P214": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P214",
                                "datavalue": {
                                    "type": "string",
                                    "value": "_instance_of",
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ]
                },
            },
        },
        "P168": {
            "entity_id": "P168",
            "entity": {
                "id": "P168",
                "type": "property",
                "datatype": "monolingualtext",
                "labels": {"en": {"language": "en", "value": "error message"}},
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "monolingual text template for error presentation with placeholders resolved by fermenter",
                    }
                },
                "claims": {
                    "P214": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P214",
                                "datavalue": {
                                    "type": "string",
                                    "value": "_error_message",
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ]
                },
            },
        },
        "P214": {
            "entity_id": "P214",
            "entity": {
                "id": "P214",
                "type": "property",
                "datatype": "string",
                "labels": {"en": {"language": "en", "value": "name identifier"}},
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "human-readable identifier for entities in this Wikibase used as a unique identifier in the JSON translations used by and within the SpiritSafe and gkc software package",
                    }
                },
                "claims": {
                    "P214": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P214",
                                "datavalue": {
                                    "type": "string",
                                    "value": "_name_identifier",
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ]
                },
            },
        },
        "Q99": {
            "entity_id": "Q99",
            "entity": {
                "id": "Q99",
                "type": "item",
                "labels": {
                    "en": {"language": "en", "value": "Wikibase Statement Type"}
                },
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "classification of items describing the basic data type aligned with the Wikibase framework",
                    }
                },
                "claims": {
                    "P214": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P214",
                                "datavalue": {
                                    "type": "string",
                                    "value": "_wikibase_statement_type",
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ],
                    "P1": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P1",
                                "datavalue": {
                                    "type": "wikibase-entityid",
                                    "value": {
                                        "entity-type": "item",
                                        "id": "Q4",
                                        "numeric-id": 4,
                                    },
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ],
                },
            },
        },
        "Q50": {
            "entity_id": "Q50",
            "entity": {
                "id": "Q50",
                "type": "item",
                "labels": {"en": {"language": "en", "value": "wikibase-item"}},
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "wikibase item property template used to set a data type for a statement, reference, or qualifier and any additional specifications",
                    }
                },
                "claims": {
                    "P1": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P1",
                                "datavalue": {
                                    "type": "wikibase-entityid",
                                    "value": {
                                        "entity-type": "item",
                                        "id": "Q99",
                                        "numeric-id": 99,
                                    },
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ],
                    "P214": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P214",
                                "datavalue": {
                                    "type": "string",
                                    "value": "_wikibase-item",
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ],
                    "P168": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "property": "P168",
                                "datavalue": {
                                    "type": "monolingualtext",
                                    "value": {
                                        "language": "mul",
                                        "text": "Item must be or resolve to a valid QID identifier.",
                                    },
                                },
                            },
                            "type": "statement",
                            "rank": "normal",
                        }
                    ],
                },
            },
        },
    }

    entities_dir = root / "still" / "entities"
    for entity_id, entity_doc in entity_docs.items():
        (entities_dir / f"{entity_id}.json").write_text(
            json.dumps(entity_doc, indent=2), encoding="utf-8"
        )

    report = build_spiritsafe_wikibase_conformance_report(root)

    assert report["comparison_source"]["mode"] == "cache-entities"
    assert report["summary"]["skipped"] >= 1
    assert report["summary"]["created"] >= 1
    wikibase_item = next(
        action
        for action in report["actions"]
        if action["name_identifier"] == "_wikibase-item"
    )
    assert wikibase_item["action"] == "skip"
    assert wikibase_item["id"] == "https://datadistillery.wikibase.cloud/entity/Q50"
    assert (
        wikibase_item["required"]["claims"]["_instance_of"][0]["mainsnak"]["datavalue"][
            "value"
        ]["name_identifier"]
        == "_wikibase_statement_type"
    )
    assert (
        wikibase_item["current"]["claims"]["_instance_of"][0]["mainsnak"]["datavalue"][
            "value"
        ]["id"]
        == "https://datadistillery.wikibase.cloud/entity/Q99"
    )


def test_build_spiritsafe_wikibase_conformance_report_rejects_ambiguous_cache_matches(
    tmp_path: Path, fixture_root: Path
):
    """Cache conformance should hard-stop when two entities claim the same internal name identifier."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    duplicate_payload = {
        "type": "item",
        "labels": {"en": {"language": "en", "value": "wikibase-item"}},
        "descriptions": {
            "en": {
                "language": "en",
                "value": "duplicate cache test entity",
            }
        },
        "claims": {
            "P214": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P214",
                        "datavalue": {
                            "type": "string",
                            "value": "_wikibase-item",
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ]
        },
    }

    entities_dir = root / "still" / "entities"
    (entities_dir / "Q50.json").write_text(
        json.dumps(
            {
                "entity_id": "Q50",
                "entity": {"id": "Q50", **duplicate_payload},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (entities_dir / "Q51.json").write_text(
        json.dumps(
            {
                "entity_id": "Q51",
                "entity": {"id": "Q51", **duplicate_payload},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Multiple cached entities resolve"):
        build_spiritsafe_wikibase_conformance_report(root)


def test_build_spiritsafe_semantic_anchor_document_requires_config(
    tmp_path: Path, fixture_root: Path
):
    """Semantic anchor generation should fail clearly without a Wikibase config."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    (root / "config" / "dd-wikibase.yaml").unlink()

    with pytest.raises(FileNotFoundError, match="Wikibase config"):
        build_spiritsafe_semantic_anchor_document(root)


def test_export_spiritsafe_semantic_anchors(fixture_root: Path, tmp_path: Path):
    """Semantic anchor export should write JSON to the requested path."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    config_dir = root / "config"
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    entity_path = root / "still" / "entities" / "Q4.json"
    entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
    entity_doc["entity"]["claims"]["P214"] = [
        {
            "mainsnak": {
                "snaktype": "value",
                "property": "P214",
                "datavalue": {
                    "value": "_entity",
                    "type": "string",
                },
                "datatype": "string",
            },
            "type": "statement",
            "id": "Q4$P214",
            "rank": "normal",
        }
    ]
    entity_path.write_text(json.dumps(entity_doc, indent=2), encoding="utf-8")

    output_path = tmp_path / "semantic_anchors.json"
    anchors = export_spiritsafe_semantic_anchors(root, output_path)

    assert output_path.exists()
    assert anchors["metadata"]["property_count"] == 0
    assert anchors["metadata"]["item_count"] == 1
    assert anchors["validation"]["error_count"] >= 0
    assert (
        anchors["entities"]["_entity"]["id"]
        == "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert anchors["entities"]["_entity"]["kind"] == "item"


def test_load_profile_reads_json_profile_document():
    """JSON profile loading should work by QID and preserve profile metadata."""

    profile = load_profile("Q4")

    assert profile["entity"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    assert profile["metadata"]["statement_count"] == 2
    assert len(profile["statements"]) == 2


def test_load_profile_uses_runtime_layout_for_github_mode(monkeypatch):
    """GitHub-mode profile loading should resolve against the configured layout path."""

    captured: dict[str, str] = {}

    def fake_load_json_from_resolved_path(resolved_path):
        captured["resolved_path"] = str(resolved_path)
        return {"entity": "https://datadistillery.wikibase.cloud/entity/Q4"}

    monkeypatch.setattr(
        "gkc.spirit_safe._load_json_from_resolved_path",
        fake_load_json_from_resolved_path,
    )
    set_spirit_safe_source(mode="github", github_repo="skybristol/SpiritSafe")

    profile = load_profile("Q4")

    assert profile["entity"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    assert captured["resolved_path"].endswith("/still/profiles/Q4.json")


def test_load_profile_package_uses_embedded_profile_graph():
    """Profile package loading should traverse metadata.profile_graph edges."""

    package = load_profile_package("Q4", depth=1)

    assert package["primary_profile"] == "Q4"
    assert package["primary_profile_entity"] == (
        "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert set(package["profiles"].keys()) == {"Q4", "Q39"}


def test_resolve_profile_link_matches_statement_uri():
    """Link resolution should match by statement QID or URI."""

    linkage = resolve_profile_link("Q4", "Q40")

    assert linkage == {
        "target_profile": "Q39",
        "target_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
        "via_statement": "https://datadistillery.wikibase.cloud/entity/Q40",
        "relationship_type": "P161",
        "label": "Office Held by Head of Government",
    }


def test_create_curation_packet_single_mode():
    """Single-mode packets should only include the primary profile scaffold."""

    packet = create_curation_packet("Q4", operation_mode="single")

    assert packet["metadata"]["primary_profile"]["name_identifier"] == "Q4"
    assert packet["metadata"]["primary_profile"]["id"] == (
        "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert len(packet["data"]["entities"]) == 1
    graph_edges = packet["metadata"]["graph"]["edges"]
    assert all(edge.get("relationship_type") != "P161" for edge in graph_edges)

    statement_ids = [
        statement.get("id") or statement.get("entity")
        for statement in packet["metadata"]["profiles"][0]["statements"]
    ]
    assert statement_ids == [
        "https://datadistillery.wikibase.cloud/entity/Q16",
        "https://datadistillery.wikibase.cloud/entity/Q40",
    ]


def test_create_curation_packet_bulk_mode():
    """Bulk packets should include linked profiles and cross references."""

    packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)

    assert len(packet["data"]["entities"]) == 2
    assert len(packet["metadata"]["graph"]["edges"]) == 2
    assert "integrity" in packet["metadata"]

    tribal_government = next(
        entity for entity in packet["data"]["entities"] if entity["profile"] == "Q4"
    )
    assert tribal_government["statements"]["Q16"]["value-list"] == "Q28"


def test_validate_packet_structure_reports_invalid_data_entity_id():
    """Packet validation should catch invalid entity identifiers in new schema."""

    packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)
    packet["data"]["entities"][0]["id"] = "Q4"

    is_valid, errors = validate_packet_structure(packet)

    assert is_valid is False
    assert "Each data.entities item id must be an HTTP URI" in errors
