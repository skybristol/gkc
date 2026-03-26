import re

from gkc.fermenter import (
    ValidationPolicy,
    ValidationPolicyConfig,
    validate_by_datatype,
    validate_commons_media,
    validate_globe_coordinate,
    validate_time,
    validate_url,
    validate_wikibase_item,
    validate_with_pattern,
)
from gkc.mash import CommonsFileInfoResult, URLFetchResult


def test_validate_url_coerces_www_prefix():
    result = validate_url("www.wikidata.org")

    assert result.valid is True
    assert result.value == "https://www.wikidata.org"
    assert any("Added https://" in warning for warning in result.warnings)
    assert result.uncertainty > 0


def test_validate_url_coerces_bare_domain_with_path():
    result = validate_url("example.org/resource")

    assert result.valid is True
    assert result.value == "https://example.org/resource"


def test_validate_url_heartbeat_online_success(monkeypatch):
    policy = ValidationPolicy.HEARTBEAT

    def fake_fetch(url: str, **kwargs):
        assert url == "https://www.wikidata.org"
        assert kwargs.get("mode") == "head"
        return URLFetchResult(
            url=url,
            ok=True,
            status_code=200,
            final_url=url,
            content_type="text/html",
        )

    monkeypatch.setattr("gkc.fermenter.fetch_url_resource", fake_fetch)

    result = validate_url("https://www.wikidata.org", validation_policy=policy)

    assert result.valid is True
    assert not result.errors


def test_validate_url_actionable_online_failure(monkeypatch):
    policy = ValidationPolicy.ACTIONABLE

    def fake_fetch(url: str, **kwargs):
        assert kwargs.get("mode") == "get"
        return URLFetchResult(
            url=url,
            ok=False,
            status_code=503,
            error="HTTP 503",
        )

    monkeypatch.setattr("gkc.fermenter.fetch_url_resource", fake_fetch)

    result = validate_url("https://www.wikidata.org", validation_policy=policy)

    assert result.valid is False
    assert any("Online URL validation failed" in error for error in result.errors)
    assert result.uncertainty == 1.0


def test_validate_wikibase_item_coerces_uri_and_lowercase_qid():
    uri_result = validate_wikibase_item("https://www.wikidata.org/entity/Q42")
    lower_result = validate_wikibase_item("q42")

    assert uri_result.valid is True
    assert uri_result.value["id"] == "Q42"
    assert any("Coerced item URI" in warning for warning in uri_result.warnings)

    assert lower_result.valid is True
    assert lower_result.value["id"] == "Q42"
    assert any("Normalized lowercase" in warning for warning in lower_result.warnings)


def test_validate_wikibase_item_online_with_custom_instance(monkeypatch):
    class FakeClient:
        def __init__(self, api_url: str, timeout: int):
            self.api_url = api_url
            self.timeout = timeout

        def get_entity(self, entity_id: str):
            assert self.api_url == "https://example.wikibase.org/w/api.php"
            assert entity_id == "Q42"
            return {"id": "Q42"}

    monkeypatch.setattr("gkc.fermenter.WikibaseApiClient", FakeClient)

    policy_config = ValidationPolicyConfig(
        wikibase_api_url="https://example.wikibase.org/w/api.php",
    )
    result = validate_wikibase_item(
        "Q42",
        validation_policy=ValidationPolicy.HEARTBEAT,
        policy_config=policy_config,
    )

    assert result.valid is True
    assert result.value["wikibase-api-url"] == "https://example.wikibase.org/w/api.php"


def test_validate_by_datatype_passes_validation_policy_for_url(monkeypatch):
    policy = ValidationPolicy.HEARTBEAT

    def fake_fetch(url: str, **kwargs):
        return URLFetchResult(url=url, ok=True, status_code=200)

    monkeypatch.setattr("gkc.fermenter.fetch_url_resource", fake_fetch)

    result = validate_by_datatype(
        "url",
        "https://www.wikidata.org",
        validation_policy=policy,
    )

    assert result.valid is True


def test_validate_with_pattern_matches_string():
    result = validate_with_pattern("AB-1234", r"^[A-Z]{2}-\d{4}$")

    assert result.valid is True
    assert result.value == "AB-1234"


