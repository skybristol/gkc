"""Tests for ProfileGraph traversal against the new manifest shape."""

import json
from pathlib import Path

import pytest

from gkc.profiles.graph import GraphEdge, ProfileGraph, ProfileNode


@pytest.fixture
def manifest_fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "spiritsafe" / "cache" / "manifest.json"


@pytest.fixture
def manifest_data(manifest_fixture_path: Path) -> dict:
    return json.loads(manifest_fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def profile_graph(manifest_data: dict) -> ProfileGraph:
    return ProfileGraph.from_manifest_data(manifest_data["profiles"])


def test_graph_created_from_manifest(profile_graph: ProfileGraph):
    """Manifest graph construction should create one node per profile QID."""

    assert profile_graph.profile_count() == 2
    assert profile_graph.has_profile("Q4")
    assert profile_graph.has_profile("Q39")


def test_graph_nodes_structure(profile_graph: ProfileGraph):
    """Graph nodes should expose normalized QID neighbors and URI statement edges."""

    tribal_node = profile_graph.nodes["Q4"]
    assert isinstance(tribal_node, ProfileNode)
    assert tribal_node.profile_id == "Q4"
    assert tribal_node.neighbors == ["Q39"]
    assert len(tribal_node.edges) == 1

    edge = tribal_node.edges[0]
    assert isinstance(edge, GraphEdge)
    assert edge.target_profile == "Q39"
    assert edge.via_statement == "https://datadistillery.wikibase.cloud/entity/Q40"
    assert edge.relationship_type == "P161"


def test_get_neighbors(profile_graph: ProfileGraph):
    """Neighbor lookup should return direct related profiles."""

    assert profile_graph.get_neighbors("Q4") == ["Q39"]
    assert profile_graph.get_neighbors("Q39") == ["Q4"]
    assert profile_graph.get_neighbors("Q999") == []


def test_get_edges(profile_graph: ProfileGraph):
    """Edge lookup should support all edges and filtered edges."""

    edges = profile_graph.get_edges("Q4")
    assert len(edges) == 1
    assert edges[0].target_profile == "Q39"

    filtered = profile_graph.get_edges("Q4", "Q39")
    assert len(filtered) == 1
    assert filtered[0].label == "Office Held by Head of Government"

    assert profile_graph.get_edges("Q4", "Q999") == []
    assert profile_graph.get_edges("Q999") == []


def test_get_cardinality_defaults_to_empty_dict(profile_graph: ProfileGraph):
    """New manifest edges omit cardinality, which should normalize to an empty dict."""

    assert profile_graph.get_cardinality("Q4", "Q39") == {}
    assert profile_graph.get_cardinality("Q4", "Q999") is None


def test_traverse_depth_1(profile_graph: ProfileGraph):
    """Traversal should return directly reachable QIDs."""

    assert profile_graph.traverse("Q4", max_depth=1) == ["Q39"]
    assert profile_graph.traverse("Q39", max_depth=1) == ["Q4"]


def test_traverse_depth_0(profile_graph: ProfileGraph):
    """Depth-zero traversal should return an empty list."""

    assert profile_graph.traverse("Q4", max_depth=0) == []


def test_traverse_with_cycle_prevention(profile_graph: ProfileGraph):
    """Traversal should not re-enter already-visited profiles."""

    reachable = profile_graph.traverse("Q4", max_depth=2)
    assert reachable == ["Q39"]


def test_validate_bidirectional_awareness(profile_graph: ProfileGraph):
    """Fixture graph should be reciprocally declared on both sides."""

    assert profile_graph.validate_bidirectional_awareness() == []


def test_validate_bidirectional_missing_reciprocal():
    """Missing reciprocal neighbors should still be detected."""

    graph = ProfileGraph(
        nodes={
            "Q4": ProfileNode(
                profile_id="Q4",
                neighbors=["Q39"],
                edges=[
                    GraphEdge(
                        target_profile="Q39",
                        via_statement="https://datadistillery.wikibase.cloud/entity/Q40",
                        relationship_type="P161",
                    )
                ],
            ),
            "Q39": ProfileNode(profile_id="Q39", neighbors=[], edges=[]),
        }
    )

    errors = graph.validate_bidirectional_awareness()
    assert errors == ["Q4 → Q39: Missing reciprocal neighbor declaration"]
