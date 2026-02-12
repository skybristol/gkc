#!/usr/bin/env python
"""Integration test for SPARQL module."""

import sys
from urllib.parse import quote

print("\n" + "=" * 60)
print("SPARQL Module Integration Test")
print("=" * 60)

# Test 1: Import from main package
print("\n[1/5] Testing module import from main package...")
try:
    from gkc import (
        SPARQLQuery,
        SPARQLError,
        execute_sparql,
        execute_sparql_to_dataframe,
    )

    print("✓ All classes and functions imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Instantiate executor
print("\n[2/5] Testing SPARQLQuery instantiation...")
try:
    executor = SPARQLQuery(endpoint="https://query.wikidata.org/sparql", timeout=30)
    print(f"✓ SPARQLQuery instantiated with endpoint: {executor.endpoint}")
except Exception as e:
    print(f"✗ Instantiation failed: {e}")
    sys.exit(1)

# Test 3: Test URL parsing
print("\n[3/5] Testing Wikidata URL parsing...")
try:
    test_query = "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"
    encoded = quote(test_query)
    url = f"https://query.wikidata.org/#{encoded}"
    extracted = SPARQLQuery.parse_wikidata_query_url(url)
    assert extracted == test_query
    print(f"✓ URL parsing works correctly")
    print(f"  Query length: {len(extracted)} characters")
except Exception as e:
    print(f"✗ URL parsing failed: {e}")
    sys.exit(1)

# Test 4: Test query normalization
print("\n[4/5] Testing query normalization...")
try:
    normalized1 = SPARQLQuery.normalize_query("  SELECT ?item WHERE { } ")
    assert "SELECT" in normalized1
    normalized2 = SPARQLQuery.normalize_query(url)
    assert normalized2 == test_query
    print(f"✓ Query normalization works (plain and URL)")
except Exception as e:
    print(f"✗ Query normalization failed: {e}")
    sys.exit(1)

# Test 5: Test error handling
print("\n[5/5] Testing error handling...")
try:
    SPARQLQuery.parse_wikidata_query_url("https://example.com/#SELECT%20*")
    print("✗ Should have raised SPARQLError")
    sys.exit(1)
except SPARQLError as e:
    print(f"✓ SPARQLError raised correctly: {str(e)[:50]}...")

print("\n" + "=" * 60)
print("✓ All integration tests passed!")
print("=" * 60 + "\n")
