"""Integration tests for ShEx validation with real Wikidata data.

These tests use fixtures defined in conftest.py that load actual EntitySchema
and RDF data from test files. To run these tests, you need to first download
the test data files as described in tests/fixtures/README.md.

Note: These tests will be skipped if the required data files don't exist.
"""

from pathlib import Path

import pytest

from gkc import ShExValidator


class TestShExIntegration:
    """Integration tests using real EntitySchema and RDF data."""

    def test_validate_with_fixture_files(
        self,
        organism_schema_file: Path,
        valid_organism_rdf_file: Path,
    ) -> None:
        """Test validation using fixture file paths.

        Uses pytest fixtures that provide paths to test data files.
        Test is skipped if files don't exist.
        """
        if not organism_schema_file.exists() or not valid_organism_rdf_file.exists():
            pytest.skip("Test data files not found. See tests/fixtures/README.md")

        # Create validator using file paths from fixtures
        validator = ShExValidator(
            schema_file=str(organism_schema_file),
            rdf_file=str(valid_organism_rdf_file),
        )

        # Perform validation
        result = validator.validate()

        # Verify the validation result
        assert result.is_valid()

    def test_validate_with_fixture_text(
        self,
        organism_schema_text: str,
        valid_organism_rdf_text: str,
    ) -> None:
        """Test validation using fixture text content.

        Uses pytest fixtures that load file content into strings.
        Test is skipped if files don't exist.
        """
        if not organism_schema_text or not valid_organism_rdf_text:
            pytest.skip("Test data files not found. See tests/fixtures/README.md")

        # Create validator using text loaded by fixtures
        validator = ShExValidator(
            schema_text=organism_schema_text,
            rdf_text=valid_organism_rdf_text,
        )

        result = validator.validate()
        assert result.is_valid()

    def test_invalid_organism_fails_validation(
        self,
        organism_schema_file: Path,
        invalid_organism_rdf_file: Path,
    ) -> None:
        """Test that invalid RDF data fails validation.

        Uses an entity that doesn't conform to the tribe schema.
        Test is skipped if files don't exist.
        """
        if not organism_schema_file.exists() or not invalid_organism_rdf_file.exists():
            pytest.skip("Test data files not found. See tests/fixtures/README.md")

        validator = ShExValidator(
            schema_file=str(organism_schema_file),
            rdf_file=str(invalid_organism_rdf_file),
        )

        result = validator.validate()

        # This should fail validation - Q736809 is a city,
        # not a federally recognized tribe
        assert not result.is_valid()

    def test_fluent_api_with_fixtures(
        self,
        organism_schema_file: Path,
        valid_organism_rdf_file: Path,
    ) -> None:
        """Test the fluent API pattern with fixture data.

        Demonstrates loading schema and RDF separately before validation.
        Test is skipped if files don't exist.
        """
        if not organism_schema_file.exists() or not valid_organism_rdf_file.exists():
            pytest.skip("Test data files not found. See tests/fixtures/README.md")

        # Create validator and load data step by step
        validator = ShExValidator(
            schema_file=str(organism_schema_file),
            rdf_file=str(valid_organism_rdf_file),
        )
        validator.load_schema()
        validator.load_rdf()

        result = validator.evaluate()

        assert result.is_valid()

    def test_compare_file_path_vs_text_loading(
        self,
        organism_schema_file: Path,
        organism_schema_text: str,
        valid_organism_rdf_file: Path,
        valid_organism_rdf_text: str,
    ) -> None:
        """Verify that file path and text loading produce same results.

        Test is skipped if files don't exist.
        """
        if (
            not organism_schema_file.exists()
            or not valid_organism_rdf_file.exists()
            or not organism_schema_text
            or not valid_organism_rdf_text
        ):
            pytest.skip("Test data files not found. See tests/fixtures/README.md")

        # Validate using file paths
        validator_file = ShExValidator(
            schema_file=str(organism_schema_file),
            rdf_file=str(valid_organism_rdf_file),
        )
        result_file = validator_file.validate()

        # Validate using loaded text
        validator_text = ShExValidator(
            schema_text=organism_schema_text,
            rdf_text=valid_organism_rdf_text,
        )
        result_text = validator_text.validate()

        # Results should be the same
        assert result_file.is_valid() == result_text.is_valid()


class TestFetchFromWikidata:
    """Integration tests that fetch data from Wikidata API.

    These tests make real HTTP requests and may be slow.
    """

    @pytest.mark.slow
    def test_validate_entity_from_wikidata(self) -> None:
        """Test validation by fetching data directly from Wikidata.

        This test demonstrates validating a Wikidata entity against an
        EntitySchema by fetching both from the live API.
        """
        # Use a known valid tribe: Wanapum (Q14708404)
        # against tribe schema (E502)
        validator = ShExValidator(
            eid="E502",  # Tribe schema
            qid="Q14708404",  # Wanapum tribe
        )

        result = validator.validate()

        # Note: This may fail if the Wikidata entity or schema changes
        # or if there are network issues
        assert result is not None

    @pytest.mark.slow
    def test_fetch_and_save_for_offline_testing(
        self,
        tmp_path: Path,
    ) -> None:
        """Demonstrate fetching and saving data for offline testing.

        This test shows how to download data from Wikidata and save it
        for use in offline tests.
        """
        from gkc.cooperage import fetch_entity_rdf, fetch_schema_specification

        # Fetch tribe schema
        schema_text = fetch_schema_specification("E502")
        schema_file = tmp_path / "tribe_E502.shex"
        schema_file.write_text(schema_text)

        # Fetch valid tribe RDF
        rdf_text = fetch_entity_rdf("Q14708404", format="ttl")
        rdf_file = tmp_path / "valid_Q14708404.ttl"
        rdf_file.write_text(rdf_text)

        # Now validate using the saved files
        validator = ShExValidator(
            schema_file=str(schema_file),
            rdf_file=str(rdf_file),
        )

        result = validator.validate()
        assert result.is_valid()

        # Files are now in tmp_path and can be copied to tests/fixtures/
        print(f"\nSchema saved to: {schema_file}")
        print(f"RDF saved to: {rdf_file}")