def test_validate_with_pattern_coerces_before_matching():
    result = validate_with_pattern(2024, r"^2024$")

    assert result.valid is True
    assert result.value == "2024"
    assert any("Coerced int to string" in warning for warning in result.warnings)


def test_validate_with_pattern_rejects_non_matching_value():
    result = validate_with_pattern("invalid", r"^[A-Z]{2}-\d{4}$")

    assert result.valid is False
    assert any("does not match required pattern" in error for error in result.errors)


def test_validate_with_pattern_supports_regex_flags():
    result = validate_with_pattern("cherokee nation", r"CHEROKEE", flags=re.IGNORECASE)

    assert result.valid is True


def test_validate_with_pattern_rejects_invalid_pattern():
    result = validate_with_pattern("Cherokee", r"([A-Z]")

    assert result.valid is False
    assert any("Invalid regex pattern" in error for error in result.errors)


# ============================================================================
# commonsMedia validation policy tests
# ============================================================================


def test_validate_commons_media_structure_coerces_missing_prefix():
    result = validate_commons_media("Example distillery.jpg")

    assert result.valid is True
    assert result.value == "File:Example distillery.jpg"
    assert not result.errors


def test_validate_commons_media_structure_preserves_file_prefix():
    result = validate_commons_media("File:Example distillery.jpg")

    assert result.valid is True
    assert result.value == "File:Example distillery.jpg"
    assert not result.errors


def test_validate_commons_media_structure_normalizes_lowercase_prefix():
    result = validate_commons_media("file:Example.jpg")

    assert result.valid is True
    assert result.value == "File:Example.jpg"
    assert any("Normalized lowercase" in w for w in result.warnings)


def test_validate_commons_media_structure_rejects_empty():
    result = validate_commons_media("")

    assert result.valid is False
    assert any("cannot be empty" in e for e in result.errors)


def test_validate_commons_media_heartbeat_file_exists(monkeypatch):
    def fake_fetch_info(client, filename, *, mode="heartbeat"):
        assert mode == "heartbeat"
        assert filename == "File:Example.jpg"
        return CommonsFileInfoResult(
            filename=filename,
            ok=True,
            exists=True,
            page_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
        )

    monkeypatch.setattr("gkc.fermenter.fetch_commons_file_info", fake_fetch_info)

    result = validate_commons_media(
        "Example.jpg",
        validation_policy=ValidationPolicy.HEARTBEAT,
    )

    assert result.valid is True
    assert result.value == "File:Example.jpg"
    assert not result.errors


def test_validate_commons_media_heartbeat_file_missing(monkeypatch):
    def fake_fetch_info(client, filename, *, mode="heartbeat"):
        return CommonsFileInfoResult(
            filename=filename,
            ok=True,
            exists=False,
            error=f"File not found on Commons: {filename}",
        )

    monkeypatch.setattr("gkc.fermenter.fetch_commons_file_info", fake_fetch_info)

    result = validate_commons_media(
        "File:DoesNotExist.jpg",
        validation_policy=ValidationPolicy.HEARTBEAT,
    )

    assert result.valid is False
    assert any("not found" in e for e in result.errors)
    assert result.uncertainty == 1.0


def test_validate_commons_media_actionable_returns_metadata(monkeypatch):
    def fake_fetch_info(client, filename, *, mode="heartbeat"):
        assert mode == "actionable"
        return CommonsFileInfoResult(
            filename=filename,
            ok=True,
            exists=True,
            page_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
            resource_url="https://upload.wikimedia.org/wikipedia/commons/a/a9/Example.jpg",
            mime_type="image/jpeg",
            size=102400,
        )

    monkeypatch.setattr("gkc.fermenter.fetch_commons_file_info", fake_fetch_info)

    result = validate_commons_media(
        "File:Example.jpg",
        validation_policy=ValidationPolicy.ACTIONABLE,
    )

    assert result.valid is True
    assert any("MIME type: image/jpeg" in w for w in result.warnings)
    assert any("resource URL" in w for w in result.warnings)
    assert any("102400 bytes" in w for w in result.warnings)


