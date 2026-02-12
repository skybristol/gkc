"""
SPARQL Query Examples for GKC

This module demonstrates various ways to use the SPARQL query utilities.
"""

from gkc.sparql import SPARQLQuery, execute_sparql, execute_sparql_to_dataframe


def example_1_simple_query():
    """Example 1: Simple query execution."""
    print("\n=== Example 1: Simple Query Execution ===\n")

    executor = SPARQLQuery()

    # Query to find items of a specific type
    query = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q7840353 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 5
    """

    results = executor.query(query)
    print("Results:", results)


def example_2_wikidata_url():
    """Example 2: Execute query from Wikidata URL."""
    print("\n=== Example 2: Execute Query from Wikidata URL ===\n")

    # This is a real Wikidata Query Service URL
    # (you can share these URLs from the Wikidata Query Service)
    url = "https://query.wikidata.org/#SELECT%20%3Fitem%20WHERE%20%7B%0A%09%3Fitem%20wdt%3AP31%20wd%3AQ146%20.%0A%7D%0ALIMIT%205"

    executor = SPARQLQuery()
    results = executor.query(url)
    print("Results:", results)


def example_3_to_dict_list():
    """Example 3: Convert results to list of dictionaries."""
    print("\n=== Example 3: Convert Results to Dict List ===\n")

    executor = SPARQLQuery()

    query = """
    SELECT ?item ?itemLabel ?description WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 3
    """

    results = executor.to_dict_list(query)

    print("Results as list of dicts:")
    for i, row in enumerate(results, 1):
        print(f"  {i}. {row}")


def example_4_to_dataframe():
    """Example 4: Convert results to pandas DataFrame."""
    print("\n=== Example 4: Convert Results to DataFrame ===\n")

    try:
        executor = SPARQLQuery()

        query = """
        SELECT ?item ?itemLabel ?description WHERE {
          ?item wdt:P31 wd:Q146 .
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
          }
        }
        LIMIT 10
        """

        df = executor.to_dataframe(query)

        print("Results as DataFrame:")
        print(df.head())
        print(f"\nShape: {df.shape}")
        print(f"Columns: {list(df.columns)}")

    except ImportError:
        print("pandas is not installed. Install with: pip install pandas")


def example_5_to_csv():
    """Example 5: Export results to CSV."""
    print("\n=== Example 5: Export Results to CSV ===\n")

    executor = SPARQLQuery()

    query = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 5
    """

    # Get CSV data
    csv_data = executor.to_csv(query)
    print("CSV data:")
    print(csv_data)

    # Save to file
    csv_file = executor.to_csv(query, filepath="/tmp/wikidata_results.csv")
    print(f"\nSaved to /tmp/wikidata_results.csv")


def example_6_convenience_function():
    """Example 6: Using convenience function."""
    print("\n=== Example 6: Convenience Function ===\n")

    query = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 3
    """

    # Use convenience function for one-off queries
    results = execute_sparql(query)
    print("Results:", results)


def example_7_dataframe_convenience():
    """Example 7: Using DataFrame convenience function."""
    print("\n=== Example 7: DataFrame Convenience Function ===\n")

    try:
        query = """
        SELECT ?item ?itemLabel WHERE {
          ?item wdt:P31 wd:Q146 .
          SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
          }
        }
        LIMIT 5
        """

        df = execute_sparql_to_dataframe(query)
        print("DataFrame:")
        print(df)

    except ImportError:
        print("pandas is not installed. Install with: pip install pandas")


def example_8_custom_endpoint():
    """Example 8: Using custom SPARQL endpoint."""
    print("\n=== Example 8: Custom SPARQL Endpoint ===\n")

    # Example with a different SPARQL endpoint
    # (using a hypothetical endpoint for demonstration)
    custom_endpoint = "https://dbpedia.org/sparql"

    executor = SPARQLQuery(endpoint=custom_endpoint)

    query = """
    SELECT ?resource ?label WHERE {
      ?resource rdf:type dbo:Animal .
      ?resource rdfs:label ?label .
      FILTER(LANG(?label) = 'en')
    }
    LIMIT 5
    """

    try:
        results = executor.query(query)
        print("Results from custom endpoint:", results)
    except Exception as e:
        print(f"Note: Custom endpoint example failed (expected if endpoint unavailable)")
        print(f"Error: {e}")


def example_9_error_handling():
    """Example 9: Error handling."""
    print("\n=== Example 9: Error Handling ===\n")

    from gkc.sparql import SPARQLError

    executor = SPARQLQuery()

    # Invalid query
    try:
        results = executor.query("INVALID SPARQL SYNTAX")
    except SPARQLError as e:
        print(f"Caught SPARQL error: {e}")

    # Invalid Wikidata URL
    try:
        executor.query("https://example.com/#SELECT%20*")
    except SPARQLError as e:
        print(f"Caught URL parsing error: {e}")


def example_10_query_with_filters():
    """Example 10: Complex query with filters."""
    print("\n=== Example 10: Complex Query with Filters ===\n")

    executor = SPARQLQuery()

    query = """
    SELECT ?item ?itemLabel ?population WHERE {
      ?item wdt:P31 wd:Q3624078 .
      ?item wdt:P1082 ?population .
      FILTER(?population > 1000000)
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    ORDER BY DESC(?population)
    LIMIT 10
    """

    try:
        results = executor.to_dict_list(query)
        print(f"Found {len(results)} cities with population > 1,000,000")
        for i, row in enumerate(results[:5], 1):
            print(f"  {i}. {row}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("GKC SPARQL Query Examples")
    print("=" * 50)

    # Run examples (comment out any you want to skip)
    example_1_simple_query()
    example_2_wikidata_url()
    example_3_to_dict_list()
    example_4_to_dataframe()
    example_5_to_csv()
    example_6_convenience_function()
    example_7_dataframe_convenience()
    example_8_custom_endpoint()
    example_9_error_handling()
    example_10_query_with_filters()

    print("\n" + "=" * 50)
    print("Examples completed!")
