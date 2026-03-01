"""Tests for expanded Wikidata datatypes in profiles."""

from gkc.profiles.validation.models import StatementValue
from gkc.profiles.validation.wikidata_normalizer import _snak_to_value


class TestMonolingualtext:
    """Test monolingualtext datatype normalization."""

    def test_monolingualtext_normalization(self):
        """Monolingualtext snak should normalize to structured value."""
        snak = {
            "snaktype": "value",
            "datatype": "monolingualtext",
            "datavalue": {
                "type": "monolingualtext",
                "value": {"text": "Klamath Tribes", "language": "kla"},
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "monolingualtext"
        assert isinstance(result.value, dict)
        assert result.value["text"] == "Klamath Tribes"
        assert result.value["language"] == "kla"

    def test_monolingualtext_missing_language(self):
        """Monolingualtext without language should return None."""
        snak = {
            "snaktype": "value",
            "datatype": "monolingualtext",
            "datavalue": {
                "type": "monolingualtext",
                "value": {"text": "Example"},
            },
        }
        result = _snak_to_value(snak)
        assert result is None

    def test_monolingualtext_missing_text(self):
        """Monolingualtext without text should return None."""
        snak = {
            "snaktype": "value",
            "datatype": "monolingualtext",
            "datavalue": {
                "type": "monolingualtext",
                "value": {"language": "en"},
            },
        }
        result = _snak_to_value(snak)
        assert result is None


class TestGlobecoordinate:
    """Test globecoordinate datatype normalization and validation."""

    def test_globecoordinate_normalization(self):
        """Globecoordinate snak should normalize to structured value."""
        snak = {
            "snaktype": "value",
            "datatype": "globe-coordinate",
            "datavalue": {
                "type": "globecoordinate",
                "value": {
                    "latitude": 42.123456,
                    "longitude": -121.123456,
                    "precision": 0.000001,
                    "globe": "http://www.wikidata.org/entity/Q2",
                },
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "globecoordinate"
        assert isinstance(result.value, dict)
        assert result.value["latitude"] == 42.123456
        assert result.value["longitude"] == -121.123456
        assert result.value["precision"] == 0.000001
        assert result.value["globe"] == "http://www.wikidata.org/entity/Q2"

    def test_globecoordinate_minimal(self):
        """Globecoordinate with only lat/long should work."""
        snak = {
            "snaktype": "value",
            "datatype": "globe-coordinate",
            "datavalue": {
                "type": "globecoordinate",
                "value": {"latitude": 42.5, "longitude": -121.5},
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "globecoordinate"
        assert result.value["latitude"] == 42.5
        assert result.value["longitude"] == -121.5

    def test_globecoordinate_missing_latitude(self):
        """Globecoordinate without latitude should return None."""
        snak = {
            "snaktype": "value",
            "datatype": "globe-coordinate",
            "datavalue": {
                "type": "globecoordinate",
                "value": {"longitude": -121.5},
            },
        }
        result = _snak_to_value(snak)
        assert result is None

    def test_globecoordinate_invalid_latitude_range(self):
        """Valid latitude constraint should catch out-of-range values."""
        from gkc.profiles.generators.pydantic_generator import _validate_lat_long_range

        invalid_coord = {"latitude": 91.0, "longitude": 0.0}
        assert _validate_lat_long_range(invalid_coord) is False

        invalid_coord = {"latitude": -91.0, "longitude": 0.0}
        assert _validate_lat_long_range(invalid_coord) is False

    def test_globecoordinate_invalid_longitude_range(self):
        """Valid longitude constraint should catch out-of-range values."""
        from gkc.profiles.generators.pydantic_generator import _validate_lat_long_range

        invalid_coord = {"latitude": 0.0, "longitude": 181.0}
        assert _validate_lat_long_range(invalid_coord) is False

        invalid_coord = {"latitude": 0.0, "longitude": -181.0}
        assert _validate_lat_long_range(invalid_coord) is False

    def test_globecoordinate_valid_ranges(self):
        """Valid coordinate ranges should pass."""
        from gkc.profiles.generators.pydantic_generator import _validate_lat_long_range

        valid_coord = {"latitude": 42.123, "longitude": -121.456}
        assert _validate_lat_long_range(valid_coord) is True

        # Test boundaries
        assert _validate_lat_long_range({"latitude": 90.0, "longitude": 180.0}) is True
        assert (
            _validate_lat_long_range({"latitude": -90.0, "longitude": -180.0}) is True
        )


class TestCommonsMedia:
    """Test commonsMedia datatype normalization."""

    def test_commonsmedia_normalization(self):
        """CommonsMedia snak should normalize to string value."""
        snak = {
            "snaktype": "value",
            "datatype": "commonsMedia",
            "datavalue": {
                "type": "string",
                "value": "Flag of the Klamath Tribes.svg",
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "commonsMedia"
        assert result.value == "Flag of the Klamath Tribes.svg"


class TestExternalId:
    """Test external-id datatype normalization."""

    def test_externalid_normalization(self):
        """External-id snak should normalize to string value."""
        snak = {
            "snaktype": "value",
            "datatype": "external-id",
            "datavalue": {"type": "string", "value": "EXAMPLE-ID-123"},
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "external-id"
        assert result.value == "EXAMPLE-ID-123"


class TestQuantityWithUnits:
    """Test quantity datatype with units."""

    def test_quantity_with_unit(self):
        """Quantity snak with unit should normalize to structured value."""
        snak = {
            "snaktype": "value",
            "datatype": "quantity",
            "datavalue": {
                "type": "quantity",
                "value": {
                    "amount": "+100.5",
                    "unit": "http://www.wikidata.org/entity/Q11570",
                },
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "quantity"
        assert isinstance(result.value, dict)
        assert result.value["amount"] == 100.5
        assert result.value["unit"] == "http://www.wikidata.org/entity/Q11570"

    def test_quantity_without_unit(self):
        """Quantity snak without unit should normalize to numeric value."""
        snak = {
            "snaktype": "value",
            "datatype": "quantity",
            "datavalue": {
                "type": "quantity",
                "value": {"amount": "+12.5", "unit": "1"},
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "quantity"
        # Unitless quantities stored as simple numeric
        assert result.value == 12.5


class TestTimeEnhanced:
    """Test time datatype with precision and calendar."""

    def test_time_with_precision_and_calendar(self):
        """Time snak with precision and calendar normalizes to structured value."""
        snak = {
            "snaktype": "value",
            "datatype": "time",
            "datavalue": {
                "type": "time",
                "value": {
                    "time": "+1855-10-14T00:00:00Z",
                    "precision": 11,  # day precision
                    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                },
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "time"
        assert isinstance(result.value, dict)
        assert result.value["time"] == "+1855-10-14T00:00:00Z"
        assert result.value["precision"] == 11
        assert result.value["calendar"] == "http://www.wikidata.org/entity/Q1985727"

    def test_time_minimal(self):
        """Time snak with only time string should work."""
        snak = {
            "snaktype": "value",
            "datatype": "time",
            "datavalue": {
                "type": "time",
                "value": {"time": "+2020-01-01T00:00:00Z"},
            },
        }
        result = _snak_to_value(snak)
        assert result is not None
        assert result.value_type == "time"
        assert isinstance(result.value, dict)
        assert result.value["time"] == "+2020-01-01T00:00:00Z"


class TestIntegerOnlyWithComplexTypes:
    """Test integer_only constraint with complex value types."""

    def test_integer_only_with_simple_quantity(self):
        """Integer-only should work with simple numeric quantities."""
        from gkc.profiles.generators.pydantic_generator import _is_integer

        assert _is_integer(12) is True
        assert _is_integer(12.0) is True
        assert _is_integer(12.5) is False

    def test_integer_only_constraint_extracts_from_dict(self):
        """Integer-only constraint should extract amount from quantity dict."""

        # This simulates what happens in the validator
        stmt_value = StatementValue(
            value={"amount": 100.0, "unit": "http://www.wikidata.org/entity/Q11570"},
            value_type="quantity",
        )

        # Validator should extract the amount before checking
        value_to_check = stmt_value.value
        if isinstance(value_to_check, dict):
            value_to_check = value_to_check.get("amount", value_to_check)

        from gkc.profiles.generators.pydantic_generator import _is_integer

        assert _is_integer(value_to_check) is True
