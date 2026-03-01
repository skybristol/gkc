"""Tests for SpiritSafe source configuration and cache resolution."""

from pathlib import Path

import pytest

import gkc


def test_default_spirit_safe_source_is_github():
    """Default source uses GitHub SpiritSafe repository."""
    source = gkc.get_spirit_safe_source()
    assert source.mode == "github"
    assert source.github_repo == gkc.DEFAULT_SPIRIT_SAFE_GITHUB_REPO


def test_set_spirit_safe_source_local_requires_root():
    """Local mode requires local_root parameter."""
    previous = gkc.get_spirit_safe_source()
    try:
        with pytest.raises(ValueError, match="local_root is required"):
            gkc.set_spirit_safe_source(mode="local")
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_set_spirit_safe_source_local_updates_cache_dir(tmp_path: Path):
    """Local mode resolves cache directory under local SpiritSafe root."""
    previous = gkc.get_spirit_safe_source()
    try:
        spirit_safe_root = tmp_path / "SpiritSafe"
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        source = gkc.get_spirit_safe_source()
        assert source.mode == "local"
        assert source.local_root == spirit_safe_root.resolve()

        cache = gkc.LookupCache()
        assert cache.cache_dir == spirit_safe_root.resolve() / "cache"
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_github_mode_relative_resolution():
    """GitHub mode resolves SpiritSafe-relative path to raw GitHub URL."""
    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(
            mode="github",
            github_repo="skybristol/SpiritSafe",
            github_ref="main",
        )
        source = gkc.get_spirit_safe_source()
        resolved = source.resolve_relative("profiles/Example.yaml")
        assert isinstance(resolved, str)
        assert resolved == (
            "https://raw.githubusercontent.com/"
            "skybristol/SpiritSafe/main/profiles/Example.yaml"
        )
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_resolve_profile_path_prefers_registrant_path():
    """Profile names resolve to registrant package profile.yaml path."""
    assert gkc.resolve_profile_path("TribalGovernmentUS") == (
        "profiles/TribalGovernmentUS/profile.yaml"
    )
    assert gkc.resolve_profile_path("TribalGovernmentUS.yaml") == (
        "profiles/TribalGovernmentUS/profile.yaml"
    )


def test_resolve_profile_path_keeps_explicit_paths():
    """Explicit profile paths are preserved as-is."""
    explicit_path = "profiles/TribalGovernmentUS/profile.yaml"
    assert gkc.resolve_profile_path(explicit_path) == explicit_path


def test_hydrate_profile_lookups_supports_legacy_flat_profile_path(tmp_path: Path):
    """Hydration supports legacy profiles/<Name>.yaml via compatibility fallback."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_dir = spirit_safe_root / "profiles" / "TribalGovernmentUS"
    query_dir = spirit_safe_root / "queries"
    profile_dir.mkdir(parents=True, exist_ok=True)
    query_dir.mkdir(parents=True, exist_ok=True)

    (query_dir / "simple.sparql").write_text(
        "SELECT ?item ?itemLabel WHERE { VALUES ?item { wd:{{qid}} } }",
        encoding="utf-8",
    )

    (profile_dir / "profile.yaml").write_text(
        """
name: Example
description: Example profile
fields:
  - id: f1
    label: Field 1
    wikidata_property: P31
    type: statement
    required: false
    value:
      type: item
    references:
      allowed:
        - id: stated_in
          wikidata_property: P248
          type: item
          label: Stated in
          allowed_items:
            source: sparql
            query_ref: queries/simple.sparql
            query_params:
              qid: Q42
