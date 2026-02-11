"""
Skeleton implementation for Wikidata item creation from mapped source data.

This is a proposed design showing the key classes and their interactions.
Not yet functional - serves as a blueprint for implementation.
"""

from datetime import datetime
from typing import Any, Optional

from gkc.auth import WikiverseAuth
from gkc.shex import ShExValidator


class DataTypeTransformer:
    """Transforms source data values to Wikidata datavalue structures."""

    @staticmethod
    def to_wikibase_item(qid: str) -> dict:
        """Convert a QID string to wikibase-entityid datavalue."""
        numeric_id = int(qid[1:])  # Remove 'Q' prefix
        return {
            "value": {
                "entity-type": "item",
                "numeric-id": numeric_id,
                "id": qid,
            },
            "type": "wikibase-entityid",
        }

    @staticmethod
    def to_quantity(value: float | int, unit: str = "1") -> dict:
        """Convert a number to quantity datavalue."""
        return {
            "value": {"amount": f"+{value}", "unit": unit},
            "type": "quantity",
        }

    @staticmethod
    def to_time(
        date_str: str, precision: int = 11, calendar: str = "Q1985727"
    ) -> dict:
        """Convert ISO date string to Wikidata time datavalue."""
        # Precision: 9=year, 10=month, 11=day
        # This is simplified - real implementation needs date parsing
        return {
            "value": {
                "time": f"+{date_str}T00:00:00Z",
                "timezone": 0,
                "before": 0,
                "after": 0,
                "precision": precision,
                "calendarmodel": f"http://www.wikidata.org/entity/{calendar}",
            },
            "type": "time",
        }

    @staticmethod
    def to_monolingualtext(text: str, language: str) -> dict:
        """Convert text to monolingualtext datavalue."""
        return {
            "value": {"text": text, "language": language},
            "type": "monolingualtext",
        }

    @staticmethod
    def to_globe_coordinate(lat: float, lon: float, precision: float = 0.0001) -> dict:
        """Convert latitude/longitude to globe-coordinate datavalue."""
        return {
            "value": {
                "latitude": lat,
                "longitude": lon,
                "precision": precision,
                "globe": "http://www.wikidata.org/entity/Q2",
            },
            "type": "globecoordinate",
        }

    @staticmethod
    def to_url(url: str) -> dict:
        """Convert URL string to url datavalue."""
        return {"value": url, "type": "string"}


class SnakBuilder:
    """Builds snak structures (the building blocks of claims)."""

    def __init__(self, transformer: DataTypeTransformer):
        self.transformer = transformer

    def create_snak(
        self, property_id: str, value: Any, datatype: str, transform_config: dict = None
    ) -> dict:
        """Create a snak with the appropriate datavalue."""
        # Apply transformations based on datatype
        if datatype == "wikibase-item":
            datavalue = self.transformer.to_wikibase_item(value)
        elif datatype == "quantity":
            unit = transform_config.get("unit", "1") if transform_config else "1"
            datavalue = self.transformer.to_quantity(value, unit)
        elif datatype == "time":
            precision = (
                transform_config.get("precision", 11) if transform_config else 11
            )
            datavalue = self.transformer.to_time(value, precision)
        elif datatype == "monolingualtext":
            language = (
                transform_config.get("language", "en") if transform_config else "en"
            )
            datavalue = self.transformer.to_monolingualtext(value, language)
        elif datatype == "globe-coordinate":
            datavalue = self.transformer.to_globe_coordinate(value["lat"], value["lon"])
        elif datatype == "url":
            datavalue = self.transformer.to_url(value)
        else:
            # Default: treat as string
            datavalue = {"value": value, "type": "string"}

        return {
            "snaktype": "value",
            "property": property_id,
            "datavalue": datavalue,
        }


