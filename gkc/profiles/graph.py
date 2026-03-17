"""
Profile graph models for traversing cross-profile relationships.

These models represent the graph of relationships between entity profiles,
enabling multi-entity curation workflows and validation.

Plain meaning: Navigate connections between different entity types.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


def _entity_id_from_reference(reference: Any) -> Optional[str]:
    """Normalize a QID or entity URI to its trailing entity identifier."""

    if not isinstance(reference, str):
        return None

    candidate = reference.rstrip("/").split("/")[-1]
    if not candidate:
        return None
    if candidate[0] in {"Q", "P"} and candidate[1:].isdigit():
        return candidate
    return None


class GraphEdge(BaseModel):
    """Define a directed edge in the profile graph.

    Args:
        target_profile: Profile ID that this edge points to.
        via_statement: Statement ID that creates this relationship.
        relationship_type: Semantic relationship identifier.
        cardinality: Min/max constraints for linked entities.
        traversal: Traversal configuration for this edge.

    Example:
        >>> GraphEdge(
        ...     target_profile="OfficeHeldByHeadOfState",
        ...     via_statement="office_held_by_head_of_state",
        ...     relationship_type="office_of_head_of_state",
        ...     cardinality={"min": 0, "max": 1},
        ...     traversal={"max_depth": 1}
        ... )

    Plain meaning: A connection from one profile to another.
    """

    target_profile: str = Field(..., description="Target profile ID")
    label: Optional[str] = Field(default=None, description="Target profile label")
    via_statement: str = Field(..., description="Statement creating relationship")
    relationship_type: str = Field(..., description="Relationship identifier")
    cardinality: Dict[str, int] = Field(
        default_factory=dict, description="Min/max constraints"
    )
    traversal: Dict[str, int] = Field(
        default_factory=dict, description="Traversal config"
    )


class ProfileNode(BaseModel):
    """Define a node in the profile graph.

    Args:
        profile_id: Unique profile identifier.
        neighbors: List of directly connected profile IDs.
        edges: List of outgoing edges with metadata.

    Example:
        >>> ProfileNode(
        ...     profile_id="TribalGovernmentUS",
        ...     neighbors=["OfficeHeldByHeadOfState"],
        ...     edges=[GraphEdge(...)]
        ... )

    Plain meaning: A profile and its connections.
    """

    profile_id: str = Field(..., description="Profile identifier")
    neighbors: List[str] = Field(default_factory=list, description="Connected profiles")
    edges: List[GraphEdge] = Field(default_factory=list, description="Outgoing edges")


class ProfileGraph(BaseModel):
    """Represent the graph of profile relationships.

    This model provides traversal and query operations for navigating
    cross-profile relationships during multi-entity curation workflows.

    Args:
        nodes: Mapping of profile IDs to ProfileNode instances.

    Example:
        >>> graph = ProfileGraph.from_manifest_data(manifest)
        >>> neighbors = graph.get_neighbors("Q4")
        >>> edges = graph.get_edges("Q4", "Q39")

    Plain meaning: The complete network of profile relationships.
    """

    nodes: Dict[str, ProfileNode] = Field(
        default_factory=dict, description="Profile nodes by ID"
    )

    @classmethod
    def from_manifest_data(cls, manifest_profiles: List[Dict]) -> ProfileGraph:
        """Build a ProfileGraph from manifest JSON data.

        Args:
            manifest_profiles: List of profile dictionaries from manifest.

        Returns:
            ProfileGraph instance with nodes and edges loaded.

        Side effects:
            None.

        Example:
            >>> import json
            >>> manifest = json.load(open("manifest.json"))
            >>> graph = ProfileGraph.from_manifest_data(manifest["profiles"])

        Plain meaning: Create graph from manifest file data.
        """
        nodes = {}
        for profile_data in manifest_profiles:
            profile_id = _entity_id_from_reference(
                profile_data.get("qid") or profile_data.get("entity")
            )
            if not profile_id:
                continue

            raw_edges = profile_data.get("profile_graph", [])
            edges: List[GraphEdge] = []
            neighbors: List[str] = []

            for edge_data in raw_edges:
                target_profile = _entity_id_from_reference(edge_data.get("entity"))
                if not target_profile:
                    continue
                neighbors.append(target_profile)
                edges.append(
                    GraphEdge(
                        target_profile=target_profile,
                        label=edge_data.get("label"),
                        via_statement=str(edge_data.get("via_statement") or ""),
                        relationship_type=str(edge_data.get("linkage_type") or ""),
                    )
                )

            nodes[profile_id] = ProfileNode(
                profile_id=profile_id,
                neighbors=neighbors,
                edges=edges,
            )

        return cls(nodes=nodes)

    @classmethod
    def from_profile_documents(
        cls, profile_documents: Dict[str, Dict[str, Any]]
    ) -> ProfileGraph:
        """Build a ProfileGraph directly from loaded JSON profile documents."""

        manifest_like_profiles: List[Dict[str, Any]] = []
        for profile_id, document in profile_documents.items():
            manifest_like_profiles.append(
                {
                    "qid": profile_id,
                    "entity": document.get("entity"),
                    "profile_graph": document.get("metadata", {}).get(
                        "profile_graph", []
                    ),
                }
            )
        return cls.from_manifest_data(manifest_like_profiles)

    @classmethod
    def from_metadata_dict(cls, profile_id: str, metadata: Dict) -> ProfileGraph:
        """Build a single-node ProfileGraph from metadata.yaml dict.

        Args:
            profile_id: Profile identifier.
            metadata: Parsed metadata.yaml dictionary.

        Returns:
            ProfileGraph with single node.

        Side effects:
            None.

        Example:
            >>> import yaml
            >>> metadata = yaml.safe_load(open("metadata.yaml"))
            >>> graph = ProfileGraph.from_metadata_dict("TribalGovernmentUS", metadata)

        Plain meaning: Create graph from single profile metadata file.
        """
        graph_data = metadata.get("profile_graph", {})

        edges = [GraphEdge(**edge_data) for edge_data in graph_data.get("edges", [])]

        node = ProfileNode(
            profile_id=profile_id,
            neighbors=graph_data.get("neighbors", []),
            edges=edges,
        )

        return cls(nodes={profile_id: node})

    def get_neighbors(self, profile_id: str) -> List[str]:
        """Get list of profiles directly connected to this profile.

        Args:
            profile_id: Profile identifier to query.

        Returns:
            List of neighbor profile IDs.

        Side effects:
            None.

        Example:
            >>> graph.get_neighbors("TribalGovernmentUS")
            ['OfficeHeldByHeadOfState']

        Plain meaning: Find all profiles this one links to.
        """
        node = self.nodes.get(profile_id)
        return node.neighbors if node else []

    def get_edges(
        self, source_profile: str, target_profile: Optional[str] = None
    ) -> List[GraphEdge]:
        """Get edges from source profile, optionally filtered by target.

        Args:
            source_profile: Source profile identifier.
            target_profile: Optional target to filter edges.

        Returns:
            List of matching GraphEdge instances.

        Side effects:
            None.

        Example:
            >>> edges = graph.get_edges("TribalGovernmentUS")
            >>> specific = graph.get_edges("TribalGovernmentUS", "OfficeHeldByHeadOfState")

        Plain meaning: Find connections from one profile to another.
        """
        node = self.nodes.get(source_profile)
        if not node:
            return []

        edges = node.edges
        if target_profile:
            edges = [e for e in edges if e.target_profile == target_profile]

        return edges

    def get_cardinality(
        self, source_profile: str, target_profile: str
    ) -> Optional[Dict[str, int]]:
        """Get cardinality constraints for a specific edge.

        Args:
            source_profile: Source profile identifier.
            target_profile: Target profile identifier.

        Returns:
            Dict with 'min' and 'max' keys, or None if edge not found.

        Side effects:
            None.

        Example:
            >>> graph.get_cardinality("TribalGovernmentUS", "OfficeHeldByHeadOfState")
            {'min': 0, 'max': 1}

        Plain meaning: How many linked entities are required or allowed.
        """
        edges = self.get_edges(source_profile, target_profile)
        return edges[0].cardinality if edges else None

    def traverse(
        self, start_profile: str, max_depth: int = 1, visited: Optional[Set[str]] = None
    ) -> List[str]:
        """Traverse the graph from a starting profile up to max_depth.

        Args:
            start_profile: Profile ID to start traversal from.
            max_depth: Maximum traversal depth (1 = immediate neighbors only).
            visited: Internal set for cycle detection.

        Returns:
            List of profile IDs reachable within max_depth steps.

        Side effects:
            None.

        Example:
            >>> graph.traverse("TribalGovernmentUS", max_depth=1)
            ['OfficeHeldByHeadOfState']
            >>> graph.traverse("TribalGovernmentUS", max_depth=2)
            ['OfficeHeldByHeadOfState', 'AdditionalProfile']

        Plain meaning: Find all profiles reachable from this one.
        """
        if visited is None:
            visited = set()

        if start_profile in visited or max_depth == 0:
            return []

        visited.add(start_profile)
        result = []

        neighbors = self.get_neighbors(start_profile)
        for neighbor in neighbors:
            if neighbor not in visited:
                result.append(neighbor)
                if max_depth > 1:
                    result.extend(self.traverse(neighbor, max_depth - 1, visited))

        return result

    def validate_bidirectional_awareness(self) -> List[str]:
        """Validate that all edges have reciprocal awareness.

        Returns:
            List of validation error messages (empty if valid).

        Side effects:
            None.

        Example:
            >>> errors = graph.validate_bidirectional_awareness()
            >>> if errors:
            ...     print("Graph validation failed:", errors)

        Plain meaning: Check that relationships are properly declared on both sides.
        """
        errors = []

        for profile_id, node in self.nodes.items():
            for edge in node.edges:
                target_id = edge.target_profile

                # Check if target profile exists in graph
                if target_id not in self.nodes:
                    errors.append(
                        f"{profile_id} → {target_id}: Target profile not found in graph"
                    )
                    continue

                # Check if target has this profile in its neighbors
                target_node = self.nodes[target_id]
                if profile_id not in target_node.neighbors:
                    errors.append(
                        f"{profile_id} → {target_id}: Missing reciprocal neighbor declaration"
                    )

        return errors

    def has_profile(self, profile_id: str) -> bool:
        """Check if a profile exists in the graph.

        Args:
            profile_id: Profile identifier to check.

        Returns:
            True if profile is in graph, False otherwise.

        Side effects:
            None.

        Example:
            >>> graph.has_profile("TribalGovernmentUS")
            True

        Plain meaning: Does this profile exist in the graph?
        """
        return profile_id in self.nodes

    def profile_count(self) -> int:
        """Get the number of profiles in the graph.

        Returns:
            Count of profile nodes.

        Side effects:
            None.

        Example:
            >>> graph.profile_count()
            2

        Plain meaning: How many profiles are in this graph?
        """
        return len(self.nodes)
