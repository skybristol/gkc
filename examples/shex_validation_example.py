"""Example script demonstrating ShEx validation with local files.

This example shows how to:
1. Validate Wikidata entities against EntitySchemas using local files
2. Use both file paths and loaded text
3. Handle validation results
4. Work with the fluent API

Before running this script, download the required test data files:
    cd examples/data
    curl https://www.wikidata.org/wiki/Special:EntitySchemaText/E502 > tribe_E502.shex
    curl https://www.wikidata.org/wiki/Special:EntityData/Q14708404.ttl > \
        valid_Q14708404.ttl

Then run:
    python examples/shex_validation_example.py
"""

from pathlib import Path

from gkc import ShExValidator


def example_basic_validation():
    """Example 1: Basic validation with local files."""
    print("\n=== Example 1: Basic Validation ===")

    data_dir = Path(__file__).parent / "data"
    schema_file = data_dir / "tribe_E502.shex"
    rdf_file = data_dir / "valid_Q14708404.ttl"

    if not schema_file.exists() or not rdf_file.exists():
        print(
            "⚠️  Data files not found. "
            "See script docstring for download instructions."
        )
        return

    # Create validator with file paths
    validator = ShExValidator(
        schema_file=str(schema_file),
        rdf_file=str(rdf_file),
    )

    # Perform validation
    result = validator.validate()

    # Check results
    if result.is_valid():
        print("✓ Validation passed!")
        print(f"  Conforms: {result.conforms}")
    else:
        print("✗ Validation failed!")
        print(f"  Conforms: {result.conforms}")
        print(f"  Reason: {result.reason}")


def example_fluent_api():
    """Example 2: Using the fluent API to load data step-by-step."""
    print("\n=== Example 2: Fluent API ===")

    data_dir = Path(__file__).parent / "data"
    schema_file = data_dir / "tribe_E502.shex"
    rdf_file = data_dir / "valid_Q14708404.ttl"

    if not schema_file.exists() or not rdf_file.exists():
        print("⚠️  Data files not found.")
        return

    # Create empty validator
    validator = ShExValidator()

    # Load schema
    print("Loading schema...")
    validator.load_schema(file_path=str(schema_file))

    # Load RDF data
    print("Loading RDF data...")
    validator.load_rdf(file_path=str(rdf_file))

    # Evaluate
    print("Evaluating...")
    result = validator.evaluate()

    if result.is_valid():
        print("✓ Validation passed!")
    else:
        print("✗ Validation failed!")


def example_text_loading():
    """Example 3: Loading data as text instead of from files."""
    print("\n=== Example 3: Text Loading ===")

    data_dir = Path(__file__).parent / "data"
    schema_file = data_dir / "tribe_E502.shex"
    rdf_file = data_dir / "valid_Q14708404.ttl"

    if not schema_file.exists() or not rdf_file.exists():
        print("⚠️  Data files not found.")
        return

    # Read files into strings
    schema_text = schema_file.read_text()
    rdf_text = rdf_file.read_text()

    # Create validator with text
    validator = ShExValidator(
        schema_text=schema_text,
        rdf_text=rdf_text,
    )

    result = validator.validate()

    if result.is_valid():
        print("✓ Validation passed using text input!")
    else:
        print("✗ Validation failed!")


def example_compare_valid_vs_invalid():
    """Example 4: Compare validation results for valid and invalid data."""
    print("\n=== Example 4: Valid vs Invalid ===")

    data_dir = Path(__file__).parent / "data"
    schema_file = data_dir / "tribe_E502.shex"
    valid_file = data_dir / "valid_Q14708404.ttl"
    invalid_file = data_dir / "invalid_Q736809.ttl"

    if not schema_file.exists() or not valid_file.exists():
        print("⚠️  Data files not found.")
        return

    # Validate valid tribe
    print("Validating valid tribe (Wanapum)...")
    validator_valid = ShExValidator(
        schema_file=str(schema_file),
        rdf_file=str(valid_file),
    )
    result_valid = validator_valid.validate()

    print(f"  Result: {'✓ PASS' if result_valid.is_valid() else '✗ FAIL'}")

    if invalid_file.exists():
        # Validate invalid entity
        print("\nValidating invalid entity...")
        validator_invalid = ShExValidator(
            schema_file=str(schema_file),
            rdf_file=str(invalid_file),
        )
        result_invalid = validator_invalid.validate()

        print(f"  Result: {'✓ PASS' if result_invalid.is_valid() else '✗ FAIL'}")
        if not result_invalid.is_valid():
            print(f"  Reason: {result_invalid.reason}")
    else:
        print("\n⚠️  Invalid entity file not found.")


def example_fetch_from_wikidata():
    """Example 5: Fetch data directly from Wikidata API."""
    print("\n=== Example 5: Fetch from Wikidata ===")
    print("Fetching EntitySchema E502 and entity Q14708404 from Wikidata...")

    try:
        # This will make HTTP requests to Wikidata
        validator = ShExValidator(
            eid="E502",  # Tribe schema
            qid="Q14708404",  # Wanapum tribe
        )

        result = validator.validate()

        if result.is_valid():
            print("✓ Validation passed (fetched from Wikidata)!")
        else:
            print("✗ Validation failed!")
            print(f"  Reason: {result.reason}")

    except Exception as e:
        print(f"✗ Error fetching from Wikidata: {e}")
        print("  (This may be due to network issues or API changes)")


def main():
    """Run all examples."""
    print("ShEx Validation Examples")
    print("=" * 50)

    example_basic_validation()
    example_fluent_api()
    example_text_loading()
    example_compare_valid_vs_invalid()

    # Optional: fetch from Wikidata (requires network)
    try_fetch = input("\nTry fetching from Wikidata API? (requires network) [y/N]: ")
    if try_fetch.lower() == "y":
        example_fetch_from_wikidata()
    else:
        print("\nSkipping Wikidata fetch example.")

    print("\n" + "=" * 50)
    print("Examples complete!")


if __name__ == "__main__":
    main()
