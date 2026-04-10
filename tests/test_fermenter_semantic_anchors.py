"""Tests for semantic-anchor validation against the package-owned init contract."""

from gkc.fermenter import validate_semantic_anchor_document
from gkc.wikibase import (
    build_meta_wikibase_semantic_anchor_contract,
    get_meta_wikibase_init_contract_digest,
)


def _valid_anchor_document() -> dict:
    contract = build_meta_wikibase_semantic_anchor_contract()
    entities: dict[str, dict[str, str]] = {}
    property_index = 0
    item_index = 0

    for anchor_name, requirement in contract.requirements.items():
        if requirement.kind == "property":
            property_index += 1
            entities[anchor_name] = {
                "id": f"https://datadistillery.wikibase.cloud/entity/P{property_index}",
                "kind": "property",
                "datatype": str(requirement.datatype),
            }
        else:
            item_index += 1
            entities[anchor_name] = {
                "id": f"https://datadistillery.wikibase.cloud/entity/Q{item_index}",
                "kind": "item",
            }

    return {
        "metadata": {
            "generated_at": "2026-04-04T00:00:00Z",
            "contract_digest": get_meta_wikibase_init_contract_digest(),
            "property_count": property_index,
            "item_count": item_index,
        },
        "entities": entities,
    }


def test_validate_semantic_anchor_document_accepts_contract_aligned_artifact() -> None:
    artifact = _valid_anchor_document()

    result = validate_semantic_anchor_document(artifact)

    assert result.valid is True
    assert result.required_anchor_count == len(artifact["entities"])
    assert result.matched_anchor_count == len(artifact["entities"])
    assert not any(notice.severity == "error" for notice in result.notices)


def test_validate_semantic_anchor_document_requires_entity_anchor() -> None:
    artifact = _valid_anchor_document()
    artifact["entities"].pop("_entity")

    result = validate_semantic_anchor_document(artifact)

    assert result.valid is False
    assert any(notice.code == "anchor_missing" for notice in result.notices)


def test_validate_semantic_anchor_document_rejects_wrong_kind() -> None:
    artifact = _valid_anchor_document()
    artifact["entities"]["_entity"][
        "id"
    ] = "https://datadistillery.wikibase.cloud/entity/P999"

    result = validate_semantic_anchor_document(artifact)

    assert result.valid is False
    assert any(notice.code == "anchor_kind_mismatch" for notice in result.notices)


def test_validate_semantic_anchor_document_rejects_property_datatype_mismatch() -> None:
    artifact = _valid_anchor_document()
    artifact["entities"]["_has_statement"]["datatype"] = "string"

    result = validate_semantic_anchor_document(artifact)

    assert result.valid is False
    assert any(notice.code == "anchor_datatype_mismatch" for notice in result.notices)


def test_validate_semantic_anchor_document_flags_stale_compare_source() -> None:
    artifact = _valid_anchor_document()
    current = _valid_anchor_document()
    current["entities"]["_statement_type"][
        "id"
    ] = "https://datadistillery.wikibase.cloud/entity/P12345"

    result = validate_semantic_anchor_document(
        artifact,
        current_anchor_document=current,
    )

    assert result.valid is False
    assert result.freshness_checked is True
    assert result.freshness_match is False
    assert any(notice.code == "artifact_stale" for notice in result.notices)
