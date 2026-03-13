"""Data Distillery Wikibase ontology snapshot and resolution utilities.

This module provides two complementary extraction layers:

1. Ontology Index (SPARQL-derived): A lightweight discovery layer that identifies
   all classified items and properties in the Wikibase by QID/PID. Used as input
   to item JSON fetching.

2. Profile Graph (item JSON): Full authoritative records for all nodes reachable
   from a set of GKC Entity Profile items, including all statement items,
   primitive property items, and their guidance texts in all stored languages.

Named after the spirit safe: a locked cabinet for reviewing the ontology before
it's used in production workflows.
"""

from __future__ import annotations

import json
import subprocess
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from gkc.mash import WikibaseApiClient
from gkc.sparql import SPARQLQuery

# ---------------------------------------------------------------------------
# Ontology Index (SPARQL-derived)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DDOntologyIndex:
    """SPARQL-derived index of all classified items and properties in DD Wikibase.

    Provides a fast discovery layer for identifying which item IDs exist and how
    they are classified. Used as input to profile graph traversal.

    Attributes:
        items: QID → {label, class_id, class_label, uri} for all entity items.
        properties: PID → {label, class_id, class_label, uri} for all properties.
        class_index: Class label → list of QIDs/PIDs belonging to that class.
        fetched_at: ISO 8601 timestamp.
    """

    items: dict[str, dict] = field(default_factory=dict)
    properties: dict[str, dict] = field(default_factory=dict)
    class_index: dict[str, list[str]] = field(default_factory=dict)
    fetched_at: str = ""

    def get_ids_for_class(self, class_label: str) -> list[str]:
        """Return QIDs/PIDs of all items/properties in the given class."""
        return list(self.class_index.get(class_label, []))


# ---------------------------------------------------------------------------
# Profile Graph (item JSON)
# ---------------------------------------------------------------------------


@dataclass
class DDProfileGraph:
    """Full item JSON for all nodes reachable from one or more profile roots.

    Built by fetching item JSON and traversing internal entity links
    breadth-first until closure. All language variants are preserved exactly
    as stored in the Wikibase.

    Attributes:
        raw_items: QID/PID → full wbgetentities item JSON.
        profile_ids: Root QIDs that are GKC Entity Profile items (P1 → Q3).
        traversal_log: Diagnostic messages: missing items, language fallbacks.
        fetched_at: ISO 8601 timestamp.
    """

    raw_items: dict[str, dict[str, Any]] = field(default_factory=dict)
    profile_ids: list[str] = field(default_factory=list)
    traversal_log: list[str] = field(default_factory=list)
    fetched_at: str = ""


@dataclass
class DDProfileCacheExportResult:
    """Result of exporting a profile graph to SpiritSafe-style cache artifacts.

    Attributes:
        cache_dir: Absolute cache directory path used for export.
        written_ids: Entity IDs successfully written as cache files.
        skipped_ids: Entity IDs skipped (for example denylist/ignore list).
        graph: Source profile graph used to produce cache artifacts.
    """

    cache_dir: str
    written_ids: list[str] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    graph: DDProfileGraph = field(default_factory=DDProfileGraph)


# ---------------------------------------------------------------------------
# SPARQL query builders
# ---------------------------------------------------------------------------


def build_discovery_sparql_query(
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
) -> str:
    """Build the comprehensive discovery SPARQL query.

    Returns all items classified under any subclass of Q1 (Entity), plus all
    properties with P1 class assignments. One operation yields the complete
    QID/PID inventory for subsequent item JSON fetches.

    Args:
        wikibase_base_uri: Base URI for entity references.

    Returns:
        SPARQL query string.
    """
    base_uri = wikibase_base_uri.rstrip("/")
    return f"""PREFIX wd: <{base_uri}/entity/>
PREFIX wdt: <{base_uri}/prop/direct/>

SELECT ?item ?itemLabel ?class ?classLabel
WHERE {{
  {{
    ?class wdt:P2* wd:Q1 .
    ?item wdt:P1 ?class .
  }}
  UNION
  {{
    ?item wikibase:directClaim ?x ;
          wdt:P1 ?class .
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""


def build_profile_ids_sparql_query(
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
    profile_class_id: str = "Q3",
) -> str:
    """Build a simple SPARQL query to find all GKC Entity Profile item IDs.

    Args:
        wikibase_base_uri: Base URI for entity references.
        profile_class_id: QID of the GKC Entity Profile class (default: Q3).

    Returns:
        SPARQL query string.
    """
    base_uri = wikibase_base_uri.rstrip("/")
    return f"""PREFIX wd: <{base_uri}/entity/>
