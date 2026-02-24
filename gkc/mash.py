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

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Union

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

        Plain meaning: Return the original entity JSON for round-trip safety.
        """
        ...


def fetch_property_labels(
    property_ids: list[str], language: Optional[str] = None
) -> dict[str, str]:
    """Fetch human-readable labels for Wikidata properties using EntityCatalog.

    Args:
        property_ids: List of property IDs (e.g., ['P31', 'P21']).
        language: Language code for labels (defaults to package configuration).

    Returns:
        Dict mapping property IDs to their labels (e.g., {'P31': 'instance of'}).

    Plain meaning: Look up property names efficiently to make QS output more readable.
    """
    if not property_ids:
        return {}
    if language is None:
        import gkc

        languages = gkc.get_languages()
        if languages == "all":
            language = "en"
        elif isinstance(languages, str):
            language = languages
        else:
            language = languages[0] if languages else "en"
    catalog = EntityCatalog()
    results = catalog.fetch_entities(property_ids)
    return {pid: entry.get_label(language) for pid, entry in results.items()}


def strip_entity_identifiers(entity_data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of entity data with identifiers stripped for new-item use.

    Removes fields that prevent using the JSON as a new item template:
    - Item-level: id, pageid, lastrevid, modified, ns, title
    - Statement-level: id (statement GUID)
    - Snak-level: hash (in mainsnak, qualifiers, and references)

    Plain meaning: Remove IDs that prevent using the JSON as a new item template.
    """

    cleaned = copy.deepcopy(entity_data)

    # Remove item-level identifiers and metadata
    cleaned.pop("id", None)
    cleaned.pop("pageid", None)
    cleaned.pop("lastrevid", None)
    cleaned.pop("modified", None)
    cleaned.pop("ns", None)
    cleaned.pop("title", None)

    # Remove statement-level identifiers and hashes
    claims = cleaned.get("claims")
    if isinstance(claims, dict):
        for statements in claims.values():
            if not isinstance(statements, list):
                continue
            for statement in statements:
                if isinstance(statement, dict):
                    statement.pop("id", None)

                    # Remove hash from mainsnak
                    mainsnak = statement.get("mainsnak")
                    if isinstance(mainsnak, dict):
                        mainsnak.pop("hash", None)

                    # Remove hash from qualifiers
                    qualifiers = statement.get("qualifiers")
                    if isinstance(qualifiers, dict):
                        for qualifier_snaks in qualifiers.values():
                            if isinstance(qualifier_snaks, list):
                                for snak in qualifier_snaks:
                                    if isinstance(snak, dict):
                                        snak.pop("hash", None)

                    # Remove hash from references
                    references = statement.get("references")
                    if isinstance(references, list):
                        for reference in references:
                            if isinstance(reference, dict):
                                reference.pop("hash", None)
                                ref_snaks = reference.get("snaks")
                                if isinstance(ref_snaks, dict):
                                    for ref_snak_list in ref_snaks.values():
                                        if isinstance(ref_snak_list, list):
                                            for snak in ref_snak_list:
                                                if isinstance(snak, dict):
                                                    snak.pop("hash", None)

    return cleaned


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
    entity_data: dict[str, Any]

    def filter_properties(
        self,
        include_properties: Optional[list[str]] = None,
        exclude_properties: Optional[list[str]] = None,
    ) -> None:
        """Filter properties from the template in-place.

        Plain meaning: Keep only specified properties, then drop excluded ones.
        """

        if include_properties:
            include_set = set(include_properties)
            self.claims = [
                claim for claim in self.claims if claim.property_id in include_set
            ]
            claims = self.entity_data.get("claims")
            if isinstance(claims, dict):
                self.entity_data["claims"] = {
                    prop_id: statements
                    for prop_id, statements in claims.items()
                    if prop_id in include_set
                }

        if exclude_properties:
            exclude_set = set(exclude_properties)
            self.claims = [
                claim for claim in self.claims if claim.property_id not in exclude_set
            ]
            claims = self.entity_data.get("claims")
            if isinstance(claims, dict):
                self.entity_data["claims"] = {
                    prop_id: statements
                    for prop_id, statements in claims.items()
                    if prop_id not in exclude_set
                }

    def filter_qualifiers(self) -> None:
        """Remove all qualifiers from claims in-place.

        Plain meaning: Strip qualifier detail from claims.
        """

        for claim in self.claims:
            claim.qualifiers = []

        claims = self.entity_data.get("claims")
        if isinstance(claims, dict):
            for statements in claims.values():
                if not isinstance(statements, list):
                    continue
                for statement in statements:
                    if isinstance(statement, dict):
                        statement.pop("qualifiers", None)
                        statement.pop("qualifiers-order", None)

    def filter_references(self) -> None:
        """Remove all references from claims in-place.

        Plain meaning: Strip reference detail from claims.
        """

        for claim in self.claims:
            claim.references = []

        claims = self.entity_data.get("claims")
        if isinstance(claims, dict):
            for statements in claims.values():
                if not isinstance(statements, list):
                    continue
                for statement in statements:
                    if isinstance(statement, dict):
                        statement.pop("references", None)

    def filter_languages(
        self, languages: Optional[Union[str, list[str]]] = None
    ) -> None:
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

        labels = self.entity_data.get("labels")
        if isinstance(labels, dict):
            self.entity_data["labels"] = {
                lang: value for lang, value in labels.items() if lang in languages
            }

        descriptions = self.entity_data.get("descriptions")
        if isinstance(descriptions, dict):
            self.entity_data["descriptions"] = {
                lang: value for lang, value in descriptions.items() if lang in languages
            }

        aliases = self.entity_data.get("aliases")
        if isinstance(aliases, dict):
            self.entity_data["aliases"] = {
                lang: value for lang, value in aliases.items() if lang in languages
            }

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

        return copy.deepcopy(self.entity_data)

    def to_simple_dict(self) -> dict[str, Any]:
        """Serialize to a simplified dictionary.

        Plain meaning: Convert to a compact summary structure.
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

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata to create a shell for new item creation.

        Returns entity data with all system IDs, metadata, and hashes removed,
        suitable for use as a template for creating new items.

        Returns:
            Dict with identifiers stripped, ready for new item creation.

        Plain meaning: Prepare this template as a clean shell for a new item.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_qsv1(
        self, for_new_item: bool = False, entity_labels: Optional[dict[str, str]] = None
    ) -> str:
        """Convert to QuickStatements V1 format.

        Args:
            for_new_item: If True, use CREATE/LAST syntax for new items.
                         If False, use the item's QID for updates.
            entity_labels: Optional dict mapping entity IDs to labels for comments.

        Returns:
            QuickStatements V1 formatted string.

        Plain meaning: Export as QuickStatements commands for bulk operations.
        """
        from gkc.mash_formatters import QSV1Formatter

        formatter = QSV1Formatter(entity_labels=entity_labels or {})
        return formatter.format(self, for_new_item=for_new_item)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Returns:
            Dict representing the GKC Entity Profile.

        Raises:
            NotImplementedError: This transformation is not yet implemented for items.

        Plain meaning: Transform into a GKC Entity Profile (not yet implemented).
        """
        raise NotImplementedError(
            "Item to GKC Entity Profile transformation is not yet implemented. "
            "This will be added in a future version."
        )


