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
            "_foo": {"id": "Q1", "entity": "https://example.org/entity/Q1"},
            "_bar": {
                "id": "P1",
                "entity": "https://example.org/entity/P1",
                "datatype": "string",
            },
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
    assert payload["details"]["anchor_count"] == 2


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
