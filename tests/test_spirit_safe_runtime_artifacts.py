"""Tests for SpiritSafe JSON profile and semantic-anchor workflows."""

import json
from pathlib import Path
from shutil import copytree

import pytest

from gkc.spirit_safe import (
    build_spiritsafe_semantic_anchor_document,
    export_spiritsafe_semantic_anchors,
    load_profile,
    load_profile_package,
    resolve_profile_link,
    set_spirit_safe_source,
    validate_packet_structure,
)
from gkc.still_charger import create_curation_packet
from gkc.wikibase import get_meta_wikibase_init_contract_digest


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
    assert (
        anchors["metadata"]["contract_digest"]
        == get_meta_wikibase_init_contract_digest()
    )
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


def test_build_spiritsafe_semantic_anchor_document_requires_config(
    tmp_path: Path, fixture_root: Path
):
    """Semantic anchor generation should fail clearly without meta-wikibase config."""

    root = tmp_path / "spiritsafe"
    copytree(fixture_root, root)
    (root / "config" / "dd-wikibase.yaml").unlink()

    with pytest.raises(FileNotFoundError, match="Meta-wikibase config"):
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
