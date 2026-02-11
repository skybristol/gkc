"""
Example demonstrating automatic mapping generation from ShEx schemas.

This example shows how to:
1. Load a ShEx EntitySchema from Wikidata
2. Parse the schema to extract properties
3. Fetch property metadata from Wikidata
4. Auto-generate a claims mapping configuration
5. Export to JSON for further customization

This is useful when starting a new mapping - it creates a skeleton
that you then customize with your actual source field names.
"""

import json
from pathlib import Path

from gkc.mapping_builder import ClaimsMapBuilder


def example_analyze_schema():
    """Example 1: Analyze a ShEx schema and print summary."""
    print("=" * 60)
    print("Example 1: Analyze ShEx Schema")
    print("=" * 60)

    # Load EntitySchema E502 (Federally recognized tribe)
    print("\nLoading EntitySchema E502 from Wikidata...")
    builder = ClaimsMapBuilder(eid="E502")
    builder.load_schema()

    # Print analysis summary
    builder.print_summary()


def example_build_claims_map():
    """Example 2: Build claims mapping from ShEx."""
    print("\n" + "=" * 60)
    print("Example 2: Generate Claims Mapping")
    print("=" * 60)

    # Load schema
    builder = ClaimsMapBuilder(eid="E502")
    builder.load_schema()

    # Build claims mapping
    print("\nGenerating claims mapping...")
    claims_map = builder.build_claims_map()

    print(f"\nGenerated {len(claims_map)} claim mappings:")
    print("-" * 60)
    print(json.dumps(claims_map[:3], indent=2))  # Show first 3
    print(f"\n... and {len(claims_map) - 3} more")


def example_build_complete_mapping():
    """Example 3: Build complete mapping configuration."""
    print("\n" + "=" * 60)
    print("Example 3: Generate Complete Mapping Configuration")
    print("=" * 60)

    # Load schema
    builder = ClaimsMapBuilder(eid="E502")

    # Build complete mapping
    print("\nGenerating complete mapping configuration...")
    mapping = builder.build_complete_mapping(entity_type="Q7840353")

    # Pretty print
    print("\nGenerated mapping configuration:")
    print("-" * 60)
    print(json.dumps(mapping, indent=2))


def example_from_file():
    """Example 4: Build mapping from local ShEx file."""
    print("\n" + "=" * 60)
    print("Example 4: Build Mapping from Local File")
    print("=" * 60)

    # Path to local schema
    schema_file = Path(__file__).parent.parent / "tests" / "fixtures" / "shex" / "tribe_E502.shex"

    if not schema_file.exists():
        print(f"⚠️  Schema file not found: {schema_file}")
        return

    print(f"\nLoading schema from: {schema_file}")
    builder = ClaimsMapBuilder(schema_file=str(schema_file))
    builder.load_schema()

    # Build and print summary
    builder.print_summary()


def example_export_mapping():
    """Example 5: Export generated mapping to JSON file."""
    print("\n" + "=" * 60)
    print("Example 5: Export Mapping to File")
    print("=" * 60)

    # Load schema
    builder = ClaimsMapBuilder(eid="E502")

    # Build complete mapping
    print("\nGenerating mapping configuration...")
    mapping = builder.build_complete_mapping(entity_type="Q7840353")

    # Add generation timestamp
    from datetime import datetime
    mapping["metadata"]["generated_date"] = datetime.now().isoformat()

    # Export to file
    output_file = Path(__file__).parent / "mappings" / "auto_generated_tribe_mapping.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"\n✓ Mapping exported to: {output_file}")
    print("\nNext steps:")
    print("1. Open the generated file")
    print("2. Update all 'source_field' values to match your data")
    print("3. Review and adjust 'transform' configurations")
    print("4. Add or update reference_library entries with your sources")
    print("5. Add fixed-value claims (instance of, country, etc.) using 'value' instead of 'source_field'")
    print("6. Reference library entries in claims (e.g., 'references': ['basic_reference'])")



def example_compare_manual_vs_auto():
    """Example 6: Compare manually created vs auto-generated mapping."""
    print("\n" + "=" * 60)
    print("Example 6: Compare Manual vs Auto-Generated")
    print("=" * 60)

    # Load both mappings
    manual_file = Path(__file__).parent / "mappings" / "tribe_mapping_example.json"
    
    if not manual_file.exists():
        print("⚠️  Manual mapping file not found")
        return

    with open(manual_file) as f:
        manual_mapping = json.load(f)

    # Generate auto mapping
    builder = ClaimsMapBuilder(eid="E502")
    auto_mapping = builder.build_complete_mapping(entity_type="Q7840353")

    # Compare
    manual_claims = manual_mapping["mappings"]["claims"]
    auto_claims = auto_mapping["mappings"]["claims"]

    print(f"\nManual mapping has {len(manual_claims)} claims")
    print(f"Auto-generated has {len(auto_claims)} claims")

    # Find properties in auto but not in manual
    manual_props = {c["property"] for c in manual_claims}
    auto_props = {c["property"] for c in auto_claims}

    missing = auto_props - manual_props
    extra = manual_props - auto_props

    if missing:
        print(f"\n⚠️  Properties in ShEx but not in manual mapping:")
        for prop in sorted(missing):
            print(f"    {prop}")

    if extra:
        print(f"\n✓ Additional properties in manual mapping:")
        for prop in sorted(extra):
            print(f"    {prop}")

    if not missing and not extra:
        print("\n✓ Both mappings cover the same properties")


def example_datatype_coverage():
    """Example 7: Show datatype coverage in ShEx."""
    print("\n" + "=" * 60)
    print("Example 7: Datatype Coverage Analysis")
    print("=" * 60)

    # Load schema and build mapping
    builder = ClaimsMapBuilder(eid="E502")
    claims_map = builder.build_claims_map()

    # Group by datatype
    by_datatype = {}
    for claim in claims_map:
        dtype = claim["datatype"]
        if dtype not in by_datatype:
            by_datatype[dtype] = []
        by_datatype[dtype].append(claim["property"])

    print("\nProperties by datatype:")
    print("-" * 60)
    for dtype, props in sorted(by_datatype.items()):
        print(f"\n{dtype} ({len(props)} properties):")
        for prop in sorted(props):
            claim = next(c for c in claims_map if c["property"] == prop)
            print(f"  {prop} - {claim['comment']}")

    # Show transform hints
    print("\n" + "=" * 60)
    print("Transform hints needed:")
    print("-" * 60)
    for claim in claims_map:
        if "transform" in claim:
            print(f"\n{claim['property']} ({claim['datatype']}):")
            print(f"  {json.dumps(claim['transform'], indent=2)}")


if __name__ == "__main__":
    print("Claims Map Builder Examples")
    print("=" * 60)
    print("\nThese examples show how to auto-generate mapping configurations")
    print("from ShEx EntitySchemas by fetching live property data from Wikidata.")
    print()

    try:
        # Run examples
        example_analyze_schema()
        # example_build_claims_map()
        # example_build_complete_mapping()
        # example_from_file()
        # example_export_mapping()
        # example_compare_manual_vs_auto()
        # example_datatype_coverage()

        print("\n" + "=" * 60)
        print("Uncomment other examples in the script to run them")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
