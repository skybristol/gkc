"""
Example showing integration between ClaimsMapBuilder and PropertyMapper.

This demonstrates how to:
1. Auto-generate a mapping from EntitySchema
2. Use it directly with PropertyMapper
3. Transform data without needing to save/load files
"""

import json

from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper


def example_direct_integration():
    """Example 1: Generate mapping and use directly."""
    print("=" * 60)
    print("Example 1: Direct Integration")
    print("=" * 60)

    # Generate mapping from EntitySchema
    print("\nGenerating mapping from EntitySchema E502...")
    builder = ClaimsMapBuilder(eid="E502")

    # Create PropertyMapper directly (no file needed!)
    mapper = PropertyMapper.from_claims_builder(builder, entity_type="Q7840353")

    print("✓ Mapper created and ready to use")
    print(f"  Labels: {len(mapper.config['mappings'].get('labels', []))} fields")
    print(f"  Claims: {len(mapper.config['mappings'].get('claims', []))} properties")

    # Transform sample data
    sample_record = {
        "label": "Cherokee Nation",
        "p31_value": "Q7840353",
        "p2124_value": 450000,
        # Note: These field names come from auto-generated mapping
        # You'd typically customize them to match your actual data
    }

    print("\nTransforming sample record...")
    result = mapper.transform_to_wikidata(sample_record)
    print(f"✓ Generated Wikidata JSON with {len(result.get('claims', {}))} claims")


def example_with_customization():
    """Example 2: Generate, customize, then use."""
    print("\n" + "=" * 60)
    print("Example 2: Generate, Customize, Use")
    print("=" * 60)

    # Step 1: Generate mapping
    print("\n1. Generating mapping from EntitySchema E502...")
    builder = ClaimsMapBuilder(eid="E502")
    mapping_config = builder.build_complete_mapping(entity_type="Q7840353")

    # Step 2: Customize the mapping
    print("2. Customizing source field names...")

    # Update field names to match your actual data
    # (In practice, you'd edit the saved JSON file)
    for claim in mapping_config["mappings"]["claims"]:
        # Example: Change p2124_value to member_count
        if claim["property"] == "P2124":
            claim["source_field"] = "member_count"
        elif claim["property"] == "P571":
            claim["source_field"] = "established_date"
        # ... etc.

    mapping_config["mappings"]["labels"][0]["source_field"] = "tribe_name"
    mapping_config["mappings"]["descriptions"][0]["source_field"] = "description"

    # Step 3: Create mapper with customized config
    print("3. Creating PropertyMapper with customized config...")
    mapper = PropertyMapper(mapping_config)

    # Step 4: Transform data with your actual field names
    print("4. Transforming data...")
    sample_record = {
        "tribe_name": "Cherokee Nation",
        "description": "Federally recognized tribe in Oklahoma",
        "member_count": 450000,
        "established_date": "1839",
    }

    result = mapper.transform_to_wikidata(sample_record)
    print(f"✓ Transformed successfully")
    print(f"  Label: {result['labels']['en']['value']}")
    print(f"  Claims: {len(result.get('claims', {}))} properties")


def example_save_and_reuse():
    """Example 3: Generate, save, edit file, then load."""
    print("\n" + "=" * 60)
    print("Example 3: Generate → Save → Edit → Load")
    print("=" * 60)

    # Generate and save
    print("\n1. Generating and saving mapping...")
    builder = ClaimsMapBuilder(eid="E502")
    mapping_config = builder.build_complete_mapping(entity_type="Q7840353")

    # Save to file
    with open("my_custom_mapping.json", "w") as f:
        json.dump(mapping_config, f, indent=2)

    print("✓ Saved to: my_custom_mapping.json")
    print("\n2. NOW: Edit my_custom_mapping.json to update source_field names")
    print("   Change 'p2124_value' → 'member_count', etc.")

    print("\n3. After editing, load the customized mapping:")
    print("   mapper = PropertyMapper.from_file('my_custom_mapping.json')")

    # Clean up
    import os

    os.remove("my_custom_mapping.json")
    print("\n(Cleaned up demo file)")


def example_workflow_comparison():
    """Example 4: Compare different workflows."""
    print("\n" + "=" * 60)
    print("Example 4: Workflow Comparison")
    print("=" * 60)

    print("\nWORKFLOW A: Quick start (for testing)")
    print("-" * 60)
    print("  builder = ClaimsMapBuilder(eid='E502')")
    print("  mapper = PropertyMapper.from_claims_builder(builder)")
    print("  # Use immediately, but field names are auto-generated (p31_value, etc.)")

    print("\nWORKFLOW B: Customized (recommended)")
    print("-" * 60)
    print("  builder = ClaimsMapBuilder(eid='E502')")
    print("  config = builder.build_complete_mapping()")
    print("  # Edit config dict or save to file and edit")
    print("  mapper = PropertyMapper(config)  # or from_file()")

    print("\nWORKFLOW C: Manual (full control)")
    print("-" * 60)
    print("  # Create mapping.json from scratch")
    print("  mapper = PropertyMapper.from_file('mapping.json')")


if __name__ == "__main__":
    print("ClaimsMapBuilder ←→ PropertyMapper Integration Examples")
    print("=" * 60)

    try:
        example_direct_integration()
        # example_with_customization()
        # example_save_and_reuse()
        example_workflow_comparison()

        print("\n" + "=" * 60)
        print("Uncomment other examples to see more workflows")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