class ClaimBuilder:
    """Builds complete claim structures with qualifiers and references."""

    def __init__(self, snak_builder: SnakBuilder):
        self.snak_builder = snak_builder

    def create_claim(
        self,
        property_id: str,
        value: Any,
        datatype: str,
        transform_config: dict = None,
        qualifiers: list[dict] = None,
        references: list[dict] = None,
        rank: str = "normal",
    ) -> dict:
        """Create a complete claim structure."""
        claim = {
            "mainsnak": self.snak_builder.create_snak(
                property_id, value, datatype, transform_config
            ),
            "type": "statement",
            "rank": rank,
        }

        # Add qualifiers if provided
        if qualifiers:
            claim["qualifiers"] = {}
            claim["qualifiers-order"] = []
            for qual in qualifiers:
                qual_prop = qual["property"]
                qual_snak = self.snak_builder.create_snak(
                    qual_prop,
                    qual["value"],
                    qual["datatype"],
                    qual.get("transform"),
                )
                claim["qualifiers"][qual_prop] = [qual_snak]
                claim["qualifiers-order"].append(qual_prop)

        # Add references if provided
        if references:
            claim["references"] = []
            for ref_group in references:
                ref_snaks = {}
                ref_order = []
                for ref_prop, ref_config in ref_group.items():
                    ref_snak = self.snak_builder.create_snak(
                        ref_prop,
                        ref_config["value"],
                        ref_config.get("datatype", "wikibase-item"),
                        ref_config.get("transform"),
                    )
                    ref_snaks[ref_prop] = [ref_snak]
                    ref_order.append(ref_prop)
                claim["references"].append(
                    {"snaks": ref_snaks, "snaks-order": ref_order}
                )

        return claim