""".strip(),
        encoding="utf-8",
    )

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        summary = gkc.hydrate_profile_lookups(
            ["profiles/TribalGovernmentUS.yaml"],
            dry_run=True,
        )
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )

    assert summary["profiles_scanned"] == 1
    assert summary["lookup_specs_found"] == 1
    assert summary["unique_queries"] == 1


def test_resolve_query_ref_prefers_profile_relative(tmp_path: Path):
    """Query resolution tries profile-relative path first for registrant profiles."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_query_dir = spirit_safe_root / "profiles" / "TribalGovernmentUS" / "queries"
    root_query_dir = spirit_safe_root / "queries"
    profile_query_dir.mkdir(parents=True, exist_ok=True)
    root_query_dir.mkdir(parents=True, exist_ok=True)

    # Create profile-relative query
    (profile_query_dir / "test.sparql").write_text(
        "SELECT ?profile_version", encoding="utf-8"
    )
    # Create root-relative query with different content
    (root_query_dir / "test.sparql").write_text(
        "SELECT ?root_version", encoding="utf-8"
    )

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        resolved = gkc.resolve_query_ref(
            "queries/test.sparql", "profiles/TribalGovernmentUS/profile.yaml"
        )

        # Should resolve to profile-relative version
        assert str(resolved) == str(
            spirit_safe_root
            / "profiles"
            / "TribalGovernmentUS"
            / "queries"
            / "test.sparql"
        )
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_resolve_query_ref_falls_back_to_root_relative(tmp_path: Path):
    """Query resolution falls back to root-relative when profile-relative not found."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    root_query_dir = spirit_safe_root / "queries"
    root_query_dir.mkdir(parents=True, exist_ok=True)

    # Create only root-relative query (no profile-relative version)
    (root_query_dir / "global.sparql").write_text("SELECT ?global", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        resolved = gkc.resolve_query_ref(
            "queries/global.sparql", "profiles/TribalGovernmentUS/profile.yaml"
        )

        # Should resolve to root-relative version
        assert str(resolved) == str(spirit_safe_root / "queries" / "global.sparql")
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_resolve_query_ref_raises_when_not_found(tmp_path: Path):
    """Raises FileNotFoundError when query is missing in both lookup locations."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    spirit_safe_root.mkdir(parents=True, exist_ok=True)

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        with pytest.raises(
            FileNotFoundError,
            match="Query not found: queries/missing.sparql",
        ):
            gkc.resolve_query_ref(
                "queries/missing.sparql",
                "profiles/TribalGovernmentUS/profile.yaml",
            )
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_resolve_query_ref_only_tries_root_for_flat_profile_paths(tmp_path: Path):
    """Query resolution only tries root-relative for non-registrant profile paths."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    root_query_dir = spirit_safe_root / "queries"
    root_query_dir.mkdir(parents=True, exist_ok=True)

    (root_query_dir / "test.sparql").write_text("SELECT ?item", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        # Flat profile path should not trigger profile-relative attempt
        resolved = gkc.resolve_query_ref(
            "queries/test.sparql", "profiles/FlatProfile.yaml"
        )

        assert str(resolved) == str(spirit_safe_root / "queries" / "test.sparql")
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_list_profiles_returns_available_profiles(tmp_path: Path):
    """list_profiles() discovers profile directories from SpiritSafe source."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profiles_dir = spirit_safe_root / "profiles"
    (profiles_dir / "ProfileA").mkdir(parents=True)
    (profiles_dir / "ProfileB").mkdir(parents=True)
    (profiles_dir / "ProfileC").mkdir(parents=True)
    # Add profile.yaml files so they're valid
    (profiles_dir / "ProfileA" / "profile.yaml").write_text("name: A", encoding="utf-8")
    (profiles_dir / "ProfileB" / "profile.yaml").write_text("name: B", encoding="utf-8")
    (profiles_dir / "ProfileC" / "profile.yaml").write_text("name: C", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        profiles = gkc.list_profiles()

        assert profiles == ["ProfileA", "ProfileB", "ProfileC"]
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_list_profiles_ignores_hidden_directories(tmp_path: Path):
    """list_profiles() ignores dotfiles and hidden directories."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profiles_dir = spirit_safe_root / "profiles"
    (profiles_dir / "VisibleProfile").mkdir(parents=True)
    (profiles_dir / ".hidden").mkdir(parents=True)
    (profiles_dir / "VisibleProfile" / "profile.yaml").write_text(
        "name: V", encoding="utf-8"
    )

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        profiles = gkc.list_profiles()

        assert profiles == ["VisibleProfile"]
        assert ".hidden" not in profiles
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_profile_exists_returns_true_for_valid_profile(tmp_path: Path):
    """profile_exists() returns True when profile directory and profile.yaml exist."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_dir = spirit_safe_root / "profiles" / "TestProfile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile.yaml").write_text("name: Test", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        assert gkc.profile_exists("TestProfile") is True
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_profile_exists_returns_false_for_missing_profile(tmp_path: Path):
    """profile_exists() returns False when profile doesn't exist."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    spirit_safe_root.mkdir(parents=True)

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        assert gkc.profile_exists("NonexistentProfile") is False
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_get_profile_metadata_loads_complete_metadata(tmp_path: Path):
    """get_profile_metadata() parses and structures metadata.yaml correctly."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_dir = spirit_safe_root / "profiles" / "TestProfile"
    profile_dir.mkdir(parents=True)

    metadata_content = """
name: Test Profile Name
description: This is a test profile description.
version: 1.2.3
status: stable
published_date: 2026-03-01
authors:
  - name: Test Author
    email: author@example.com
maintainers:
  - name: Test Maintainer
source_references:
  - name: Reference One
    url: https://example.com/ref1
related_profiles:
  - RelatedProfileA
  - RelatedProfileB
community_feedback:
  issue_tracker: https://github.com/test/issues
datatypes_used:
  - item
  - url
statements_count: 5
references_required: true
qualifiers_used:
  - P580
  - P582
sparql_sources:
  - query1.sparql
""".strip()

    (profile_dir / "metadata.yaml").write_text(metadata_content, encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        metadata = gkc.get_profile_metadata("TestProfile")

        assert metadata.profile_id == "TestProfile"
        assert metadata.name == "Test Profile Name"
        assert metadata.description == "This is a test profile description."
        assert metadata.version == "1.2.3"
        assert metadata.status == "stable"
        assert metadata.published_date == "2026-03-01"
        assert len(metadata.authors) == 1
        assert metadata.authors[0]["name"] == "Test Author"
        assert metadata.authors[0]["email"] == "author@example.com"
        assert len(metadata.maintainers) == 1
        assert metadata.maintainers[0]["name"] == "Test Maintainer"
        assert len(metadata.source_references) == 1
        assert metadata.source_references[0]["url"] == "https://example.com/ref1"
        assert metadata.related_profiles == ["RelatedProfileA", "RelatedProfileB"]
        assert (
            metadata.community_feedback["issue_tracker"]
            == "https://github.com/test/issues"
        )
        assert metadata.datatypes_used == ["item", "url"]
        assert metadata.statements_count == 5
        assert metadata.references_required is True
        assert metadata.qualifiers_used == ["P580", "P582"]
        assert metadata.sparql_sources == ["query1.sparql"]
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_get_profile_metadata_requires_name_version_status(tmp_path: Path):
    """get_profile_metadata() validates required fields in metadata.yaml."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_dir = spirit_safe_root / "profiles" / "InvalidProfile"
    profile_dir.mkdir(parents=True)

    # Missing 'version' field
    incomplete_metadata = """
name: Incomplete Profile
status: draft
""".strip()

    (profile_dir / "metadata.yaml").write_text(incomplete_metadata, encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        with pytest.raises(ValueError, match="missing required field 'version'"):
            gkc.get_profile_metadata("InvalidProfile")
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_get_profile_metadata_raises_for_missing_profile(tmp_path: Path):
    """get_profile_metadata() raises FileNotFoundError for nonexistent profile."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    spirit_safe_root.mkdir(parents=True)

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        with pytest.raises(FileNotFoundError, match="Could not load metadata"):
            gkc.get_profile_metadata("MissingProfile")
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )
