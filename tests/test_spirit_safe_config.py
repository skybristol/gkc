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
        resolved = source.resolve_relative("still/profiles/Q4.json")
        assert isinstance(resolved, str)
        assert resolved == (
            "https://raw.githubusercontent.com/"
            "skybristol/SpiritSafe/main/still/profiles/Q4.json"
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
    """list_profiles() discovers JSON profiles from the configured layout."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profiles_dir = spirit_safe_root / "still" / "profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "Q4.json").write_text("{}", encoding="utf-8")
    (profiles_dir / "Q39.json").write_text("{}", encoding="utf-8")
    (profiles_dir / "Q51.json").write_text("{}", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        profiles = gkc.list_profiles()

        assert profiles == ["Q4", "Q39", "Q51"]
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_list_profiles_ignores_hidden_files(tmp_path: Path):
    """list_profiles() ignores hidden files and non-JSON content."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profiles_dir = spirit_safe_root / "still" / "profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "Q4.json").write_text("{}", encoding="utf-8")
    (profiles_dir / ".hidden.json").write_text("{}", encoding="utf-8")
    (profiles_dir / "README.md").write_text("ignore me", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)
        profiles = gkc.list_profiles()

        assert profiles == ["Q4"]
        assert ".hidden" not in profiles
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )


def test_profile_exists_returns_true_for_valid_profile(tmp_path: Path):
    """profile_exists() returns True when a JSON profile document exists."""
    spirit_safe_root = tmp_path / "SpiritSafe"
    profile_dir = spirit_safe_root / "still" / "profiles"
    profile_dir.mkdir(parents=True)
    (profile_dir / "Q99.json").write_text("{}", encoding="utf-8")

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

        assert gkc.profile_exists("Q99") is True
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
