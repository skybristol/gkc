"""SPARQL-driven entity cache builder for Data Distillery Wikibase.

This module builds and reconciles SpiritSafe-style entity cache artifacts from
one authoritative path:

1. Run profile-rooted traversal SPARQL to discover QID/PID identifiers.
2. Fetch raw entity JSON via WikibaseLoader in API-sized batches.
3. Reconcile cache directory content to exactly match discovered identifiers.
4. Produce a deterministic summary payload (optionally written to disk).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional

from gkc.auth import WikiverseAuth
from gkc.mash import WikibaseLoader
from gkc.sparql import SPARQLQuery

_ENTITY_ID_PATTERN = re.compile(r"^[QP]\d+$")


@dataclass(frozen=True)
class WikibaseCacheBuildResult:
    """Result of a full SPARQL-driven cache build and reconciliation."""

    cache_dir: str
    summary_path: Optional[str]
    queried_ids: list[str] = field(default_factory=list)
    fetched_ids: list[str] = field(default_factory=list)
    written_ids: list[str] = field(default_factory=list)
    new_ids: list[str] = field(default_factory=list)
    changed_ids: list[str] = field(default_factory=list)
    unchanged_ids: list[str] = field(default_factory=list)
    deleted_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)
    fetched_at: str = ""


def build_entity_profile_identifiers_sparql_query(
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
    profile_class_id: str = "Q3",
) -> str:
    """Build SPARQL query used to derive profile-linked DD entity identifiers."""
    base_uri = wikibase_base_uri.rstrip("/")
    return f"""PREFIX wd: <{base_uri}/entity/>
PREFIX wdt: <{base_uri}/prop/direct/>

