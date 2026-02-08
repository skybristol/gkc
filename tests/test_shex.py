"""Tests for ShEx validation module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gkc.shex import ShExValidationError, ShExValidator


class TestShExValidatorInit:
    """Tests for ShExValidator initialization."""

    def test_init_with_qid_eid(self):
        """Test initialization with QID and EID."""
        validator = ShExValidator(qid="Q42", eid="E502")
        assert validator.qid == "Q42"
        assert validator.eid == "E502"
        assert validator._schema is None
        assert validator._rdf is None
        assert validator.results is None

    def test_init_with_text_sources(self):
        """Test initialization with text sources."""
        validator = ShExValidator(
            schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        assert validator.schema_text == "PREFIX wd: <>"
        assert validator.rdf_text == "@prefix wd: <> ."

    def test_init_with_file_sources(self):
        """Test initialization with file sources."""
        validator = ShExValidator(schema_file="schema.shex", rdf_file="data.ttl")
        assert validator.schema_file == "schema.shex"
        assert validator.rdf_file == "data.ttl"

    def test_repr(self):
        """Test string representation."""
        validator = ShExValidator(qid="Q42", eid="E502")
        repr_str = repr(validator)
        assert "ShExValidator" in repr_str
        assert "Q42" in repr_str
        assert "E502" in repr_str


class TestLoadSchema:
    """Tests for load_schema method."""

    def test_load_schema_from_text(self):
        """Test loading schema from text."""
        schema_text = "PREFIX wd: <http://www.wikidata.org/entity/>"
        validator = ShExValidator(schema_text=schema_text)
        validator.load_schema()
        assert validator._schema == schema_text

    def test_load_schema_from_file(self):
        """Test loading schema from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".shex") as f:
            f.write("PREFIX wd: <>")
            schema_file = f.name

        try:
            validator = ShExValidator(schema_file=schema_file)
            validator.load_schema()
            assert "PREFIX wd: <>" in validator._schema
        finally:
            Path(schema_file).unlink()

    def test_load_schema_file_not_found(self):
        """Test error when schema file not found."""
        validator = ShExValidator(schema_file="nonexistent.shex")
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_schema()
        assert "not found" in str(exc_info.value)

    @patch("gkc.shex.fetch_entity_schema")
    def test_load_schema_from_wikidata(self, mock_fetch):
        """Test loading schema from Wikidata."""
        mock_fetch.return_value = "PREFIX wd: <>"
        validator = ShExValidator(eid="E502")
        validator.load_schema()
        assert validator._schema == "PREFIX wd: <>"
        mock_fetch.assert_called_once_with("E502", None)

    @patch("gkc.shex.fetch_entity_schema")
    def test_load_schema_wikidata_fetch_error(self, mock_fetch):
        """Test error when fetching from Wikidata fails."""
        from gkc.wd import WikidataFetchError

        mock_fetch.side_effect = WikidataFetchError("Network error")
        validator = ShExValidator(eid="E502")
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_schema()
        assert "Failed to load schema" in str(exc_info.value)

    def test_load_schema_no_source(self):
        """Test error when no schema source provided."""
        validator = ShExValidator()
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_schema()
        assert "No schema source" in str(exc_info.value)

    def test_load_schema_returns_self(self):
        """Test that load_schema returns self for chaining."""
        validator = ShExValidator(schema_text="PREFIX wd: <>")
        result = validator.load_schema()
        assert result is validator


