"""
Test Phase 3 spirit_safe module functions.

Tests for manifest loading, profile loading, profile packages, and curation packet creation.
"""

from pathlib import Path

import pytest

from gkc.spirit_safe import (
    create_curation_packet,
    get_profile_graph,
    load_manifest,
    load_profile,
    load_profile_package,
    resolve_profile_link,
    set_spirit_safe_source,
    validate_packet_structure,
)


@pytest.fixture(autouse=True)
def setup_local_source():
    """Configure spirit_safe to use deterministic in-repo SpiritSafe fixtures."""
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"
    set_spirit_safe_source(mode="local", local_root=str(fixture_root))

    yield

    # Reset to github after test
    set_spirit_safe_source(mode="github")


class TestManifestLoading:
    """Test manifest loading and caching."""

    def test_load_manifest(self):
        """Test loading manifest from local source."""
        manifest = load_manifest()

        assert manifest is not None
        assert manifest.generated_at
        assert manifest.commit_sha
        assert len(manifest.profile_ids) >= 2
        assert "TribalGovernmentUS" in manifest.profile_ids
        assert "OfficeHeldByHeadOfState" in manifest.profile_ids

    def test_manifest_profile_entry(self):
        """Test retrieving specific profile entry from manifest."""
        manifest = load_manifest()

        entry = manifest.get_profile_entry("TribalGovernmentUS")
        assert entry is not None
        assert entry["id"] == "TribalGovernmentUS"
        assert entry["name"]
        assert entry["description"]
        assert entry["version"] == "1.0.0"
        assert entry["status"] == "stable"

    def test_manifest_profile_files_paths(self):
        """Test that manifest contains file paths for profiles."""
        manifest = load_manifest()

        entry = manifest.get_profile_entry("TribalGovernmentUS")
        files = entry.get("files", {})
        assert "profile_yaml" in files
        assert "metadata_yaml" in files
        assert files["profile_yaml"].endswith("profile.yaml")

    def test_manifest_profile_graph_metadata(self):
        """Test that manifest contains profile_graph metadata."""
        manifest = load_manifest()

        entry = manifest.get_profile_entry("TribalGovernmentUS")
        profile_graph = entry.get("profile_graph", {})
        assert "neighbors" in profile_graph
        assert "OfficeHeldByHeadOfState" in profile_graph["neighbors"]
        assert "edges" in profile_graph
        assert len(profile_graph["edges"]) > 0

    def test_manifest_caching(self):
        """Test that manifest caching works."""
        manifest1 = load_manifest(use_cache=True)
        manifest2 = load_manifest(use_cache=True)

        # Should be the same object due to caching
        assert manifest1 is manifest2

    def test_manifest_missing_profile(self):
        """Test that querying missing profile returns None."""
        manifest = load_manifest()

        entry = manifest.get_profile_entry("NonexistentProfile")
        assert entry is None


class TestProfileLoading:
    """Test profile YAML loading."""

    def test_load_profile_tribal_government(self):
        """Test loading TribalGovernmentUS profile."""
        profile = load_profile("TribalGovernmentUS")

        assert profile is not None
        assert isinstance(profile, dict)
        assert "name" in profile
        assert "statements" in profile

    def test_load_profile_office_held(self):
        """Test loading OfficeHeldByHeadOfState profile."""
        profile = load_profile("OfficeHeldByHeadOfState")

        assert profile is not None
        assert "name" in profile
        assert "statements" in profile

    def test_load_profile_with_manifest(self):
        """Test loading profile with pre-loaded manifest."""
        manifest = load_manifest()
        profile = load_profile("TribalGovernmentUS", manifest=manifest)

        assert profile is not None
        assert "name" in profile

    def test_load_nonexistent_profile_raises_error(self):
        """Test that loading nonexistent profile raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_profile("NonexistentProfile")


class TestProfilePackage:
    """Test profile package loading with related profiles."""

    def test_load_profile_package_depth_0(self):
        """Test loading profile package with no depth (primary only)."""
        package = load_profile_package("TribalGovernmentUS", depth=0)

        assert package["primary_profile"] == "TribalGovernmentUS"
        assert "TribalGovernmentUS" in package["profiles"]
        assert package["depth"] == 0
        # Depth 0 should only include primary profile
        assert len(package["profiles"]) == 1

    def test_load_profile_package_depth_1(self):
        """Test loading profile package with depth 1 (primary + neighbors)."""
        package = load_profile_package("TribalGovernmentUS", depth=1)

        assert package["primary_profile"] == "TribalGovernmentUS"
        assert "TribalGovernmentUS" in package["profiles"]
        assert "OfficeHeldByHeadOfState" in package["profiles"]
        assert package["depth"] == 1

    def test_profile_package_has_graph(self):
        """Test that profile package includes graph."""
        package = load_profile_package("TribalGovernmentUS", depth=1)

        assert "graph" in package
        graph = package["graph"]
        assert hasattr(graph, "nodes")
        assert "TribalGovernmentUS" in graph.nodes

    def test_profile_package_has_manifest_sha(self):
        """Test that profile package includes manifest SHA."""
        package = load_profile_package("TribalGovernmentUS", depth=1)

        assert "manifest_commit_sha" in package
        assert len(package["manifest_commit_sha"]) == 40  # SHA-1 is 40 hex chars


class TestProfileGraph:
    """Test profile graph operations."""

    def test_get_profile_graph(self):
        """Test getting complete profile graph."""
        graph = get_profile_graph()

        assert graph is not None
        assert hasattr(graph, "nodes")
        assert "TribalGovernmentUS" in graph.nodes or len(graph.nodes) > 0

    def test_profile_graph_neighbors(self):
        """Test that profile graph reports correct neighbors."""
        graph = get_profile_graph()

        neighbors = graph.get_neighbors("TribalGovernmentUS")
        assert "OfficeHeldByHeadOfState" in neighbors

        neighbors_reverse = graph.get_neighbors("OfficeHeldByHeadOfState")
        assert "TribalGovernmentUS" in neighbors_reverse


class TestProfileLinkage:
    """Test cross-profile linkage resolution."""

    def test_resolve_profile_link_exists(self):
        """Test resolving existing profile link."""
        linkage = resolve_profile_link(
            "TribalGovernmentUS", "office_held_by_head_of_state"
        )

        assert linkage is not None
        assert linkage["target_profile"] == "OfficeHeldByHeadOfState"
        assert "cardinality" in linkage
        assert "workflow_policy" in linkage

    def test_resolve_profile_link_cardinality(self):
        """Test that linkage includes cardinality constraints."""
        linkage = resolve_profile_link(
            "TribalGovernmentUS", "office_held_by_head_of_state"
        )

        assert linkage is not None
        cardinality = linkage.get("cardinality", {})
        assert "min" in cardinality
        assert "max" in cardinality
        assert cardinality["max"] == 1  # At most one office held by head

    def test_resolve_profile_link_nonexistent(self):
        """Test resolving nonexistent link returns None."""
        linkage = resolve_profile_link("TribalGovernmentUS", "nonexistent_statement")

        assert linkage is None


class TestCurationPacketCreation:
    """Test curation packet creation and validation."""

    def test_create_single_entity_packet(self):
        """Test creating single-entity curation packet."""
        packet = create_curation_packet("TribalGovernmentUS", operation_mode="single")

        assert "packet_id" in packet
        assert packet["packet_id"].startswith("pkt-")
        assert packet["operation_mode"] == "single"
        assert packet["primary_profile"] == "TribalGovernmentUS"
        assert "created_at" in packet
        assert "manifest_commit_sha" in packet

    def test_create_bulk_entity_packet(self):
        """Test creating multi-entity (bulk) curation packet."""
        packet = create_curation_packet(
            "TribalGovernmentUS", operation_mode="bulk", depth=1
        )

        assert packet["operation_mode"] == "bulk"
        assert len(packet["entities"]) >= 1  # At least primary
        # With depth=1, should include related profiles
        assert len(packet["entities"]) >= 1

    def test_packet_entity_ids(self):
        """Test that packet entities have proper IDs."""
        packet = create_curation_packet("TribalGovernmentUS", operation_mode="bulk")

        entity_ids = [e["id"] for e in packet["entities"]]
        # Should have sequential IDs
        assert "ent-001" in entity_ids
        # All should follow ent-XXX pattern
        for ent_id in entity_ids:
            assert ent_id.startswith("ent-")
            assert len(ent_id) == 7  # "ent-" + 3 digits

    def test_packet_cross_references(self):
        """Test that packet includes cross-references."""
        packet = create_curation_packet(
            "TribalGovernmentUS", operation_mode="bulk", depth=1
        )

        cross_refs = packet.get("cross_references", [])
        # If we have multiple entities, should have cross-references
        if len(packet["entities"]) > 1:
            assert len(cross_refs) > 0
            # Each cross-ref should have from/to/via_statement
            for ref in cross_refs:
                assert "from" in ref
                assert "to" in ref
                assert "via_statement" in ref

    def test_packet_cardinality_constraints(self):
        """Test that packet includes cardinality constraints."""
        packet = create_curation_packet(
            "TribalGovernmentUS", operation_mode="bulk", depth=1
        )

        constraints = packet.get("cardinality_constraints", [])
        if len(packet["entities"]) > 1:
            assert len(constraints) > 0
            # Each constraint should have min/max
            for constraint in constraints:
                assert "min" in constraint
                assert "max" in constraint
                assert constraint["min"] >= 0

    def test_packet_profile_package(self):
        """Test that packet includes profile package data."""
        packet = create_curation_packet("TribalGovernmentUS", operation_mode="bulk")

        assert "profile_package" in packet
        profile_pkg = packet["profile_package"]
        assert "profiles" in profile_pkg
        assert "graph" in profile_pkg
        assert "primary_profile" in profile_pkg


class TestPacketValidation:
    """Test curation packet validation."""

    def test_validate_valid_packet(self):
        """Test validating a valid packet."""
        packet = create_curation_packet("TribalGovernmentUS", operation_mode="bulk")

        is_valid, errors = validate_packet_structure(packet)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_field_errors(self):
        """Test that validation catches missing required fields."""
        packet = {
            "operation_mode": "single"
        }  # Missing entities, cross_references, etc.

        is_valid, errors = validate_packet_structure(packet)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_bad_cross_reference(self):
        """Test that validation catches invalid cross-references."""
        packet = {
            "packet_id": "pkt-test",
            "operation_mode": "single",
            "entities": [{"id": "ent-001", "profile": "Test"}],
            "cross_references": [
                {
                    "from": "ent-001",
                    "to": "ent-999",  # References nonexistent entity
                    "via_statement": "test",
                }
            ],
        }

        is_valid, errors = validate_packet_structure(packet)

        assert is_valid is False
        assert any("unknown entity" in str(e) for e in errors)

    def test_validate_bad_cardinality(self):
        """Test that validation catches invalid cardinality."""
        packet = {
            "packet_id": "pkt-test",
            "operation_mode": "single",
            "entities": [{"id": "ent-001"}],
            "cross_references": [],
            "cardinality_constraints": [
                {
                    "from": "ent-001",
                    "to": "ent-002",
                    "min": 5,
                    "max": 2,  # max < min
                }
            ],
        }

        is_valid, errors = validate_packet_structure(packet)

        assert is_valid is False
        assert any("min" in str(e).lower() for e in errors)


class TestIntegration:
    """Integration tests combining multiple Phase 3 functions."""

    def test_full_workflow_load_manifest_to_packet(self):
        """Test full workflow: load manifest → profile → package → packet."""
        # 1. Load manifest
        manifest = load_manifest()
        assert manifest is not None

        # 2. Load profile
        profile = load_profile("TribalGovernmentUS", manifest)
        assert profile is not None

        # 3. Load profile package
        package = load_profile_package("TribalGovernmentUS", depth=1, manifest=manifest)
        assert len(package["profiles"]) >= 1

        # 4. Get profile graph
        graph = get_profile_graph(manifest)
        assert graph is not None

        # 5. Resolve linkage
        linkage = resolve_profile_link(
            "TribalGovernmentUS", "office_held_by_head_of_state", manifest
        )
        assert linkage is not None

        # 6. Create curation packet
        packet = create_curation_packet(
            "TribalGovernmentUS", "bulk", depth=1, manifest=manifest
        )
        assert packet is not None

        # 7. Validate packet
        is_valid, errors = validate_packet_structure(packet)
        assert is_valid is True
        assert len(errors) == 0

    def test_packet_entity_data_structure(self):
        """Test that packet entities have proper structure for wizard consumption."""
        packet = create_curation_packet("TribalGovernmentUS", "bulk")

        for entity in packet["entities"]:
            # Each entity should have these fields
            assert "id" in entity
            assert "profile" in entity
            assert "data" in entity
            assert "profile_structure" in entity

            # profile_structure should contain profile info
            structure = entity["profile_structure"]
            assert "statements" in structure
