"""
Example demonstrating sitelinks usage in GKC mapping.

This shows how to configure and use sitelinks to connect Wikidata items
to Wikipedia articles and other Wikimedia projects.
"""

import json
from gkc.item_creator import PropertyMapper

# Example mapping configuration with sitelinks
mapping_config = {
    "version": "1.0",
    "metadata": {
        "name": "Sitelinks Example",
        "description": "Demonstrates sitelinks configuration"
    },
    "mappings": {
        "labels": [
            {
                "source_field": "name",
                "language": "en",
                "required": True
            }
        ],
        "descriptions": [
            {
                "source_field": "description",
                "language": "en",
                "required": False
            }
        ],
        "aliases": [],
        "sitelinks": [
            {
                "site": "enwiki",
                "source_field": "wikipedia_en_title",
                "required": False,
                "badges": [],
                "comment": "English Wikipedia article"
            },
            {
                "site": "frwiki",
                "source_field": "wikipedia_fr_title",
                "required": False,
                "badges": [],
                "comment": "French Wikipedia article"
            },
            {
                "site": "commonswiki",
                "source_field": "commons_category",
                "required": False,
                "badges": [],
                "comment": "Wikimedia Commons category"
            }
        ],
        "claims": [
            {
                "property": "P31",
                "value": "Q5",  # instance of human
                "datatype": "wikibase-item",
                "qualifiers": [],
                "references": []
            }
        ]
    }
}

# Example source data
source_records = [
    {
        "name": "Albert Einstein",
        "description": "German-born theoretical physicist",
        "wikipedia_en_title": "Albert Einstein",
        "wikipedia_fr_title": "Albert Einstein",
        "commons_category": "Category:Albert Einstein"
    },
    {
        "name": "Marie Curie",
        "description": "Polish-French physicist and chemist",
        "wikipedia_en_title": "Marie Curie",
        "wikipedia_fr_title": "Marie Curie",
        "commons_category": None  # This will be skipped
    },
    {
        "name": "Example Person",
        "description": "Person without Wikipedia articles",
        # No Wikipedia fields - sitelinks will be empty
    }
]

# Create mapper
mapper = PropertyMapper(mapping_config)

# Transform each record
print("=" * 70)
print("SITELINKS TRANSFORMATION EXAMPLES")
print("=" * 70)

for i, record in enumerate(source_records, 1):
    print(f"\n--- Record {i}: {record['name']} ---")
    print(f"Source data: {json.dumps(record, indent=2)}")
    
    # Transform to Wikidata JSON
    item_json = mapper.transform_to_wikidata(record)
    
    # Show only sitelinks section
    print(f"\nGenerated sitelinks:")
    if item_json["sitelinks"]:
        print(json.dumps(item_json["sitelinks"], indent=2, ensure_ascii=False))
    else:
        print("  (no sitelinks)")
    
    # Show full item for first record
    if i == 1:
        print(f"\nFull Wikidata JSON for {record['name']}:")
        print(json.dumps(item_json, indent=2, ensure_ascii=False))

print("\n" + "=" * 70)
print("KEY OBSERVATIONS")
print("=" * 70)
print("""
1. Empty/None values are automatically skipped (Marie Curie's commons_category)
2. Missing fields don't cause errors when required=False
3. Multiple sitelinks can be configured for different wikis
4. Each sitelink includes site, title, and badges
5. Titles are automatically trimmed of whitespace
""")

# Example with fixed title
print("\n" + "=" * 70)
print("EXAMPLE WITH FIXED TITLE")
print("=" * 70)

fixed_title_config = {
    "version": "1.0", 
    "metadata": {"name": "Fixed Title Example"},
    "mappings": {
        "labels": [{"source_field": "name", "language": "en", "required": True}],
        "descriptions": [],
        "aliases": [],
        "sitelinks": [
            {
                "site": "commonswiki",
                "title": "Category:Physics",  # Fixed title for all items
                "required": False,
                "badges": []
            }
        ],
        "claims": []
    }
}

fixed_mapper = PropertyMapper(fixed_title_config)
fixed_record = {"name": "Test Item"}
fixed_item = fixed_mapper.transform_to_wikidata(fixed_record)

print(f"Source: {json.dumps(fixed_record, indent=2)}")
print(f"Sitelinks: {json.dumps(fixed_item['sitelinks'], indent=2)}")

# Example with badges
print("\n" + "=" * 70)
print("EXAMPLE WITH BADGES")
print("=" * 70)

badge_config = {
    "version": "1.0",
    "metadata": {"name": "Badge Example"},
    "mappings": {
        "labels": [{"source_field": "name", "language": "en", "required": True}],
        "descriptions": [],
        "aliases": [],
        "sitelinks": [
            {
                "site": "enwiki",
                "source_field": "wikipedia_title",
                "badges": ["Q17437798"],  # Featured article badge
                "required": False
            }
        ],
        "claims": []
    }
}

badge_mapper = PropertyMapper(badge_config)
badge_record = {"name": "Featured Article", "wikipedia_title": "Featured Article"}
badge_item = badge_mapper.transform_to_wikidata(badge_record)

print(f"Source: {json.dumps(badge_record, indent=2)}")
print(f"Sitelinks: {json.dumps(badge_item['sitelinks'], indent=2)}")
print("\nNote: Q17437798 is the QID for 'Featured article' badge")

print("\n" + "=" * 70)
print("COMMON SITE CODES")
print("=" * 70)
print("""
Wikipedia:
  - enwiki (English)
  - frwiki (French)
  - dewiki (German)
  - eswiki (Spanish)
  - jawiki (Japanese)
  - ...

Other Projects:
  - commonswiki (Wikimedia Commons)
  - specieswiki (Wikispecies)
  - enwikisource (English Wikisource)
  - enwikivoyage (English Wikivoyage)
  - enwiktionary (English Wiktionary)

Full list: https://www.wikidata.org/w/api.php?action=help&modules=wbsetsitelink
""")
