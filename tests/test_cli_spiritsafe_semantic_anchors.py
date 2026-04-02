"""CLI tests for SpiritSafe semantic anchor artifact build command."""

import json

from gkc import cli


def test_spiritsafe_semantic_anchors_build_json(monkeypatch, capsys, tmp_path):
    local_root = tmp_path / "SpiritSafe"
    local_root.mkdir(parents=True, exist_ok=True)

    def fake_export(spiritsafe_root, output_path=None):
        assert str(spiritsafe_root).endswith("SpiritSafe")
        assert str(output_path).endswith("cache/config/semantic_anchors.json")
        return {
            "config": {
                "path": "config/dd-wikibase.yaml",
                "id": "datadistillery-wikibase",
            },
            "anchor_count": 3,
            "internal_anchor_count": 1,
        }

    monkeypatch.setattr(cli, "export_spiritsafe_semantic_anchors", fake_export)

    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "semantic-anchors",
            "build",
            "--source",
            "local",
            "--local-root",
            str(local_root),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["command"] == "spiritsafe.semantic-anchors.build"
    assert payload["ok"] is True
    assert payload["details"]["config_path"] == "config/dd-wikibase.yaml"
    assert payload["details"]["anchor_count"] == 3
    assert payload["details"]["internal_anchor_count"] == 1


def test_spiritsafe_semantic_anchors_build_requires_local_root(capsys):
    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "semantic-anchors",
            "build",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert "requires --source local --local-root" in payload["message"]
