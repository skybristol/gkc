"""Tests for profile lookup hydration workflow."""

from pathlib import Path

import pytest
from typing import Optional

import gkc


@pytest.fixture
def spirit_safe_tmp(tmp_path: Path) -> Path:
    root = tmp_path / ".SpiritSafe"
    (root / "profiles").mkdir(parents=True, exist_ok=True)
    (root / "queries").mkdir(parents=True, exist_ok=True)
    return root


def test_hydrate_profile_lookups_dry_run_dedupes(spirit_safe_tmp: Path):
    query_path = spirit_safe_tmp / "queries" / "simple.sparql"
    query_path.write_text(
        """
PREFIX wd: <http://www.wikidata.org/entity/>
SELECT ?item ?itemLabel WHERE {
  VALUES ?item { wd:{{qid}} }
  ?item <http://www.w3.org/2000/01/rdf-schema#label> ?itemLabel .
  FILTER(LANG(?itemLabel) = "en")
}
""".strip(),
        encoding="utf-8",
    )

    profile_path = spirit_safe_tmp / "profiles" / "example.yaml"
    profile_path.write_text(
        """
name: Example
description: Example
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
  - id: f2
    label: Field 2
    wikidata_property: P279
    type: statement
    required: false
    value:
      type: item
    qualifiers:
      - id: language
        label: Language
        wikidata_property: P407
        required: false
        value:
          type: item
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
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_tmp)
        summary = gkc.hydrate_profile_lookups([profile_path], dry_run=True)
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )

    assert summary["profiles_scanned"] == 1
    assert summary["lookup_specs_found"] == 2
    assert summary["unique_queries"] == 1
    assert summary["unique_queries_executed"] == 0
    assert summary["dry_run"] is True


def test_hydrate_profile_lookups_executes_and_writes_cache(
    spirit_safe_tmp: Path, monkeypatch: pytest.MonkeyPatch
):
    query_path = spirit_safe_tmp / "queries" / "simple.sparql"
    query_path.write_text(
        "SELECT ?item ?itemLabel WHERE { VALUES ?item { wd:{{qid}} } }",
        encoding="utf-8",
    )

    profile_path = spirit_safe_tmp / "profiles" / "example.yaml"
    profile_path.write_text(
        """
name: Example
description: Example
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
        id: stated_in
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

    captured_queries: list[str] = []

    def fake_paginate_query(
        query: str,
        page_size: int = 1000,
        endpoint: str = "https://query.wikidata.org/sparql",
        max_results: Optional[int] = None,
    ):
        captured_queries.append(query)
        return [{"item": "Q42", "itemLabel": "Douglas Adams"}]

    monkeypatch.setattr("gkc.spirit_safe.paginate_query", fake_paginate_query)

    previous = gkc.get_spirit_safe_source()
    try:
        gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_tmp)
        summary = gkc.hydrate_profile_lookups([profile_path], dry_run=False)
    finally:
        gkc.set_spirit_safe_source(
            mode=previous.mode,
            github_repo=previous.github_repo,
            github_ref=previous.github_ref,
            local_root=previous.local_root,
        )

    assert summary["unique_queries"] == 1
    assert summary["unique_queries_executed"] == 1
    assert summary["cache_file_count"] >= 1
    assert captured_queries
    assert "{{qid}}" not in captured_queries[0]


def test_lookup_fetcher_deduplicates_results(monkeypatch: pytest.MonkeyPatch):
    """LookupFetcher removes duplicate results from query execution."""
    from gkc.spirit_safe import LookupFetcher

    # Mock paginate_query to return results with duplicates
    def fake_paginate_query(
        query: str,
        page_size: int = 1000,
        endpoint: str = "https://query.wikidata.org/sparql",
        max_results: Optional[int] = None,
    ):
        # Return results with intentional duplicates
        return [
            {"item": "Q1", "label": "Item 1"},
            {"item": "Q2", "label": "Item 2"},
            {"item": "Q1", "label": "Item 1"},  # Duplicate
            {"item": "Q3", "label": "Item 3"},
            {"item": "Q2", "label": "Item 2"},  # Duplicate
            {"item": "Q1", "label": "Item 1"},  # Duplicate
        ]

    monkeypatch.setattr("gkc.spirit_safe.paginate_query", fake_paginate_query)

    fetcher = LookupFetcher()
    results = fetcher.fetch("SELECT ?item ?label WHERE { ... }")

    # Verify: duplicates removed, order preserved, first occurrence kept
    assert len(results) == 3
    assert results[0]["item"] == "Q1"
    assert results[1]["item"] == "Q2"
    assert results[2]["item"] == "Q3"
