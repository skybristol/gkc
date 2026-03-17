"""Tests for SpiritSafe JSON entity profile builder/export utilities."""

import json

from gkc.spirit_safe import (
    build_entity_profile_json_documents,
    export_entity_profile_json_documents,
)


def _build_entity_claim_entity_id(entity_id: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "id": entity_id,
                }
            }
        }
    }


def test_build_entity_profile_json_documents_from_cache_entities(tmp_path):
    """Build returns JSON entity profile docs for cache entities typed as Q3."""
    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"en": {"value": "Tribal Government in the United States"}},
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    docs = build_entity_profile_json_documents(cache_entities_dir)

    assert len(docs) == 1
    assert docs[0]["entity"].endswith("/Q4")
    assert docs[0]["metadata"]["statement_count"] == 0


def test_export_entity_profile_json_documents_writes_qid_files(tmp_path):
    """Export writes one JSON file per built profile document."""
    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"en": {"value": "Tribal Government in the United States"}},
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(cache_entities_dir, output_dir)

    assert result.output_dir == str(output_dir.resolve())
    assert result.written_ids == ["Q4"]

    profile_path = output_dir / "Q4.json"
    assert profile_path.exists()
    profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile_payload["entity"].endswith("/Q4")
