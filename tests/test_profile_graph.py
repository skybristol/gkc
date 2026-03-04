"""
Test ProfileGraph model and graph traversal operations.

Validates graph construction from manifest data, neighbor queries,
edge traversal, cardinality constraints, and bidirectional validation.
"""

import json
from pathlib import Path

import pytest

from gkc.profiles.graph import GraphEdge, ProfileGraph, ProfileNode


@pytest.fixture
def manifest_fixture_path() -> Path:
    """Return path to manifest.json fixture."""
    return Path(__file__).parent / "fixtures" / "spiritsafe" / "cache" / "manifest.json"


@pytest.fixture
def manifest_data(manifest_fixture_path: Path) -> dict:
    """Load manifest.json fixture data."""
    with open(manifest_fixture_path) as f:
        return json.load(f)


@pytest.fixture
def profile_graph(manifest_data: dict) -> ProfileGraph:
    """Create ProfileGraph from manifest fixture."""
    return ProfileGraph.from_manifest_data(manifest_data["profiles"])


def test_graph_created_from_manifest(profile_graph: ProfileGraph):
    """Test that ProfileGraph is correctly created from manifest data."""
    assert profile_graph.profile_count() == 2
    assert profile_graph.has_profile("TribalGovernmentUS")
    assert profile_graph.has_profile("OfficeHeldByHeadOfState")


def test_graph_nodes_structure(profile_graph: ProfileGraph):
    """Test that graph nodes have correct structure."""
    tribal_node = profile_graph.nodes["TribalGovernmentUS"]
    assert isinstance(tribal_node, ProfileNode)
    assert tribal_node.profile_id == "TribalGovernmentUS"
    assert len(tribal_node.neighbors) == 1
    assert len(tribal_node.edges) == 1

    office_node = profile_graph.nodes["OfficeHeldByHeadOfState"]
    assert isinstance(office_node, ProfileNode)
    assert office_node.profile_id == "OfficeHeldByHeadOfState"
    assert len(office_node.neighbors) == 1
    assert len(office_node.edges) == 1


def test_get_neighbors(profile_graph: ProfileGraph):
    """Test retrieving neighbors from a profile."""
    # TribalGovernmentUS should have OfficeHeldByHeadOfState as neighbor
    neighbors = profile_graph.get_neighbors("TribalGovernmentUS")
    assert neighbors == ["OfficeHeldByHeadOfState"]

    # OfficeHeldByHeadOfState should have TribalGovernmentUS as neighbor
    neighbors = profile_graph.get_neighbors("OfficeHeldByHeadOfState")
    assert neighbors == ["TribalGovernmentUS"]

    # Non-existent profile should return empty list
    neighbors = profile_graph.get_neighbors("NonExistent")
    assert neighbors == []


def test_get_edges(profile_graph: ProfileGraph):
    """Test retrieving edges from a profile."""
    # Get all edges from TribalGovernmentUS
    edges = profile_graph.get_edges("TribalGovernmentUS")
    assert len(edges) == 1
    assert isinstance(edges[0], GraphEdge)
    assert edges[0].target_profile == "OfficeHeldByHeadOfState"
    assert edges[0].via_statement == "office_held_by_head_of_state"
    assert edges[0].relationship_type == "office_of_head_of_state"

    # Get specific edge from TribalGovernmentUS to OfficeHeldByHeadOfState
    edges = profile_graph.get_edges("TribalGovernmentUS", "OfficeHeldByHeadOfState")
    assert len(edges) == 1
    assert edges[0].target_profile == "OfficeHeldByHeadOfState"

    # Get edges to non-existent target should return empty list
    edges = profile_graph.get_edges("TribalGovernmentUS", "NonExistent")
    assert edges == []

    # Get edges from non-existent source should return empty list
    edges = profile_graph.get_edges("NonExistent")
    assert edges == []


