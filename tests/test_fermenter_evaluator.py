import hashlib
import json
from pathlib import Path

from gkc.fermenter import (
    ConformanceOutcome,
    EntityEvaluation,
    evaluate_entity,
    evaluate_statement_claim,
    evaluate_statement_instance,
    validate_packet_from_file,
    validate_packet_inline,
)


def _claim(value: object) -> dict:
    return {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "value": value,
            },
        }
    }


def _statement(
    *,
    statement_id: str,
    data_type: str,
    property_id: str,
    max_count: int = 1,
    value_list_id: str | None = None,
) -> dict:
    value_block: dict[str, object] = {"type": data_type}
    if value_list_id:
        value_block["value_list_id"] = value_list_id

    return {
        "id": statement_id,
        "max_count": max_count,
        "value": value_block,
        "io_map": [{"to": f"http://www.wikidata.org/entity/{property_id}"}],
    }


def _canonical_digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _packet_template() -> dict:
    metadata = {
        "primary_profile": {
            "name_identifier": "tribal_government_us",
            "id": "https://datadistillery.wikibase.cloud/entity/Q4",
        },
        "profiles": [],
        "graph": {"nodes": [], "edges": []},
        "mint": {
            "minted_at": "2026-03-25T00:00:00Z",
            "generator": "tests",
            "gkc_version": "test",
        },
    }
    metadata["integrity"] = {
        "metadata_canonicalization": "json-sort-keys-v1",
        "metadata_digest_algorithm": "sha256",
        "metadata_digest": _canonical_digest(metadata),
    }
    return {
        "packet_id": "pkt-test",
        "operation_mode": "single",
        "metadata": metadata,
        "data": {"entities": []},
    }


def test_evaluate_statement_claim_conformant():
    statement = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q19",
        data_type="wikibase-item",
        property_id="P31",
    )
    claim = _claim({"entity-type": "item", "numeric-id": 5, "id": "Q5"})

    evaluation = evaluate_statement_claim(statement, [claim], entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.CONFORMANT
    assert evaluation.normalized_value["id"] == "Q5"
    assert not evaluation.notices


def test_evaluate_statement_claim_missing_required():
    statement = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q19",
        data_type="wikibase-item",
        property_id="P31",
        max_count=1,
    )

    evaluation = evaluate_statement_claim(statement, [], entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.MISSING
    assert any(notice.code == "statement_missing" for notice in evaluation.notices)


def test_evaluate_statement_claim_non_conformant_mappable_datatype():
    statement = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q29",
        data_type="url",
        property_id="P856",
    )
    claim = _claim("not-a-url")

    evaluation = evaluate_statement_claim(statement, [claim], entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    assert any(notice.code == "datatype_mismatch" for notice in evaluation.notices)


def test_evaluate_statement_claim_non_conformant_mappable_value_list(tmp_path: Path):
    cache_file = tmp_path / "cache" / "queries" / "Q28.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item": "http://www.wikidata.org/entity/Q5",
                        "itemLabel": "human",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    statement = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q16",
        data_type="wikibase-item",
        property_id="P31",
        value_list_id="Q28",
    )
    claim = _claim({"entity-type": "item", "numeric-id": 1, "id": "Q1"})

    evaluation = evaluate_statement_claim(
        statement,
        [claim],
        entity_ref="Q195562",
        value_list_root=tmp_path,
    )

    assert evaluation.outcome == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    assert any(notice.code == "value_list_miss" for notice in evaluation.notices)


