"""
Recipe: Transformation blueprint design from specifications and live metadata.

A recipe is the mapping configuration that transforms raw source data into
distilled, validated knowledge. Like a culinary recipe, it specifies ingredients
(source fields), transformations (fermentation), and the resulting dish.

This module helps design recipes by parsing ShEx specifications and fetching
live property metadata from Wikidata.

Plain meaning: Build and design transformation blueprints from schemas.
"""

import re
from typing import Any, Optional

import requests

from gkc.cooperage import DEFAULT_USER_AGENT
from gkc.spirit_safe import SpiritSafeValidator


class PropertyProfile:
    """Container for Wikidata property metadata (formerly PropertyInfo)."""

    def __init__(self, property_id: str, data: dict):
        self.property_id = property_id
        self.datatype = data.get("datatype", "unknown")
        self.labels = data.get("labels", {})
        self.descriptions = data.get("descriptions", {})
        self.aliases = data.get("aliases", {})

    def get_label(self, language: str = "en") -> str:
        """Get property label in specified language."""
        if language in self.labels:
            return self.labels[language].get("value", self.property_id)
        return self.property_id

    def get_description(self, language: str = "en") -> str:
        """Get property description in specified language."""
        if language in self.descriptions:
            return self.descriptions[language].get("value", "")
        return ""


class SpecificationExtractor:
    """Extracts property information from ShExC specification text."""

    # Pattern to match property references like wdt:P31, p:P571, etc.
    PROPERTY_PATTERN = re.compile(r"\b(wdt?|p|ps|pq|pr):P(\d+)\b")

    # Pattern to match shape definitions with comments
    SHAPE_PATTERN = re.compile(r"<(\w+)>\s*{([^}]+)}", re.MULTILINE | re.DOTALL)

    # Pattern to match inline comments
    COMMENT_PATTERN = re.compile(r"#\s*(.+?)(?:\n|$)")

    def __init__(self, schema_text: str):
        self.schema_text = schema_text
        self.properties = {}
        self.shape_comments = {}

    def extract(self) -> dict[str, dict]:
        """
        Extract all properties from ShExC specification with context.

        Returns:
            Dictionary mapping property IDs to their context information
        """
        self._extract_shapes()
        self._extract_properties()
        return self.properties

    def _extract_shapes(self):
        """Extract shape definitions and their comments."""
        for match in self.SHAPE_PATTERN.finditer(self.schema_text):
            shape_name = match.group(1)
            shape_body = match.group(2)
            self.shape_comments[shape_name] = self._extract_shape_properties(shape_body)

    def _extract_shape_properties(self, shape_body: str) -> dict:
        """Extract properties from a shape body with their comments."""
        properties = {}
        lines = shape_body.split("\n")

        for line in lines:
            # Look for property references
            prop_match = self.PROPERTY_PATTERN.search(line)
            if prop_match:
                prefix = prop_match.group(1)
                prop_num = prop_match.group(2)
                prop_id = f"P{prop_num}"

                # Extract comment if present
                comment_match = self.COMMENT_PATTERN.search(line)
                comment = comment_match.group(1).strip() if comment_match else ""

                # Determine cardinality
                cardinality = self._extract_cardinality(line)

                # Determine if it's a qualifier or reference
                context = self._determine_context(prefix)

                if prop_id not in properties:
                    properties[prop_id] = {
                        "property_id": prop_id,
                        "comment": comment,
                        "cardinality": cardinality,
                        "context": context,
                        "prefix": prefix,
                        "full_line": line.strip(),
                    }

        return properties

    def _extract_properties(self):
        """Combine all property information from shapes."""
        for shape_name, shape_props in self.shape_comments.items():
            for prop_id, prop_info in shape_props.items():
                if prop_id not in self.properties:
                    self.properties[prop_id] = prop_info
                    self.properties[prop_id]["shapes"] = [shape_name]
                else:
                    # Property appears in multiple shapes
                    if "shapes" not in self.properties[prop_id]:
                        self.properties[prop_id]["shapes"] = []
                    self.properties[prop_id]["shapes"].append(shape_name)

    def _extract_cardinality(self, line: str) -> dict:
        """Extract cardinality information from a property line."""
        cardinality = {"min": 1, "max": 1}  # Default: exactly one

        # Check for cardinality indicators
        if line.strip().endswith(";"):
            # Exactly one (required)
            cardinality = {"min": 1, "max": 1, "required": True}
        elif line.strip().endswith("?"):
            # Zero or one (optional)
            cardinality = {"min": 0, "max": 1, "required": False}
        elif line.strip().endswith("*"):
            # Zero or more
            cardinality = {"min": 0, "max": None, "required": False}
        elif line.strip().endswith("+"):
            # One or more
            cardinality = {"min": 1, "max": None, "required": True}

        return cardinality

    def _determine_context(self, prefix: str) -> str:
        """Determine the context of a property based on its prefix."""
        context_map = {
            "wdt": "direct",  # Direct property value
            "wd": "item",  # Item reference
            "p": "statement",  # Full statement
            "ps": "statement_value",  # Statement value
            "pq": "qualifier",  # Qualifier
            "pr": "reference",  # Reference
        }
        return context_map.get(prefix, "unknown")