@dataclass
class WikidataPropertyTemplate:
    """An extracted Wikidata property ready for filtering and export.

    This is the property-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikidata property template ready for modification.
    """

    pid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    datatype: Optional[str]
    formatter_url: Optional[str]
    entity_data: dict[str, Any]

    def filter_languages(
        self, languages: Optional[Union[str, list[str]]] = None
    ) -> None:
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

        labels = self.entity_data.get("labels")
        if isinstance(labels, dict):
            self.entity_data["labels"] = {
                lang: value for lang, value in labels.items() if lang in languages
            }

        descriptions = self.entity_data.get("descriptions")
        if isinstance(descriptions, dict):
            self.entity_data["descriptions"] = {
                lang: value for lang, value in descriptions.items() if lang in languages
            }

        aliases = self.entity_data.get("aliases")
        if isinstance(aliases, dict):
            self.entity_data["aliases"] = {
                lang: value for lang, value in aliases.items() if lang in languages
            }

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "pid": self.pid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "datatype": self.datatype,
            "formatter_url": self.formatter_url,
            "aliases": self.aliases,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return copy.deepcopy(self.entity_data)

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata to create a shell for new property creation.

        Returns entity data with all system IDs, metadata, and hashes removed,
        suitable for use as a template for creating new properties.

        Returns:
            Dict with identifiers stripped, ready for new property creation.

        Plain meaning: Prepare this template as a clean shell for a new property.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Returns:
            Dict representing the GKC Entity Profile.

        Raises:
            NotImplementedError: This transformation is not yet implemented
                for properties.

        Plain meaning: Transform into a GKC Entity Profile
            (not yet implemented).
        """
        raise NotImplementedError(
            "Property to GKC Entity Profile transformation is not yet implemented. "
            "This will be added in a future version."
        )


@dataclass
class WikidataEntitySchemaTemplate:
    """An extracted Wikidata EntitySchema ready for filtering and export.

    This is the EntitySchema-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikidata EntitySchema template ready for modification.
    """

    eid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    schema_text: str
    entity_data: dict[str, Any]

    def filter_languages(
        self, languages: Optional[Union[str, list[str]]] = None
    ) -> None:
        """Filter labels and descriptions to specified languages.

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

        labels = self.entity_data.get("labels")
        if isinstance(labels, dict):
            self.entity_data["labels"] = {
                lang: value for lang, value in labels.items() if lang in languages
            }

        descriptions = self.entity_data.get("descriptions")
        if isinstance(descriptions, dict):
            self.entity_data["descriptions"] = {
                lang: value for lang, value in descriptions.items() if lang in languages
            }

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "eid": self.eid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "schema_text_length": len(self.schema_text),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return copy.deepcopy(self.entity_data)

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata for new EntitySchema creation.

        Returns entity data with all system IDs and metadata removed,
        suitable for use as a template for creating new EntitySchemas.

        Returns:
            Dict with identifiers stripped, ready for new EntitySchema creation.

        Plain meaning: Prepare this template as a clean shell for a new EntitySchema.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Uses the existing RecipeBuilder logic to generate a profile from
        the EntitySchema's ShEx specification.

        Returns:
            Dict representing the GKC Entity Profile.

        Plain meaning: Transform into a GKC Entity Profile.
        """
        from gkc.recipe import RecipeBuilder

        builder = RecipeBuilder(eid=self.eid)
        builder.schema_text = self.schema_text
        builder.load_specification()
        return builder.generate_gkc_entity_profile()


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

    def load_item(self, qid: str) -> WikidataTemplate:
        """Load a Wikidata item and return it as a template.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            WikidataTemplate with the item's structure.

        Raises:
            RuntimeError: If the item cannot be fetched or parsed.

        Plain meaning: Retrieve the item and return it ready for use.

        Example:
            >>> loader = WikidataLoader()
            >>> template = loader.load_item("Q42")
            >>> print(template.summary())
        """

        entity_data = self.load_entity_data(qid)

        # Convert to MashTemplate
        template = self._build_template(qid, entity_data)

        return template

    def load(self, qid: str) -> WikidataTemplate:
        """Load a Wikidata item and return it as a template.

        .. deprecated:: 1.0
            Use :meth:`load_item` instead. This method is maintained for
            backwards compatibility and will be removed in a future version.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            WikidataTemplate with the item's structure.

        Plain meaning: Retrieve the item and return it ready for use.
        """
        return self.load_item(qid)

    def load_items(self, qids: list[str]) -> dict[str, WikidataTemplate]:
        """Load multiple Wikidata items in batch and return them as templates.

        Uses the wbgetentities API to efficiently fetch multiple items in batches
        of 50. Handles partial failures gracefully.

        Args:
            qids: List of Wikidata item IDs (e.g., ['Q42', 'Q5']).

        Returns:
            Dict mapping QIDs to WikidataTemplates. Only successfully loaded
            items are included in the result.

        Raises:
            RuntimeError: If the API request fails completely.

        Plain meaning: Load multiple items efficiently in batch.

        Example:
            >>> loader = WikidataLoader()
            >>> templates = loader.load_items(["Q42", "Q5", "Q30"])
            >>> print(len(templates))
            3
        """
        if not qids:
            return {}

        result: dict[str, WikidataTemplate] = {}

        # Process in batches of 50 (wbgetentities limit)
        batch_size = 50
        for i in range(0, len(qids), batch_size):
            batch = qids[i : i + batch_size]
            batch_results = self._fetch_entities_batch(batch)

            # Build templates for each successfully fetched entity
            for qid, entity_data in batch_results.items():
                try:
                    template = self._build_template(qid, entity_data)
                    result[qid] = template
                except Exception:
                    # Skip items that fail to parse
                    continue

        return result

    def load_property(self, pid: str) -> WikidataPropertyTemplate:
        """Load a Wikidata property and return it as a template.

        Args:
            pid: The Wikidata property ID (e.g., 'P31').

        Returns:
            WikidataPropertyTemplate with the property's metadata.

        Raises:
            RuntimeError: If the property cannot be fetched or parsed.

        Plain meaning: Retrieve a property definition and return it ready for use.

        Example:
            >>> loader = WikidataLoader()
            >>> prop = loader.load_property("P31")
            >>> print(prop.summary())
        """
        entity_data = self.load_entity_data(pid)
        return self._build_property_template(pid, entity_data)

    def load_properties(self, pids: list[str]) -> dict[str, WikidataPropertyTemplate]:
        """Load multiple Wikidata properties in batch using SPARQL.

        Uses SPARQL queries to efficiently fetch property metadata including
        labels, descriptions, datatype, and formatter URLs.

        Args:
            pids: List of Wikidata property IDs (e.g., ['P31', 'P279']).

        Returns:
            Dict mapping PIDs to WikidataPropertyTemplates.

        Raises:
            RuntimeError: If the SPARQL query fails.

        Plain meaning: Load multiple property definitions efficiently.

        Example:
            >>> loader = WikidataLoader()
            >>> props = loader.load_properties(["P31", "P279", "P21"])
            >>> print(len(props))
            3
        """
        if not pids:
            return {}

        # Use EntityCatalog for efficient SPARQL-based batch fetching
        catalog = EntityCatalog(user_agent=self.user_agent, fetch_property_details=True)
        results = catalog.fetch_entities(pids)

        templates: dict[str, WikidataPropertyTemplate] = {}
        for pid, entry in results.items():
            if pid.startswith("P"):
                # Build template from catalog entry
                templates[pid] = self._build_property_template_from_catalog(pid, entry)

        return templates

    def load_entity_schema(self, eid: str) -> WikidataEntitySchemaTemplate:
        """Load a Wikidata EntitySchema and return it as a template.

        Args:
            eid: The Wikidata EntitySchema ID (e.g., 'E502').

        Returns:
            WikidataEntitySchemaTemplate with the schema content.

        Raises:
            RuntimeError: If the EntitySchema cannot be fetched or parsed.

        Plain meaning: Retrieve an EntitySchema and return it ready for use.

        Example:
            >>> loader = WikidataLoader()
            >>> schema = loader.load_entity_schema("E502")
            >>> print(schema.summary())
        """
        from gkc.cooperage import fetch_entity_schema_json

        entity_data = fetch_entity_schema_json(eid, user_agent=self.user_agent)
        return self._build_entity_schema_template(eid, entity_data)

    def fetch_descriptors(
        self, entity_ids: list[str]
    ) -> dict[str, dict[str, Union[str, dict[str, str]]]]:
        """Fetch basic labels and descriptions for a mix of items and properties.

        This is a lightweight convenience method for getting just labels and
        descriptions without full entity data. Uses SPARQL for efficiency.

        Args:
            entity_ids: List of entity IDs (e.g., ['Q5', 'P31', 'Q30']).

        Returns:
            Dict mapping entity IDs to dicts with `labels` and `descriptions`
            keys, each containing language->value mappings.

        Plain meaning: Quickly look up names and descriptions for any entities.
        """
        if not entity_ids:
            return {}

        catalog = EntityCatalog(user_agent=self.user_agent)
        results = catalog.fetch_entities(entity_ids)

        descriptors: dict[str, dict[str, Union[str, dict[str, str]]]] = {}
        for eid, entry in results.items():
            descriptors[eid] = {
                "labels": entry.labels,
                "descriptions": entry.descriptions,
            }

        return descriptors

    def _fetch_entities_batch(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch multiple entities using wbgetentities API.

        Args:
            entity_ids: List of entity IDs (max 50).

        Returns:
            Dict mapping entity IDs to their entity data.

        Raises:
            RuntimeError: If the API request fails.

        Plain meaning: Fetch a batch of entities from Wikidata.
        """
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": "|".join(entity_ids),
            "format": "json",
        }

        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract entities from response
            entities = data.get("entities", {})

            # Filter out entities with "missing" key (not found)
            return {
                eid: entity_data
                for eid, entity_data in entities.items()
                if "missing" not in entity_data
            }

        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to fetch entities batch: {exc}") from exc

    def load_entity_data(self, qid: str) -> dict[str, Any]:
        """Load raw Wikidata entity data.

        Plain meaning: Return the entity JSON as provided by Wikidata.
        """

        # Fetch the item via Special:EntityData endpoint which returns JSON
        # This is equivalent to wbgetentities but simpler for single-item fetches
        json_text = self._fetch_entity_json(qid)

        # Parse the JSON response from Wikidata
        return self._parse_wikidata_json(json_text, qid)

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
        entity_data: dict[str, Any] = entities.get(qid, {})

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
            entity_data=copy.deepcopy(entity_data),
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

    def _build_property_template(
        self, pid: str, entity_data: dict[str, Any]
    ) -> WikidataPropertyTemplate:
        """Convert entity data to a WikidataPropertyTemplate.

        Plain meaning: Transform API data into our simplified property format.
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

        # Extract property-specific metadata
        datatype = entity_data.get("datatype")

        # Formatter URL is in claims P1630
        formatter_url = None
        claims = entity_data.get("claims", {})
        p1630_statements = claims.get("P1630", [])
        if p1630_statements and isinstance(p1630_statements, list):
            first_statement = p1630_statements[0]
            mainsnak = first_statement.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            if datavalue.get("type") == "string":
                formatter_url = datavalue.get("value")

        return WikidataPropertyTemplate(
            pid=pid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            aliases=aliases_dict,
            datatype=datatype,
            formatter_url=formatter_url,
            entity_data=copy.deepcopy(entity_data),
        )

    def _build_property_template_from_catalog(
        self, pid: str, entry: Any
    ) -> WikidataPropertyTemplate:
        """Build a WikidataPropertyTemplate from an EntityCatalog entry.

        Plain meaning: Convert catalog data into our property template format.
        """
        from gkc.recipe import PropertyLedgerEntry

        if not isinstance(entry, PropertyLedgerEntry):
            raise ValueError(
                f"Expected PropertyLedgerEntry for {pid}, got {type(entry)}"
            )

        # Build minimal entity_data structure
        entity_data = {
            "id": pid,
            "type": "property",
            "datatype": entry.datatype,
            "labels": {
                lang: {"language": lang, "value": label}
                for lang, label in entry.labels.items()
            },
            "descriptions": {
                lang: {"language": lang, "value": desc}
                for lang, desc in entry.descriptions.items()
            },
            "aliases": {
                lang: [{"language": lang, "value": alias} for alias in alias_list]
                for lang, alias_list in entry.aliases.items()
            },
        }

        # Add formatter URL if present
        if entry.formatter_url:
            entity_data["claims"] = {
                "P1630": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "type": "string",
                                "value": entry.formatter_url,
                            }
                        }
                    }
                ]
            }

        return WikidataPropertyTemplate(
            pid=pid,
            labels=entry.labels,
            descriptions=entry.descriptions,
            aliases=entry.aliases,
            datatype=entry.datatype,
            formatter_url=entry.formatter_url,
            entity_data=entity_data,
        )

    def _build_entity_schema_template(
        self, eid: str, entity_data: dict[str, Any]
    ) -> WikidataEntitySchemaTemplate:
        """Convert entity data to a WikidataEntitySchemaTemplate.

        Plain meaning: Transform API data into our simplified EntitySchema format.
        """
        # Extract labels and descriptions
        labels = entity_data.get("labels", {})
        descriptions = entity_data.get("descriptions", {})

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

        # Extract schema text
        schema_text = entity_data.get("schemaText", "")

        return WikidataEntitySchemaTemplate(
            eid=eid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            schema_text=schema_text,
            entity_data=copy.deepcopy(entity_data),
        )

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


@dataclass
class WikipediaTemplate:
    """A Wikipedia template loaded from Wikimedia API for use in Wikipedia editing.

    This is the Wikipedia-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikipedia template ready for display and use
    in editing workflows.
    """

    title: str
    description: str
    params: dict[str, Any]
    param_order: list[str]
    raw_data: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Returns:
            Dict with title, description, and number of parameters.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "title": self.title,
            "description": self.description,
            "param_count": len(self.params),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Returns:
            Dict containing title, description, params, and paramOrder.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return {
            "title": self.title,
            "description": self.description,
            "params": self.params,
            "paramOrder": self.param_order,
        }


class WikipediaLoader:
    """Load Wikipedia templates from Wikimedia API as templates for editing workflows.

    This is the Wikipedia-specific implementation of a data loader.

    Plain meaning: Fetch and parse a Wikipedia template into a usable format.
    """

    def __init__(self, user_agent: Optional[str] = None):
        """Initialize the loader.

        Args:
            user_agent: Custom user agent for Wikimedia API requests.
                       If not provided, a default GKC user agent is used.

        Plain meaning: Set up the loader with optional custom user agent.
        """
        if user_agent is None:
            user_agent = "GKC/1.0 (https://github.com/skybristol/gkc; data integration)"

        self.user_agent = user_agent
        self.base_url = "https://en.wikipedia.org/w/api.php"

    def load_template(self, template_name: str) -> WikipediaTemplate:
        """Load a Wikipedia template and return it as a template.

        Args:
            template_name: The Wikipedia template name (e.g., 'Infobox settlement').

        Returns:
            WikipediaTemplate with the template's structure.

        Raises:
            RuntimeError: If the template cannot be fetched or parsed.

        Plain meaning: Retrieve the template and return it ready for use.

        Example:
            >>> loader = WikipediaLoader()
            >>> template = loader.load_template("Infobox settlement")
            >>> print(template.summary())
        """
        # Fetch template data from Wikimedia API
        params: dict[str, Any] = {
            "action": "templatedata",
            "format": "json",
            "titles": f"Template:{template_name}",
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch template '{template_name}' from Wikimedia API: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Failed to parse JSON response for template '{template_name}': {exc}"
            ) from exc

        # Extract pages from response. The templatedata API returns pages directly,
        # not nested under a "query" key like other Mediawiki APIs.
        pages = data.get("pages", {})
        if not pages:
            raise RuntimeError(
                f"Template '{template_name}' not found in Wikimedia API response"
            )

        # Get the first (and only) page
        page_data = next(iter(pages.values()))

        # Check if this page has template data
        if "notabledescriptions" in page_data or "missing" in page_data:
            raise RuntimeError(
                f"Template '{template_name}' not found or has no template data"
            )

        # Extract required fields
        title = page_data.get("title", template_name)

        # Get description in English, or empty string if not available
        descriptions = page_data.get("description", {})
        if isinstance(descriptions, dict):
            description = descriptions.get("en", "")
        else:
            description = str(descriptions) if descriptions else ""

        params_data = page_data.get("params", {})
        param_order = page_data.get("paramOrder", [])

        # Build and return the template
        return WikipediaTemplate(
            title=title,
            description=description,
            params=params_data,
            param_order=param_order,
            raw_data=page_data,
        )