def test_evaluate_statement_claim_conformant_with_single_item_inline_value_list():
    statement = {
        "id": "https://datadistillery.wikibase.cloud/entity/Q16",
        "max_count": 1,
        "value": {
            "type": "wikibase-item",
            "value_list": [{"item": "Q5", "itemLabel": "human"}],
        },
        "io_map": [{"to": "http://www.wikidata.org/entity/P31"}],
    }
    claim = _claim({"entity-type": "item", "numeric-id": 5, "id": "Q5"})

    evaluation = evaluate_statement_claim(statement, [claim], entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.CONFORMANT
    assert not any(
        notice.code == "fixed_value_violation" for notice in evaluation.notices
    )


def test_evaluate_statement_instance_reference_group_conformant_with_one_present():
    statement = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
        "name_identifier": "official_website",
        "value": {"type": "url"},
        "io_map": [{"to": "http://www.wikidata.org/entity/P856"}],
        "references": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q29",
                "name_identifier": "reference_url",
                "value": {"type": "url"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P854"}],
            },
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q44",
                "name_identifier": "stated_in",
                "value": {"type": "wikibase-item"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P248"}],
            },
        ],
    }
    claim = {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"value": "https://example.org"},
        },
        "references": [
            {
                "snaks": {
                    "P854": [
                        {
                            "snaktype": "value",
                            "datavalue": {"value": "https://example.org/source"},
                        }
                    ]
                }
            }
        ],
    }

    evaluation = evaluate_statement_instance(statement, claim, entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.CONFORMANT
    assert len(evaluation.reference_evaluations) == 2
    reference_by_ref = {
        child.statement_ref: child for child in evaluation.reference_evaluations
    }
    assert (
        reference_by_ref["https://datadistillery.wikibase.cloud/entity/Q29"].outcome
        == ConformanceOutcome.CONFORMANT
    )
    assert (
        reference_by_ref["https://datadistillery.wikibase.cloud/entity/Q44"].outcome
        == ConformanceOutcome.MISSING
    )


def test_evaluate_statement_instance_reference_group_missing_when_none_present():
    statement = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
        "name_identifier": "official_website",
        "value": {"type": "url"},
        "io_map": [{"to": "http://www.wikidata.org/entity/P856"}],
        "references": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q29",
                "name_identifier": "reference_url",
                "value": {"type": "url"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P854"}],
            },
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q44",
                "name_identifier": "stated_in",
                "value": {"type": "wikibase-item"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P248"}],
            },
        ],
    }
    claim = {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"value": "https://example.org"},
        },
        "references": [],
    }

    evaluation = evaluate_statement_instance(statement, claim, entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    assert any(
        notice.code == "reference_group_missing" for notice in evaluation.notices
    )
    assert all(
        child.outcome == ConformanceOutcome.MISSING
        for child in evaluation.reference_evaluations
    )


def test_evaluate_statement_instance_reference_group_allows_valid_or_invalid_mix():
    statement = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
        "name_identifier": "official_website",
        "value": {"type": "url"},
        "io_map": [{"to": "http://www.wikidata.org/entity/P856"}],
        "references": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q29",
                "name_identifier": "reference_url",
                "value": {"type": "url"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P854"}],
            },
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q44",
                "name_identifier": "stated_in",
                "value": {"type": "wikibase-item"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P248"}],
            },
        ],
    }
    claim = {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"value": "https://example.org"},
        },
        "references": [
            {
                "snaks": {
                    "P854": [
                        {
                            "snaktype": "value",
                            "datavalue": {"value": "https://example.org/source"},
                        }
                    ],
                    "P248": [
                        {
                            "snaktype": "value",
                            "datavalue": {"value": "not-a-qid"},
                        }
                    ],
                }
            }
        ],
    }

    evaluation = evaluate_statement_instance(statement, claim, entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.CONFORMANT
    reference_by_ref = {
        child.statement_ref: child for child in evaluation.reference_evaluations
    }
    assert (
        reference_by_ref["https://datadistillery.wikibase.cloud/entity/Q29"].outcome
        == ConformanceOutcome.CONFORMANT
    )
    assert (
        reference_by_ref["https://datadistillery.wikibase.cloud/entity/Q44"].outcome
        == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    )


def test_evaluate_statement_instance_qualifier_validation_fails_parent_when_invalid():
    statement = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
        "name_identifier": "official_website",
        "value": {"type": "url"},
        "io_map": [{"to": "http://www.wikidata.org/entity/P856"}],
        "qualifiers": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q27",
                "name_identifier": "language_of_work_or_name",
                "value": {"type": "wikibase-item"},
                "io_map": [{"to": "http://www.wikidata.org/entity/P407"}],
            }
        ],
    }
    claim = {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"value": "https://example.org"},
        },
        "qualifiers": {
            "P407": [
                {
                    "snaktype": "value",
                    "datavalue": {"value": "not-a-qid"},
                }
            ]
        },
    }

    evaluation = evaluate_statement_instance(statement, claim, entity_ref="Q195562")

    assert evaluation.outcome == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    assert len(evaluation.qualifier_evaluations) == 1
    assert (
        evaluation.qualifier_evaluations[0].outcome
        == ConformanceOutcome.NON_CONFORMANT_MAPPABLE
    )


def test_evaluate_entity_classifies_all_buckets():
    s_instance_of = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q16",
        data_type="wikibase-item",
        property_id="P31",
    )
    s_country = _statement(
        statement_id="https://datadistillery.wikibase.cloud/entity/Q40",
        data_type="wikibase-item",
        property_id="P17",
    )

    wikidata_item = {
        "id": "Q195562",
        "claims": {
            "P31": [_claim({"entity-type": "item", "numeric-id": 5, "id": "Q5"})],
            "P999": [_claim({"entity-type": "item", "numeric-id": 2, "id": "Q2"})],
        },
    }

    evaluation: EntityEvaluation = evaluate_entity(
        [s_instance_of, s_country],
        wikidata_item,
        io_map_index={"P31": s_instance_of, "P17": s_country},
        entity_ref="Q195562",
    )

    assert len(evaluation.conformant) == 1
    assert len(evaluation.missing) == 1
    assert len(evaluation.to_be_defined) == 1
    assert evaluation.is_conformant is False


def test_validate_packet_inline_integrity_passes():
    packet = _packet_template()

    passed, notices = validate_packet_inline(packet)

    assert passed is True
    assert any(notice.code == "packet_integrity_pass" for notice in notices)


def test_validate_packet_inline_integrity_mismatch_fails():
    packet = _packet_template()
    packet["metadata"]["mint"]["generator"] = "tampered"

    passed, notices = validate_packet_inline(packet)

    assert passed is False
    assert notices[0].code == "metadata_digest_mismatch"


def test_validate_packet_file_and_inline_parity(tmp_path: Path):
    packet = _packet_template()
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    inline_result = validate_packet_inline(packet)
    file_result = validate_packet_from_file(packet_path)

    assert inline_result[0] is file_result[0]
    assert [notice.code for notice in inline_result[1]] == [
        notice.code for notice in file_result[1]
    ]
