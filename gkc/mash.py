"""
Mash: Load data from various sources as templates for processing.

The Mash stage loads data from diverse sources (Wikidata items, CSV files,
JSON APIs, dataframes, etc.) as templates, allowing users to view, filter,
and export them in various formats for further processing.

Current implementations:
- Wikidata items: Load existing items as templates for bulk modification

Future implementations:
- CSV files: Parse CSV data into template format
- JSON APIs: Fetch and transform API responses
- Dataframes: Process in-memory data structures

Plain meaning: Load source data and prepare it for distillery processing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import requests

from gkc.recipe import EntityCatalog


class DataTemplate(Protocol):
    """Abstract interface for all data templates in the mash module.

    All template types (Wikidata, CSV, JSON, etc.) should implement this
    protocol to ensure consistent behavior across different data sources.

    This protocol defines the minimum interface that templates must provide:
    - summary(): Return a dict with basic metadata about the template
    - to_dict(): Serialize the template to a dictionary

    Future template implementations should follow this pattern to ensure
    compatibility with formatters and other downstream components.

    Plain meaning: The blueprint that all data templates must follow.
    """

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        ...


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


@dataclass
class WikidataTemplate:
    """An extracted Wikidata item ready for filtering and export.

    This is the Wikidata-specific implementation of the DataTemplate protocol.

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

    def filter_languages(self, languages: Optional[str | list[str]] = None) -> None:
        """Filter labels, descriptions, and aliases to specified languages.

        Args:
            languages: Either:
                - A single language code (e.g., "en")
                - A list of language codes (e.g., ["en", "es", "fr"])
                - The string "all" to keep all languages
                - None to use the package-level language configuration

        Plain meaning: Keep only the specified language versions.
        """
        import gkc

        if languages is None:
            languages = gkc.get_languages()

        # If "all", don't filter anything
        if languages == "all":
            return

        # Convert single string to list for uniform handling
        if isinstance(languages, str):
            languages = [languages]

        # Filter each field
        self.labels = {k: v for k, v in self.labels.items() if k in languages}
        self.descriptions = {
            k: v for k, v in self.descriptions.items() if k in languages
        }
        self.aliases = {k: v for k, v in self.aliases.items() if k in languages}

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


class WikidataLoader:
    """Load a Wikidata item as a template for bulk modification.

    This is the Wikidata-specific implementation of a data loader.
    Future loaders for CSV, JSON APIs, etc. should follow a similar pattern.

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

    def load(self, qid: str) -> WikidataTemplate:
        """Load a Wikidata item and return it as a template.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            WikidataTemplate with the item's structure.

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

    def _build_template(
        self, qid: str, entity_data: dict[str, Any]
    ) -> WikidataTemplate:
        """Convert entity data to a WikidataTemplate.

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

        return WikidataTemplate(
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
                claim = WikidataLoader._statement_to_claim(prop_id, statement)
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
        value = WikidataLoader._snak_to_value(mainsnak)

        if value is None:
            return None

        # Extract qualifiers with their values
        qualifiers = statement.get("qualifiers", {})
        qualifiers_list = []
        for prop, snaks in qualifiers.items():
            if snaks:
                # Extract value from the first snak of each qualifier property
                snak = snaks[0]
                qual_value = WikidataLoader._snak_to_value(snak)
                if qual_value:
                    qualifiers_list.append({"property": prop, "value": qual_value})

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
        )

    @staticmethod
    def _snak_to_value(snak: dict[str, Any]) -> Optional[str]:
        """Extract a human-readable value from a snak.

        Plain meaning: Get a simple string representation of the value.
        """

        snaktype = snak.get("snaktype", "value")

        if snaktype == "novalue":
            return "[no value]"
        if snaktype == "somevalue":
            return "[unknown value]"

        datavalue = snak.get("datavalue")
        if not datavalue:
            return None

        dv_type = datavalue.get("type", "")
        dv_value = datavalue.get("value")

        if dv_type == "wikibase-entityid":
            if isinstance(dv_value, dict):
                return dv_value.get("id", "[entity]")
            return str(dv_value)

        if dv_type == "quantity":
            if isinstance(dv_value, dict):
                return dv_value.get("amount", "[quantity]")
            return str(dv_value)

        if dv_type == "time":
            if isinstance(dv_value, dict):
                return dv_value.get("time", "[time]")
            return str(dv_value)

        if dv_type == "monolingualtext":
            if isinstance(dv_value, dict):
                return dv_value.get("text", "[text]")
            return str(dv_value)

        if dv_type == "string":
            return str(dv_value)

        if dv_type == "globecoordinate":
            if isinstance(dv_value, dict):
                lat = dv_value.get("latitude", "?")
                lon = dv_value.get("longitude", "?")
                return f"({lat}, {lon})"
            return str(dv_value)

        return str(dv_value) if dv_value else None