def test_validate_commons_media_actionable_uses_custom_commons_url(monkeypatch):
    captured = {}

    def fake_client_init(api_url, timeout):
        captured["api_url"] = api_url

    class FakeClient:
        def __init__(self, api_url, timeout):
            captured["api_url"] = api_url

    def fake_fetch_info(client, filename, *, mode="heartbeat"):
        return CommonsFileInfoResult(filename=filename, ok=True, exists=True)

    monkeypatch.setattr("gkc.fermenter.WikibaseApiClient", FakeClient)
    monkeypatch.setattr("gkc.fermenter.fetch_commons_file_info", fake_fetch_info)

    policy_config = ValidationPolicyConfig(
        commons_api_url="https://test.commons.example.org/w/api.php",
    )
    validate_commons_media(
        "File:Example.jpg",
        validation_policy=ValidationPolicy.HEARTBEAT,
        policy_config=policy_config,
    )

    assert captured["api_url"] == "https://test.commons.example.org/w/api.php"


def test_validate_by_datatype_passes_validation_policy_for_commons_media(monkeypatch):
    def fake_fetch_info(client, filename, *, mode="heartbeat"):
        return CommonsFileInfoResult(filename=filename, ok=True, exists=True)

    monkeypatch.setattr("gkc.fermenter.fetch_commons_file_info", fake_fetch_info)

    result = validate_by_datatype(
        "commonsMedia",
        "File:Example.jpg",
        validation_policy=ValidationPolicy.HEARTBEAT,
    )

    assert result.valid is True


# ============================================================================
# time and globe-coordinate coercion tests
# ============================================================================


def test_validate_time_accepts_year_string_and_fills_wikibase_fields():
    result = validate_time("2024")

    assert result.valid is True
    assert result.value["time"] == "+2024-01-01T00:00:00Z"
    assert result.value["precision"] == 9
    assert result.value["timezone"] == 0
    assert result.value["before"] == 0
    assert result.value["after"] == 0
    assert result.value["calendarmodel"] == "http://www.wikidata.org/entity/Q1985727"


def test_validate_time_accepts_partial_iso_date_and_derives_precision():
    result = validate_time("2024-03")

    assert result.valid is True
    assert result.value["time"] == "+2024-03-01T00:00:00Z"
    assert result.value["precision"] == 10


def test_validate_time_accepts_component_dict():
    result = validate_time({"year": 2024, "month": 5, "day": 6})

    assert result.valid is True
    assert result.value["time"] == "+2024-05-06T00:00:00Z"
    assert result.value["precision"] == 11
    assert any("component fields" in warning for warning in result.warnings)


def test_validate_time_accepts_minimal_wikibase_dict_and_fills_defaults():
    result = validate_time({"time": "+2024-05-06T00:00:00Z"})

    assert result.valid is True
    assert result.value["timezone"] == 0
    assert result.value["before"] == 0
    assert result.value["after"] == 0
    assert result.value["calendarmodel"] == "http://www.wikidata.org/entity/Q1985727"
    assert any(
        "Filled missing Wikibase time fields" in warning for warning in result.warnings
    )


def test_validate_globe_coordinate_accepts_string_pair_and_derives_precision():
    result = validate_globe_coordinate("42.1234,-121.5000")

    assert result.valid is True
    assert result.value["latitude"] == 42.1234
    assert result.value["longitude"] == -121.5
    assert result.value["globe"] == "http://www.wikidata.org/entity/Q2"
    assert result.value["precision"] > 0
    assert any("Derived coordinate precision" in warning for warning in result.warnings)


def test_validate_globe_coordinate_accepts_shorthand_dict_keys():
    result = validate_globe_coordinate({"lat": "42.5", "lng": "-121.25"})

    assert result.valid is True
    assert result.value["latitude"] == 42.5
    assert result.value["longitude"] == -121.25
    assert any("shorthand coordinate keys" in warning for warning in result.warnings)


def test_validate_globe_coordinate_accepts_dms_components():
    result = validate_globe_coordinate(
        {"latitude": "42 30 0 N", "longitude": "121 30 0 W"}
    )

    assert result.valid is True
    assert result.value["latitude"] == 42.5
    assert result.value["longitude"] == -121.5


def test_validate_globe_coordinate_rejects_out_of_range_after_coercion():
    result = validate_globe_coordinate("91.0,10.0")

    assert result.valid is False
    assert any("latitude must be between -90 and 90" in err for err in result.errors)
