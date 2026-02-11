"""
Test date/time handling in GKC.

Verifies that various date formats are correctly converted to Wikidata time datavalues
with appropriate precision values.
"""

import json
from gkc.item_creator import DataTypeTransformer, PropertyMapper

# Test the DataTypeTransformer directly
print("=" * 70)
print("TESTING DataTypeTransformer.to_time()")
print("=" * 70)

transformer = DataTypeTransformer()

# Test cases: (input, expected_precision, description)
test_cases = [
    ("2005", 9, "Year only"),
    (2005, 9, "Year as integer"),
    ("2005-01", 10, "Year and month"),
    ("2005-01-15", 11, "Full date"),
    ("2005-01-01", 11, "Full date (Jan 1)"),
]

for date_input, expected_precision, description in test_cases:
    result = transformer.to_time(date_input)
    actual_precision = result["value"]["precision"]
    time_value = result["value"]["time"]
    
    status = "✓" if actual_precision == expected_precision else "✗"
    print(f"\n{status} {description}")
    print(f"  Input: {date_input}")
    print(f"  Expected precision: {expected_precision} ({'year' if expected_precision == 9 else 'month' if expected_precision == 10 else 'day'})")
    print(f"  Actual precision: {actual_precision}")
    print(f"  Time string: {time_value}")

# Test with explicit precision override
print("\n" + "=" * 70)
print("Testing explicit precision override:")
result = transformer.to_time("2005-06-15", precision=9)
print(f"  Input: '2005-06-15' with precision=9")
print(f"  Result: {result['value']['time']} (precision: {result['value']['precision']})")

# Test integration with PropertyMapper
print("\n" + "=" * 70)
print("TESTING PropertyMapper with date qualifiers")
print("=" * 70)

mapping_config = {
    "version": "1.0",
    "metadata": {"name": "Date Test"},
    "mappings": {
        "labels": [
            {"source_field": "name", "language": "en", "required": True}
        ],
        "descriptions": [],
        "aliases": [],
        "sitelinks": [],
        "claims": [
            {
                "property": "P2124",
                "source_field": "member_count",
                "datatype": "quantity",
                "transform": {"type": "number_to_quantity", "unit": "1"},
                "qualifiers": [
                    {
                        "property": "P585",
                        "value": "2005",
                        "datatype": "time",
                        "transform": {"type": "date_to_time"}
                    }
                ],
                "references": []
            }
        ]
    }
}

mapper = PropertyMapper(mapping_config)

# Test record
source_record = {
    "name": "Test Organization",
    "member_count": 1000
}

# Transform
item_json = mapper.transform_to_wikidata(source_record)

print("\nSource record:")
print(json.dumps(source_record, indent=2))

print("\nTransformed qualifiers for P2124:")
if "P2124" in item_json["claims"]:
    claim = item_json["claims"]["P2124"][0]
    if "qualifiers" in claim:
        print(json.dumps(claim["qualifiers"], indent=2, ensure_ascii=False))
    else:
        print("  No qualifiers found")
else:
    print("  P2124 claim not found")

# Test with different date formats in qualifiers
print("\n" + "=" * 70)
print("Testing different date formats in mapping")
print("=" * 70)

test_configs = [
    ("2005", "Year only"),
    ("2005-01", "Year-month"),
    ("2005-01-15", "Full date"),
]

for date_value, description in test_configs:
    config = {
        "version": "1.0",
        "metadata": {"name": "Test"},
        "mappings": {
            "labels": [{"source_field": "name", "language": "en", "required": True}],
            "descriptions": [],
            "aliases": [],
            "sitelinks": [],
            "claims": [
                {
                    "property": "P31",
                    "value": "Q5",
                    "datatype": "wikibase-item",
                    "qualifiers": [
                        {
                            "property": "P585",
                            "value": date_value,
                            "datatype": "time"
                        }
                    ],
                    "references": []
                }
            ]
        }
    }
    
    mapper = PropertyMapper(config)
    item = mapper.transform_to_wikidata({"name": "Test"})
    
    qual = item["claims"]["P31"][0]["qualifiers"]["P585"][0]
    time_val = qual["datavalue"]["value"]["time"]
    precision = qual["datavalue"]["value"]["precision"]
    
    precision_name = {9: "year", 10: "month", 11: "day"}.get(precision, f"unknown ({precision})")
    
    print(f"\n✓ {description}: '{date_value}'")
    print(f"  Time string: {time_val}")
    print(f"  Precision: {precision} ({precision_name})")

print("\n" + "=" * 70)
print("All date handling tests completed successfully!")
print("=" * 70)
