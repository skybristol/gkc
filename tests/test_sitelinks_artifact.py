"""Tests for Wikimedia sitematrix artifact normalization and export."""

import json
from pathlib import Path

import pytest

from gkc.sitelinks import (
    build_wikimedia_sites_artifact_from_sitematrix,
    export_wikimedia_sites_artifact,
)


def _sample_sitematrix_payload() -> dict:
    return {
        "sitematrix": {
            "0": {
                "code": "en",
                "name": "English",
                "site": [
                    {
                        "code": "en",
                        "dbname": "enwiki",
                        "url": "https://en.wikipedia.org/wiki/$1",
                        "sitename": "Wikipedia",
                    },
                    {
                        "code": "en",
                        "dbname": "enwikinews",
                        "url": "https://en.wikinews.org/wiki/$1",
                        "sitename": "Wikinews",
                        "closed": "",
                    },
                ],
            },
            "specials": [
                {
                    "code": "commons",
                    "dbname": "commonswiki",
                    "url": "https://commons.wikimedia.org/wiki/$1",
                    "sitename": "Wikimedia Commons",
                }
            ],
        }
    }


def test_build_wikimedia_sites_artifact_includes_closed_and_indexes() -> None:
    artifact = build_wikimedia_sites_artifact_from_sitematrix(
        _sample_sitematrix_payload(),
        source_url="https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json&smstate=all",
        fetched_at="2026-03-27T00:00:00Z",
    )

    metadata = artifact["metadata"]
    assert metadata["total_sites"] == 3
    assert metadata["active_sites"] == 2
    assert metadata["closed_sites"] == 1
    assert metadata["fetched_at"] == "2026-03-27T00:00:00Z"

    by_dbname = artifact["index"]["by_dbname"]
    assert by_dbname["enwiki"]["domain"] == "en.wikipedia.org"
    assert by_dbname["enwikinews"]["closed"] is True
    assert by_dbname["commonswiki"]["project"] == "wiki"

    by_domain = artifact["index"]["by_domain"]
    assert by_domain["en.wikipedia.org"] == ["enwiki"]
    assert by_domain["en.wikinews.org"] == ["enwikinews"]


def test_build_wikimedia_sites_artifact_raises_on_conflicting_dbname() -> None:
    payload = {
        "sitematrix": {
            "0": {
                "code": "en",
                "name": "English",
                "site": [
                    {
                        "code": "en",
                        "dbname": "enwiki",
                        "url": "https://en.wikipedia.org/wiki/$1",
                        "sitename": "Wikipedia",
                    },
                    {
                        "code": "en",
                        "dbname": "enwiki",
                        "url": "https://en.wikipedia.org/wiki/Main_Page",
                        "sitename": "Wikipedia",
                    },
                ],
            }
        }
    }

    with pytest.raises(ValueError, match="Conflicting sitematrix entries"):
        build_wikimedia_sites_artifact_from_sitematrix(payload)


def test_export_wikimedia_sites_artifact_writes_json(
    monkeypatch, tmp_path: Path
) -> None:
    payload = _sample_sitematrix_payload()

    def fake_fetch(**kwargs):
        _ = kwargs
        return payload

    monkeypatch.setattr("gkc.sitelinks.fetch_wikimedia_sitematrix", fake_fetch)

    output = tmp_path / "wikimedia_sites.json"
    artifact = export_wikimedia_sites_artifact(str(output))

    assert output.exists()
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert (
        persisted["metadata"]["schema_version"]
        == artifact["metadata"]["schema_version"]
    )
    assert persisted["metadata"]["total_sites"] == 3
    assert persisted["index"]["by_dbname"]["enwiki"]["domain"] == "en.wikipedia.org"
