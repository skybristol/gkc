"""CLI tests for SpiritSafe sitelinks artifact sync command."""

import json

from gkc import cli


def test_spiritsafe_sitelinks_sync_wikimedia_sites_json(monkeypatch, capsys, tmp_path):
    local_root = tmp_path / "SpiritSafe"
    config_dir = local_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
  layout_version: 2
  roots:
    materialized: still
    partners: partners
  paths:
    entities: still/entities
    profiles: still/profiles
    value_list_queries: still/value_lists/queries
    value_list_cache: still/value_lists/cache
    semantic_anchors: config/semantic_anchors.json
    logs: still/logs
    wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_export(output_path, *, source_url, timeout, user_agent):
        assert output_path.endswith("partners/wikimedia_sites.json")
        assert source_url.startswith("https://meta.wikimedia.org/")
        assert timeout == 30
        assert user_agent
        return {
            "metadata": {
                "source_url": source_url,
                "schema_version": "1.0",
                "fetched_at": "2026-03-27T00:00:00Z",
                "total_sites": 3,
                "active_sites": 2,
                "closed_sites": 1,
            },
            "index": {
                "by_dbname": {"enwiki": {}},
                "by_domain": {"en.wikipedia.org": ["enwiki"]},
            },
        }

    monkeypatch.setattr(cli, "export_wikimedia_sites_artifact", fake_export)

    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "sitelinks",
            "sync-wikimedia-sites",
            "--source",
            "local",
            "--local-root",
            str(local_root),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["command"] == "spiritsafe.sitelinks.sync-wikimedia-sites"
    assert payload["ok"] is True
    assert payload["details"]["total_sites"] == 3
    assert payload["details"]["closed_sites"] == 1


def test_spiritsafe_sitelinks_sync_requires_local_root(capsys):
    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "sitelinks",
            "sync-wikimedia-sites",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert "requires --source local --local-root" in payload["message"]