PREFIX wdt: <{base_uri}/prop/direct/>

SELECT ?profile WHERE {{
  ?profile wdt:P1 wd:{profile_class_id} .
}}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_binding_value(value: object) -> Optional[str]:
    """Extract scalar value from SPARQL binding or plain dict row value."""
    if value is None:
        return None
    if isinstance(value, dict):
        inner = value.get("value")
        return inner if isinstance(inner, str) else None
    if isinstance(value, str):
        return value
    return str(value)


def _run_sparql(sparql_endpoint: str, query: str) -> list[dict]:
    """Execute a SPARQL query and return rows as a list of plain dicts."""
    executor = SPARQLQuery(endpoint=sparql_endpoint)
    try:
        return executor.to_dict_list(query)
    except Exception:
        raw_str: str = executor.query(query, format="json", raw=True)
        parsed: dict = json.loads(raw_str)
        return parsed.get("results", {}).get("bindings", [])


def _collect_snak_entity_id(snak: dict, found: set[str]) -> None:
    """Extract entity ID from a snak if it carries a wikibase-entityid datavalue."""
    if not isinstance(snak, dict):
        return
    datavalue = snak.get("datavalue", {})
    if not isinstance(datavalue, dict):
        return
    if datavalue.get("type") != "wikibase-entityid":
        return
    value = datavalue.get("value", {})
    if isinstance(value, dict):
        entity_id = value.get("id")
        if isinstance(entity_id, str) and entity_id:
            found.add(entity_id)


def _collect_internal_item_ids(item_json: dict) -> set[str]:
    """Collect all internal entity IDs referenced in an item's claims.

    Traverses main snaks and qualifier snaks for wikibase-entityid datavalues.
    These always refer to items/properties within the same Wikibase instance
    (cross-Wikibase references use string/external-id datatypes).

    Args:
        item_json: Full item JSON from wbgetentities.

    Returns:
        Set of QID/PID strings found in claims and qualifiers.
    """
    found: set[str] = set()
    claims = item_json.get("claims", {})
    for _prop_id, statement_list in claims.items():
        if not isinstance(statement_list, list):
            continue
        for statement in statement_list:
            if not isinstance(statement, dict):
                continue
            _collect_snak_entity_id(statement.get("mainsnak", {}), found)
            qualifiers = statement.get("qualifiers", {})
            for qual_snaks in qualifiers.values():
                if isinstance(qual_snaks, list):
                    for snak in qual_snaks:
                        _collect_snak_entity_id(snak, found)
    return found


def _check_language_presence(
    item_json: dict,
    item_id: str,
    language: str,
    graph: "DDProfileGraph",
) -> None:
    """Warn and log if the configured default language is absent from item labels."""
    if language == "mul":
        return
    labels = item_json.get("labels", {})
    if labels and language not in labels:
        warnings.warn(
            f"Default language '{language}' absent from item {item_id} labels. "
            f"Falling back to 'mul'.",
            stacklevel=4,
        )
        graph.traversal_log.append(
            f"language_fallback: {item_id} has no '{language}' label, using 'mul'"
        )


# ---------------------------------------------------------------------------
# SPARQL fetch functions
# ---------------------------------------------------------------------------


def fetch_ontology_index(
    sparql_endpoint: str,
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
) -> DDOntologyIndex:
    """Fetch the full ontology discovery index via SPARQL.

    Runs the combined items+properties discovery query, returning all QIDs and
    PIDs with their class assignments in a single SPARQL operation.

    Args:
        sparql_endpoint: SPARQL endpoint URL.
        wikibase_base_uri: Base URI for entity references.

    Returns:
        DDOntologyIndex with all classified items and properties.
    """
    query = build_discovery_sparql_query(wikibase_base_uri)
    rows = _run_sparql(sparql_endpoint, query)

    items: dict[str, dict] = {}
    properties: dict[str, dict] = {}
    class_index: dict[str, list[str]] = {}

    for row in rows:
        item_uri = _extract_binding_value(row.get("item"))
        item_label = _extract_binding_value(row.get("itemLabel"))
        class_uri = _extract_binding_value(row.get("class"))
        class_label = _extract_binding_value(row.get("classLabel"))

        if not item_uri:
            continue

        item_id = item_uri.rstrip("/").split("/")[-1]
        class_id = class_uri.rstrip("/").split("/")[-1] if class_uri else ""

        entry = {
            "label": item_label or "",
            "class_id": class_id,
            "class_label": class_label or "",
            "uri": item_uri,
        }

        if item_id.startswith("Q"):
            items[item_id] = entry
        elif item_id.startswith("P"):
            properties[item_id] = entry

        if class_label and item_id:
            bucket = class_index.setdefault(class_label, [])
            if item_id not in bucket:
                bucket.append(item_id)

    return DDOntologyIndex(
        items=items,
        properties=properties,
        class_index=class_index,
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )


