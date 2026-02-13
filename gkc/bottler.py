"""
Bottler: Transform distilled data into final Wikidata item form.

The Bottler is the final stage where distilled, validated, and enriched data
is transformed into the precise structure required by Wikidata: claims, qualifiers,
references, and other item components. Like bottling spirits, this stage ensures
the product is in the right format, labeled correctly, and ready for consumption.

Plain meaning: Convert transformed data into Wikidata item structure.
"""

import math
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from gkc.recipe import RecipeBuilder


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
    def to_quantity(value: Union[float, int], unit: str = "1") -> dict:
        """Convert a number to quantity datavalue."""
        return {
            "value": {"amount": f"+{value}", "unit": unit},
            "type": "quantity",
        }

    @staticmethod
    def to_time(
        date_input: Union[str, int],
        precision: Optional[int] = None,
        calendar: str = "Q1985727",
    ) -> dict:
        """Convert date input to Wikidata time datavalue.

        Args:
            date_input: Year (2005), partial date (2005-01),
                or full ISO date (2005-01-15)
            precision: Explicit precision (9=year, 10=month, 11=day)
                or None to auto-detect
            calendar: Calendar model QID (default: Q1985727 = Gregorian)

        Returns:
            Wikidata time datavalue structure
        """
        # Convert int to string
        date_str = str(date_input).strip()

        # Parse the date and determine precision
        if precision is None:
            # Auto-detect precision from format
            if "-" not in date_str:
                # Just a year: 2005
                precision = 9
                time_str = f"+{date_str.zfill(4)}-00-00T00:00:00Z"
            else:
                parts = date_str.split("-")
                if len(parts) == 2:
                    # Year-month: 2005-01
                    precision = 10
                    year, month = parts
                    time_str = f"+{year.zfill(4)}-{month.zfill(2)}-00T00:00:00Z"
                elif len(parts) == 3:
                    # Full date: 2005-01-15
                    precision = 11
                    year, month, day = parts
                    # Handle time portion if present
                    if "T" in day:
                        day = day.split("T")[0]
                    time_str = (
                        f"+{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}T00:00:00Z"
                    )
                else:
                    # Fallback for unexpected format
                    precision = 11
                    time_str = (
                        f"+{date_str}T00:00:00Z"
                        if "T" not in date_str
                        else f"+{date_str}"
                    )
        else:
            # Use explicit precision
            if precision == 9:
                # Year precision: use -00-00
                year = date_str.split("-")[0]
                time_str = f"+{year.zfill(4)}-00-00T00:00:00Z"
            elif precision == 10:
                # Month precision: use -00 for day
                parts = date_str.split("-")
                year = parts[0]
                month = parts[1] if len(parts) > 1 else "01"
                time_str = f"+{year.zfill(4)}-{month.zfill(2)}-00T00:00:00Z"
            else:
                # Day precision (11) or other
                if "T" not in date_str:
                    time_str = f"+{date_str}T00:00:00Z"
                else:
                    time_str = (
                        f"+{date_str}" if date_str.startswith("+") else f"+{date_str}"
                    )

        return {
            "value": {
                "time": time_str,
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
            # Get precision from transform_config or auto-detect
            precision = None
            if transform_config:
                precision = transform_config.get("precision")
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


class Distillate:
    """
    Distillate: Final product of the distillation process (formerly PropertyMapper).

    A Distillate is the fully configured transformer ready to convert source data
    into Wikidata claims. It knows how to handle properties, qualifiers, references,
    and all the complex datatype transformations needed.

    Plain meaning: A fully configured data transformer ready to produce output.
    """

    def __init__(self, mapping_config: dict):
        """Initialize with a transformation recipe configuration."""
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
    def from_file(cls, file_path: str) -> "Distillate":
        """Load distillate configuration from a JSON file."""
        import json

        with open(file_path) as f:
            config = json.load(f)
        return cls(config)

    @classmethod
    def from_recipe(
        cls, builder: "RecipeBuilder", entity_type: Optional[str] = None
    ) -> "Distillate":
        """
        Create a Distillate directly from a RecipeBuilder.

        Args:
            builder: RecipeBuilder instance (can be already loaded
                or will load specification)
            entity_type: Optional entity type QID for the distillate

        Returns:
            Distillate instance ready to transform data

        Example:
            >>> from gkc import RecipeBuilder, Distillate
            >>> builder = RecipeBuilder(eid="E502")
            >>> distillate = Distillate.from_recipe(
            ...     builder, entity_type="Q7840353"
            ... )
            >>> # Now distillate is ready to process data
        """
        # Import here to avoid circular dependency

        config = builder.finalize_recipe(entity_type=entity_type)
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
            named_refs = [
                r
                for r in references
                if isinstance(r, dict) and "name" in r and "property" in r
            ]

            if named_refs:
                # Get the name from the first named reference
                name = named_refs[0]["name"]

                # Don't override explicit library entries
                if name not in self.reference_library:
                    # Store all property objects (without "name" key)
                    # as the library entry
                    ref_array = []
                    for ref in references:
                        if isinstance(ref, dict) and "property" in ref:
                            ref_copy = {k: v for k, v in ref.items() if k != "name"}
                            ref_array.append(ref_copy)
                    self.reference_library[name] = ref_array

            # Extract named qualifiers
            qualifiers = claim.get("qualifiers", [])

            named_quals = [
                q
                for q in qualifiers
                if isinstance(q, dict) and "name" in q and "property" in q
            ]

            if named_quals:
                name = named_quals[0]["name"]

                if name not in self.qualifier_library:
                    qual_array = []
                    for qual in qualifiers:
                        if isinstance(qual, dict) and "property" in qual:
                            qual_copy = {k: v for k, v in qual.items() if k != "name"}
                            qual_array.append(qual_copy)
                    self.qualifier_library[name] = qual_array

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        try:
            import pandas as pd
        except Exception:
            pd = None
        if pd is not None and pd.isna(value):
            return True
        try:
            nan_check = value != value
        except Exception:
            nan_check = False
        if isinstance(nan_check, bool) and nan_check:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    @staticmethod
    def _split_values(value: Any, separator: Optional[str] = None) -> list[str]:
        values = value if isinstance(value, (list, tuple)) else [value]
        result: list[str] = []

        for val in values:
            if Distillate._is_empty_value(val):
                continue
            text = val if isinstance(val, str) else str(val)
            text = text.strip()

            if separator and separator in text:
                # Split and filter
                parts = [p.strip() for p in text.split(separator)]
                result.extend([p for p in parts if p])
            else:
                result.append(text)

        return result


# Backwards compatibility aliases (deprecated; will be removed)
PropertyMapper = Distillate