def test_edge_cardinality(profile_graph: ProfileGraph):
    """Test that edge cardinality is correctly loaded."""
    edges = profile_graph.get_edges("TribalGovernmentUS", "OfficeHeldByHeadOfState")
    assert len(edges) == 1

    cardinality = edges[0].cardinality
    assert cardinality["min"] == 0
    assert cardinality["max"] == 1


def test_edge_traversal(profile_graph: ProfileGraph):
    """Test that edge traversal config is correctly loaded."""
    edges = profile_graph.get_edges("TribalGovernmentUS", "OfficeHeldByHeadOfState")
    assert len(edges) == 1

    traversal = edges[0].traversal
    assert traversal["max_depth"] == 1


def test_get_cardinality(profile_graph: ProfileGraph):
    """Test get_cardinality helper method."""
    # Valid edge
    cardinality = profile_graph.get_cardinality(
        "TribalGovernmentUS", "OfficeHeldByHeadOfState"
    )
    assert cardinality is not None
    assert cardinality["min"] == 0
    assert cardinality["max"] == 1

    # Reverse direction
    cardinality = profile_graph.get_cardinality(
        "OfficeHeldByHeadOfState", "TribalGovernmentUS"
    )
    assert cardinality is not None
    assert cardinality["min"] == 0
    assert cardinality["max"] == 1

    # Non-existent edge
    cardinality = profile_graph.get_cardinality("TribalGovernmentUS", "NonExistent")
    assert cardinality is None


def test_traverse_depth_1(profile_graph: ProfileGraph):
    """Test graph traversal at depth 1."""
    # Traverse from TribalGovernmentUS
    reachable = profile_graph.traverse("TribalGovernmentUS", max_depth=1)
    assert "OfficeHeldByHeadOfState" in reachable

    # Traverse from OfficeHeldByHeadOfState
    reachable = profile_graph.traverse("OfficeHeldByHeadOfState", max_depth=1)
    assert "TribalGovernmentUS" in reachable


def test_traverse_depth_0(profile_graph: ProfileGraph):
    """Test that depth 0 returns empty list."""
    reachable = profile_graph.traverse("TribalGovernmentUS", max_depth=0)
    assert reachable == []


def test_traverse_non_existent(profile_graph: ProfileGraph):
    """Test traversal from non-existent profile."""
    reachable = profile_graph.traverse("NonExistent", max_depth=1)
    assert reachable == []


def test_traverse_with_cycle_prevention(profile_graph: ProfileGraph):
    """Test that traversal prevents infinite loops on bidirectional edges."""
    # Even though edges are bidirectional, traversal should not loop
    reachable = profile_graph.traverse("TribalGovernmentUS", max_depth=2)

    # Should include OfficeHeldByHeadOfState but not loop back to TribalGovernmentUS
    assert "OfficeHeldByHeadOfState" in reachable
    assert "TribalGovernmentUS" not in reachable


def test_validate_bidirectional_awareness(profile_graph: ProfileGraph):
    """Test bidirectional validation on valid graph."""
    errors = profile_graph.validate_bidirectional_awareness()
    assert errors == [], f"Valid graph should have no errors, got: {errors}"


def test_validate_bidirectional_missing_reciprocal():
    """Test validation detects missing reciprocal edges."""
    # Create graph with one-sided edge
    graph = ProfileGraph(
        nodes={
            "ProfileA": ProfileNode(
                profile_id="ProfileA",
                neighbors=["ProfileB"],
                edges=[
                    GraphEdge(
                        target_profile="ProfileB",
                        via_statement="linked_to",
                        relationship_type="links",
                        cardinality={"min": 0, "max": 1},
                        traversal={"max_depth": 1},
                    )
                ],
            ),
            "ProfileB": ProfileNode(
                profile_id="ProfileB",
                neighbors=[],  # Missing ProfileA in neighbors
                edges=[],
            ),
        }
    )

    errors = graph.validate_bidirectional_awareness()
    assert len(errors) > 0
    assert "Missing reciprocal neighbor declaration" in errors[0]