SELECT ?s ?p ?o WHERE {{
    ?root wdt:P1 wd:{profile_class_id} .
    ?root (wdt:P1|wdt:P2)* ?s .
    ?s ?p ?o .
    FILTER(isIRI(?s) && isIRI(?p) && isIRI(?o))
    FILTER( !STRSTARTS(STR(?o), \"{base_uri}/entity/statement/\") )
}}"""


def extract_entity_profile_identifiers(
    rows: list[dict[str, Any]],
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
) -> list[str]:
    """Extract sorted unique local Q/P identifiers from traversal SPARQL rows."""
    base_uri = wikibase_base_uri.rstrip("/")
    found: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        for field_name in ("s", "p", "o"):
            uri = _extract_binding_value(row.get(field_name))
            entity_id = _extract_local_entity_id(uri, base_uri)
            if entity_id:
                found.add(entity_id)

    return sorted(found)


def build_wikibase_cache(
    *,
    sparql_endpoint: str,
    api_url: str,
    cache_dir: str | Path,
    wikibase_base_uri: str = "https://datadistillery.wikibase.cloud",
    profile_class_id: str = "Q3",
    source_endpoint: Optional[str] = None,
    workflow_mode: str = "cache-builder",
    summary_output: Optional[str | Path] = None,
    loader: Optional[WikibaseLoader] = None,
    auth: Optional[WikiverseAuth] = None,
) -> WikibaseCacheBuildResult:
    """Build and reconcile entity cache using SPARQL-derived QID/PID identifiers."""
    query = build_entity_profile_identifiers_sparql_query(
        wikibase_base_uri=wikibase_base_uri,
        profile_class_id=profile_class_id,
    )
    rows = _run_sparql(sparql_endpoint, query)
    discovered_ids = extract_entity_profile_identifiers(rows, wikibase_base_uri)

    active_loader = loader or WikibaseLoader(api_url=api_url, auth=auth)
    fetched_entities = active_loader.load_entities_raw(discovered_ids)

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    extractor_version = _get_installed_gkc_version()

    new_ids: list[str] = []
    changed_ids: list[str] = []
    unchanged_ids: list[str] = []
    written_ids: list[str] = []
    missing_ids: list[str] = []

    for entity_id in discovered_ids:
        entity_data = fetched_entities.get(entity_id)
        if not isinstance(entity_data, dict) or not entity_data:
            missing_ids.append(entity_id)
            continue

        out_file = cache_path / f"{entity_id}.json"
        existing_entity = _read_existing_entity_payload(out_file)

        if existing_entity is None:
            new_ids.append(entity_id)
        elif existing_entity == entity_data:
            unchanged_ids.append(entity_id)
        else:
            changed_ids.append(entity_id)

        payload_doc = {
            "entity_id": entity_id,
            "entity": entity_data,
            "metadata": {
                "source_endpoint": source_endpoint or api_url,
                "workflow_mode": workflow_mode,
                "profile_entry_ids": [],
                "graph_fetched_at": fetched_at,
                "cache_exported_at": fetched_at,
                "extractor": "gkc.wikibase.cache.build_wikibase_cache",
                "extractor_version": extractor_version,
            },
        }
        out_file.write_text(json.dumps(payload_doc, indent=2), encoding="utf-8")
        written_ids.append(entity_id)

    discovered_set = set(discovered_ids)
    deleted_ids: list[str] = []
    for existing_path in cache_path.glob("*.json"):
        match = _ENTITY_ID_PATTERN.fullmatch(existing_path.stem)
        if match and existing_path.stem not in discovered_set:
            existing_path.unlink()
            deleted_ids.append(existing_path.stem)

    summary_payload = {
        "metadata": {
            "source_endpoint": source_endpoint or api_url,
            "sparql_endpoint": sparql_endpoint,
            "wikibase_base_uri": wikibase_base_uri.rstrip("/"),
            "profile_class_id": profile_class_id,
            "workflow_mode": workflow_mode,
            "fetched_at": fetched_at,
            "cache_dir": str(cache_path.resolve()),
        },
        "summary": {
            "queried_count": len(discovered_ids),
            "fetched_count": len(fetched_entities),
            "written_count": len(written_ids),
            "new_count": len(new_ids),
            "changed_count": len(changed_ids),
            "unchanged_count": len(unchanged_ids),
            "missing_count": len(missing_ids),
            "deleted_count": len(deleted_ids),
        },
        "queried_ids": discovered_ids,
        "fetched_ids": sorted(fetched_entities.keys()),
        "written_ids": sorted(written_ids),
        "new_ids": sorted(new_ids),
        "changed_ids": sorted(changed_ids),
        "unchanged_ids": sorted(unchanged_ids),
        "missing_ids": sorted(missing_ids),
        "deleted_ids": sorted(deleted_ids),
    }

    summary_path: Optional[str] = None
    if summary_output:
        summary_file = Path(summary_output)
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        summary_path = str(summary_file.resolve())

    return WikibaseCacheBuildResult(
        cache_dir=str(cache_path.resolve()),
        summary_path=summary_path,
        queried_ids=summary_payload["queried_ids"],
        fetched_ids=summary_payload["fetched_ids"],
        written_ids=summary_payload["written_ids"],
        new_ids=summary_payload["new_ids"],
        changed_ids=summary_payload["changed_ids"],
        unchanged_ids=summary_payload["unchanged_ids"],
        deleted_ids=summary_payload["deleted_ids"],
        missing_ids=summary_payload["missing_ids"],
        fetched_at=fetched_at,
    )


def _extract_binding_value(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        nested = value.get("value")
        return nested if isinstance(nested, str) else None
    if isinstance(value, str):
        return value
    return str(value)


def _extract_local_entity_id(uri: Optional[str], base_uri: str) -> Optional[str]:
    if not uri or not uri.startswith(base_uri):
        return None
    if f"{base_uri}/entity/statement/" in uri:
        return None

    candidate = uri.rstrip("/").split("/")[-1]
    if _ENTITY_ID_PATTERN.fullmatch(candidate):
        return candidate
    return None


def _run_sparql(sparql_endpoint: str, query: str) -> list[dict[str, Any]]:
    executor = SPARQLQuery(endpoint=sparql_endpoint)
    try:
        return executor.to_dict_list(query)
    except Exception:
        raw = executor.query(query, format="json", raw=True)
        parsed: dict[str, Any] = json.loads(raw)
        bindings = parsed.get("results", {}).get("bindings", [])
        return bindings if isinstance(bindings, list) else []


def _read_existing_entity_payload(file_path: Path) -> Optional[dict[str, Any]]:
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if isinstance(payload, dict):
        entity = payload.get("entity")
        if isinstance(entity, dict):
            return entity
    return {}


def _get_installed_gkc_version() -> str:
    try:
        return importlib_metadata.version("gkc")
    except Exception:
        return "unknown"
