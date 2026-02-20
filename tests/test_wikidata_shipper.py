"""Tests for Wikidata shipper."""

from unittest.mock import Mock

from gkc.shipper import WikidataShipper


class FakeAuth:
    """Minimal auth double for shipper tests."""

    def __init__(self):
        self.api_url = "https://www.wikidata.org/w/api.php"
        self.session = Mock()
        self._logged_in = False
        self.login_called = False

    def is_logged_in(self) -> bool:
        return self._logged_in

    def login(self) -> None:
        self._logged_in = True
        self.login_called = True

    def get_csrf_token(self) -> str:
        return "csrf_token"


def _basic_payload() -> dict:
    return {
        "labels": {"en": {"language": "en", "value": "Test"}},
        "descriptions": {"en": {"language": "en", "value": "Desc"}},
    }


def test_write_item_dry_run_does_not_post():
    """Dry run returns payload and skips network."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth)

    result = shipper.write_item(
        _basic_payload(),
        summary="Dry run",
        dry_run=True,
    )

    assert result.status == "dry_run"
    auth.session.post.assert_not_called()


def test_write_item_validate_only_blocks_missing_labels():
    """Validation-only blocks writes without labels."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth)

    result = shipper.write_item(
        {"descriptions": {"en": {"language": "en", "value": "Desc"}}},
        summary="Validate only",
        validate_only=True,
    )

    assert result.status == "blocked"
    assert any("labels" in warning for warning in result.warnings)
    auth.session.post.assert_not_called()


def test_write_item_submit_posts_request():
    """Submit sends a wbeditentity request."""
    auth = FakeAuth()
    shipper = WikidataShipper(auth=auth, dry_run_default=False)

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "entity": {"id": "Q123", "lastrevid": 42},
    }
    auth.session.post.return_value = response

    result = shipper.write_item(
        _basic_payload(),
        summary="Submit",
        dry_run=False,
        tags=["gkc"],
        bot=True,
    )

    assert auth.login_called
    assert result.status == "submitted"
    assert result.entity_id == "Q123"
    assert result.revision_id == 42

    auth.session.post.assert_called_once()
    call_args = auth.session.post.call_args
    sent_data = call_args[1]["data"]
    assert sent_data["action"] == "wbeditentity"
    assert sent_data["summary"] == "Submit"
    assert sent_data["tags"] == "gkc"
    assert sent_data["bot"] == "1"
    assert "data" in sent_data