def fetch_profile_ids(
    sparql_endpoint: str,
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
    profile_class_id: str = "Q3",
) -> list[str]:
    """Return bare QIDs for all items classified as GKC Entity Profile.

    A targeted alternative to fetch_ontology_index() when only profile IDs
    are needed as the starting point for graph traversal.

    Args:
        sparql_endpoint: SPARQL endpoint URL.
        wikibase_base_uri: Base URI for entity references.
        profile_class_id: QID of the GKC Entity Profile class (default: Q3).

    Returns:
        List of QID strings (e.g., ["Q100", "Q101"]).
    """
    query = build_profile_ids_sparql_query(wikibase_base_uri, profile_class_id)
    rows = _run_sparql(sparql_endpoint, query)
    ids = []
    for row in rows:
        uri = _extract_binding_value(row.get("profile"))
        if uri:
            qid = uri.rstrip("/").split("/")[-1]
            if qid.startswith("Q"):
                ids.append(qid)
    return ids


# ---------------------------------------------------------------------------
# Item JSON fetch and graph traversal
# ---------------------------------------------------------------------------


def fetch_profile_graph(
    profile_ids: list[str],
    api_client: WikibaseApiClient,
    default_language: str = "mul",
    max_hops: int = 5,
) -> DDProfileGraph:
    """Fetch full item JSON for all nodes reachable from profile items.

    Performs a breadth-first traversal from each profile ID, following all
    internal wikibase-entityid links in claims and qualifiers until no new
    IDs are discovered or max_hops is reached.

    All language variants are preserved exactly as stored. If default_language
    is absent from an item's labels, a warning is emitted and the traversal
    log records the fallback.

    Args:
        profile_ids: QIDs of GKC Entity Profile items to start from.
        api_client: WikibaseApiClient configured for the target Wikibase.
        default_language: Package default language for diagnostic checks.
        max_hops: Safety limit on traversal depth (default: 5).

    Returns:
        DDProfileGraph with all reachable item JSON and traversal diagnostics.
    """
    graph = DDProfileGraph(
        profile_ids=list(profile_ids),
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )
    if not profile_ids:
        return graph

    visited: set[str] = set()
    frontier: set[str] = set(profile_ids)
    hop = 0

    while frontier and hop < max_hops:
        to_fetch = frontier - visited
        if not to_fetch:
            break

        fetched = api_client.get_entities(list(to_fetch))
        for entity_id, entity_data in fetched.items():
            graph.raw_items[entity_id] = entity_data
            _check_language_presence(entity_data, entity_id, default_language, graph)

        missing = to_fetch - set(fetched.keys())
        for mid in sorted(missing):
            graph.traversal_log.append(f"missing: {mid} not returned by wbgetentities")

        visited.update(to_fetch)

        next_frontier: set[str] = set()
        for entity_data in fetched.values():
            next_frontier.update(_collect_internal_item_ids(entity_data))
        frontier = next_frontier - visited
        hop += 1

    if hop >= max_hops and frontier:
        graph.traversal_log.append(
            f"traversal stopped at hop limit ({max_hops}); "
            f"{len(frontier)} unvisited IDs remain"
        )

    return graph