def test_validate_bidirectional_missing_target():
    """Test validation detects missing target profile."""
    # Create graph with edge to non-existent profile
    graph = ProfileGraph(
        nodes={
            "ProfileA": ProfileNode(
                profile_id="ProfileA",
                neighbors=["NonExistent"],
                edges=[
                    GraphEdge(
                        target_profile="NonExistent",
                        via_statement="linked_to",
                        relationship_type="links",
                        cardinality={"min": 0, "max": 1},
                        traversal={"max_depth": 1},
                    )
                ],
            )
        }
    )

    errors = graph.validate_bidirectional_awareness()
    assert len(errors) > 0
    assert "Target profile not found in graph" in errors[0]


def test_has_profile(profile_graph: ProfileGraph):
    """Test has_profile method."""
    assert profile_graph.has_profile("TribalGovernmentUS") is True
    assert profile_graph.has_profile("OfficeHeldByHeadOfState") is True
    assert profile_graph.has_profile("NonExistent") is False


def test_profile_count(profile_graph: ProfileGraph):
    """Test profile_count method."""
    assert profile_graph.profile_count() == 2

    # Empty graph
    empty_graph = ProfileGraph()
    assert empty_graph.profile_count() == 0


def test_from_metadata_dict():
    """Test creating ProfileGraph from metadata.yaml dict."""
    metadata = {
        "profile_graph": {
            "neighbors": ["OfficeHeldByHeadOfState"],
            "edges": [
                {
                    "target_profile": "OfficeHeldByHeadOfState",
                    "via_statement": "office_held_by_head_of_state",
                    "relationship_type": "office_of_head_of_state",
                    "cardinality": {"min": 0, "max": 1},
                    "traversal": {"max_depth": 1},
                }
            ],
        }
    }

    graph = ProfileGraph.from_metadata_dict("TribalGovernmentUS", metadata)

    assert graph.profile_count() == 1
    assert graph.has_profile("TribalGovernmentUS")

    neighbors = graph.get_neighbors("TribalGovernmentUS")
    assert neighbors == ["OfficeHeldByHeadOfState"]

    edges = graph.get_edges("TribalGovernmentUS")
    assert len(edges) == 1
    assert edges[0].target_profile == "OfficeHeldByHeadOfState"


def test_from_metadata_dict_empty_graph():
    """Test creating ProfileGraph from metadata without profile_graph section."""
    metadata = {}

    graph = ProfileGraph.from_metadata_dict("SimpleProfile", metadata)

    assert graph.profile_count() == 1
    assert graph.has_profile("SimpleProfile")

    neighbors = graph.get_neighbors("SimpleProfile")
    assert neighbors == []

    edges = graph.get_edges("SimpleProfile")
    assert edges == []


def test_graph_edge_structure():
    """Test GraphEdge model structure."""
    edge = GraphEdge(
        target_profile="TargetProfile",
        via_statement="statement_id",
        relationship_type="relationship",
        cardinality={"min": 1, "max": 5},
        traversal={"max_depth": 2},
    )

    assert edge.target_profile == "TargetProfile"
    assert edge.via_statement == "statement_id"
    assert edge.relationship_type == "relationship"
    assert edge.cardinality["min"] == 1
    assert edge.cardinality["max"] == 5
    assert edge.traversal["max_depth"] == 2


def test_profile_node_structure():
    """Test ProfileNode model structure."""
    node = ProfileNode(
        profile_id="TestProfile",
        neighbors=["Profile1", "Profile2"],
        edges=[
            GraphEdge(
                target_profile="Profile1",
                via_statement="link1",
                relationship_type="rel1",
                cardinality={"min": 0, "max": 1},
                traversal={"max_depth": 1},
            )
        ],
    )

    assert node.profile_id == "TestProfile"
    assert len(node.neighbors) == 2
    assert len(node.edges) == 1