class PropertyMapper:
    """Manages property mappings and transforms source data to Wikidata format."""

    def __init__(self, mapping_config: dict):
        """Initialize with a mapping configuration."""
        self.config = mapping_config
        self.transformer = DataTypeTransformer()
        self.snak_builder = SnakBuilder(self.transformer)
        self.claim_builder = ClaimBuilder(self.snak_builder)
        
        # Load explicit reference and qualifier libraries
        self.reference_library = mapping_config.get("reference_library", {}).copy()
        self.qualifier_library = mapping_config.get("qualifier_library", {}).copy()
        
        # Extract and merge inline named references/qualifiers from claims
        self._extract_inline_named_elements()

    @classmethod
    def from_file(cls, file_path: str) -> "PropertyMapper":
        """Load mapping configuration from a JSON file."""
        import json

        with open(file_path) as f:
            config = json.load(f)
        return cls(config)

    @classmethod
    def from_claims_builder(
        cls, builder: "ClaimsMapBuilder", entity_type: Optional[str] = None
    ) -> "PropertyMapper":
        """
        Create a PropertyMapper directly from a ClaimsMapBuilder.

        Args:
            builder: ClaimsMapBuilder instance (can be already loaded or will load schema)
            entity_type: Optional entity type QID for the mapping

        Returns:
            PropertyMapper instance ready to use

        Example:
            >>> from gkc import ClaimsMapBuilder, PropertyMapper
            >>> builder = ClaimsMapBuilder(eid="E502")
            >>> mapper = PropertyMapper.from_claims_builder(builder, entity_type="Q7840353")
            >>> # Now mapper is ready to transform data
        """
        # Import here to avoid circular dependency
        from gkc.mapping_builder import ClaimsMapBuilder

        config = builder.build_complete_mapping(entity_type=entity_type)
        return cls(config)

    def _extract_inline_named_elements(self):
        """
        Scan all claims for inline named references and qualifiers.
        Merge them into the reference_library and qualifier_library.
        Explicit library entries take precedence over inline named elements.
        
        New consistent structure: references/qualifiers use "property" field,
        not property-as-key. Named references are defined inline with "name" field.
        """
        claims = self.config.get("mappings", {}).get("claims", [])
        
        for claim in claims:
            # Extract named references
            references = claim.get("references", [])
            
            # Check if this reference array has a name (defines a reusable reference)
            named_refs = [r for r in references if isinstance(r, dict) and "name" in r and "property" in r]
            
            if named_refs:
                # Get the name from the first named reference
                name = named_refs[0]["name"]
                
                # Don't override explicit library entries
                if name not in self.reference_library:
                    # Store all property objects (without "name" key) as the library entry
                    ref_array = []
                    for ref in references:
                        if isinstance(ref, dict) and "property" in ref:
                            ref_copy = {k: v for k, v in ref.items() if k != "name"}
                            ref_array.append(ref_copy)
                    self.reference_library[name] = ref_array
            
            # Extract named qualifiers
            qualifiers = claim.get("qualifiers", [])
            
            named_quals = [q for q in qualifiers if isinstance(q, dict) and "name" in q and "property" in q]
            
            if named_quals:
                name = named_quals[0]["name"]
                
                if name not in self.qualifier_library:
                    qual_array = []
                    for qual in qualifiers:
                        if isinstance(qual, dict) and "property" in qual:
                            qual_copy = {k: v for k, v in qual.items() if k != "name"}
                            qual_array.append(qual_copy)
                    self.qualifier_library[name] = qual_array

    def transform_to_wikidata(self, source_record: dict) -> dict:
        """Transform a source record to Wikidata item JSON."""
        item = {"labels": {}, "descriptions": {}, "aliases": {}, "claims": {}}

        # Process labels
        for label_mapping in self.config["mappings"].get("labels", []):
            source_field = label_mapping["source_field"]
            if source_field in source_record and source_record[source_field]:
                lang = label_mapping["language"]
                value = source_record[source_field]
                
                # Handle separator if multiple values in one field
                if "separator" in label_mapping:
                    # If there's a separator, take the first value as the primary label
                    values = [v.strip() for v in value.split(label_mapping["separator"]) if v.strip()]
                    if values:
                        item["labels"][lang] = {"language": lang, "value": values[0]}
                else:
                    # Single value
                    item["labels"][lang] = {"language": lang, "value": value}
        
        # Process aliases
        for alias_mapping in self.config["mappings"].get("aliases", []):
            source_field = alias_mapping["source_field"]
            if source_field in source_record and source_record[source_field]:
                lang = alias_mapping["language"]
                value = source_record[source_field]
                
                # Handle separator for multiple aliases in one field
                if "separator" in alias_mapping:
                    values = [v.strip() for v in value.split(alias_mapping["separator"]) if v.strip()]
                else:
                    values = [value]
                
                # Add all values as aliases
                if lang not in item["aliases"]:
                    item["aliases"][lang] = []
                
                for val in values:
                    item["aliases"][lang].append({"language": lang, "value": val})

        # Process descriptions
        for desc_mapping in self.config["mappings"].get("descriptions", []):
            source_field = desc_mapping.get("source_field")
            lang = desc_mapping["language"]

            if source_field and source_field in source_record:
                value = source_record[source_field]
            else:
                value = desc_mapping.get("default", "")

            if value:
                item["descriptions"][lang] = {"language": lang, "value": value}

        # Process all claims (both data-driven and fixed-value)
        for claim_mapping in self.config["mappings"].get("claims", []):
            prop_id = claim_mapping["property"]
            
            # Determine the value - either from source data or fixed
            if "source_field" in claim_mapping:
                source_field = claim_mapping["source_field"]
                
                # Skip if field not in source or is empty
                if source_field not in source_record or not source_record[source_field]:
                    if claim_mapping.get("required", False):
                        raise ValueError(f"Required field '{source_field}' is missing")
                    continue
                
                value = source_record[source_field]
            elif "value" in claim_mapping:
                # Fixed/default value
                value = claim_mapping["value"]
            else:
                # Skip claims without a value source
                continue

            datatype = claim_mapping["datatype"]
            transform_config = claim_mapping.get("transform")

            # Process qualifiers (support both inline and library references)
            qualifiers = self._resolve_qualifiers(
                claim_mapping.get("qualifiers", []), source_record
            )

            # Process references (support both inline and library references)
            references = self._resolve_references(
                claim_mapping.get("references", []), source_record
            )

            # Create the claim
            claim = self.claim_builder.create_claim(
                prop_id,
                value,
                datatype,
                transform_config,
                qualifiers if qualifiers else None,
                references if references else None,
            )

            if prop_id not in item["claims"]:
                item["claims"][prop_id] = []
            item["claims"][prop_id].append(claim)

        return item

    def _resolve_qualifiers(
        self, qualifier_configs: list, source_record: dict
    ) -> list[dict]:
        """
        Resolve qualifiers from library references or inline definitions.
        
        Consistent structure with references: Each qualifier is a property object with
        "property", "value"/"source_field", "datatype" fields.
        
        Args:
            qualifier_configs: Array of property objects
                              OR [{"name": "lib_name"}] for library reference
            source_record: Source data record
            
        Returns:
            List of resolved qualifier dictionaries
        """
        # Check if this is a library reference (name-only object)
        if (len(qualifier_configs) == 1 and 
            isinstance(qualifier_configs[0], dict) and 
            "name" in qualifier_configs[0] and 
            "property" not in qualifier_configs[0]):
            # Library reference - expand it
            name = qualifier_configs[0]["name"]
            if name in self.qualifier_library:
                lib_quals = self.qualifier_library[name]
                # Recursively resolve the library contents
                return self._resolve_qualifiers(lib_quals, source_record)
            else:
                raise ValueError(f"Qualifier library entry '{name}' not found")
        
        qualifiers = []
        
        for qual_config in qualifier_configs:
            if not isinstance(qual_config, dict):
                continue
                
            # Skip name-only or objects without property
            if "property" not in qual_config:
                continue
            
            # Inline qualifier definition
            qual_field = qual_config.get("source_field")
            if qual_field and qual_field in source_record:
                qualifiers.append({
                    "property": qual_config["property"],
                    "value": source_record[qual_field],
                    "datatype": qual_config["datatype"],
                    "transform": qual_config.get("transform"),
                })
            elif "value" in qual_config:
                # Static value
                qualifiers.append({
                    "property": qual_config["property"],
                    "value": qual_config["value"],
                    "datatype": qual_config["datatype"],
                })
        
        return qualifiers

    def _resolve_references(
        self, reference_configs: list, source_record: dict
    ) -> list[dict]:
        """
        Resolve references from library references or inline definitions.
        
        New consistent structure: Each reference is a property object with
        "property", "value"/"value_from", "datatype" fields.
        
        Args:
            reference_configs: Array of property objects (one reference block)
                              OR [{"name": "lib_name"}] for library reference
            source_record: Source data record
            
        Returns:
            List of resolved reference dictionaries (typically one block)
        """
        # Check if this is a library reference (name-only object)
        if (len(reference_configs) == 1 and 
            isinstance(reference_configs[0], dict) and 
            "name" in reference_configs[0] and 
            "property" not in reference_configs[0]):
            # Library reference - expand it
            name = reference_configs[0]["name"]
            if name in self.reference_library:
                lib_refs = self.reference_library[name]
                # Recursively resolve the library contents
                return self._resolve_references(lib_refs, source_record)
            else:
                raise ValueError(f"Reference library entry '{name}' not found")
        
        # Build one reference block from all property objects (Option A)
        resolved_ref = {}
        
        for prop_obj in reference_configs:
            if not isinstance(prop_obj, dict):
                continue
                
            # Skip name-only or objects without property
            if "property" not in prop_obj:
                continue
            
            prop = prop_obj["property"]
            
            # Determine value
            if "value_from" in prop_obj:
                # Get value from source record
                field = prop_obj["value_from"]
                if field == "current_date":
                    value = datetime.now().strftime("%Y-%m-%d")
                elif field in source_record:
                    value = source_record[field]
                else:
                    continue  # Skip if field not in source
            elif "value" in prop_obj:
                # Static value
                value = prop_obj["value"]
            else:
                continue  # Skip if no value specified
            
            resolved_ref[prop] = {
                "value": value,
                "datatype": prop_obj.get("datatype", "wikibase-item"),
                "transform": prop_obj.get("transform"),
            }
        
        # Return array with single reference block (Option A)
        return [resolved_ref] if resolved_ref else []