def export_profile_graph_to_entity_cache(
    profile_ids: list[str],
    api_client: WikibaseApiClient,
    cache_dir: str | Path,
    *,
    default_language: str = "mul",
    max_hops: int = 5,
    source_endpoint: Optional[str] = None,
    workflow_mode: str = "profile-entry",
    ignore_ids: Optional[set[str]] = None,
) -> DDProfileCacheExportResult:
    """Export profile-linked entity JSON into per-entity cache files.

    Uses ``fetch_profile_graph`` to collect all linked entities from one or more
    profile roots, then writes deterministic JSON artifacts keyed by entity ID
    into a single cache namespace.

    Args:
        profile_ids: Root profile QIDs used as traversal entry points.
        api_client: Wikibase API client for wbgetentities reads.
        cache_dir: Output directory for cache files (one ``<ID>.json`` per entity).
        default_language: Default language for diagnostics during traversal.
        max_hops: Maximum traversal depth.
        source_endpoint: Optional Wikibase API/SPARQL endpoint identifier.
        workflow_mode: Export context (for example ``profile-entry``).
        ignore_ids: Optional entity IDs to skip during export.

    Returns:
        DDProfileCacheExportResult with written/skipped IDs and source graph.
    """
    graph = fetch_profile_graph(
        profile_ids=profile_ids,
        api_client=api_client,
        default_language=default_language,
        max_hops=max_hops,
    )

    ignore_set = set(ignore_ids or set())
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    source_repo_path = Path(__file__).resolve().parents[2]
    source_branch, source_commit = _get_git_context(source_repo_path)
    extractor_version = _get_installed_gkc_version()

    written_ids: list[str] = []
    skipped_ids: list[str] = []
    exported_at = datetime.utcnow().isoformat() + "Z"

    for entity_id in sorted(graph.raw_items.keys()):
        if entity_id in ignore_set:
            skipped_ids.append(entity_id)
            continue

        payload = {
            "entity_id": entity_id,
            "entity": graph.raw_items[entity_id],
            "metadata": {
                "source_endpoint": source_endpoint or api_client.api_url,
                "workflow_mode": workflow_mode,
                "profile_entry_ids": list(profile_ids),
                "graph_fetched_at": graph.fetched_at,
                "cache_exported_at": exported_at,
                "extractor": "gkc.wikibase.ontology.export_profile_graph_to_entity_cache",
                "extractor_version": extractor_version,
                "source_branch": source_branch,
                "source_commit": source_commit,
            },
        }

        out_file = cache_path / f"{entity_id}.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written_ids.append(entity_id)

    return DDProfileCacheExportResult(
        cache_dir=str(cache_path.resolve()),
        written_ids=written_ids,
        skipped_ids=skipped_ids,
        graph=graph,
    )


