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
        spirit_safe_root = tmp_path / ".SpiritSafe"
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