class PropertyCatalog:
    """Fetches and caches property metadata from Wikidata API."""

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.api_url = "https://www.wikidata.org/w/api.php"
        self._cache = {}

    def fetch_properties(self, property_ids: list[str]) -> dict[str, PropertyProfile]:
        """
        Fetch metadata for multiple properties from Wikidata.

        Args:
            property_ids: List of property IDs (e.g., ['P31', 'P571'])

        Returns:
            Dictionary mapping property IDs to PropertyProfile objects
        """
        # Filter out cached properties
        uncached_ids = [pid for pid in property_ids if pid not in self._cache]

        if uncached_ids:
            # Fetch in batches of 50 (API limit)
            for i in range(0, len(uncached_ids), 50):
                batch = uncached_ids[i : i + 50]
                self._fetch_batch(batch)

        return {pid: self._cache[pid] for pid in property_ids if pid in self._cache}

    def _fetch_batch(self, property_ids: list[str]):
        """Fetch a batch of properties from the API."""
        params = {
            "action": "wbgetentities",
            "ids": "|".join(property_ids),
            "props": "labels|descriptions|aliases|datatype",
            "format": "json",
        }

        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "entities" in data:
                for prop_id, prop_data in data["entities"].items():
                    if "missing" not in prop_data:
                        self._cache[prop_id] = PropertyProfile(prop_id, prop_data)
        except requests.RequestException as e:
            print(f"Warning: Failed to fetch properties: {e}")


