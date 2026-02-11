"""
Example demonstrating sitelinks validation before Wikidata submission.

This shows how to:
1. Check if individual Wikipedia pages exist
2. Validate multiple sitelinks at once
3. Filter out invalid sitelinks before submission
4. Integrate validation into a data processing workflow
"""

import pandas as pd
from gkc import SitelinkValidator, check_wikipedia_page, validate_sitelink_dict


def example_1_check_single_page():
    """Check if a single Wikipedia page exists."""
    print("=" * 60)
    print("Example 1: Check Single Wikipedia Page")
    print("=" * 60)
    
    # Simple check - returns title if valid, None if invalid
    result = check_wikipedia_page("Python (programming language)", site_code="enwiki")
    print(f"Valid page: {result}")
    
    result = check_wikipedia_page("ThisPageDoesNotExist123456", site_code="enwiki")
    print(f"Invalid page: {result}")
    
    # Check with redirects allowed
    result = check_wikipedia_page("USA", site_code="enwiki", allow_redirects=True)
    print(f"Redirect (allowed): {result}")
    
    result = check_wikipedia_page("USA", site_code="enwiki", allow_redirects=False)
    print(f"Redirect (rejected): {result}")


def example_2_validate_multiple():
    """Validate multiple sitelinks and get detailed results."""
    print("\n" + "=" * 60)
    print("Example 2: Validate Multiple Sitelinks")
    print("=" * 60)
    
    # Create validator
    validator = SitelinkValidator()
    
    # Test multiple pages
    pages = [
        ("Python (programming language)", "enwiki"),
        ("Python", "frwiki"),
        ("ThisDoesNotExist123", "enwiki"),
        ("Category:Mountains", "commonswiki"),
    ]
    
    print("\nValidation results:")
    for title, site_code in pages:
        exists, message = validator.check_page_exists(title, site_code)
        status = "✓" if exists else "✗"
        msg = message if message else "valid"
        print(f"{status} {site_code}: '{title}' - {msg}")


def example_3_filter_sitelinks():
    """Filter sitelinks to keep only valid ones."""
    print("\n" + "=" * 60)
    print("Example 3: Filter Valid Sitelinks")
    print("=" * 60)
    
    # Simulate sitelinks from transform_to_wikidata
    sitelinks = {
        "enwiki": {
            "site": "enwiki",
            "title": "Alaska",
            "badges": []
        },
        "frwiki": {
            "site": "frwiki",
            "title": "Alaska",
            "badges": []
        },
        "dewiki": {
            "site": "dewiki",
            "title": "Alaska",
            "badges": []
        },
        "commonswiki": {
            "site": "commonswiki",
            "title": "Category:Alaska",
            "badges": []
        }
    }
    
    print("\nOriginal sitelinks:")
    for site, data in sitelinks.items():
        print(f"  {site}: {data['title']}")
    
    # Validate and filter
    print("\nValidation results:")
    valid_sitelinks = validate_sitelink_dict(sitelinks)
    
    validator = SitelinkValidator()
    results = validator.validate_sitelinks(sitelinks)
    for site, (is_valid, message) in results.items():
        status = "✓" if is_valid else "✗"
        msg = message if message else "valid"
        print(f"  {status} {site}: {msg}")
    
    print(f"\nKept {len(valid_sitelinks)}/{len(sitelinks)} valid sitelinks")


def example_4_dataframe_workflow():
    """Validate sitelinks in a pandas DataFrame workflow."""
    print("\n" + "=" * 60)
    print("Example 4: DataFrame Workflow Integration")
    print("=" * 60)
    
    # Sample data with Wikipedia titles
    data = {
        'name': ['Python', 'Java', 'FakeLanguage123'],
        'wikipedia_en': [
            'Python (programming language)',
            'Java (programming language)',
            'ThisDoesNotExist'
        ]
    }
    df = pd.DataFrame(data)
    
    print("\nOriginal data:")
    print(df)
    
    # Validate all Wikipedia pages
    print("\nValidating Wikipedia pages...")
    df['wikipedia_en_valid'] = df['wikipedia_en'].apply(
        lambda x: check_wikipedia_page(x, site_code="enwiki")
    )
    
    # Keep only rows with valid pages
    df_valid = df[df['wikipedia_en_valid'].notna()].copy()
    
    print("\nAfter validation:")
    print(df_valid[['name', 'wikipedia_en', 'wikipedia_en_valid']])
    print(f"\nKept {len(df_valid)}/{len(df)} rows with valid Wikipedia pages")


def example_5_advanced_validation():
    """Advanced validation with custom settings."""
    print("\n" + "=" * 60)
    print("Example 5: Advanced Validation")
    print("=" * 60)
    
    # Create validator with custom settings
    validator = SitelinkValidator(
        user_agent="MyBot/1.0 (https://example.com)",
        timeout=15  # Longer timeout
    )
    
    # Test different Wikimedia projects
    test_cases = [
        ("Alaska", "enwiki"),
        ("File:Example.jpg", "commonswiki"),
        ("Homo sapiens", "specieswiki"),
    ]
    
    print("\nTesting multiple Wikimedia projects:")
    for title, site in test_cases:
        exists, message = validator.check_page_exists(title, site)
        status = "✓" if exists else "✗"
        msg = message if message else "valid"
        print(f"{status} {site:15s} '{title}' - {msg}")


def example_6_integration_with_mapper():
    """Show how to integrate with PropertyMapper workflow."""
    print("\n" + "=" * 60)
    print("Example 6: Integration with PropertyMapper")
    print("=" * 60)
    
    # Simulate a record with sitelinks
    from gkc.item_creator import PropertyMapper
    
    # Load mapping
    mapper = PropertyMapper.from_file("mappings/fed_tribe_from_missing_ak_tribes.json")
    
    # Sample record
    record = {
        'fr_label': 'Example Tribe',
        'wikipedia_en': 'Example_Tribe'  # This would be validated
    }
    
    print("\nWorkflow:")
    print("1. Transform record to Wikidata JSON")
    wikidata_json = mapper.transform_to_wikidata(record)
    
    print("2. Extract sitelinks for validation")
    sitelinks = wikidata_json.get('sitelinks', {})
    print(f"   Found {len(sitelinks)} sitelinks")
    
    print("3. Validate sitelinks")
    if sitelinks:
        valid_sitelinks = validate_sitelink_dict(sitelinks)
        print(f"   {len(valid_sitelinks)}/{len(sitelinks)} sitelinks are valid")
        
        # Replace with validated sitelinks
        wikidata_json['sitelinks'] = valid_sitelinks
        print("4. Updated Wikidata JSON with validated sitelinks")
    
    print("\n✓ Ready for submission to Wikidata")


if __name__ == "__main__":
    # Run all examples
    examples = [
        example_1_check_single_page,
        example_2_validate_multiple,
        example_3_filter_sitelinks,
        example_4_dataframe_workflow,
        example_5_advanced_validation,
        example_6_integration_with_mapper,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Error in {example.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
