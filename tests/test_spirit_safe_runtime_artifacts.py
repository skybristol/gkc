"""Tests for next-generation SpiritSafe manifest and JSON profile workflows."""

import json
from pathlib import Path
from shutil import copytree

import pytest

from gkc.spirit_safe import (
    build_spiritsafe_entity_index_document,
    build_spiritsafe_manifest_document,
    build_spiritsafe_semantic_anchor_document,
    export_spiritsafe_entity_index,
    export_spiritsafe_manifest,
    export_spiritsafe_semantic_anchors,
    load_manifest,
    load_profile,
    load_profile_package,
    resolve_profile_link,
    set_spirit_safe_source,
    validate_packet_structure,
)
from gkc.still_charger import create_curation_packet


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "spiritsafe"


def _default_semantic_anchor_document() -> dict:
    return {
        "entities": {
            "_instance_of": {"id": "P1", "datatype": "wikibase-item"},
            "_name_identifier": {"id": "P214", "datatype": "string"},
            "_same_as": {"id": "P5", "datatype": "url"},
            "_has_statement": {"id": "P157", "datatype": "wikibase-item"},
            "_has_value": {"id": "P161", "datatype": "wikibase-item"},
            "_has_qualifier": {"id": "P158", "datatype": "wikibase-item"},
            "_has_reference": {"id": "P211", "datatype": "wikibase-item"},
            "_applies_to_profile": {"id": "P205", "datatype": "wikibase-item"},
            "_applies_to_statement": {"id": "P163", "datatype": "wikibase-item"},
            "_statement_type": {"id": "P194", "datatype": "wikibase-item"},
            "_max_count": {"id": "P182", "datatype": "quantity"},
            "_statement_prompt": {"id": "P171", "datatype": "monolingualtext"},
            "_statement_guidance": {"id": "P169", "datatype": "monolingualtext"},
            "_consequences_message": {"id": "P170", "datatype": "monolingualtext"},
            "_error_message": {"id": "P168", "datatype": "monolingualtext"},
            "_derives_default_value_from": {"id": "P213", "datatype": "wikibase-item"},
        }
    }


@pytest.fixture(autouse=True)
def setup_local_source(fixture_root: Path):
    """Configure SpiritSafe access to use deterministic local fixture artifacts."""

    set_spirit_safe_source(mode="local", local_root=str(fixture_root))
    yield
    set_spirit_safe_source(mode="github")


def test_build_spiritsafe_manifest_document(fixture_root: Path):
    """Manifest builder should index generated SpiritSafe artifacts."""

    manifest = build_spiritsafe_manifest_document(fixture_root)

    assert manifest["source"] == "https://github.com/skybristol/SpiritSafe"
    assert {profile["qid"] for profile in manifest["profiles"]} == {"Q4", "Q39"}
    assert manifest["entities"] == {"count": 1, "qids": ["Q4"]}
    assert manifest["queries"] == [
        {"qid": "Q28", "path": "still/value_lists/queries/Q28.sparql"}
    ]
    assert manifest["value_lists"] == [
        {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q28",
            "qid": "Q28",
            "label": "List of Federal Register Sources",
            "path": "still/value_lists/cache/Q28.json",
            "item_count": 2,
        }
    ]

    q4_profile = next(
        profile for profile in manifest["profiles"] if profile["qid"] == "Q4"
    )
    assert q4_profile["value_list_graph"] == [
        {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q28",
            "label": "List of Federal Register Sources",
            "via_statement": "https://datadistillery.wikibase.cloud/entity/Q16",
            "value_list_id": "Q28",
        }
    ]


def test_export_spiritsafe_manifest(fixture_root: Path, tmp_path: Path):
    """Manifest export should write JSON to the requested path."""

    output_path = tmp_path / "manifest.json"
    manifest = export_spiritsafe_manifest(fixture_root, output_path)

    assert output_path.exists()
    assert {profile["qid"] for profile in manifest["profiles"]} == {"Q4", "Q39"}


def test_build_spiritsafe_entity_index_document(fixture_root: Path):
    """Entity index builder should normalize cached entity artifacts."""

    index = build_spiritsafe_entity_index_document(
        fixture_root,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert index["source"] == "https://github.com/skybristol/SpiritSafe"
    assert index["entity_count"] == 1
    assert "Q4" in index["entities"]
    q4 = index["entities"]["Q4"]
    assert q4["id"] == "Q4"
    assert q4["entity"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    assert q4["label"] == "Tribal Government in the United States"
    assert q4["classes"] == []
    assert q4["links"]["statements"] == []


def test_export_spiritsafe_entity_index(fixture_root: Path, tmp_path: Path):
    """Entity index export should write JSON to the requested path."""

    output_path = tmp_path / "entity_index.json"
    index = export_spiritsafe_entity_index(
        fixture_root,
        output_path,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert output_path.exists()
    assert index["entity_count"] == 1
    assert index["class_index"] == {}


def test_build_spiritsafe_semantic_anchor_document(tmp_path: Path, fixture_root: Path):
    """Semantic anchor builder should emit metadata plus underscore mappings."""

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
        logs: still/refresh
        wikimedia_sites: partners/wikimedia_sites.json
        manifest: still/manifest.json
        entity_index: still/entity_index.json
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
                    "value": "_TribalGovernmentInTheUnitedStates",
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
    assert anchors["entities"] == {
        "_TribalGovernmentInTheUnitedStates": {
            "id": "Q4",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        }
    }


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
        logs: still/refresh
        wikimedia_sites: partners/wikimedia_sites.json
        manifest: still/manifest.json
        entity_index: still/entity_index.json
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
    assert anchors["entities"] == {
        "_time": {
            "id": "P192",
            "entity": "https://datadistillery.wikibase.cloud/entity/P192",
            "datatype": "time",
        }
    }


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
        logs: still/refresh
        wikimedia_sites: partners/wikimedia_sites.json
        manifest: still/manifest.json
        entity_index: still/entity_index.json
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
    assert anchors["entities"] == {}


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
        logs: still/refresh
        wikimedia_sites: partners/wikimedia_sites.json
        manifest: still/manifest.json
        entity_index: still/entity_index.json
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
                    "value": "_TribalGovernmentInTheUnitedStates",
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
    assert anchors["entities"] == {
        "_TribalGovernmentInTheUnitedStates": {
            "id": "Q4",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        }
    }


def test_load_manifest_reads_new_shape():
    """Manifest loader should parse the artifact-index shape."""

    manifest = load_manifest(use_cache=False)

    assert manifest.generated_at
    assert manifest.source == "https://github.com/skybristol/SpiritSafe"
    assert manifest.profile_qids == ["Q4", "Q39"]
    assert manifest.get_profile_entry("Q4") is not None
    assert (
        manifest.get_profile_entry("https://datadistillery.wikibase.cloud/entity/Q39")
        is not None
    )


def test_load_profile_reads_json_profile_document():
    """JSON profile loading should work by QID and preserve profile metadata."""

    profile = load_profile("Q4")

    assert profile["entity"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    assert profile["metadata"]["statement_count"] == 2
    assert len(profile["statements"]) == 2


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
