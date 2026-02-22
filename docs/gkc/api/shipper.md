# Shipper API

## Overview

The Shipper module provides write operations for delivering Bottled data to external knowledge systems. Currently it supports Wikidata write operations using the MediaWiki API, with planned support for Wikimedia Commons and OpenStreetMap.

**Current implementations:** Wikidata production and test instance write operations  
**Future implementations:** Wikimedia Commons uploads, OpenStreetMap data contribution

## Quick Start

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

# Authenticate to Wikidata
auth = WikiverseAuth(
    username="MyUsername@MyBot",
    password="abc123def456ghi789"
)
auth.login()

# Create a shipper with dry-run enabled by default
shipper = WikidataShipper(auth=auth)

# Write an item (dry-run, no actual submission)
payload = {
    "labels": {"en": {"language": "en", "value": "Test Item"}},
    "descriptions": {"en": {"language": "en", "value": "A test item"}},
}

result = shipper.write_item(
    payload=payload,
    summary="Creating test item via GKC",
    dry_run=True
)

print(f"Status: {result.status}")
print(f"Warnings: {result.warnings}")
```

## Classes

### ShipperError

::: gkc.shipper.ShipperError
    options:
      show_root_heading: false
      heading_level: 4

### WriteResult

::: gkc.shipper.WriteResult
    options:
      show_root_heading: false
      heading_level: 4

### Shipper

::: gkc.shipper.Shipper
    options:
      show_root_heading: false
      heading_level: 4

### WikidataShipper

::: gkc.shipper.WikidataShipper
    options:
      show_root_heading: false
      heading_level: 4

### CommonsShipper

::: gkc.shipper.CommonsShipper
    options:
      show_root_heading: false
      heading_level: 4

### OpenStreetMapShipper

::: gkc.shipper.OpenStreetMapShipper
    options:
      show_root_heading: false
      heading_level: 4

## Examples

### Create a new Wikidata item with dry-run

Test your payload structure without actually submitting to Wikidata:

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

auth = WikiverseAuth()
auth.login()

shipper = WikidataShipper(auth=auth, dry_run_default=True)

# Prepare a minimal item payload
payload = {
    "labels": {
        "en": {"language": "en", "value": "Douglas Adams"},
        "de": {"language": "de", "value": "Douglas Adams"}
    },
    "descriptions": {
        "en": {"language": "en", "value": "English science fiction writer"}
    },
    "claims": {
        "P31": [{  # instance of
            "mainsnak": {
                "snaktype": "value",
                "property": "P31",
                "datavalue": {
                    "value": {"entity-type": "item", "id": "Q5"},
                    "type": "wikibase-entityid"
                }
            },
            "type": "statement",
            "rank": "normal"
        }]
    }
}

# Dry-run write (no actual submission)
result = shipper.write_item(
    payload=payload,
    summary="Creating Douglas Adams item",
    dry_run=True
)

print(f"Dry-run status: {result.status}")
print(f"Payload validated: {len(result.warnings) == 0}")
if result.warnings:
    print(f"Warnings: {result.warnings}")
```

### Validate payload without submitting

Use validation-only mode to check payload structure:

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

auth = WikiverseAuth()
shipper = WikidataShipper(auth=auth)

# Missing required fields
incomplete_payload = {
    "labels": {"en": {"language": "en", "value": "Test"}}
    # Missing descriptions
}

result = shipper.write_item(
    payload=incomplete_payload,
    summary="Test validation",
    validate_only=True
)

if result.status == "blocked":
    print("Validation failed:")
    for warning in result.warnings:
        print(f"  - {warning}")
else:
    print("Payload is valid")
```

### Submit to test.wikidata.org for testing

Use the test instance before submitting to production:

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

# Authenticate to test.wikidata.org
auth = WikiverseAuth(
    username="TestBot@BotAccount",
    password="test_password_123",
    api_url="wikidata_test"
)
auth.login()

# Create shipper with dry-run disabled for actual submission
shipper = WikidataShipper(auth=auth, dry_run_default=False)

payload = {
    "labels": {"en": {"language": "en", "value": "Test Item"}},
    "descriptions": {"en": {"language": "en", "value": "Testing item creation"}},
}

# Submit to test instance
result = shipper.write_item(
    payload=payload,
    summary="Test item creation via GKC",
    dry_run=False,
    tags=["gkc", "test"],
    bot=True
)

if result.status == "submitted":
    print(f"Created item: {result.entity_id}")
    print(f"Revision ID: {result.revision_id}")
elif result.status == "error":
    print(f"Submission failed: {result.warnings}")
```