class RecipeBuilder:
    """
    Builds transformation recipes from ShExC specifications (formerly ClaimsMapBuilder).

    A recipe combines ShExC schema analysis with live Wikidata property metadata
    to generate skeleton mapping configurations that guide transformation.

    Plain meaning: Design transformation blueprints from schemas and metadata.
    """

    def __init__(
        self,
        eid: Optional[str] = None,
        schema_text: Optional[str] = None,
        schema_file: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the recipe builder.

        Args:
            eid: EntitySchema ID (e.g., 'E502')
            schema_text: ShExC schema as text
            schema_file: Path to ShExC schema file
            user_agent: Custom user agent for API requests
        """
        self.validator = SpiritSafeValidator(
            eid=eid, schema_text=schema_text, schema_file=schema_file
        )
        self.user_agent = user_agent
        self.schema_text: Optional[str] = None
        self.property_fetcher = PropertyCatalog(user_agent)

    def load_specification(self) -> "RecipeBuilder":
        """Load the ShExC specification."""
        self.validator.load_specification()
        self.schema_text = self.validator._schema
        return self

    def load_schema(self) -> "RecipeBuilder":
        """
        Deprecated: Use load_specification() instead.
        """
        return self.load_specification()

    def assemble_recipe(
        self, include_qualifiers: bool = True, include_references: bool = True
    ) -> list[dict[str, Any]]:
        """
        Assemble a recipe (claims mapping) from the loaded ShExC specification.

        Args:
            include_qualifiers: Whether to include qualifier properties
            include_references: Whether to include reference properties

        Returns:
            List of claim mapping dictionaries
        """
        if not self.schema_text:
            self.load_specification()

        # Extract properties from ShExC
        extractor = SpecificationExtractor(self.schema_text)
        shex_properties = extractor.extract()

        # Separate by context
        statement_props = {
            pid: info
            for pid, info in shex_properties.items()
            if info["context"] in ["direct", "statement", "statement_value"]
        }
        qualifier_props = {
            pid: info
            for pid, info in shex_properties.items()
            if info["context"] == "qualifier"
        }
        reference_props = {
            pid: info
            for pid, info in shex_properties.items()
            if info["context"] == "reference"
        }

        # Fetch property metadata from Wikidata
        all_prop_ids = list(shex_properties.keys())
        property_info = self.property_fetcher.fetch_properties(all_prop_ids)

        # Build claims mapping
        claims_map = []

        for prop_id, shex_info in statement_props.items():
            prop_data = property_info.get(prop_id)

            claim_mapping = {
                "property": prop_id,
                "comment": self._format_comment(shex_info, prop_data),
                "source_field": f"{prop_id.lower()}_value",
                "datatype": prop_data.datatype if prop_data else "unknown",
                "required": shex_info["cardinality"].get("required", False),
            }

            # Add transform hints based on datatype
            if prop_data:
                transform_hint = self._get_transform_hint(prop_data.datatype)
                if transform_hint:
                    claim_mapping["transform"] = transform_hint

            # Add qualifiers if requested
            if include_qualifiers and qualifier_props:
                claim_mapping["qualifiers"] = []
                # Note: In a real implementation, we'd need to parse which qualifiers
                # go with which statements from the ShExC structure

            # Add references if requested
            if include_references and reference_props:
                claim_mapping["references"] = []
                # Note: Similar to qualifiers, need ShExC structure parsing

            claims_map.append(claim_mapping)

        return claims_map

    def build_claims_map(
        self, include_qualifiers: bool = True, include_references: bool = True
    ) -> list[dict[str, Any]]:
        """
        Deprecated: Use assemble_recipe() instead.
        """
        return self.assemble_recipe(include_qualifiers, include_references)

    def finalize_recipe(self, entity_type: Optional[str] = None) -> dict[str, Any]:
        """
        Finalize a complete recipe configuration skeleton.

        Args:
            entity_type: Wikidata QID of the entity type (e.g., 'Q7840353')

        Returns:
            Complete transformation recipe (mapping configuration)
        """
        if not self.schema_text:
            self.load_specification()

        claims_map = self.assemble_recipe()

        mapping = {
            "$schema": "https://example.com/gkc/recipe-schema.json",
            "version": "1.0",
            "metadata": {
                "name": "Auto-generated recipe",
                "description": "Generated from ShExC specification",
                "entity_schema_id": self.validator.eid or "unknown",
                "target_entity_type": entity_type or "TODO",
                "generated_date": "TODO",
            },
            "reference_library": {
                "basic_reference": [
                    {
                        "property": "P248",
                        "value": "TODO_SOURCE_QID",
                        "datatype": "wikibase-item",
                        "comment": "Stated in: UPDATE with actual source QID",
                    },
                    {
                        "property": "P813",
                        "value": "current_date",
                        "datatype": "time",
                        "comment": "Retrieved date",
                    },
                ]
            },
            "qualifier_library": {
                "point_in_time": [
                    {
                        "property": "P585",
                        "source_field": "TODO_date_field",
                        "datatype": "time",
                        "comment": "Point in time qualifier - UPDATE source_field",
                    }
                ]
            },
            "mappings": {
                "labels": [
                    {
                        "source_field": "label",
                        "language": "en",
                        "required": True,
                        "comment": (
                            "Main label - UPDATE source_field to " "match your data"
                        ),
                    }
                ],
                "aliases": [
                    {
                        "source_field": "aliases",
                        "language": "en",
                        "separator": ";",
                        "required": False,
                        "comment": "Aliases - UPDATE source_field to match your data",
                    }
                ],
                "descriptions": [
                    {
                        "source_field": "description",
                        "language": "en",
                        "required": False,
                        "comment": (
                            "Description - UPDATE source_field to match your data"
                        ),
                    }
                ],
                "claims": claims_map,
            },
        }

        return mapping

    def build_complete_mapping(
        self, entity_type: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Deprecated: Use finalize_recipe() instead.
        """
        return self.finalize_recipe(entity_type)

    @staticmethod
    def _format_comment(shex_info: dict, prop_data: Optional[PropertyProfile]) -> str:
        """Format a comment for a property from ShEx and metadata."""
        parts = []
        if shex_info.get("comment"):
            parts.append(shex_info["comment"])
        if prop_data:
            desc = prop_data.get_description()
            if desc:
                parts.append(f"({desc})")
        return " ".join(parts) if parts else "Property mapping"

    @staticmethod
    def _get_transform_hint(datatype: str) -> Optional[dict]:
        """Get transformation hints for common Wikidata datatypes."""
        hints = {
            "time": {"type": "time", "hint": "Provide ISO date or YYYY format"},
            "quantity": {"type": "quantity", "hint": "Numeric value and optional unit"},
            "wikibase-item": {"type": "entity", "hint": "Wikidata QID"},
            "globe-coordinate": {
                "type": "coordinates",
                "hint": "Latitude/longitude pair",
            },
            "monolingualtext": {
                "type": "text",
                "hint": "Text with language tag",
            },
            "url": {"type": "url", "hint": "HTTP or HTTPS URL"},
        }
        return hints.get(datatype)