class TestLoadRdf:
    """Tests for load_rdf method."""

    def test_load_rdf_from_text(self):
        """Test loading RDF from text."""
        rdf_text = "@prefix wd: <http://www.wikidata.org/entity/> ."
        validator = ShExValidator(rdf_text=rdf_text)
        validator.load_rdf()
        assert validator._rdf == rdf_text

    def test_load_rdf_from_file(self):
        """Test loading RDF from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ttl") as f:
            f.write("@prefix wd: <> .")
            rdf_file = f.name

        try:
            validator = ShExValidator(rdf_file=rdf_file)
            validator.load_rdf()
            assert "@prefix wd: <>" in validator._rdf
        finally:
            Path(rdf_file).unlink()

    def test_load_rdf_file_not_found(self):
        """Test error when RDF file not found."""
        validator = ShExValidator(rdf_file="nonexistent.ttl")
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_rdf()
        assert "not found" in str(exc_info.value)

    @patch("gkc.shex.fetch_entity_rdf")
    def test_load_rdf_from_wikidata(self, mock_fetch):
        """Test loading RDF from Wikidata."""
        mock_fetch.return_value = "@prefix wd: <> ."
        validator = ShExValidator(qid="Q42")
        validator.load_rdf()
        assert validator._rdf == "@prefix wd: <> ."
        mock_fetch.assert_called_once_with("Q42", format="ttl", user_agent=None)

    @patch("gkc.shex.fetch_entity_rdf")
    def test_load_rdf_wikidata_fetch_error(self, mock_fetch):
        """Test error when fetching from Wikidata fails."""
        from gkc.wd import WikidataFetchError

        mock_fetch.side_effect = WikidataFetchError("Network error")
        validator = ShExValidator(qid="Q42")
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_rdf()
        assert "Failed to load RDF" in str(exc_info.value)

    def test_load_rdf_no_source(self):
        """Test error when no RDF source provided."""
        validator = ShExValidator()
        with pytest.raises(ShExValidationError) as exc_info:
            validator.load_rdf()
        assert "No RDF source" in str(exc_info.value)

    def test_load_rdf_returns_self(self):
        """Test that load_rdf returns self for chaining."""
        validator = ShExValidator(rdf_text="@prefix wd: <> .")
        result = validator.load_rdf()
        assert result is validator


class TestEvaluate:
    """Tests for evaluate method."""

    @patch("gkc.shex.ShExEvaluator")
    def test_evaluate_success(self, mock_evaluator_class):
        """Test successful evaluation."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = True
        mock_evaluator_class.return_value = mock_evaluator

        validator = ShExValidator(
            qid="Q42", schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        validator.load_schema()
        validator.load_rdf()
        validator.evaluate()

        assert validator.results is True
        mock_evaluator_class.assert_called_once()
        mock_evaluator.evaluate.assert_called_once()

    @patch("gkc.shex.ShExEvaluator")
    def test_evaluate_with_focus(self, mock_evaluator_class):
        """Test evaluation uses correct focus node."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = True
        mock_evaluator_class.return_value = mock_evaluator

        validator = ShExValidator(
            qid="Q42", schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        validator.load_schema()
        validator.load_rdf()
        validator.evaluate()

        call_kwargs = mock_evaluator_class.call_args[1]
        assert call_kwargs["focus"] == "http://www.wikidata.org/entity/Q42"

    def test_evaluate_without_schema(self):
        """Test error when schema not loaded."""
        validator = ShExValidator(rdf_text="@prefix wd: <> .")
        validator.load_rdf()
        with pytest.raises(ShExValidationError) as exc_info:
            validator.evaluate()
        assert "Schema not loaded" in str(exc_info.value)

    def test_evaluate_without_rdf(self):
        """Test error when RDF not loaded."""
        validator = ShExValidator(schema_text="PREFIX wd: <>")
        validator.load_schema()
        with pytest.raises(ShExValidationError) as exc_info:
            validator.evaluate()
        assert "RDF data not loaded" in str(exc_info.value)

    @patch("gkc.shex.ShExEvaluator")
    def test_evaluate_shex_error(self, mock_evaluator_class):
        """Test handling of ShEx evaluation errors."""
        mock_evaluator_class.side_effect = Exception("ShEx parse error")

        validator = ShExValidator(
            schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        validator.load_schema()
        validator.load_rdf()

        with pytest.raises(ShExValidationError) as exc_info:
            validator.evaluate()
        assert "evaluation failed" in str(exc_info.value)


class TestValidate:
    """Tests for validate convenience method."""

    @patch("gkc.shex.ShExEvaluator")
    @patch("gkc.shex.fetch_entity_rdf")
    @patch("gkc.shex.fetch_entity_schema")
    def test_validate_convenience_method(
        self, mock_fetch_schema, mock_fetch_rdf, mock_evaluator_class
    ):
        """Test validate convenience method."""
        mock_fetch_schema.return_value = "PREFIX wd: <>"
        mock_fetch_rdf.return_value = "@prefix wd: <> ."
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = True
        mock_evaluator_class.return_value = mock_evaluator

        validator = ShExValidator(qid="Q42", eid="E502")
        result = validator.validate()

        assert result is validator
        assert validator.results is True
        mock_fetch_schema.assert_called_once()
        mock_fetch_rdf.assert_called_once()


class TestIsValid:
    """Tests for is_valid method."""

    @patch("gkc.shex.ShExEvaluator")
    def test_is_valid_true(self, mock_evaluator_class):
        """Test is_valid returns True when validation passes."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = True
        mock_evaluator_class.return_value = mock_evaluator

        validator = ShExValidator(
            schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        validator.validate()

        assert validator.is_valid() is True

    @patch("gkc.shex.ShExEvaluator")
    def test_is_valid_false(self, mock_evaluator_class):
        """Test is_valid returns False when validation fails."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = False
        mock_evaluator_class.return_value = mock_evaluator

        validator = ShExValidator(
            schema_text="PREFIX wd: <>", rdf_text="@prefix wd: <> ."
        )
        validator.validate()

        assert validator.is_valid() is False

    def test_is_valid_without_validation(self):
        """Test error when is_valid called before validation."""
        validator = ShExValidator()
        with pytest.raises(ShExValidationError) as exc_info:
            validator.is_valid()
        assert "No validation results" in str(exc_info.value)
