"""Tests for shipper base classes and results."""

from gkc.shipper import Shipper, WriteResult


def test_write_result_to_dict_and_json():
    """Serialize write results to dict and JSON."""
    result = WriteResult(
        entity_id="Q1",
        revision_id=10,
        status="dry_run",
        warnings=["note"],
        api_response={"ok": True},
        request_payload={"labels": {}},
        metadata={"run_id": "test"},
    )

    as_dict = result.to_dict()
    assert as_dict["entity_id"] == "Q1"
    assert as_dict["revision_id"] == 10
    assert as_dict["status"] == "dry_run"
    assert as_dict["warnings"] == ["note"]
    assert as_dict["api_response"] == {"ok": True}
    assert as_dict["request_payload"] == {"labels": {}}
    assert as_dict["metadata"] == {"run_id": "test"}

    as_json = result.to_json()
    assert '"entity_id"' in as_json


def test_shipper_write_raises():
    """Ensure base shipper raises for unimplemented write."""
    shipper = Shipper()

    try:
        shipper.write({})
    except NotImplementedError as exc:
        assert "Shipper.write" in str(exc)
    else:
        raise AssertionError("Shipper.write should raise NotImplementedError")