class ItemCreator:
    """Creates Wikidata items from source data with optional ShEx validation."""

    def __init__(
        self,
        auth: WikiverseAuth,
        mapper: PropertyMapper,
        validator: Optional[ShExValidator] = None,
        dry_run: bool = False,
    ):
        """
        Initialize the item creator.

        Args:
            auth: Authenticated WikiverseAuth instance
            mapper: PropertyMapper with mapping configuration
            validator: Optional ShExValidator for pre-submission validation
            dry_run: If True, don't actually submit to Wikidata
        """
        self.auth = auth
        self.mapper = mapper
        self.validator = validator
        self.dry_run = dry_run

    def create_item(self, source_record: dict, validate: bool = True) -> str:
        """
        Create a new Wikidata item from source data.

        Args:
            source_record: Dictionary containing source data
            validate: Whether to validate against ShEx before submission

        Returns:
            QID of the created item (or "DRY_RUN" if dry_run is True)

        Raises:
            ValueError: If validation fails or required data is missing
        """
        # Transform source data to Wikidata JSON
        item_json = self.mapper.transform_to_wikidata(source_record)

        # Validate if requested and validator is available
        if validate and self.validator:
            # TODO: Implement validation
            # This requires converting JSON to RDF first
            # validation_result = self.validator.validate_json(item_json)
            # if not validation_result.is_valid():
            #     raise ValueError(f"Validation failed: {validation_result.reason}")
            pass

        # Submit to Wikidata
        if self.dry_run:
            print("DRY RUN - Would create item:")
            import json

            print(json.dumps(item_json, indent=2))
            return "DRY_RUN"
        else:
            return self._submit_to_wikidata(item_json)

    def _submit_to_wikidata(self, item_json: dict) -> str:
        """
        Submit the item to Wikidata via the API.

        Args:
            item_json: Complete item JSON structure

        Returns:
            QID of the created item
        """
        if not self.auth.is_logged_in():
            raise ValueError("Not logged in to Wikidata")

        # Get CSRF token
        token_response = self.auth.session.get(
            self.auth.api_url,
            params={"action": "query", "meta": "tokens", "format": "json"},
        )
        token_data = token_response.json()
        csrf_token = token_data["query"]["tokens"]["csrftoken"]

        # Submit the item
        import json

        create_params = {
            "action": "wbeditentity",
            "new": "item",
            "data": json.dumps(item_json),
            "token": csrf_token,
            "format": "json",
            "summary": "Created via GKC",
        }

        response = self.auth.session.post(self.auth.api_url, data=create_params)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise ValueError(f"API error: {result['error']}")

        # Extract and return the QID
        return result["entity"]["id"]

    def create_batch(self, source_records: list[dict], validate: bool = True) -> dict:
        """
        Create multiple items from a batch of source records.

        Args:
            source_records: List of source data dictionaries
            validate: Whether to validate each item before submission

        Returns:
            Dictionary with 'success' and 'failed' lists
        """
        results = {"success": [], "failed": []}

        for i, record in enumerate(source_records):
            try:
                qid = self.create_item(record, validate=validate)
                results["success"].append({"index": i, "record": record, "qid": qid})
            except Exception as e:
                results["failed"].append(
                    {"index": i, "record": record, "error": str(e)}
                )

        return results
