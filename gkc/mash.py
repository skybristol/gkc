"""
Mash: Load Wikidata items as templates for bulk modification and export.

The Mash stage loads existing Wikidata items as templates, allowing users to
view, filter, and export them in formats like QuickStatements V1 for bulk
creation of similar items.

Plain meaning: Copy an existing item's structure and re-export it for
creating new items.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

from gkc.recipe import EntityCatalog

# Package-level default language
DEFAULT_LANGUAGE = "en"


def set_default_language(lang: str) -> None:
    """Set the package-wide default language for output.

    Plain meaning: Choose which language to use when displaying items.
    """

    global DEFAULT_LANGUAGE
    DEFAULT_LANGUAGE = lang


def get_default_language() -> str:
    """Get the current default language.

    Plain meaning: Find out which language is set for output.
    """

    return DEFAULT_LANGUAGE


def fetch_property_labels(
    property_ids: list[str], language: str = "en"
) -> dict[str, str]:
    """Fetch human-readable labels for Wikidata properties using EntityCatalog.

    Args:
        property_ids: List of property IDs (e.g., ['P31', 'P21']).
        language: Language code for labels (default: 'en').

    Returns:
        Dict mapping property IDs to their labels (e.g., {'P31': 'instance of'}).

    Plain meaning: Look up property names efficiently to make QS output more readable.
    """
    if not property_ids:
        return {}
    catalog = EntityCatalog()
    results = catalog.fetch_entities(property_ids, descriptions=False)
    return {pid: data["label"] for pid, data in results.items() if "label" in data}


@dataclass
class ClaimSummary:
    """Simplified representation of a Wikidata claim for display and export.

    Plain meaning: A simple view of a claim without requiring RDF knowledge.
    """

    property_id: str
    value: str
    qualifiers: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    rank: str = "normal"
    value_metadata: Optional[dict[str, Any]] = None


@dataclass
class MashTemplate:
    """An extracted Wikidata item ready for filtering and export.

    Plain meaning: A loaded Wikidata item template ready for modification.
    """

    qid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    claims: list[ClaimSummary]

    def filter_properties(self, exclude_properties: Optional[list[str]] = None) -> None:
        """Remove specified properties from the template in-place.

        Plain meaning: Delete certain claims to slim down the template.
        """

        if not exclude_properties:
            return

        self.claims = [
            claim
            for claim in self.claims
            if claim.property_id not in exclude_properties
        ]

    def filter_qualifiers(self) -> None:
        """Remove all qualifiers from claims in-place.

        Plain meaning: Strip qualifier detail from claims.
        """

        for claim in self.claims:
            claim.qualifiers = []

    def filter_references(self) -> None:
        """Remove all references from claims in-place.

        Plain meaning: Strip reference detail from claims.
        """

        for claim in self.claims:
            claim.references = []

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """

        return {
            "qid": self.qid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "total_statements": len(self.claims),
            "aliases": self.aliases,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """

        return {
            "qid": self.qid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "aliases": self.aliases,
            "claims": [
                {
                    "property_id": c.property_id,
                    "value": c.value,
                    "qualifiers": c.qualifiers,
                    "references": c.references,
                    "rank": c.rank,
                }
                for c in self.claims
            ],
        }


class MashLoader:
    """Load a Wikidata item as a template for bulk modification.

    Plain meaning: Fetch and parse a Wikidata item into a usable template.
    """

    def __init__(self, user_agent: Optional[str] = None):
        """Initialize the loader.

        Args:
            user_agent: Custom user agent for Wikidata requests.
                       If not provided, a default GKC user agent is used.
        """

        if user_agent is None:
            user_agent = "GKC/1.0 (https://github.com/skybristol/gkc; data integration)"

        self.user_agent = user_agent

    def load(self, qid: str) -> MashTemplate:
        """Load a Wikidata item and return it as a template.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            MashTemplate with the item's structure.

        Raises:
            Exception: If the item cannot be fetched or parsed.

        Plain meaning: Retrieve the item and return it ready for use.
        """

        # Fetch the item via Special:EntityData endpoint which returns JSON
        # This is equivalent to wbgetentities but simpler for single-item fetches
        json_text = self._fetch_entity_json(qid)

        # Parse the JSON response from Wikidata
        entity_data = self._parse_wikidata_json(json_text, qid)

        # Convert to MashTemplate
        template = self._build_template(qid, entity_data)

        return template

    def _fetch_entity_json(self, qid: str) -> str:
        """Fetch a single Wikidata entity as JSON.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            JSON string with entity data.

        Raises:
            RuntimeError: If the fetch fails or entity doesn't exist.

        Plain meaning: Download the item from Wikidata as JSON.
        """

        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"

        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent

        try:
            response = requests.get(url, headers=headers, timeout=30)

            # Handle 404 or 400 errors which indicate item doesn't exist
            if response.status_code == 404:
                raise RuntimeError(f"no-such-entity: {qid} not found on Wikidata")
            if response.status_code == 400:
                raise RuntimeError(f"no-such-entity: {qid} is invalid")

            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to load item {qid}: {exc}") from exc

    def _parse_wikidata_json(self, json_text: str, qid: str) -> dict[str, Any]:
        """Parse Wikidata JSON response from Special:EntityData endpoint.

        Args:
            json_text: Raw JSON response text.
            qid: The QID being parsed (used for error messages).

        Returns:
            Dictionary with entity data.

        Raises:
            ValueError: If JSON parsing fails or format is unexpected.

        Plain meaning: Extract entity data from the API response.
        """

        try:
            response = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON response for {qid}: {exc}") from exc

        if not isinstance(response, dict):
            raise ValueError(f"Expected JSON object for {qid}, got {type(response)}")

        # Special:EntityData wraps data in an "entities" key
        entities = response.get("entities", {})
        entity_data = entities.get(qid, {})

        # Check for API error
        if "error" in entity_data:
            error_code = entity_data["error"].get("code", "unknown")
            error_info = entity_data["error"].get("info", "No error details")
            raise ValueError(
                f"Wikidata API error for {qid} ({error_code}): {error_info}"
            )

        if not entity_data:
            raise ValueError(f"Entity {qid} not found in response")

        return entity_data

    def _build_template(self, qid: str, entity_data: dict[str, Any]) -> MashTemplate:
        """Convert entity data to a MashTemplate.

        Plain meaning: Transform API data into our simplified format.
        """

        # Extract labels, descriptions, aliases
        labels = entity_data.get("labels", {})
        descriptions = entity_data.get("descriptions", {})
        aliases = entity_data.get("aliases", {})

        # Simplify to language -> value mappings
        labels_dict = {
            lang: item.get("value", "")
            for lang, item in labels.items()
            if isinstance(item, dict)
        }
        descriptions_dict = {
            lang: item.get("value", "")
            for lang, item in descriptions.items()
            if isinstance(item, dict)
        }
        aliases_dict = {
            lang: [alias.get("value", "") for alias in alias_list]
            for lang, alias_list in aliases.items()
            if isinstance(alias_list, list)
        }

        # Extract claims
        claims = self._extract_claims(entity_data.get("claims", {}))

        return MashTemplate(
            qid=qid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            aliases=aliases_dict,
            claims=claims,
        )

    @staticmethod
    def _extract_claims(claims_data: dict[str, Any]) -> list[ClaimSummary]:
        """Extract claims from entity data.

        Plain meaning: Parse statement data into simplified claim objects.
        """

        claims: list[ClaimSummary] = []

        for prop_id, statements in claims_data.items():
            if not isinstance(statements, list):
                continue

            for statement in statements:
                claim = MashLoader._statement_to_claim(prop_id, statement)
                if claim:
                    claims.append(claim)

        return claims

    @staticmethod
    @staticmethod
    def _statement_to_claim(
        prop_id: str, statement: dict[str, Any]
    ) -> Optional[ClaimSummary]:
        """Convert a single statement to a ClaimSummary.

        Plain meaning: Simplify a statement object for display.
        """

        # Extract main value
        mainsnak = statement.get("mainsnak", {})
        value, value_metadata = WikidataLoader._snak_to_value(mainsnak)

        if value is None:
            return None

        # Extract qualifiers with their values
        qualifiers = statement.get("qualifiers", {})
        qualifiers_list = []
        for prop, snaks in qualifiers.items():
            if snaks:
                # Extract value from the first snak of each qualifier property
                snak = snaks[0]
                qual_value, qual_metadata = WikidataLoader._snak_to_value(snak)
                if qual_value:
                    qualifier_dict = {"property": prop, "value": qual_value}
                    if qual_metadata:
                        qualifier_dict["metadata"] = qual_metadata
                    qualifiers_list.append(qualifier_dict)

        # Extract references
        references = statement.get("references", [])
        references_list = [{"count": len(ref.get("snaks", {}))} for ref in references]

        rank = statement.get("rank", "normal")

        return ClaimSummary(
            property_id=prop_id,
            value=value,
            qualifiers=qualifiers_list,
            references=references_list,
            rank=rank,
            value_metadata=value_metadata,
        )

    @staticmethod
    def _snak_to_value(
        snak: dict[str, Any],
    ) -> tuple[Optional[str], Optional[dict[str, Any]]]:
        """Extract a human-readable value from a snak with metadata.

        Returns:
            Tuple of (value_string, metadata_dict) where metadata contains
            things like precision for dates, units for quantities, etc.

        Plain meaning: Get a simple string representation of the value plus metadata.
        """

        snaktype = snak.get("snaktype", "value")

        if snaktype == "novalue":
            return "[no value]", None
        if snaktype == "somevalue":
            return "[unknown value]", None

        datavalue = snak.get("datavalue")
        if not datavalue:
            return None, None

        dv_type = datavalue.get("type", "")
        dv_value = datavalue.get("value")

        if dv_type == "wikibase-entityid":
            if isinstance(dv_value, dict):
                return dv_value.get("id", "[entity]"), None
            return str(dv_value), None

        if dv_type == "quantity":
            if isinstance(dv_value, dict):
                amount = dv_value.get("amount", "[quantity]")
                unit = dv_value.get("unit")
                metadata = {"unit": unit} if unit else None
                return amount, metadata
            return str(dv_value), None

        if dv_type == "time":
            if isinstance(dv_value, dict):
                time_str = dv_value.get("time", "[time]")
                precision = dv_value.get("precision")
                metadata = {"precision": precision} if precision is not None else None
                return time_str, metadata
            return str(dv_value), None

        if dv_type == "monolingualtext":
            if isinstance(dv_value, dict):
                return dv_value.get("text", "[text]"), None
            return str(dv_value), None

        if dv_type == "string":
            return str(dv_value), None

        if dv_type == "globecoordinate":
            if isinstance(dv_value, dict):
                lat = dv_value.get("latitude", "?")
                lon = dv_value.get("longitude", "?")
                precision_val = dv_value.get("precision")
                metadata = (
                    {"precision": precision_val} if precision_val is not None else None
                )
                return f"({lat}, {lon})", metadata
            return str(dv_value), None

        return (str(dv_value), None) if dv_value else (None, None)
