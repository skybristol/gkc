"""CLI tests for SpiritSafe semantic anchor artifact build and validate commands."""

import json
from pathlib import Path

from gkc import cli


def test_spiritsafe_semantic_anchors_build_json(monkeypatch, capsys, tmp_path):
    local_root = tmp_path / "SpiritSafe"
    local_root.mkdir(parents=True, exist_ok=True)

    def fake_export(spiritsafe_root, output_path=None):
        assert str(spiritsafe_root).endswith("SpiritSafe")
        assert str(output_path).endswith("cache/config/semantic_anchors.json")
        return {
            "metadata": {
                "generated_at": "2026-04-03T00:00:00Z",
                "property_count": 1,
                "item_count": 1,
            },
            "entities": {
                "_foo": {"id": "Q1", "entity": "https://example.org/entity/Q1"},
                "_bar": {
                    "id": "P1",
                    "entity": "https://example.org/entity/P1",
                    "datatype": "string",
                },
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
    assert payload["details"]["property_count"] == 1
    assert payload["details"]["item_count"] == 1


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


def test_spiritsafe_semantic_anchors_validate_json(monkeypatch, capsys, tmp_path):
    artifact_path = tmp_path / "semantic_anchors.json"
    artifact_path.write_text(
        json.dumps({"metadata": {}, "entities": {"_entity": {"id": "Q1"}}}),
        encoding="utf-8",
    )

    class FakeResult:
        valid = True
        required_anchor_count = 2
        matched_anchor_count = 2
        evaluated_anchor_count = 1
        freshness_checked = False
        freshness_match = None
        notices = []

    monkeypatch.setattr(cli, "validate_semantic_anchor_document", lambda *args, **kwargs: FakeResult())

    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "semantic-anchors",
            "validate",
            "--artifact-file",
            str(artifact_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["command"] == "spiritsafe.semantic-anchors.validate"
    assert payload["ok"] is True
    assert payload["details"]["artifact_path"] == str(artifact_path)
    assert payload["details"]["required_anchor_count"] == 2


def test_spiritsafe_semantic_anchors_validate_can_compare_current_cache(
    monkeypatch, capsys, tmp_path
):
    local_root = tmp_path / "SpiritSafe"
    artifact_path = local_root / "cache" / "config" / "semantic_anchors.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps({"metadata": {}, "entities": {"_entity": {"id": "Q1"}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli,
        "resolve_spiritsafe_meta_wikibase_config",
        lambda root: (Path(root) / "config" / "dd-wikibase.yaml", {"internal_name_identifier_prefix": "_"}),
    )
    monkeypatch.setattr(
        cli,
        "build_spiritsafe_semantic_anchor_document",
        lambda root: {"metadata": {}, "entities": {"_entity": {"id": "Q1"}}},
    )

    class FakeResult:
        valid = True
        required_anchor_count = 2
        matched_anchor_count = 2
        evaluated_anchor_count = 1
        freshness_checked = True
        freshness_match = True
        notices = []

    monkeypatch.setattr(cli, "validate_semantic_anchor_document", lambda *args, **kwargs: FakeResult())

    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "semantic-anchors",
            "validate",
            "--local-root",
            str(local_root),
            "--check-current-cache",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["details"]["freshness_checked"] is True
    assert payload["details"]["freshness_match"] is True


def test_spiritsafe_semantic_anchors_validate_requires_input(capsys):
    exit_code = cli.main(
        [
            "--json",
            "spiritsafe",
            "semantic-anchors",
            "validate",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert "requires --artifact-file or --local-root" in payload["message"]