### Update an existing Wikidata item

Add claims to an existing item by providing the entity ID:

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

auth = WikiverseAuth()
auth.login()

shipper = WikidataShipper(auth=auth, dry_run_default=False)

# Add a new claim to Q42 (Douglas Adams)
payload = {
    "claims": {
        "P106": [{  # occupation
            "mainsnak": {
                "snaktype": "value",
                "property": "P106",
                "datavalue": {
                    "value": {"entity-type": "item", "id": "Q36180"},
                    "type": "wikibase-entityid"
                }
            },
            "type": "statement",
            "rank": "normal"
        }]
    }
}

result = shipper.write_item(
    payload=payload,
    summary="Adding occupation claim",
    entity_id="Q42",  # Update existing item
    dry_run=True,  # Use dry-run for this example
    bot=True
)

print(f"Update status: {result.status}")
```

### Batch operations with metadata tracking

Track multiple write operations with custom metadata:

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

auth = WikiverseAuth()
auth.login()

shipper = WikidataShipper(auth=auth, dry_run_default=True)

items_to_create = [
    {"name": "Item 1", "description": "First test item"},
    {"name": "Item 2", "description": "Second test item"},
    {"name": "Item 3", "description": "Third test item"},
]

results = []
for idx, item_data in enumerate(items_to_create):
    payload = {
        "labels": {"en": {"language": "en", "value": item_data["name"]}},
        "descriptions": {"en": {"language": "en", "value": item_data["description"]}},
    }
    
    result = shipper.write_item(
        payload=payload,
        summary=f"Batch creation: {item_data['name']}",
        dry_run=True,
        metadata={
            "batch_id": "batch_001",
            "item_index": idx,
            "source": "test_dataset"
        }
    )
    
    results.append(result)

# Analyze batch results
successful = [r for r in results if r.status in ("dry_run", "submitted")]
blocked = [r for r in results if r.status == "blocked"]

print(f"Successful: {len(successful)}, Blocked: {len(blocked)}")
```

## Error Handling

### Handle validation errors

```python
from gkc import WikiverseAuth
from gkc.shipper import WikidataShipper

auth = WikiverseAuth()
shipper = WikidataShipper(auth=auth)

payload = {
    # Missing required labels and descriptions
}

result = shipper.write_item(
    payload=payload,
    summary="Test",
    validate_only=True
)

if result.status == "blocked":
    print("Payload validation failed:")
    for warning in result.warnings:
        print(f"  - {warning}")
    # Fix issues before retrying
```

### Handle API errors

```python
from gkc import WikiverseAuth, AuthenticationError
from gkc.shipper import WikidataShipper

try:
    auth = WikiverseAuth()
    auth.login()
    
    shipper = WikidataShipper(auth=auth, dry_run_default=False)
    
    payload = {
        "labels": {"en": {"language": "en", "value": "Test"}},
        "descriptions": {"en": {"language": "en", "value": "Test item"}},
    }
    
    result = shipper.write_item(
        payload=payload,
        summary="Test submission",
        dry_run=False
    )
    
    if result.status == "error":
        print(f"API error occurred: {result.warnings}")
        print(f"Full API response: {result.api_response}")
    elif result.status == "submitted":
        print(f"Successfully created: {result.entity_id}")
        
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
```

### Missing or invalid authentication

```python
from gkc import WikiverseAuth, AuthenticationError
from gkc.shipper import WikidataShipper

try:
    # Missing credentials
    auth = WikiverseAuth()
    auth.login()
    
    shipper = WikidataShipper(auth=auth, dry_run_default=False)
    
    # This will fail if not authenticated
    result = shipper.write_item(
        payload={"labels": {}, "descriptions": {}},
        summary="Test",
        dry_run=False
    )
    
except AuthenticationError as e:
    print(f"Please set WIKIVERSE_USERNAME and WIKIVERSE_PASSWORD: {e}")
```

## See Also

- [Authentication API](auth.md) - Required for all write operations
- [Shipping](../shipping.md) - Conceptual overview of the shipping stage
- [MediaWiki Wikibase API](https://www.mediawiki.org/wiki/Wikibase/API) - Underlying API documentation
