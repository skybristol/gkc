"""
Example demonstrating item creation from source data using mapping configuration.

This example shows the complete workflow:
1. Load a mapping configuration
2. Load source data
3. Transform to Wikidata JSON format
4. Optionally validate against ShEx
5. Submit to Wikidata (or dry-run)

Before running:
1. Set up authentication credentials:
   export WIKIVERSE_USERNAME="YourUsername@YourBot"
   export WIKIVERSE_PASSWORD="your_bot_password"

2. Ensure you have the mapping config and source data files
"""

import json
from pathlib import Path

from gkc import WikiverseAuth
from gkc.item_creator import ItemCreator, PropertyMapper
from gkc.shex import ShExValidator


def example_dry_run():
    """Example 1: Dry run - transform data but don't submit."""
    print("=" * 60)
    print("Example 1: Dry Run - Transform Without Submission")
    print("=" * 60)

    # Load mapping configuration
    mapping_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    mapper = PropertyMapper.from_file(str(mapping_file))

    # Load source data
    data_file = Path(__file__).parent / "data" / "tribe_source_example.json"
    with open(data_file) as f:
        source_data = json.load(f)

    # Create auth (but don't need to login for dry run)
    auth = WikiverseAuth()

    # Create ItemCreator in dry-run mode
    creator = ItemCreator(auth=auth, mapper=mapper, dry_run=True)

    # Process first record
    print("\nProcessing first record (Cherokee Nation)...")
    print("-" * 60)
    creator.create_item(source_data[0], validate=False)


def example_transform_only():
    """Example 2: Just transform data to see the Wikidata JSON."""
    print("\n" + "=" * 60)
    print("Example 2: Transform to Wikidata JSON")
    print("=" * 60)

    # Load mapping configuration
    mapping_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    mapper = PropertyMapper.from_file(str(mapping_file))

    # Load source data
    data_file = Path(__file__).parent / "data" / "tribe_source_example.json"
    with open(data_file) as f:
        source_data = json.load(f)

    # Transform the first record (Cherokee Nation - has multiple aliases with separator)
    print("\nTransforming Cherokee Nation record (note the alias separator handling)...")
    wikidata_json = mapper.transform_to_wikidata(source_data[0])

    # Pretty print the result
    print("\nResulting Wikidata JSON:")
    print("-" * 60)
    print(json.dumps(wikidata_json, indent=2))
    
    # Highlight the aliases section
    if "aliases" in wikidata_json and "en" in wikidata_json["aliases"]:
        print("\n" + "=" * 60)
        print("Note: Aliases were split from semicolon-separated string:")
        for alias in wikidata_json["aliases"]["en"]:
            print(f"  - {alias['value']}")
        print("=" * 60)


def example_with_validation():
    """Example 3: Transform and validate against ShEx (dry run)."""
    print("\n" + "=" * 60)
    print("Example 3: Transform and Validate Against ShEx")
    print("=" * 60)

    # Load mapping configuration
    mapping_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    mapper = PropertyMapper.from_file(str(mapping_file))

    # Create validator for EntitySchema E502
    validator = ShExValidator(eid="E502")

    # Create auth (dry run mode)
    auth = WikiverseAuth()

    # Create ItemCreator with validator
    creator = ItemCreator(auth=auth, mapper=mapper, validator=validator, dry_run=True)

    # Load source data
    data_file = Path(__file__).parent / "data" / "tribe_source_example.json"
    with open(data_file) as f:
        source_data = json.load(f)

    # Process with validation
    print("\nProcessing with ShEx validation enabled...")
    print("(Note: Full validation implementation pending)")
    print("-" * 60)
    try:
        result = creator.create_item(source_data[0], validate=True)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Validation error: {e}")