def _get_git_context(repo_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Return git branch and commit for a repository path when available."""
    try:
        branch_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        commit_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return branch_result.stdout.strip(), commit_result.stdout.strip()
    except Exception:
        return None, None


def _get_installed_gkc_version() -> str:
    """Return installed package version when available."""
    try:
        return importlib_metadata.version("gkc")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Language and text resolution
# ---------------------------------------------------------------------------


def get_label_for_language(
    item_json: dict,
    language: str,
    default_language: str = "mul",
) -> Optional[str]:
    """Get item label for the requested language, with fallback.

    Language keys are returned exactly as stored (Wikibase rules the process).
    Falls back to default_language if requested language is absent.

    Args:
        item_json: Full item JSON from wbgetentities.
        language: Requested language code.
        default_language: Fallback language if requested is absent.

    Returns:
        Label string or None if not available in any language.
    """
    labels = item_json.get("labels", {})
    if language in labels:
        return labels[language].get("value")
    if language != default_language and default_language in labels:
        return labels[default_language].get("value")
    for lang_data in labels.values():
        return lang_data.get("value")
    return None


def get_monolingualtext_for_language(
    claims: list[dict],
    language: str,
    default_language: str = "mul",
) -> Optional[str]:
    """Get monolingual text value for a language from a property's claim list.

    Used for guidance and prompt properties (P185-P190, P168-P171) which use
    the monolingualtext Wikibase datatype. Each statement carries one language.

    Falls back to default_language if the requested language is not found.
    Language keys are preserved exactly as stored.

    Args:
        claims: List of claim dicts for one property (item_json["claims"][PID]).
        language: Requested language code.
        default_language: Fallback language (typically "mul").

    Returns:
        Text string or None if not found at any language level.
    """
    preferred: Optional[str] = None
    fallback: Optional[str] = None

    for statement in claims:
        mainsnak = statement.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        if datavalue.get("type") != "monolingualtext":
            continue
        value = datavalue.get("value", {})
        text = value.get("text")
        lang = value.get("language")
        if lang == language:
            preferred = text
        elif lang == default_language and fallback is None:
            fallback = text

    return preferred if preferred is not None else fallback


def _get_qualifier_monolingualtext_for_language(
    claim: dict,
    qualifier_prop_id: str,
    language: str,
    default_language: str = "mul",
) -> Optional[str]:
    """Get monolingualtext qualifier value for one property and language.

    Args:
        claim: Statement claim dict that may contain qualifiers.
        qualifier_prop_id: Qualifier PID to inspect.
        language: Requested language code.
        default_language: Fallback language.

    Returns:
        Text value when present; otherwise None.
    """
    qualifiers = claim.get("qualifiers", {})
    qualifier_snaks = qualifiers.get(qualifier_prop_id, [])
    if not isinstance(qualifier_snaks, list):
        return None

    preferred: Optional[str] = None
    fallback: Optional[str] = None

    for snak in qualifier_snaks:
        if not isinstance(snak, dict):
            continue
        datavalue = snak.get("datavalue", {})
        if not isinstance(datavalue, dict):
            continue
        if datavalue.get("type") != "monolingualtext":
            continue

        value = datavalue.get("value", {})
        if not isinstance(value, dict):
            continue

        text = value.get("text")
        lang = value.get("language")
        if not isinstance(text, str) or not isinstance(lang, str):
            continue

        if lang == language:
            preferred = text
        elif lang == default_language and fallback is None:
            fallback = text

    return preferred if preferred is not None else fallback


# ---------------------------------------------------------------------------
# Guidance precedence resolution
# ---------------------------------------------------------------------------


def resolve_statement_guidance(
    graph: DDProfileGraph,
    statement_item_id: str,
    guidance_prop_id: str,
    language: str = "mul",
    default_language: str = "mul",
    primitive_item_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve guidance text with fallback precedence.

    Precedence:
    1. Statement item guidance — the GKC Entity Statement item's own guidance
       claims (most specific shared context, reused across profiles).
    2. Primitive property item guidance — the linked primitive property item
       (e.g., statement type property), used as general datatype-level fallback.

    Note: Profile-level statement guidance override (via qualifiers on P157
    claims in a profile item) is pending confirmation of the Wikibase qualifier
    model. Once validated against live data this function will gain a third
    precedence level above statement item guidance.

    Args:
        graph: DDProfileGraph containing all fetched item JSON.
        statement_item_id: QID of the GKC Entity Statement item.
        guidance_prop_id: PID of the guidance property (e.g., "P169").
        language: Requested language code.
        default_language: Fallback language.
        primitive_item_id: Optional QID/PID of the linked primitive property item.

    Returns:
        Guidance text string or None if not found at any level.
    """
    statement_item = graph.raw_items.get(statement_item_id)
    if statement_item:
        claims = statement_item.get("claims", {}).get(guidance_prop_id, [])
        text = get_monolingualtext_for_language(claims, language, default_language)
        if text:
            return text

    if primitive_item_id:
        primitive_item = graph.raw_items.get(primitive_item_id)
        if primitive_item:
            claims = primitive_item.get("claims", {}).get(guidance_prop_id, [])
            return get_monolingualtext_for_language(claims, language, default_language)

    return None


def resolve_profile_statement_guidance(
    graph: DDProfileGraph,
    profile_item_id: str,
    statement_item_id: str,
    guidance_prop_id: str,
    language: str = "mul",
    default_language: str = "mul",
    primitive_item_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve statement guidance with profile-level qualifier override precedence.

    Precedence:
    1. Profile-level qualifier text on matching P157 claim.
    2. Statement item guidance claim.
    3. Primitive/template item guidance claim.

    Args:
        graph: DDProfileGraph containing fetched item JSON.
        profile_item_id: QID of the GKC Entity Profile item.
        statement_item_id: QID of the linked GKC Entity Statement item.
        guidance_prop_id: PID for the guidance channel (e.g., P171, P170, P169, P168).
        language: Requested language code.
        default_language: Fallback language.
        primitive_item_id: Optional QID/PID for primitive/template fallback guidance.

    Returns:
        Guidance text string or None if absent at all levels.
    """
    profile_item = graph.raw_items.get(profile_item_id)
    if profile_item:
        p157_claims = profile_item.get("claims", {}).get("P157", [])
        if isinstance(p157_claims, list):
            for claim in p157_claims:
                if not isinstance(claim, dict):
                    continue

                mainsnak = claim.get("mainsnak", {})
                if not isinstance(mainsnak, dict):
                    continue
                datavalue = mainsnak.get("datavalue", {})
                if not isinstance(datavalue, dict):
                    continue
                if datavalue.get("type") != "wikibase-entityid":
                    continue

                value = datavalue.get("value", {})
                if not isinstance(value, dict):
                    continue

                if value.get("id") != statement_item_id:
                    continue

                qualifier_text = _get_qualifier_monolingualtext_for_language(
                    claim,
                    qualifier_prop_id=guidance_prop_id,
                    language=language,
                    default_language=default_language,
                )
                if qualifier_text:
                    return qualifier_text

    return resolve_statement_guidance(
        graph=graph,
        statement_item_id=statement_item_id,
        guidance_prop_id=guidance_prop_id,
        language=language,
        default_language=default_language,
        primitive_item_id=primitive_item_id,
    )
