"""Tests for next-generation SpiritSafe manifest and JSON profile workflows."""

from pathlib import Path

import pytest

from gkc.spirit_safe import (
    build_spiritsafe_manifest_document,
    create_curation_packet,
    export_spiritsafe_manifest,
    get_profile_graph,
    load_manifest,
    load_profile,
    load_profile_package,
    resolve_profile_link,
    set_spirit_safe_source,
    validate_packet_structure,
)


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "spiritsafe"


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
    assert manifest["queries"] == [{"qid": "Q28", "path": "queries/Q28.sparql"}]
    assert manifest["value_lists"] == [
        {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q28",
            "qid": "Q28",
            "label": "List of Federal Register Sources",
            "path": "cache/queries/Q28.json",
            "item_count": 2,
        }
    ]


def test_export_spiritsafe_manifest(fixture_root: Path, tmp_path: Path):
    """Manifest export should write JSON to the requested path."""

    output_path = tmp_path / "manifest.json"
    manifest = export_spiritsafe_manifest(fixture_root, output_path)

    assert output_path.exists()
    assert {profile["qid"] for profile in manifest["profiles"]} == {"Q4", "Q39"}


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
    assert set(package["graph"].nodes.keys()) == {"Q4", "Q39"}


def test_get_profile_graph_builds_from_manifest_fixture():
    """Profile graph helper should return the QID-keyed graph from manifest."""

    graph = get_profile_graph()

    assert graph.profile_count() == 2
    assert graph.get_neighbors("Q4") == ["Q39"]


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

    assert packet["primary_profile"] == "Q4"
    assert packet["primary_profile_entity"] == (
        "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert len(packet["entities"]) == 1
    assert packet["cross_references"] == []

    statement_ids = [
        statement.get("id")
        for statement in packet["entities"][0]["profile_structure"]["statements"]
    ]
    assert statement_ids == ["Q16", "Q40"]


def test_create_curation_packet_bulk_mode():
    """Bulk packets should include linked profiles and cross references."""

    packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)

    assert len(packet["entities"]) == 2
    assert len(packet["cross_references"]) == 2
    assert packet["cardinality_constraints"] == [
        {"from": "ent-001", "to": "ent-002", "min": 0, "max": -1},
        {"from": "ent-002", "to": "ent-001", "min": 0, "max": -1},
    ]


def test_validate_packet_structure_reports_invalid_cross_reference():
    """Packet validation should catch broken entity references."""

    packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)
    packet["cross_references"][0]["to"] = "ent-999"

    is_valid, errors = validate_packet_structure(packet)

    assert is_valid is False
    assert "Cross-reference to ent-999 points to unknown entity" in errors