def example_batch_processing():
    """Example 4: Process multiple records in batch."""
    print("\n" + "=" * 60)
    print("Example 4: Batch Processing (Dry Run)")
    print("=" * 60)

    # Setup
    mapping_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    mapper = PropertyMapper.from_file(str(mapping_file))

    auth = WikiverseAuth()
    creator = ItemCreator(auth=auth, mapper=mapper, dry_run=True)

    # Load all source data
    data_file = Path(__file__).parent / "data" / "tribe_source_example.json"
    with open(data_file) as f:
        source_data = json.load(f)

    # Process batch
    print(f"\nProcessing {len(source_data)} records...")
    print("-" * 60)
    results = creator.create_batch(source_data, validate=False)

    print(f"\nSuccessful: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")

    if results["success"]:
        print("\nSuccessfully processed:")
        for item in results["success"]:
            record = item["record"]
            print(f"  - {record['tribe_name']} → {item['qid']}")

    if results["failed"]:
        print("\nFailed records:")
        for item in results["failed"]:
            record = item["record"]
            print(f"  - {record.get('tribe_name', 'Unknown')}: {item['error']}")


def example_actual_submission():
    """Example 5: Actually submit to Wikidata (requires auth)."""
    print("\n" + "=" * 60)
    print("Example 5: Actual Submission to Wikidata")
    print("=" * 60)
    print("WARNING: This will create real items on Wikidata!")
    print("=" * 60)

    # Check for authentication
    auth = WikiverseAuth()
    if not auth.is_authenticated():
        print("\n⚠️  No credentials found.")
        print("Set WIKIVERSE_USERNAME and WIKIVERSE_PASSWORD to run this example.")
        return

    print(f"\nAuthenticating as: {auth.username}")
    try:
        auth.login()
        print("✓ Successfully logged in")
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return

    # Setup mapper
    mapping_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    mapper = PropertyMapper.from_file(str(mapping_file))

    # Create ItemCreator (NOT in dry-run mode)
    creator = ItemCreator(auth=auth, mapper=mapper, dry_run=False)

    # Load source data
    data_file = Path(__file__).parent / "data" / "tribe_source_example.json"
    with open(data_file) as f:
        source_data = json.load(f)

    # For safety, only process first record
    record = source_data[0]
    print(f"\nCreating item for: {record['tribe_name']}")

    response = input("Are you sure you want to create this item? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        auth.logout()
        return

    try:
        qid = creator.create_item(record, validate=False)
        print(f"\n✓ Successfully created item: {qid}")
        print(f"   View at: https://www.wikidata.org/wiki/{qid}")
    except Exception as e:
        print(f"\n✗ Failed to create item: {e}")
    finally:
        auth.logout()
        print("\nLogged out.")


def show_datatype_examples():
    """Example 6: Show how different datatypes are transformed."""
    print("\n" + "=" * 60)
    print("Example 6: Datatype Transformation Examples")
    print("=" * 60)

    from gkc.item_creator import DataTypeTransformer

    transformer = DataTypeTransformer()

    print("\n1. Wikibase Item (QID):")
    print(json.dumps(transformer.to_wikibase_item("Q7840353"), indent=2))

    print("\n2. Quantity:")
    print(json.dumps(transformer.to_quantity(450000), indent=2))

    print("\n3. Time/Date:")
    print(json.dumps(transformer.to_time("2023-01-01"), indent=2))

    print("\n4. Monolingualtext:")
    print(json.dumps(transformer.to_monolingualtext("ᏣᎳᎩ ᎠᏰᎵ", "chr"), indent=2))

    print("\n5. Globe Coordinate:")
    print(json.dumps(transformer.to_globe_coordinate(35.9149, -94.8703), indent=2))

    print("\n6. URL:")
    print(json.dumps(transformer.to_url("https://www.cherokee.org/"), indent=2))


if __name__ == "__main__":
    print("Wikidata Item Creation Examples")
    print("=" * 60)

    # Run examples
    try:
        example_dry_run()
        example_transform_only()
        show_datatype_examples()

        # Uncomment to run these examples:
        # example_with_validation()
        # example_batch_processing()
        # example_actual_submission()  # BE CAREFUL!

    except FileNotFoundError as e:
        print(f"\n⚠️  Required file not found: {e}")
        print("Make sure you're running from the examples directory")
        print("or that the mapping and data files exist.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
