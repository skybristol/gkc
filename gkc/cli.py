"""Command line interface for GKC.

Plain meaning: Run GKC tasks from the terminal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import gkc
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth
from gkc.fermenter import validate_semantic_anchor_document
from gkc.mash import (
    WikibaseApiClient,
    WikibaseLoader,
    WikipediaLoader,
    apply_item_property_filters,
    apply_template_language_filter,
    fetch_recent_entity_changes,
    full_sync_wikibase_entity_cache,
    get_latest_cache_timestamp,
    refresh_entity_cache_from_recentchanges,
)
from gkc.runtime_config import (
    DEFAULT_USER_AGENT,
    SpiritSafeLayout,
    discover_wikibase_config_path,
    get_wikibase_runtime_config,
)
from gkc.sitelinks import (
    DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
    export_wikimedia_sites_artifact,
)
from gkc.sparql import execute_sparql, fetch_entity_labels
from gkc.spirit_safe import (
    build_entity_profile_json_documents,
    build_spiritsafe_semantic_anchor_document,
    build_spiritsafe_semantic_anchor_resolver,
    export_entity_profile_json_documents,
    export_spiritsafe_semantic_anchors,
    get_spirit_safe_source,
    list_profiles,
    load_profile,
    load_profile_package,
    resolve_spiritsafe_layout,
    resolve_spiritsafe_wikibase_config,
    validate_packet_structure,
)
from gkc.still_charger import create_curation_packet


class CLIError(Exception):
    """Raised when CLI execution fails.

    Plain meaning: The CLI could not complete the requested command.
    """


def _normalize_global_flag_positions(argv: list[str]) -> list[str]:
    """Allow global flags to be passed after nested subcommands.

    Moves known global flags to the front while preserving relative order,
    so invocations like ``gkc mash qid Q42 --verbose`` are accepted.
    """

    global_flags = {"--json", "--verbose"}
    extracted: list[str] = []
    remaining: list[str] = []

    for token in argv:
        if token in global_flags:
            extracted.append(token)
        else:
            remaining.append(token)

    return extracted + remaining


def main(argv: Optional[list[str]] = None) -> int:
    """Run the GKC CLI.

    Plain meaning: Parse arguments, execute a command, and return an exit code.
    """

    parser = _build_parser()
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    effective_argv = _normalize_global_flag_positions(effective_argv)
    args = parser.parse_args(effective_argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 1

    try:
        output = args.handler(args)
    except CLIError as exc:
        output = {
            "command": getattr(args, "command_path", "unknown"),
            "ok": False,
            "message": str(exc),
            "details": {},
        }

    _emit_output(output, args.json, args.verbose)
    return 0 if output.get("ok") else 1


def _build_parser() -> argparse.ArgumentParser:
    runtime_config = get_wikibase_runtime_config()
    layout = getattr(runtime_config, "spiritsafe_layout", SpiritSafeLayout())

    parser = argparse.ArgumentParser(prog="gkc")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )

    subparsers = parser.add_subparsers(dest="command")

    auth_parser = subparsers.add_parser("auth", help="Authentication helpers")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_target")

    wikiverse_parser = auth_subparsers.add_parser(
        "wikiverse", help="Wikiverse authentication commands"
    )
    wikiverse_subparsers = wikiverse_parser.add_subparsers(dest="wikiverse_command")

    wikiverse_login = wikiverse_subparsers.add_parser(
        "login", help="Login to Wikiverse"
    )
    _add_wikiverse_args(wikiverse_login)
    wikiverse_login.set_defaults(
        handler=_handle_wikiverse_login, command_path="auth.wikiverse.login"
    )

    wikiverse_status = wikiverse_subparsers.add_parser(
        "status", help="Check Wikiverse authentication status"
    )
    _add_wikiverse_args(wikiverse_status)
    wikiverse_status.set_defaults(
        handler=_handle_wikiverse_status, command_path="auth.wikiverse.status"
    )

    wikiverse_token = wikiverse_subparsers.add_parser(
        "token", help="Get a Wikiverse CSRF token"
    )
    _add_wikiverse_args(wikiverse_token)
    wikiverse_token.add_argument(
        "--show-token",
        action="store_true",
        help="Display the full token in output",
    )
    wikiverse_token.set_defaults(
        handler=_handle_wikiverse_token, command_path="auth.wikiverse.token"
    )

    osm_parser = auth_subparsers.add_parser(
        "osm", help="OpenStreetMap authentication commands"
    )
    osm_subparsers = osm_parser.add_subparsers(dest="osm_command")

    osm_login = osm_subparsers.add_parser(
        "login", help="Check OpenStreetMap credentials"
    )
    _add_osm_args(osm_login)
    osm_login.set_defaults(handler=_handle_osm_login, command_path="auth.osm.login")

    osm_status = osm_subparsers.add_parser(
        "status", help="Check OpenStreetMap credential status"
    )
    _add_osm_args(osm_status)
    osm_status.set_defaults(handler=_handle_osm_status, command_path="auth.osm.status")

    # Mash commands for loading Wikidata entities as templates
    mash_parser = subparsers.add_parser(
        "mash", help="Load Wikidata entities as templates"
    )
    mash_subparsers = mash_parser.add_subparsers(dest="mash_command")

    # QID: Load Wikidata items
    mash_qid = mash_subparsers.add_parser("qid", help="Load one or more Wikidata items")
    mash_qid.add_argument("qid", nargs="?", help="The Wikidata item ID (e.g., Q42)")
    mash_qid.add_argument(
        "--qid",
        action="append",
        dest="qids",
        help="Wikidata item ID (repeatable for multiple items)",
    )
    mash_qid.add_argument(
        "--qid-list",
        type=str,
        help="Path to file containing item IDs (one per line)",
    )
    mash_qid.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write output to file instead of stdout",
    )
    mash_qid.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON to stdout (default for single item)",
    )
    mash_qid.add_argument(
        "--summary",
        action="store_true",
        help="Output summary of the item(s)",
    )
    mash_qid.add_argument(
        "--transform",
        choices=["shell", "qsv1", "gkc_entity_profile"],
        help=(
            "Transform the output "
            "(shell=strip IDs, qsv1=QuickStatements, gkc_entity_profile=profile)"
        ),
    )
    mash_qid.add_argument(
        "--include-properties",
        help="Comma-separated list of properties to include (e.g., P31,P21)",
    )
    mash_qid.add_argument(
        "--exclude-properties",
        help="Comma-separated list of properties to exclude (e.g., P31,P21)",
    )
    mash_qid.add_argument(
        "--exclude-qualifiers",
        action="store_true",
        help="Omit qualifiers from output",
    )
    mash_qid.add_argument(
        "--exclude-references",
        action="store_true",
        help="Omit references from output",
    )
    mash_qid.add_argument(
        "--no-entity-labels",
        action="store_false",
        dest="include_entity_labels",
        help="Skip fetching entity labels for QuickStatements comments (faster)",
    )
    mash_qid.set_defaults(
        handler=_handle_mash_qid,
        command_path="mash.qid",
    )

    # PID: Load Wikidata properties
    mash_pid = mash_subparsers.add_parser(
        "pid", help="Load one or more Wikidata properties"
    )
    mash_pid.add_argument("pid", nargs="?", help="The Wikidata property ID (e.g., P31)")
    mash_pid.add_argument(
        "--pid",
        action="append",
        dest="pids",
        help="Wikidata property ID (repeatable for multiple properties)",
    )
    mash_pid.add_argument(
        "--pid-list",
        type=str,
        help="Path to file containing property IDs (one per line)",
    )
    mash_pid.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write output to file instead of stdout",
    )
    mash_pid.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON to stdout (default)",
    )
    mash_pid.add_argument(
        "--summary",
        action="store_true",
        help="Output summary of the property(ies)",
    )
    mash_pid.add_argument(
        "--transform",
        choices=["shell", "gkc_entity_profile"],
        help="Transform the output (shell=strip IDs, gkc_entity_profile=profile)",
    )
    mash_pid.set_defaults(
        handler=_handle_mash_pid,
        command_path="mash.pid",
    )

    # EID: Load Wikidata EntitySchemas
    mash_eid = mash_subparsers.add_parser(
        "eid", help="Load a Wikidata EntitySchema as a template"
    )
    mash_eid.add_argument("eid", help="The Wikidata EntitySchema ID (e.g., E502)")
    mash_eid.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write output to file instead of stdout",
    )
    mash_eid.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON to stdout (default)",
    )
    mash_eid.add_argument(
        "--summary",
        action="store_true",
        help="Output summary of the EntitySchema",
    )
    mash_eid.add_argument(
        "--transform",
        choices=["shell", "gkc_entity_profile"],
        help="Transform the output (shell=strip IDs, gkc_entity_profile=profile)",
    )
    mash_eid.set_defaults(
        handler=_handle_mash_eid,
        command_path="mash.eid",
    )

    # Wikipedia Template: Load a Wikipedia template
    mash_wp_template = mash_subparsers.add_parser(
        "wp_template", help="Load a Wikipedia template"
    )
    mash_wp_template.add_argument(
        "template_name",
        nargs="?",
        help="The Wikipedia template name (e.g., Infobox_settlement)",
    )
    mash_wp_template.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write output to file instead of stdout",
    )
    mash_wp_template.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON response instead of summary",
    )
    mash_wp_template.set_defaults(
        handler=_handle_mash_wp_template,
        command_path="mash.wp_template",
    )

    mash_check_wikibase_revisions = mash_subparsers.add_parser(
        "check-wikibase-revisions",
        help="Check recent MediaWiki revisions affecting Wikibase entities",
    )
    mash_check_wikibase_revisions.add_argument(
        "--api-url",
        help="Override the configured Wikibase API URL (default: META_WB_API_URL env var)",
    )
    mash_check_wikibase_revisions.add_argument(
        "--since",
        help="Explicit recentchanges watermark timestamp (ISO 8601)",
    )
    mash_check_wikibase_revisions.add_argument(
        "--cache-dir",
        help="Optional cache directory used to infer watermark when --since is omitted",
    )
    mash_check_wikibase_revisions.add_argument(
        "--overlap-seconds",
        type=int,
        default=60,
        help="Safety overlap window applied to watermark polling (default: 60)",
    )
    mash_check_wikibase_revisions.add_argument(
        "--ignore-id",
        action="append",
        dest="ignore_ids",
        help="Entity ID to ignore during change discovery (repeatable)",
    )
    mash_check_wikibase_revisions.add_argument(
        "--output",
        help="Optional output path for revision-check summary JSON",
    )
    mash_check_wikibase_revisions.set_defaults(
        handler=_handle_mash_check_wikibase_revisions,
        command_path="mash.check-wikibase-revisions",
    )

    mash_cache_wikibase_revisions = mash_subparsers.add_parser(
        "cache-wikibase-revisions",
        help="Refresh Wikibase entity cache from MediaWiki recentchanges",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--cache-dir",
        required=True,
        help="Directory containing per-entity cache files",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--api-url",
        help="Override the configured Wikibase API URL (default: META_WB_API_URL env var)",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--source-endpoint",
        help="Optional source endpoint label recorded in refreshed cache metadata",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--since",
        help="Explicit recentchanges watermark timestamp (ISO 8601)",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--overlap-seconds",
        type=int,
        default=60,
        help="Safety overlap window applied to watermark polling (default: 60)",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--ignore-id",
        action="append",
        dest="ignore_ids",
        help="Entity ID to ignore during change refresh (repeatable)",
    )
    mash_cache_wikibase_revisions.add_argument(
        "--output",
        help="Optional output path for refresh summary JSON",
    )
    mash_cache_wikibase_revisions.set_defaults(
        handler=_handle_mash_cache_wikibase_revisions,
        command_path="mash.cache-wikibase-revisions",
    )

    mash_full_sync_wikibase = mash_subparsers.add_parser(
        "full-sync-wikibase",
        help="Full-sync baseline: discover and re-cache all entities from a Wikibase instance",
    )
    mash_full_sync_wikibase.add_argument(
        "--cache-dir",
        required=True,
        type=str,
        help="Local directory where cached entity JSON files are stored",
    )
    mash_full_sync_wikibase.add_argument(
        "--api-url",
        type=str,
        help="Wikibase MediaWiki API URL (overrides runtime config)",
    )
    mash_full_sync_wikibase.add_argument(
        "--ignore-id",
        action="append",
        dest="ignore_ids",
        metavar="ID",
        help="Entity ID to skip (may be repeated: --ignore-id Q1 --ignore-id P1)",
    )
    mash_full_sync_wikibase.add_argument(
        "--items-only",
        action="store_true",
        default=False,
        help="Discover and cache items (Q-entities) only",
    )
    mash_full_sync_wikibase.add_argument(
        "--properties-only",
        action="store_true",
        default=False,
        help="Discover and cache properties (P-entities) only",
    )
    mash_full_sync_wikibase.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override API batch size (default: 50 for unauthenticated mash reads)",
    )
    mash_full_sync_wikibase.add_argument(
        "--output",
        type=str,
        help="Optional output path for full-sync result JSON",
    )
    mash_full_sync_wikibase.set_defaults(
        handler=_handle_mash_full_sync_wikibase,
        command_path="mash.full-sync-wikibase",
    )

    # ShEx validation commands
    shex_parser = subparsers.add_parser("shex", help="ShEx validation utilities")
    shex_subparsers = shex_parser.add_subparsers(dest="shex_command")

    shex_validate = shex_subparsers.add_parser(
        "validate", help="Validate RDF data against ShEx schema"
    )
    shex_validate.add_argument(
        "--qid",
        type=str,
        help="Wikidata entity ID (e.g., Q42)",
    )
    shex_validate.add_argument(
        "--eid",
        type=str,
        help="Wikidata EntitySchema ID (e.g., E502)",
    )
    shex_validate.add_argument(
        "--schema-file",
        type=str,
        help="Path to local ShEx schema file",
    )
    shex_validate.add_argument(
        "--rdf-file",
        type=str,
        help="Path to local RDF file",
    )
    shex_validate.add_argument(
        "--user-agent",
        type=str,
        help="Custom user agent for Wikidata requests",
    )
    shex_validate.set_defaults(
        handler=_handle_shex_validate,
        command_path="shex.validate",
    )

    # Profile commands
    profile_parser = subparsers.add_parser("profile", help="Profile utilities")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command")

    profile_export_json = profile_subparsers.add_parser(
        "export-json",
        help="Build JSON entity profiles from SpiritSafe cache entities",
    )
    profile_export_json.add_argument(
        "--cache-entities-dir",
        help=(
            "Directory containing SpiritSafe cache entity JSON files "
            f"(defaults to <local_root>/{layout.entities_path} when using --source local)"
        ),
    )
    profile_export_json.add_argument(
        "--profile-id",
        action="append",
        dest="profile_ids",
        help="Optional profile QID to export (repeatable)",
    )
    profile_export_json.add_argument(
        "-o",
        "--output",
        help=(
            "Output directory for per-profile JSON files "
            "(writes <output>/<QID>.json). If omitted, prints JSON to stdout"
        ),
    )
    profile_export_json.add_argument(
        "--summary-output",
        help=(
            "Optional summary JSON path to write/merge profile export diagnostics "
            f"(defaults to the configured SpiritSafe logs path: {layout.logs_path}/last_run_summary.json)"
        ),
    )
    _add_profile_source_args(profile_export_json)
    profile_export_json.set_defaults(
        handler=_handle_profile_export_json,
        command_path="profile.export_json",
    )

    # New top-level 'wizard' command
    wizard_parser = subparsers.add_parser(
        "wizard", help="Launch the interactive GKC curation wizard (Streamlit UI)"
    )
    wizard_parser.add_argument(
        "--profile",
        required=True,
        help="Profile reference (QID or full profile entity URI)",
    )
    wizard_parser.add_argument(
        "--qid",
        help="Optional Wikidata item ID for editing an existing item",
    )
    wizard_parser.add_argument(
        "--packet",
        help="Path to curation packet JSON file for multi-entity workflow",
    )
    wizard_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Related profile depth when creating packet on-the-fly (default: 1)",
    )
    _add_profile_source_args(wizard_parser)
    wizard_parser.set_defaults(
        handler=_handle_wizard,
        command_path="wizard",
    )

    profile_value_lists = profile_subparsers.add_parser(
        "value-lists", help="Value-list query extraction and hydration utilities"
    )
    profile_value_lists_subparsers = profile_value_lists.add_subparsers(
        dest="profile_value_lists_command"
    )

    profile_value_lists_sync = profile_value_lists_subparsers.add_parser(
        "sync",
        help="Sync talk-page-derived value-list artifacts without SPARQL hydration",
    )
    profile_value_lists_sync.add_argument(
        "--cache-entities-dir",
        help=(
            "Directory containing SpiritSafe cache entity JSON files "
            f"(defaults to <local_root>/{layout.entities_path} when using --source local)"
        ),
    )
    profile_value_lists_sync.add_argument(
        "--queries-dir",
        help=(
            "Directory to write SPARQL query files "
            f"(defaults to <local_root>/{layout.value_list_queries_path} when using --source local)"
        ),
    )
    profile_value_lists_sync.add_argument(
        "--cache-queries-dir",
        help=(
            "Directory to write embedded JSON value-list artifacts "
            f"(defaults to <local_root>/{layout.value_list_cache_path} when using --source local)"
        ),
    )
    profile_value_lists_sync.add_argument(
        "--value-list-id",
        action="append",
        dest="value_list_ids",
        help="Optional value list QID filter (repeatable)",
    )
    profile_value_lists_sync.add_argument(
        "--api-url",
        default=runtime_config.api_url,
        help=(
            "Wikibase API URL used for talk-page retrieval "
            "(default: META_WB_API_URL env var, config file, or Data Distillery API)"
        ),
    )
    profile_value_lists_sync.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue syncing other value lists when one fails",
    )
    _add_profile_source_args(profile_value_lists_sync)
    profile_value_lists_sync.set_defaults(
        handler=_handle_profile_value_lists_sync,
        command_path="profile.value_lists.sync",
    )

    profile_value_lists_hydrate = profile_value_lists_subparsers.add_parser(
        "hydrate",
        help="Sync value-list artifacts and hydrate SPARQL-backed caches",
    )
    profile_value_lists_hydrate.add_argument(
        "--cache-entities-dir",
        help=(
            "Directory containing SpiritSafe cache entity JSON files "
            f"(defaults to <local_root>/{layout.entities_path} when using --source local)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--queries-dir",
        help=(
            "Directory to write SPARQL query files "
            f"(defaults to <local_root>/{layout.value_list_queries_path} when using --source local)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--cache-queries-dir",
        help=(
            "Directory to write hydrated value-list cache JSON "
            f"(defaults to <local_root>/{layout.value_list_cache_path} when using --source local)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--value-list-id",
        action="append",
        dest="value_list_ids",
        help="Optional value list QID filter (repeatable)",
    )
    profile_value_lists_hydrate.add_argument(
        "--api-url",
        default=runtime_config.api_url,
        help=(
            "Wikibase API URL used for talk-page retrieval "
            "(default: META_WB_API_URL env var, config file, or Data Distillery API)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--endpoint",
        default=runtime_config.sparql_endpoint,
        help=(
            "SPARQL endpoint URL used for hydration "
            "(default: META_WB_SPARQL_ENDPOINT env var, config file, or Wikidata Query Service)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Query page size for pagination (default: 1000)",
    )
    profile_value_lists_hydrate.add_argument(
        "--max-results",
        type=int,
        help="Maximum total results per value list query",
    )
    profile_value_lists_hydrate.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue hydrating other value lists when one fails",
    )
    _add_profile_source_args(profile_value_lists_hydrate)
    profile_value_lists_hydrate.set_defaults(
        handler=_handle_profile_value_lists_hydrate,
        command_path="profile.value_lists.hydrate",
    )

    # Profile package commands
    profile_package = profile_subparsers.add_parser(
        "package", help="Profile package operations"
    )
    profile_package_subparsers = profile_package.add_subparsers(
        dest="profile_package_command"
    )

    profile_package_load = profile_package_subparsers.add_parser(
        "load", help="Load a profile package with dependencies"
    )
    profile_package_load.add_argument(
        "--profile",
        required=True,
        help="Profile ID to load",
    )
    profile_package_load.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Depth of related profiles to include (default: 1)",
    )
    _add_profile_source_args(profile_package_load)
    profile_package_load.set_defaults(
        handler=_handle_profile_package_load,
        command_path="profile.package.load",
    )

    profile_package_validate = profile_package_subparsers.add_parser(
        "validate", help="Validate profile package structure"
    )
    profile_package_validate.add_argument(
        "--profile",
        required=True,
        help="Profile ID to validate",
    )
    profile_package_validate.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Depth of related profiles to include (default: 1)",
    )
    _add_profile_source_args(profile_package_validate)
    profile_package_validate.set_defaults(
        handler=_handle_profile_package_validate,
        command_path="profile.package.validate",
    )

    # Registry commands
    registry_parser = subparsers.add_parser(
        "registry", help="SpiritSafe registry operations"
    )
    registry_subparsers = registry_parser.add_subparsers(dest="registry_command")

    registry_list = registry_subparsers.add_parser(
        "list", help="List all profiles in the registry"
    )
    _add_profile_source_args(registry_list)
    registry_list.set_defaults(
        handler=_handle_registry_list,
        command_path="registry.list",
    )

    registry_info = registry_subparsers.add_parser(
        "info", help="Show detailed profile metadata"
    )
    registry_info.add_argument(
        "--profile",
        required=True,
        help="Profile ID to show info for",
    )
    _add_profile_source_args(registry_info)
    registry_info.set_defaults(
        handler=_handle_registry_info,
        command_path="registry.info",
    )

    registry_validate = registry_subparsers.add_parser(
        "validate", help="Validate registry profile structure"
    )
    _add_profile_source_args(registry_validate)
    registry_validate.set_defaults(
        handler=_handle_registry_validate,
        command_path="registry.validate",
    )

    wikibase_parser = subparsers.add_parser(
        "wikibase", help="Wikibase seed bootstrap and preview operations"
    )
    wikibase_subparsers = wikibase_parser.add_subparsers(dest="wikibase_command")

    wikibase_init = wikibase_subparsers.add_parser(
        "init",
        help=("Preview the Wikibase seed compilation and dry-run baseline plan"),
    )
    wikibase_init.add_argument(
        "--api-url",
        default=runtime_config.api_url,
        help=(
            "Override the configured Wikibase API URL when live comparison is used "
            "(default: META_WB_API_URL env var, config file, or Data Distillery API)"
        ),
    )
    wikibase_init.add_argument(
        "--local-root",
        help=(
            "Optional local SpiritSafe root used to load and validate semantic anchors "
            "for live comparison"
        ),
    )
    wikibase_init.add_argument(
        "--artifact-file",
        help=(
            "Optional semantic_anchors.json artifact used for live comparison; "
            "when provided without --local-root it is loaded directly"
        ),
    )
    wikibase_init.add_argument(
        "--show-entity",
        help=(
            "Optional seed entity key or internal name identifier whose compiled payload "
            "should be included in the output"
        ),
    )
    wikibase_init.add_argument(
        "--language",
        help=(
            "Optional override for the package-level language used for labels, descriptions, "
            "and aliases in the compiled seed preview"
        ),
    )
    wikibase_init.set_defaults(
        handler=_handle_wikibase_init,
        command_path="wikibase.init",
    )

    spiritsafe_parser = subparsers.add_parser(
        "spiritsafe", help="SpiritSafe artifact operations"
    )
    spiritsafe_subparsers = spiritsafe_parser.add_subparsers(dest="spiritsafe_command")

    spiritsafe_sitelinks = spiritsafe_subparsers.add_parser(
        "sitelinks", help="Build SpiritSafe sitelink source artifacts"
    )
    spiritsafe_sitelinks_subparsers = spiritsafe_sitelinks.add_subparsers(
        dest="spiritsafe_sitelinks_command"
    )

    spiritsafe_sitelinks_sync = spiritsafe_sitelinks_subparsers.add_parser(
        "sync-wikimedia-sites",
        help="Fetch Wikimedia sitematrix and write sitelink source cache artifact",
    )
    spiritsafe_sitelinks_sync.add_argument(
        "--source-url",
        default=DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
        help="Wikimedia sitematrix URL (default: API endpoint with smstate=all)",
    )
    spiritsafe_sitelinks_sync.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds for sitematrix fetch (default: 30)",
    )
    spiritsafe_sitelinks_sync.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for sitematrix fetch",
    )
    spiritsafe_sitelinks_sync.add_argument(
        "-o",
        "--output",
        help=(
            "Optional output path for artifact JSON "
            f"(default: <local_root>/{layout.wikimedia_sites_path})"
        ),
    )
    _add_profile_source_args(spiritsafe_sitelinks_sync)
    spiritsafe_sitelinks_sync.set_defaults(
        handler=_handle_spiritsafe_sitelinks_sync_wikimedia_sites,
        command_path="spiritsafe.sitelinks.sync-wikimedia-sites",
    )

    spiritsafe_semantic_anchors = spiritsafe_subparsers.add_parser(
        "semantic-anchors", help="Build SpiritSafe semantic anchor artifacts"
    )
    spiritsafe_semantic_anchors_subparsers = spiritsafe_semantic_anchors.add_subparsers(
        dest="spiritsafe_semantic_anchors_command"
    )

    spiritsafe_semantic_anchors_build = (
        spiritsafe_semantic_anchors_subparsers.add_parser(
            "build",
            help="Build semantic anchor metadata from local SpiritSafe cache entities",
        )
    )
    spiritsafe_semantic_anchors_build.add_argument(
        "-o",
        "--output",
        help=(
            "Optional output path for artifact JSON "
            f"(default: <local_root>/{layout.semantic_anchors_path}; "
            "SpiritSafe workflows may override this)"
        ),
    )
    _add_profile_source_args(spiritsafe_semantic_anchors_build)
    spiritsafe_semantic_anchors_build.set_defaults(
        handler=_handle_spiritsafe_semantic_anchors_build,
        command_path="spiritsafe.semantic-anchors.build",
    )

    spiritsafe_semantic_anchors_validate = spiritsafe_semantic_anchors_subparsers.add_parser(
        "validate",
        help="Validate semantic anchors against the package-owned Wikibase seed contract",
    )
    spiritsafe_semantic_anchors_validate.add_argument(
        "--artifact-file",
        help=(
            "Path to an existing semantic_anchors.json artifact "
            f"(defaults to <local_root>/{layout.semantic_anchors_path} when --local-root is provided)"
        ),
    )
    spiritsafe_semantic_anchors_validate.add_argument(
        "--local-root",
        help=(
            "Optional local SpiritSafe root used to locate the default artifact path "
            "and optionally rebuild current semantic anchors from cache"
        ),
    )
    spiritsafe_semantic_anchors_validate.add_argument(
        "--check-current-cache",
        action="store_true",
        help=(
            "Compare the artifact against a freshly rebuilt semantic-anchor document "
            "from the current local cache"
        ),
    )
    spiritsafe_semantic_anchors_validate.set_defaults(
        handler=_handle_spiritsafe_semantic_anchors_validate,
        command_path="spiritsafe.semantic-anchors.validate",
    )

    # Packet commands
    packet_parser = subparsers.add_parser("packet", help="Curation packet operations")
    packet_subparsers = packet_parser.add_subparsers(dest="packet_command")

    packet_create = packet_subparsers.add_parser(
        "create", help="Create a curation packet"
    )
    packet_create.add_argument(
        "--profile",
        required=True,
        help="Primary profile ID for the packet",
    )
    packet_create.add_argument(
        "--mode",
        choices=["single", "bulk"],
        default="single",
        help="Operation mode: single or bulk (default: single)",
    )
    packet_create.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Related profile depth for bulk mode (default: 1)",
    )
    packet_create.add_argument(
        "-o",
        "--output",
        help="Write packet to file (JSON) instead of stdout",
    )
    _add_profile_source_args(packet_create)
    packet_create.set_defaults(
        handler=_handle_packet_create,
        command_path="packet.create",
    )

    packet_info = packet_subparsers.add_parser(
        "info", help="Show packet metadata and summary"
    )
    packet_info.add_argument(
        "--packet-file",
        required=True,
        help="Path to packet JSON file",
    )
    packet_info.set_defaults(
        handler=_handle_packet_info,
        command_path="packet.info",
    )

    packet_validate = packet_subparsers.add_parser(
        "validate", help="Validate packet structure"
    )
    packet_validate.add_argument(
        "--packet-file",
        required=True,
        help="Path to packet JSON file",
    )
    packet_validate.set_defaults(
        handler=_handle_packet_validate,
        command_path="packet.validate",
    )

    packet_build = packet_subparsers.add_parser(
        "build", help="Build a curation packet from a JSON Entity Profile"
    )
    packet_build.add_argument(
        "--profile",
        required=True,
        help="Profile QID (e.g., Q4) or full entity URI",
    )
    packet_build.add_argument(
        "-o",
        "--output",
        help="Write packet to file (JSON) instead of stdout",
    )
    _add_profile_source_args(packet_build)
    packet_build.set_defaults(
        handler=_handle_packet_build,
        command_path="packet.build",
    )

    packet_charge = packet_subparsers.add_parser(
        "charge", help="Charge a curation packet with Wikidata item data"
    )
    packet_charge.add_argument(
        "--packet-file",
        help="Path to curation packet JSON file",
    )
    packet_charge.add_argument(
        "--profile",
        help="Profile QID or URI to create and charge in one call",
    )
    packet_charge.add_argument(
        "--include-linked-profiles",
        action="store_true",
        help="Include directly linked profiles during packet creation",
    )
    packet_charge.add_argument(
        "--source",
        choices=["wikidata", "local"],
        default="wikidata",
        help="Data source: wikidata or local file (default: wikidata)",
    )
    packet_charge.add_argument(
        "--qid",
        help="Wikidata QID to charge packet with (for source=wikidata)",
    )
    packet_charge.add_argument(
        "--mapping-file",
        help="JSON file mapping entity IDs/profile keys to QIDs (optional)",
    )
    packet_charge.add_argument(
        "-o",
        "--output",
        help="Write charged packet to file (JSON) instead of stdout",
    )
    _add_profile_source_args(
        packet_charge,
        source_flag="--profile-source",
        source_dest="profile_source",
        local_root_flag="--profile-local-root",
        local_root_dest="profile_local_root",
        repo_flag="--profile-repo",
        repo_dest="profile_repo",
        ref_flag="--profile-ref",
        ref_dest="profile_github_ref",
    )
    packet_charge.set_defaults(
        handler=_handle_packet_charge,
        command_path="packet.charge",
    )

    return parser


def _add_wikiverse_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for credentials if not found",
    )
    parser.add_argument(
        "--api-url",
        help="Override the Wikiverse API URL",
    )


def _add_osm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for credentials if not found",
    )


def _add_profile_source_args(
    parser: argparse.ArgumentParser,
    *,
    source_flag: str = "--source",
    source_dest: str = "source",
    local_root_flag: str = "--local-root",
    local_root_dest: str = "local_root",
    repo_flag: str = "--repo",
    repo_dest: str = "repo",
    ref_flag: str = "--ref",
    ref_dest: str = "github_ref",
) -> None:
    """Add SpiritSafe source override args for profile-loading commands."""
    parser.add_argument(
        source_flag,
        dest=source_dest,
        choices=["github", "local"],
        help="Override SpiritSafe source mode for this command",
    )
    parser.add_argument(
        local_root_flag,
        dest=local_root_dest,
        help="Local SpiritSafe root (required with --source local)",
    )
    parser.add_argument(
        repo_flag,
        dest=repo_dest,
        help="GitHub repo slug when --source github (e.g., owner/SpiritSafe)",
    )
    parser.add_argument(
        ref_flag,
        dest=ref_dest,
        help="Git reference when --source github (default: main)",
    )


def _apply_source_override(
    args: argparse.Namespace,
    *,
    source_attr: str = "source",
    local_root_attr: str = "local_root",
    repo_attr: str = "repo",
    ref_attr: str = "github_ref",
) -> tuple[Any, bool]:
    """Apply temporary SpiritSafe source override from CLI args."""
    previous_source = gkc.get_spirit_safe_source()
    source_value = getattr(args, source_attr, None)
    source_overridden = source_value is not None

    if source_overridden:
        if source_value == "local":
            local_root = getattr(args, local_root_attr, None)
            if not local_root:
                raise CLIError("--local-root is required when --source local")
            gkc.set_spirit_safe_source(mode="local", local_root=local_root)
        else:
            repo_value = getattr(args, repo_attr, None)
            ref_value = getattr(args, ref_attr, None)
            gkc.set_spirit_safe_source(
                mode="github",
                github_repo=repo_value or previous_source.github_repo,
                github_ref=ref_value or previous_source.github_ref,
            )

    return previous_source, source_overridden


def _restore_source_override(previous_source: Any, source_overridden: bool) -> None:
    """Restore previous SpiritSafe source config after a temporary override."""
    if source_overridden:
        gkc.set_spirit_safe_source(
            mode=previous_source.mode,
            github_repo=previous_source.github_repo,
            github_ref=previous_source.github_ref,
            local_root=previous_source.local_root,
        )


def _resolve_local_spiritsafe_layout(local_root: Path):
    return resolve_spiritsafe_layout(local_root)


def _infer_local_spiritsafe_root_from_cache_entities_dir(
    cache_entities_dir: Path,
) -> Optional[Path]:
    cache_dir = cache_entities_dir.expanduser().resolve()

    config_path = discover_wikibase_config_path(start_dir=cache_dir)
    if config_path is not None:
        candidate_root = (
            config_path.parent.parent
            if config_path.parent.name == "config"
            else config_path.parent
        )
        layout = _resolve_local_spiritsafe_layout(candidate_root)
        if layout.entities_dir(candidate_root) == cache_dir:
            return candidate_root

    if cache_dir.name == "entities" and cache_dir.parent.name == "cache":
        return cache_dir.parent.parent

    return None


def _preferred_profile_text(values: Any) -> str:
    """Pick a curator-facing string from a multilingual profile text map."""

    if not isinstance(values, dict):
        return ""
    for language in ("mul", "en"):
        value = values.get(language)
        if isinstance(value, str) and value:
            return value
    for value in values.values():
        if isinstance(value, str) and value:
            return value
    return ""


def _handle_wikiverse_login(args: argparse.Namespace) -> dict[str, Any]:
    auth = WikiverseAuth(interactive=args.interactive, api_url=args.api_url)

    try:
        auth.login()
    except AuthenticationError as exc:
        raise CLIError(str(exc)) from exc

    return {
        "command": args.command_path,
        "ok": True,
        "message": "Login successful",
        "details": {
            "authenticated": auth.is_authenticated(),
            "logged_in": auth.is_logged_in(),
            "api_url": auth.api_url,
        },
    }


def _handle_wikiverse_status(args: argparse.Namespace) -> dict[str, Any]:
    auth = WikiverseAuth(interactive=False, api_url=args.api_url)

    details = {
        "authenticated": auth.is_authenticated(),
        "logged_in": auth.is_logged_in(),
        "api_url": auth.api_url,
    }

    ok = details["authenticated"]
    message = "Credentials present" if ok else "Credentials missing"

    if ok:
        try:
            auth.login()
            auth.get_csrf_token()
            details["token_ok"] = True
            message = "Credentials and token validated"
        except AuthenticationError:
            details["token_ok"] = False
            ok = False
            message = "Token validation failed"

    return {
        "command": args.command_path,
        "ok": ok,
        "message": message,
        "details": details,
    }


def _handle_wikiverse_token(args: argparse.Namespace) -> dict[str, Any]:
    auth = WikiverseAuth(interactive=args.interactive, api_url=args.api_url)

    try:
        auth.login()
        token = auth.get_csrf_token()
    except AuthenticationError as exc:
        raise CLIError(str(exc)) from exc

    token_value = token if args.show_token else "<redacted>"

    return {
        "command": args.command_path,
        "ok": True,
        "message": "CSRF token obtained",
        "details": {
            "token": token_value,
            "api_url": auth.api_url,
        },
    }


def _handle_osm_login(args: argparse.Namespace) -> dict[str, Any]:
    auth = OpenStreetMapAuth(interactive=args.interactive)

    ok = auth.is_authenticated()
    message = "Credentials present" if ok else "Credentials missing"

    return {
        "command": args.command_path,
        "ok": ok,
        "message": message,
        "details": {
            "authenticated": ok,
        },
    }


def _handle_osm_status(args: argparse.Namespace) -> dict[str, Any]:
    auth = OpenStreetMapAuth(interactive=False)

    ok = auth.is_authenticated()
    message = "Credentials present" if ok else "Credentials missing"

    return {
        "command": args.command_path,
        "ok": ok,
        "message": message,
        "details": {
            "authenticated": ok,
        },
    }


def _read_id_list(filepath: str) -> list[str]:
    """Read a list of entity IDs from a file.

    Args:
        filepath: Path to file with one ID per line.

    Returns:
        List of entity IDs with whitespace stripped.

    Raises:
        CLIError: If file cannot be read.

    Plain meaning: Load IDs from a file for batch processing.
    """
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
        # Strip whitespace and filter out empty lines and comments
        ids = [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        return ids
    except FileNotFoundError:
        raise CLIError(f"ID list file not found: {filepath}")
    except Exception as exc:
        raise CLIError(f"Failed to read ID list from {filepath}: {exc}")


def _handle_mash_qid(args: argparse.Namespace) -> dict[str, Any]:
    """Handle mash qid subcommand: load and display Wikidata items."""
    # Collect all QIDs from various sources
    qids = []
    if args.qid:  # Positional argument
        qids.append(args.qid)
    if getattr(args, "qids", None):  # --qid flags
        qids.extend(args.qids)
    if args.qid_list:  # --qid-list file
        qids.extend(_read_id_list(args.qid_list))

    if not qids:
        raise CLIError("No QIDs specified. Provide at least one QID.")

    # Remove duplicates while preserving order
    seen = set()
    qids = [qid for qid in qids if not (qid in seen or seen.add(qid))]  # type: ignore[func-returns-value]

    # Parse filter options
    include_properties = []
    exclude_properties = []
    if args.include_properties:
        include_properties = [p.strip() for p in args.include_properties.split(",")]
    if args.exclude_properties:
        exclude_properties = [p.strip() for p in args.exclude_properties.split(",")]

    try:
        loader = WikibaseLoader()

        # Load items (single or batch)
        if len(qids) == 1:
            templates = {qids[0]: loader.load_item(qids[0])}
        else:
            templates = loader.load_items(qids)

        # Apply filters to all templates
        for template in templates.values():
            apply_template_language_filter(template)
            if include_properties or exclude_properties:
                apply_item_property_filters(
                    template,
                    include_properties=include_properties,
                    exclude_properties=exclude_properties,
                )
            if args.exclude_qualifiers:
                template.filter_qualifiers()
            if args.exclude_references:
                template.filter_references()

        # Check if --summary was requested
        if getattr(args, "summary", False):
            # Output summary for each template
            summaries = [template.summary() for template in templates.values()]
            output_data = summaries if len(summaries) > 1 else summaries[0]
        else:
            # Handle transformation
            transform = getattr(args, "transform", None)

            if transform == "shell":
                # Strip identifiers for new item creation
                output_data = (
                    [template.to_shell() for template in templates.values()]
                    if len(templates) > 1
                    else templates[qids[0]].to_shell()
                )
            elif transform == "qsv1":
                # Convert to QuickStatements V1
                entity_labels = {}
                if getattr(args, "include_entity_labels", True):
                    entity_ids = set()
                    for template in templates.values():
                        for claim in template.claims:
                            entity_ids.add(claim.property_id)
                            if (
                                claim.value.startswith("Q")
                                and claim.value[1:].isdigit()
                            ):
                                entity_ids.add(claim.value)
                            if not args.exclude_qualifiers:
                                for qual in claim.qualifiers:
                                    qual_prop = qual.get("property", "")
                                    qual_val = qual.get("value", "")
                                    if qual_prop:
                                        entity_ids.add(qual_prop)
                                    if (
                                        qual_val.startswith("Q")
                                        and qual_val[1:].isdigit()
                                    ):
                                        entity_ids.add(qual_val)

                    if entity_ids:
                        try:
                            languages = gkc.get_languages()
                            language = (
                                "en"
                                if languages == "all"
                                else (
                                    languages
                                    if isinstance(languages, str)
                                    else languages[0] if languages else "en"
                                )
                            )
                            entity_labels = fetch_entity_labels(
                                list(entity_ids), languages=[language]
                            )
                        except Exception as exc:
                            raise CLIError(
                                f"Failed to fetch entity labels: {exc}. "
                                "Use --no-entity-labels to skip."
                            ) from exc

                qs_outputs: list[str] = []
                for qid in qids:
                    if qid in templates:
                        qs_text = templates[qid].to_qsv1(
                            for_new_item=False, entity_labels=entity_labels
                        )
                        qs_outputs.append(qs_text)

                qs_outputs_str: str = (
                    "\n\n".join(qs_outputs) if len(qs_outputs) > 1 else qs_outputs[0]
                )
                output_data = qs_outputs_str  # type: ignore[assignment]
            elif transform == "gkc_entity_profile":
                raise CLIError(
                    "Item to GKC Entity Profile transformation is not yet implemented."
                )
            else:
                # No transformation - output raw JSON
                output_data = (
                    [template.to_dict() for template in templates.values()]
                    if len(templates) > 1
                    else templates[qids[0]].to_dict()
                )

        # Handle output (file or stdout)
        if args.output:
            # Write to file
            with open(args.output, "w") as f:
                if isinstance(output_data, str):
                    f.write(output_data)
                else:
                    json.dump(output_data, f, indent=2)
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Wrote output for {len(qids)} item(s) to {args.output}",
                "details": {"q ids": qids, "output_file": args.output},
            }
        else:
            # Print to stdout
            if isinstance(output_data, str):
                print(output_data)
            else:
                print(json.dumps(output_data, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Output for {len(qids)} item(s)",
                "details": {"qids": qids},
            }

    except Exception as exc:
        raise CLIError(f"Failed to process items: {exc}") from exc


def _handle_mash_pid(args: argparse.Namespace) -> dict[str, Any]:
    """Handle mash pid subcommand: load and display Wikidata properties."""
    # Collect all PIDs from various sources
    pids = []
    if args.pid:  # Positional argument
        pids.append(args.pid)
    if getattr(args, "pids", None):  # --pid flags
        pids.extend(args.pids)
    if args.pid_list:  # --pid-list file
        pids.extend(_read_id_list(args.pid_list))

    if not pids:
        raise CLIError("No PIDs specified. Provide at least one PID.")

    # Remove duplicates while preserving order
    seen = set()
    pids = [pid for pid in pids if not (pid in seen or seen.add(pid))]  # type: ignore[func-returns-value]

    try:
        loader = WikibaseLoader()

        # Load properties individually (batch loading removed with EntityCatalog)
        templates = {}
        for pid in pids:
            templates[pid] = loader.load_property(pid)

        # Apply filters to all templates
        for template in templates.values():
            apply_template_language_filter(template)

        # Check if --summary was requested
        if getattr(args, "summary", False):
            # Output summary for each template
            summaries = [template.summary() for template in templates.values()]
            output_data = summaries if len(summaries) > 1 else summaries[0]
        else:
            # Handle transformation
            transform = getattr(args, "transform", None)

            if transform == "shell":
                # Strip identifiers for new property creation
                output_data = (
                    [template.to_shell() for template in templates.values()]
                    if len(templates) > 1
                    else templates[pids[0]].to_shell()
                )
            elif transform == "gkc_entity_profile":
                raise CLIError(
                    "Property to GKC Entity Profile transformation is "
                    "not yet implemented."
                )
            else:
                # No transformation - output raw JSON
                output_data = (
                    [template.to_dict() for template in templates.values()]
                    if len(templates) > 1
                    else templates[pids[0]].to_dict()
                )

        # Handle output (file or stdout)
        if args.output:
            # Write to file
            with open(args.output, "w") as f:
                if isinstance(output_data, str):
                    f.write(output_data)
                else:
                    json.dump(output_data, f, indent=2)
            return {
                "command": args.command_path,
                "ok": True,
                "message": (
                    f"Wrote output for {len(pids)} property/properties "
                    f"to {args.output}"
                ),
                "details": {"pids": pids, "output_file": args.output},
            }
        else:
            # Print to stdout
            if isinstance(output_data, str):
                print(output_data)
            else:
                print(json.dumps(output_data, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Output for {len(pids)} property/properties",
                "details": {"pids": pids},
            }

    except Exception as exc:
        raise CLIError(f"Failed to process properties: {exc}") from exc


def _handle_mash_eid(args: argparse.Namespace) -> dict[str, Any]:
    """Handle mash eid subcommand: load and display Wikidata EntitySchema."""
    eid = args.eid
    transform = getattr(args, "transform", None)

    try:
        loader = WikibaseLoader()
        template = loader.load_entity_schema(eid)

        # Apply filters
        apply_template_language_filter(template)

        # Check if --summary was requested
        if getattr(args, "summary", False):
            output_data = template.summary()
        else:
            # Handle transformation
            transform = getattr(args, "transform", None)

            if transform == "shell":
                # Strip identifiers for new EntitySchema creation
                output_data = template.to_shell()
            elif transform == "gkc_entity_profile":
                # Convert to GKC Entity Profile
                output_data = template.to_gkc_entity_profile()
            else:
                # No transformation - output raw JSON
                output_data = template.to_dict()

        # Handle output (file or stdout)
        if args.output:
            # Write to file
            with open(args.output, "w") as f:
                if isinstance(output_data, str):
                    f.write(output_data)
                else:
                    json.dump(output_data, f, indent=2)
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Wrote EntitySchema {eid} to {args.output}",
                "details": {"eid": eid, "output_file": args.output},
            }
        else:
            # Print to stdout
            if isinstance(output_data, str):
                print(output_data)
            else:
                print(json.dumps(output_data, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Output for EntitySchema {eid}",
                "details": {"eid": eid},
            }

    except Exception as exc:
        raise CLIError(f"Failed to process EntitySchema {eid}: {exc}") from exc


def _handle_mash_wp_template(args: argparse.Namespace) -> dict[str, Any]:
    """Handle mash wp_template subcommand: load and display Wikipedia template."""
    template_name = args.template_name

    if not template_name:
        raise CLIError(
            "Template name is required. "
            "Provide a Wikipedia template name (e.g., Infobox_settlement)."
        )

    try:
        loader = WikipediaLoader()
        template = loader.load_template(template_name)

        # Determine output format: --raw or summary (default)
        if args.raw:
            output_data = template.to_dict()
        else:
            output_data = template.summary()

        # Handle output (file or stdout)
        if args.output:
            # Write to file
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            return {
                "command": args.command_path,
                "ok": True,
                "message": (
                    f"Wrote Wikipedia template '{template_name}' to {args.output}"
                ),
                "details": {
                    "template_name": template_name,
                    "output_file": args.output,
                },
            }
        else:
            # Print to stdout
            print(json.dumps(output_data, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Output for Wikipedia template '{template_name}'",
                "details": {"template_name": template_name},
            }

    except Exception as exc:
        raise CLIError(
            f"Failed to load Wikipedia template '{template_name}': {exc}"
        ) from exc


def _handle_shex_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Handle shex validate subcommand: validate RDF against ShEx schema."""
    from gkc.shex import ShexValidationError, ShexValidator

    # Validate required arguments combinations
    has_wikidata = args.qid and args.eid
    has_local = args.rdf_file and args.schema_file
    has_mixed_wikidata_local = (args.qid and args.schema_file) or (
        args.eid and args.rdf_file
    )

    if not (has_wikidata or has_local or has_mixed_wikidata_local):
        raise CLIError(
            "Validation requires either:\n"
            "  - Both --qid and --eid for Wikidata validation\n"
            "  - Both --rdf-file and --schema-file for local file validation\n"
            "  - --qid with --schema-file or --eid with --rdf-file for mixed validation"
        )

    try:
        # Create validator with provided arguments
        validator = ShexValidator(
            qid=args.qid,
            eid=args.eid,
            schema_file=args.schema_file,
            rdf_file=args.rdf_file,
            user_agent=args.user_agent,
        )

        # Perform validation
        validator.check()
        is_valid = validator.is_valid()

        # Build output details
        details: dict[str, Any] = {}

        if args.qid:
            details["entity"] = args.qid
            from gkc.utilities import get_entity_uri

            details["entity_uri"] = get_entity_uri(args.qid)
        elif args.rdf_file:
            details["rdf_file"] = args.rdf_file

        if args.eid:
            details["schema"] = args.eid
        elif args.schema_file:
            details["schema_file"] = args.schema_file

        details["valid"] = is_valid

        # Extract error summary if validation failed
        if not is_valid:
            error_summary = _extract_validation_error_summary(validator.results)
            details["error_summary"] = error_summary

        # Include full results in verbose mode
        if args.verbose and validator.results:
            details["results"] = str(validator.results)

        # Build human-readable message
        if is_valid:
            message = "✓ Validation passed"
        else:
            message = "✗ Validation failed"
            if not args.verbose and "error_summary" in details:
                message += f"\nError: {details['error_summary']}"

        # Add entity/schema info to message
        if args.qid:
            message += f"\nEntity: {args.qid}"
        if args.eid:
            message += f"\nSchema: {args.eid}"

        return {
            "command": args.command_path,
            "ok": is_valid,
            "message": message,
            "details": details,
        }

    except ShexValidationError as exc:
        raise CLIError(f"Validation error: {exc}") from exc
    except Exception as exc:
        raise CLIError(f"Unexpected error during validation: {exc}") from exc


def _extract_validation_error_summary(results: Any) -> str:
    """Extract a brief error summary from PyShEx validation results."""
    if not results:
        return "No validation results available"

    # Try to extract first error message
    for result in results:
        reason = result.reason or ""
        if any(
            indicator in reason
            for indicator in [
                "not in value set",
                "does not match",
                "Constraint violation",
                "No matching",
                "Failed to",
            ]
        ):
            # Extract first line of error message
            first_line = reason.split("\n")[0]
            if len(first_line) > 100:
                return first_line[:97] + "..."
            return first_line

    return "Validation failed (see --verbose for details)"


# New handler for 'wizard' CLI entry
def _handle_wizard(args: argparse.Namespace) -> dict[str, Any]:
    """Launch the interactive GKC curation wizard (Streamlit UI).

    Note: Starts a local Streamlit server at http://localhost:8501
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    previous_source, source_overridden = _apply_source_override(args)

    try:
        # Verify profile is loadable before launching Streamlit.
        profile_doc = load_profile(args.profile)
        profile_entity = profile_doc.get("entity", args.profile)
        profile_name = (
            profile_doc.get("metadata", {}).get("labels", {}).get("mul")
            or profile_doc.get("metadata", {}).get("labels", {}).get("en")
            or profile_entity
        )

        try:
            from gkc.wizard import streamlit_app
        except ImportError as exc:
            raise CLIError(
                "Streamlit UI dependencies are unavailable. Install `streamlit` to use `gkc wizard`."
            ) from exc

        # Get path to streamlit_app.py module
        app_path = Path(streamlit_app.__file__)

        # Set environment variables for Streamlit app to read
        env = os.environ.copy()
        env["GKC_WIZARD_PROFILE"] = profile_entity
        source_config = gkc.get_spirit_safe_source()
        env["GKC_SPIRIT_SAFE_SOURCE_MODE"] = source_config.mode
        env["GKC_SPIRIT_SAFE_GITHUB_REPO"] = source_config.github_repo
        env["GKC_SPIRIT_SAFE_GITHUB_REF"] = source_config.github_ref
        if source_config.local_root is not None:
            env["GKC_SPIRIT_SAFE_LOCAL_ROOT"] = str(source_config.local_root)
        if args.qid:
            env["GKC_WIZARD_QID"] = args.qid
        if args.packet:
            env["GKC_WIZARD_PACKET"] = args.packet

        # Launch Streamlit in subprocess
        print(f"🚀 Launching Streamlit wizard for profile: {profile_name}")
        print("📍 URL: http://localhost:8501")
        print("⌨️  Press Ctrl+C to stop the server")
        print()

        result = subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            env=env,
        )

        return {
            "command": args.command_path,
            "ok": result.returncode == 0,
            "message": "Streamlit wizard closed",
            "details": {
                "profile": profile_name,
                "profile_ref": profile_entity,
                "qid": args.qid,
                "packet": args.packet,
            },
        }
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_profile_export_json(args: argparse.Namespace) -> dict[str, Any]:
    """Build/export JSON entity profiles from SpiritSafe cache entities."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        cache_entities_dir: Optional[Path]
        if args.cache_entities_dir:
            cache_entities_dir = Path(args.cache_entities_dir)
        else:
            source = gkc.get_spirit_safe_source()
            if source.mode == "local" and source.local_root is not None:
                layout = _resolve_local_spiritsafe_layout(source.local_root)
                cache_entities_dir = layout.entities_dir(source.local_root)
            else:
                cache_entities_dir = None

        if cache_entities_dir is None:
            raise CLIError(
                "Unable to resolve cache entities directory. Provide "
                "--cache-entities-dir or use --source local with --local-root."
            )

        if not cache_entities_dir.exists():
            raise CLIError(f"Cache entities directory not found: {cache_entities_dir}")

        selected_profile_ids = list(args.profile_ids or [])

        if args.output:
            export_result = export_entity_profile_json_documents(
                cache_entities_dir=cache_entities_dir,
                output_dir=args.output,
                profile_ids=selected_profile_ids or None,
            )

            summary_output = _resolve_profile_export_summary_output(
                cache_entities_dir=cache_entities_dir,
                requested_summary_output=args.summary_output,
            )
            summary_output_file: Optional[str] = None
            if summary_output is not None:
                summary_output_file = _merge_profile_export_summary(
                    summary_path=summary_output,
                    export_result=export_result,
                    requested_profile_ids=selected_profile_ids,
                    cache_entities_dir=cache_entities_dir,
                )

            message = (
                "Exported JSON entity profiles to "
                f"{export_result.output_dir} ({len(export_result.written_ids)} files)"
            )
            details = {
                "cache_entities_dir": str(cache_entities_dir.resolve()),
                "output_file": export_result.output_dir,
                "profile_ids_requested": selected_profile_ids,
                "written_count": len(export_result.written_ids),
                "written_ids": export_result.written_ids,
                "skipped_count": len(export_result.skipped_ids),
                "skipped_ids": export_result.skipped_ids,
                "failure_count": len(export_result.failures),
                "failures": export_result.failures,
                "language_filtering": export_result.language_filtering,
            }
            if summary_output_file:
                details["summary_output_file"] = summary_output_file
            return {
                "command": args.command_path,
                "ok": True,
                "message": message,
                "details": details,
            }

        documents = build_entity_profile_json_documents(cache_entities_dir)
        if selected_profile_ids:
            selected = set(selected_profile_ids)
            documents = [
                document
                for document in documents
                if str(document.get("entity", "")).rstrip("/").split("/")[-1]
                in selected
            ]

        print(json.dumps(documents, indent=2))
        return {
            "command": args.command_path,
            "ok": True,
            "message": f"Generated {len(documents)} JSON entity profiles",
            "details": {
                "cache_entities_dir": str(cache_entities_dir.resolve()),
                "output": "stdout",
                "profile_ids_requested": selected_profile_ids,
                "generated_count": len(documents),
            },
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _resolve_profile_export_summary_output(
    *,
    cache_entities_dir: Path,
    requested_summary_output: Optional[str],
) -> Optional[Path]:
    if requested_summary_output:
        return Path(requested_summary_output)

    spiritsafe_root = _infer_local_spiritsafe_root_from_cache_entities_dir(
        cache_entities_dir
    )
    if spiritsafe_root is not None:
        layout = _resolve_local_spiritsafe_layout(spiritsafe_root)
        return layout.logs_dir(spiritsafe_root) / "last_run_summary.json"

    return cache_entities_dir.resolve().parent / "refresh" / "last_run_summary.json"


def _merge_profile_export_summary(
    *,
    summary_path: Path,
    export_result: Any,
    requested_profile_ids: list[str],
    cache_entities_dir: Path,
) -> str:
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    base_payload: dict[str, Any] = {}
    if summary_path.exists():
        try:
            parsed = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                base_payload = parsed
        except Exception:
            base_payload = {}

    metadata = base_payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    metadata.setdefault("cache_dir", str(cache_entities_dir.resolve()))
    base_payload["metadata"] = metadata

    profile_export = {
        "summary": {
            "requested_count": len(requested_profile_ids),
            "written_count": len(export_result.written_ids),
            "skipped_count": len(export_result.skipped_ids),
            "failure_count": len(export_result.failures),
            "language_filtered_count": len(export_result.language_filtering),
        },
        "requested_profile_ids": requested_profile_ids,
        "written_ids": export_result.written_ids,
        "skipped_ids": export_result.skipped_ids,
        "failures": export_result.failures,
        "language_filtering": export_result.language_filtering,
        "output_dir": export_result.output_dir,
    }
    base_payload["profile_export"] = profile_export

    summary_path.write_text(json.dumps(base_payload, indent=2), encoding="utf-8")
    return str(summary_path.resolve())


def _resolve_profile_value_list_paths(
    args: argparse.Namespace,
) -> tuple[Path, Path, Path, list[str]]:
    cache_entities_dir: Optional[Path]
    queries_dir: Optional[Path]
    cache_queries_dir: Optional[Path]

    if args.cache_entities_dir:
        cache_entities_dir = Path(args.cache_entities_dir)
    else:
        source = gkc.get_spirit_safe_source()
        cache_entities_dir = (
            _resolve_local_spiritsafe_layout(source.local_root).entities_dir(
                source.local_root
            )
            if source.mode == "local" and source.local_root is not None
            else None
        )

    if args.queries_dir:
        queries_dir = Path(args.queries_dir)
    else:
        source = gkc.get_spirit_safe_source()
        queries_dir = (
            _resolve_local_spiritsafe_layout(source.local_root).value_list_queries_dir(
                source.local_root
            )
            if source.mode == "local" and source.local_root is not None
            else None
        )

    if args.cache_queries_dir:
        cache_queries_dir = Path(args.cache_queries_dir)
    else:
        source = gkc.get_spirit_safe_source()
        cache_queries_dir = (
            _resolve_local_spiritsafe_layout(source.local_root).value_list_cache_dir(
                source.local_root
            )
            if source.mode == "local" and source.local_root is not None
            else None
        )

    if cache_entities_dir is None:
        raise CLIError(
            "Unable to resolve cache entities directory. Provide "
            "--cache-entities-dir or use --source local with --local-root."
        )
    if queries_dir is None:
        raise CLIError(
            "Unable to resolve queries directory. Provide --queries-dir or use "
            "--source local with --local-root."
        )
    if cache_queries_dir is None:
        raise CLIError(
            "Unable to resolve cache queries directory. Provide "
            "--cache-queries-dir or use --source local with --local-root."
        )

    if not cache_entities_dir.exists():
        raise CLIError(f"Cache entities directory not found: {cache_entities_dir}")

    selected_ids = sorted(set(args.value_list_ids or []))
    if not selected_ids:
        selected_ids = gkc.discover_value_list_ids(cache_entities_dir)

    return cache_entities_dir, queries_dir, cache_queries_dir, selected_ids


def _handle_profile_value_lists_sync(args: argparse.Namespace) -> dict[str, Any]:
    """Sync talk-page-derived value-list artifacts without SPARQL hydration."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        cache_entities_dir, queries_dir, cache_queries_dir, selected_ids = (
            _resolve_profile_value_list_paths(args)
        )

        result = gkc.sync_value_list_artifacts_from_cache(
            cache_entities_dir=cache_entities_dir,
            queries_dir=queries_dir,
            cache_queries_dir=cache_queries_dir,
            api_url=args.api_url,
            value_list_ids=selected_ids,
            fail_on_error=not args.continue_on_error,
        )

        failure_count = len(result.failures)
        ok = failure_count == 0
        message = (
            "Synchronized value-list artifacts: "
            f"{len(result.discovered_ids)} inspected"
        )
        if failure_count:
            message += f" ({failure_count} failures)"

        details = {
            "cache_entities_dir": str(cache_entities_dir.resolve()),
            "queries_dir": result.queries_dir,
            "cache_queries_dir": result.cache_queries_dir,
            "value_list_ids_requested": selected_ids,
            "discovered_count": len(result.discovered_ids),
            "query_files_written": result.query_files_written,
            "cache_files_written": result.cache_files_written,
            "query_files_deleted": result.query_files_deleted,
            "cache_files_deleted": result.cache_files_deleted,
            "failures": result.failures,
        }

        return {
            "command": args.command_path,
            "ok": ok,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_profile_value_lists_hydrate(args: argparse.Namespace) -> dict[str, Any]:
    """Extract value-list SPARQL and hydrate cache/queries artifacts."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        cache_entities_dir, queries_dir, cache_queries_dir, selected_ids = (
            _resolve_profile_value_list_paths(args)
        )

        result = gkc.hydrate_value_lists_from_cache(
            cache_entities_dir=cache_entities_dir,
            queries_dir=queries_dir,
            cache_queries_dir=cache_queries_dir,
            api_url=args.api_url,
            endpoint=args.endpoint,
            value_list_ids=selected_ids,
            page_size=args.page_size,
            max_results=args.max_results,
            fail_on_hydration_error=not args.continue_on_error,
        )

        failure_count = len(result.failures)
        ok = failure_count == 0
        message = (
            "Hydrated value lists: "
            f"{len(result.hydrated_ids)}/{len(result.discovered_ids)} succeeded"
        )
        if failure_count:
            message += f" ({failure_count} failures)"

        details = {
            "cache_entities_dir": str(cache_entities_dir.resolve()),
            "queries_dir": result.queries_dir,
            "cache_queries_dir": result.cache_queries_dir,
            "value_list_ids_requested": selected_ids,
            "discovered_count": len(result.discovered_ids),
            "hydrated_count": len(result.hydrated_ids),
            "query_files_written": result.query_files_written,
            "cache_files_written": result.cache_files_written,
            "query_files_deleted": result.query_files_deleted,
            "cache_files_deleted": result.cache_files_deleted,
            "failures": result.failures,
        }

        return {
            "command": args.command_path,
            "ok": ok,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_registry_list(args: argparse.Namespace) -> dict[str, Any]:
    """List all profiles in the configured SpiritSafe registry."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        profiles = []

        for profile_id in list_profiles():
            profile = load_profile(profile_id)
            metadata = profile.get("metadata", {})
            profiles.append(
                {
                    "qid": profile_id,
                    "entity": profile.get("entity"),
                    "label": _preferred_profile_text(metadata.get("labels", {})),
                    "description": _preferred_profile_text(
                        metadata.get("descriptions", {})
                    ),
                    "statement_count": metadata.get(
                        "statement_count", len(profile.get("statements", []))
                    ),
                }
            )

        message = f"Found {len(profiles)} profiles in registry"
        details = {
            "profiles": profiles,
            "source": get_spirit_safe_source().mode,
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_registry_info(args: argparse.Namespace) -> dict[str, Any]:
    """Show detailed profile metadata from the JSON profile document."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        available_profiles = list_profiles()
        profile = load_profile(args.profile)
        metadata = profile.get("metadata", {})
        profile_entity = profile.get("entity")
        profile_qid = (
            str(profile_entity).rstrip("/").split("/")[-1]
            if isinstance(profile_entity, str) and profile_entity
            else args.profile
        )
        message = f"Profile: {_preferred_profile_text(metadata.get('labels', {})) or profile_qid}"
        details = {
            "qid": profile_qid,
            "entity": profile.get("entity"),
            "labels": metadata.get("labels", {}),
            "descriptions": metadata.get("descriptions", {}),
            "statement_count": metadata.get(
                "statement_count", len(profile.get("statements", []))
            ),
            "profile_graph": metadata.get("profile_graph", []),
            "value_list_graph": metadata.get("value_list_graph", []),
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        if isinstance(exc, FileNotFoundError):
            raise CLIError(
                f"Profile '{args.profile}' not found. Available: {', '.join(available_profiles)}"
            ) from exc
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_registry_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate registry profile structure."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        errors = []
        profile_ids = list_profiles()

        if not profile_ids:
            errors.append("No profiles found in registry")

        for profile_id in profile_ids:
            profile = load_profile(profile_id)
            metadata = profile.get("metadata", {})

            if not profile.get("entity"):
                errors.append(f"Profile {profile_id} missing entity URI")
            if not isinstance(metadata.get("profile_graph", []), list):
                errors.append(f"Profile {profile_id} has invalid profile_graph")
            if not isinstance(metadata.get("value_list_graph", []), list):
                errors.append(f"Profile {profile_id} has invalid value_list_graph")
            if not isinstance(profile.get("statements", []), list):
                errors.append(f"Profile {profile_id} has invalid statements section")

        ok = len(errors) == 0
        message = "✓ Registry is valid" if ok else "✗ Registry validation failed"

        details = {
            "profile_count": len(profile_ids),
            "errors": errors,
        }

        return {
            "command": args.command_path,
            "ok": ok,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_spiritsafe_sitelinks_sync_wikimedia_sites(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Sync the Wikimedia sites cache artifact from sitematrix."""

    if args.source != "local" or not args.local_root:
        raise CLIError(
            "spiritsafe sitelinks sync-wikimedia-sites requires --source local --local-root /path/to/SpiritSafe"
        )

    try:
        local_root = Path(args.local_root).expanduser().resolve()
        layout = _resolve_local_spiritsafe_layout(local_root)
        output_path = (
            Path(args.output).expanduser().resolve()
            if args.output
            else layout.wikimedia_sites_file(local_root)
        )

        artifact = export_wikimedia_sites_artifact(
            str(output_path),
            source_url=args.source_url,
            timeout=args.timeout,
            user_agent=args.user_agent,
        )

        metadata = artifact.get("metadata", {})
        details = {
            "output_path": str(output_path),
            "source_url": metadata.get("source_url"),
            "schema_version": metadata.get("schema_version"),
            "fetched_at": metadata.get("fetched_at"),
            "total_sites": metadata.get("total_sites", 0),
            "active_sites": metadata.get("active_sites", 0),
            "closed_sites": metadata.get("closed_sites", 0),
            "by_dbname_count": len(artifact.get("index", {}).get("by_dbname", {})),
            "by_domain_count": len(artifact.get("index", {}).get("by_domain", {})),
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": f"Synced Wikimedia sites artifact to {output_path}",
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_spiritsafe_semantic_anchors_build(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Build the SpiritSafe semantic anchor artifact from local cache entities."""

    if args.source != "local" or not args.local_root:
        raise CLIError(
            "spiritsafe semantic-anchors build requires --source local --local-root /path/to/SpiritSafe"
        )

    try:
        local_root = Path(args.local_root).expanduser().resolve()
        layout = _resolve_local_spiritsafe_layout(local_root)
        output_path = (
            Path(args.output).expanduser().resolve()
            if args.output
            else layout.semantic_anchors_file(local_root)
        )

        artifact = export_spiritsafe_semantic_anchors(local_root, output_path)
        entities = artifact.get("entities", {})
        metadata = artifact.get("metadata", {})
        details = {
            "output_path": str(output_path),
            "anchor_count": len(entities) if isinstance(entities, dict) else 0,
            "property_count": metadata.get("property_count", 0),
            "item_count": metadata.get("item_count", 0),
            "validation_status": artifact.get("validation", {}).get("status"),
            "error_count": artifact.get("validation", {}).get("error_count", 0),
            "warning_count": artifact.get("validation", {}).get("warning_count", 0),
        }
        return {
            "command": args.command_path,
            "ok": True,
            "message": f"Built SpiritSafe semantic anchor artifact at {output_path}",
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_spiritsafe_semantic_anchors_validate(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Validate a semantic-anchor artifact against the package-owned contract."""

    if not args.artifact_file and not args.local_root:
        raise CLIError(
            "spiritsafe semantic-anchors validate requires --artifact-file or --local-root"
        )
    if args.check_current_cache and not args.local_root:
        raise CLIError(
            "--check-current-cache requires --local-root /path/to/SpiritSafe"
        )

    try:
        local_root = (
            Path(args.local_root).expanduser().resolve() if args.local_root else None
        )
        layout = (
            _resolve_local_spiritsafe_layout(local_root)
            if local_root is not None
            else get_wikibase_runtime_config().spiritsafe_layout
        )
        artifact_path = (
            Path(args.artifact_file).expanduser().resolve()
            if args.artifact_file
            else layout.semantic_anchors_file(local_root)
        )

        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CLIError(f"Failed to load semantic anchor artifact: {exc}") from exc

        internal_prefix: str | None = None
        if local_root is not None:
            _config_path, config_values = resolve_spiritsafe_wikibase_config(local_root)
            internal_prefix = config_values.get("internal_name_identifier_prefix")
        else:
            runtime_config = get_wikibase_runtime_config()
            internal_prefix = runtime_config.internal_name_identifier_prefix

        current_document = None
        if args.check_current_cache and local_root is not None:
            current_document = build_spiritsafe_semantic_anchor_document(local_root)

        result = validate_semantic_anchor_document(
            artifact,
            internal_name_identifier_prefix=internal_prefix,
            current_anchor_document=current_document,
        )

        notices_payload = [
            {
                "severity": notice.severity,
                "entity_ref": notice.entity_ref,
                "statement_ref": notice.statement_ref,
                "code": notice.code,
                "message": notice.message,
                "normalized_value": notice.normalized_value,
            }
            for notice in result.notices
        ]
        error_count = sum(1 for notice in result.notices if notice.severity == "error")
        warning_count = sum(
            1 for notice in result.notices if notice.severity == "warning"
        )
        entity_results_payload = {
            anchor_name: {
                "status": entity_result.status,
                "notices": [
                    {
                        "severity": notice.severity,
                        "entity_ref": notice.entity_ref,
                        "statement_ref": notice.statement_ref,
                        "code": notice.code,
                        "message": notice.message,
                        "normalized_value": notice.normalized_value,
                    }
                    for notice in entity_result.notices
                ],
            }
            for anchor_name, entity_result in result.entity_results.items()
        }
        details = {
            "artifact_path": str(artifact_path),
            "status": result.status,
            "required_anchor_count": result.required_anchor_count,
            "matched_anchor_count": result.matched_anchor_count,
            "evaluated_anchor_count": result.evaluated_anchor_count,
            "freshness_checked": result.freshness_checked,
            "freshness_match": result.freshness_match,
            "error_count": error_count,
            "warning_count": warning_count,
            "notices": notices_payload,
            "entity_results": entity_results_payload,
        }
        message = (
            f"Validated SpiritSafe semantic anchor artifact at {artifact_path}"
            if result.valid
            else f"Semantic anchor artifact failed validation at {artifact_path}"
        )
        return {
            "command": args.command_path,
            "ok": result.valid,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_profile_package_load(args: argparse.Namespace) -> dict[str, Any]:
    """Load a profile package with dependencies."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        package = load_profile_package(args.profile, depth=args.depth)

        message = (
            f"Loaded package for '{args.profile}' "
            f"with {len(package['profiles'])} profiles at depth {args.depth}"
        )

        details = {
            "primary_profile": package["primary_profile"],
            "primary_profile_entity": package.get("primary_profile_entity"),
            "depth": package["depth"],
            "profiles_included": list(package["profiles"].keys()),
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_profile_package_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate profile package structure."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        package = load_profile_package(args.profile, depth=args.depth)
        errors = []

        # Check package structure
        if "primary_profile" not in package:
            errors.append("Missing primary_profile field")
        if "profiles" not in package:
            errors.append("Missing profiles field")

        # Check all profiles loaded
        if package.get("primary_profile") not in package.get("profiles", {}):
            errors.append("Primary profile not in loaded profiles")

        ok = len(errors) == 0
        message = (
            "✓ Package is valid"
            if ok
            else f"✗ Package validation failed with {len(errors)} errors"
        )

        details = {
            "primary_profile": package.get("primary_profile"),
            "primary_profile_entity": package.get("primary_profile_entity"),
            "depth": package.get("depth"),
            "profiles_count": len(package.get("profiles", {})),
            "errors": errors,
        }

        return {
            "command": args.command_path,
            "ok": ok,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_packet_create(args: argparse.Namespace) -> dict[str, Any]:
    """Create a curation packet."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        packet = create_curation_packet(
            profile_id=args.profile, operation_mode=args.mode, depth=args.depth
        )

        # Optionally write to file
        if args.output:
            with open(args.output, "w") as f:
                json.dump(packet, f, indent=2, default=str)
            message = f"Created packet {packet['packet_id']} and saved to {args.output}"
        else:
            message = f"Created packet {packet['packet_id']}"

        entity_count = len(
            packet.get("data", {}).get("entities", packet.get("entities", []))
        )
        graph_edge_count = len(
            packet.get("metadata", {})
            .get("graph", {})
            .get("edges", packet.get("cross_references", []))
        )
        primary_profile = packet.get("metadata", {}).get("primary_profile", {})

        details = {
            "packet_id": packet["packet_id"],
            "operation_mode": packet["operation_mode"],
            "primary_profile": primary_profile.get("name_identifier")
            or packet.get("primary_profile"),
            "primary_profile_entity": primary_profile.get("id")
            or packet.get("primary_profile_entity"),
            "entity_count": entity_count,
            "graph_edge_count": graph_edge_count,
            "output_file": args.output,
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_packet_info(args: argparse.Namespace) -> dict[str, Any]:
    """Show packet metadata and summary."""
    try:
        with open(args.packet_file, "r") as f:
            packet = json.load(f)

        entity_count = len(
            packet.get("data", {}).get("entities", packet.get("entities", []))
        )
        graph_edge_count = len(
            packet.get("metadata", {})
            .get("graph", {})
            .get("edges", packet.get("cross_references", []))
        )
        primary_profile = packet.get("metadata", {}).get("primary_profile", {})

        message = f"Packet {packet.get('packet_id', 'unknown')}"
        details = {
            "packet_id": packet.get("packet_id"),
            "operation_mode": packet.get("operation_mode"),
            "minted_at": packet.get("metadata", {})
            .get("mint", {})
            .get("minted_at", packet.get("created_at")),
            "primary_profile": primary_profile.get("name_identifier")
            or packet.get("primary_profile"),
            "primary_profile_entity": primary_profile.get("id")
            or packet.get("primary_profile_entity"),
            "entity_count": entity_count,
            "graph_edge_count": graph_edge_count,
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except FileNotFoundError:
        raise CLIError(f"Packet file not found: {args.packet_file}")
    except json.JSONDecodeError as exc:
        raise CLIError(f"Invalid JSON in packet file: {exc}") from exc
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_packet_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate packet structure."""
    try:
        with open(args.packet_file, "r") as f:
            packet = json.load(f)

        is_valid, errors = validate_packet_structure(packet)

        entity_count = len(
            packet.get("data", {}).get("entities", packet.get("entities", []))
        )
        graph_edge_count = len(
            packet.get("metadata", {})
            .get("graph", {})
            .get("edges", packet.get("cross_references", []))
        )

        message = (
            f"✓ Packet {packet.get('packet_id', 'unknown')} is valid"
            if is_valid
            else f"✗ Packet validation failed with {len(errors)} errors"
        )

        details = {
            "packet_id": packet.get("packet_id"),
            "is_valid": is_valid,
            "errors": errors,
            "entity_count": entity_count,
            "graph_edge_count": graph_edge_count,
        }

        return {
            "command": args.command_path,
            "ok": is_valid,
            "message": message,
            "details": details,
        }
    except FileNotFoundError:
        raise CLIError(f"Packet file not found: {args.packet_file}")
    except json.JSONDecodeError as exc:
        raise CLIError(f"Invalid JSON in packet file: {exc}") from exc
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_packet_build(args: argparse.Namespace) -> dict[str, Any]:
    """Build a curation packet from a JSON Entity Profile."""
    from gkc.still_charger import build_curation_packet_from_json_profile

    previous_source, source_overridden = _apply_source_override(args)

    try:
        # Normalize profile identifier to full URI
        profile_id = args.profile
        if not (profile_id.startswith("http://") or profile_id.startswith("https://")):
            # Assume it's a QID; construct default URI
            if not profile_id.startswith("Q"):
                raise CLIError(
                    f"Invalid profile identifier: {profile_id}. Expected QID or full URI."
                )
            profile_entity = (
                f"https://datadistillery.wikibase.cloud/entity/{profile_id}"
            )
        else:
            profile_entity = profile_id

        try:
            json_profile_doc = load_profile(profile_entity)
        except FileNotFoundError as exc:
            raise CLIError(str(exc)) from exc
        except Exception as exc:
            raise CLIError(f"Failed to load profile {profile_entity}: {exc}") from exc

        source_config = get_spirit_safe_source()
        source_root = (
            source_config.local_root if source_config.mode == "local" else None
        )

        # Build the packet
        packet = build_curation_packet_from_json_profile(
            profile_entity=profile_entity,
            json_profile_doc=json_profile_doc,
            source_root=source_root,
        )

        # Optionally write to file
        if args.output:
            with open(args.output, "w") as f:
                json.dump(packet, f, indent=2, default=str)
            message = f"Built packet {packet['packet_id']} and saved to {args.output}"
        else:
            message = f"Built packet {packet['packet_id']}"

        entity_count = len(
            packet.get("data", {}).get("entities", packet.get("entities", []))
        )
        graph_edge_count = len(
            packet.get("metadata", {})
            .get("graph", {})
            .get("edges", packet.get("cross_references", []))
        )
        primary_profile = packet.get("metadata", {}).get("primary_profile", {})

        details = {
            "packet_id": packet["packet_id"],
            "profile_entity": primary_profile.get("id") or packet.get("profile_entity"),
            "profile_name_identifier": primary_profile.get("name_identifier"),
            "entity_count": entity_count,
            "graph_edge_count": graph_edge_count,
            "output_file": args.output,
        }

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        if isinstance(exc, CLIError):
            raise
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_packet_charge(args: argparse.Namespace) -> dict[str, Any]:
    """Charge a curation packet with Wikidata item data."""
    from pathlib import Path

    from gkc.still_charger import (
        charge_packet_from_wikidata_items,
        create_and_charge_curation_packet,
    )

    previous_source, source_overridden = _apply_source_override(args)

    try:
        if not args.packet_file and not args.profile:
            raise CLIError("Provide either --packet-file or --profile")
        if args.packet_file and args.profile:
            raise CLIError("Use either --packet-file or --profile, not both")

        qid_map: dict[str, str] = {}
        if args.source == "wikidata":
            if args.mapping_file:
                mapping_path = Path(args.mapping_file)
                if not mapping_path.exists():
                    raise CLIError(f"Mapping file not found: {mapping_path}")
                try:
                    loaded_map = json.loads(mapping_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise CLIError(f"Invalid JSON in mapping file: {exc}") from exc
                if not isinstance(loaded_map, dict):
                    raise CLIError("Mapping file must contain a JSON object")
                qid_map = {str(k): str(v) for k, v in loaded_map.items()}

        if args.profile:
            if args.source != "wikidata":
                raise CLIError("--profile charging currently supports source=wikidata")
            if not args.qid and not qid_map:
                raise CLIError(
                    "Provide --qid or --mapping-file for profile-based charge"
                )

            charged_packet, notices = create_and_charge_curation_packet(
                args.profile,
                qid=args.qid,
                qid_map=qid_map or None,
                include_linked_profiles=bool(args.include_linked_profiles),
            )
        else:
            packet_path = Path(args.packet_file)
            if not packet_path.exists():
                raise CLIError(f"Packet file not found: {packet_path}")

            try:
                packet = json.loads(packet_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CLIError(f"Invalid JSON in packet file: {exc}") from exc

            if args.source == "wikidata":
                if args.qid:
                    entities = packet.get("data", {}).get("entities", [])
                    if not isinstance(entities, list):
                        entities = packet.get("entities", [])

                    for entity in entities:
                        if not isinstance(entity, dict):
                            continue
                        entity_id = entity.get("id")
                        profile_name = entity.get("profile")
                        if isinstance(entity_id, str) and entity_id:
                            qid_map[entity_id] = args.qid
                        if isinstance(profile_name, str) and profile_name:
                            qid_map[profile_name] = args.qid

                if not qid_map:
                    raise CLIError(
                        "Either --qid or --mapping-file required for source=wikidata"
                    )

            charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

        # Count notice severities
        error_count = sum(1 for n in notices if n.severity == "error")
        warning_count = sum(1 for n in notices if n.severity == "warning")
        info_count = sum(1 for n in notices if n.severity == "info")

        # Optionally write to file
        if args.output:
            with open(args.output, "w") as f:
                json.dump(charged_packet, f, indent=2, default=str)
            message = f"Charged packet {charged_packet.get('packet_id', 'unknown')} and saved to {args.output}"
        else:
            message = f"Charged packet {charged_packet.get('packet_id', 'unknown')}"

        details = {
            "packet_id": charged_packet.get("packet_id"),
            "entities_charged": len(charged_packet.get("data", {}).get("entities", [])),
            "notices_error": error_count,
            "notices_warning": warning_count,
            "notices_info": info_count,
            "conformance_summary": charged_packet.get("metadata", {}).get(
                "conformance_summary"
            ),
            "output_file": args.output,
        }

        return {
            "command": args.command_path,
            "ok": error_count == 0,
            "message": message,
            "details": details,
        }
    except Exception as exc:
        if isinstance(exc, CLIError):
            raise
        raise CLIError(str(exc)) from exc
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_mash_check_wikibase_revisions(args: argparse.Namespace) -> dict[str, Any]:
    """Check recent MediaWiki revisions affecting Wikibase entity pages."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url

    try:
        api_client = WikibaseApiClient(api_url=api_url)
        resolved_since = args.since
        if not resolved_since and args.cache_dir:
            resolved_since = get_latest_cache_timestamp(args.cache_dir)
        if not resolved_since:
            raise CLIError(
                "No watermark available; provide --since or --cache-dir with existing cache metadata"
            )

        recent_result = fetch_recent_entity_changes(
            api_client=api_client,
            since=resolved_since,
            overlap_seconds=args.overlap_seconds,
            ignore_ids=set(args.ignore_ids or []),
        )

        output_payload = {
            "metadata": {
                "api_url": api_url,
                "since": recent_result.since,
                "next_since": recent_result.next_since,
                "overlap_seconds": args.overlap_seconds,
            },
            "summary": {
                "changed_count": len(recent_result.changed_ids),
                "ignored_count": len(recent_result.ignored_ids),
                "recentchanges_count": len(recent_result.recentchanges),
            },
            "changed_ids": recent_result.changed_ids,
            "ignored_ids": recent_result.ignored_ids,
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2), encoding="utf-8"
            )

        details: dict[str, Any] = {
            "api_url": api_url,
            "since": recent_result.since,
            "next_since": recent_result.next_since,
            "overlap_seconds": args.overlap_seconds,
            "changed_count": len(recent_result.changed_ids),
            "ignored_count": len(recent_result.ignored_ids),
            "recentchanges_count": len(recent_result.recentchanges),
            "changed_ids_preview": recent_result.changed_ids[:20],
            "ignored_ids_preview": recent_result.ignored_ids[:20],
        }

        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                "✓ Recentchanges revision check complete: "
                f"{len(recent_result.changed_ids)} changed, "
                f"{len(recent_result.ignored_ids)} ignored"
            ),
            "details": details,
        }
    except CLIError:
        raise
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_mash_cache_wikibase_revisions(args: argparse.Namespace) -> dict[str, Any]:
    """Refresh Wikibase entity cache files from MediaWiki recentchanges."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url

    try:
        api_client = WikibaseApiClient(api_url=api_url)
        resolved_since = args.since or get_latest_cache_timestamp(args.cache_dir)
        if not resolved_since:
            raise CLIError(
                "No cache watermark available; provide --since or seed the cache first"
            )

        refresh_result = refresh_entity_cache_from_recentchanges(
            api_client=api_client,
            cache_dir=args.cache_dir,
            since=resolved_since,
            overlap_seconds=args.overlap_seconds,
            ignore_ids=set(args.ignore_ids or []),
            source_endpoint=args.source_endpoint,
        )

        output_payload = {
            "metadata": {
                "api_url": api_url,
                "cache_dir": refresh_result.cache_dir,
                "since": refresh_result.since,
                "next_since": refresh_result.next_since,
                "overlap_seconds": args.overlap_seconds,
            },
            "summary": {
                "changed_count": len(refresh_result.changed_ids),
                "ignored_count": len(refresh_result.ignored_ids),
                "refreshed_count": len(refresh_result.refreshed_ids),
                "deleted_count": len(refresh_result.deleted_ids),
                "missing_count": len(refresh_result.missing_ids),
            },
            "changed_ids": refresh_result.changed_ids,
            "ignored_ids": refresh_result.ignored_ids,
            "refreshed_ids": refresh_result.refreshed_ids,
            "deleted_ids": refresh_result.deleted_ids,
            "missing_ids": refresh_result.missing_ids,
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2), encoding="utf-8"
            )

        details: dict[str, Any] = {
            "api_url": api_url,
            "cache_dir": refresh_result.cache_dir,
            "since": refresh_result.since,
            "next_since": refresh_result.next_since,
            "overlap_seconds": args.overlap_seconds,
            "changed_count": len(refresh_result.changed_ids),
            "ignored_count": len(refresh_result.ignored_ids),
            "refreshed_count": len(refresh_result.refreshed_ids),
            "deleted_count": len(refresh_result.deleted_ids),
            "missing_count": len(refresh_result.missing_ids),
            "changed_ids_preview": refresh_result.changed_ids[:20],
            "refreshed_ids_preview": refresh_result.refreshed_ids[:20],
            "deleted_ids_preview": refresh_result.deleted_ids[:20],
            "ignored_ids_preview": refresh_result.ignored_ids[:20],
        }

        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                "✓ Recentchanges cache refresh complete: "
                f"{len(refresh_result.refreshed_ids)} refreshed, "
                f"{len(refresh_result.deleted_ids)} deleted, "
                f"{len(refresh_result.ignored_ids)} ignored"
            ),
            "details": details,
        }
    except CLIError:
        raise
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_mash_full_sync_wikibase(args: argparse.Namespace) -> dict[str, Any]:
    """Full-sync baseline: discover and re-cache all entities from a Wikibase instance."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url
    api_url_source = "arg" if args.api_url else "runtime_config"
    auth: Optional[WikiverseAuth] = None

    if args.items_only and args.properties_only:
        raise CLIError("--items-only and --properties-only are mutually exclusive")

    try:
        api_client = WikibaseApiClient(api_url=api_url)
        sync_result = full_sync_wikibase_entity_cache(
            api_client=api_client,
            cache_dir=args.cache_dir,
            auth=auth,
            ignore_ids=set(args.ignore_ids or []),
            include_items=not args.properties_only,
            include_properties=not args.items_only,
            batch_size=args.batch_size,
            source_endpoint=api_url,
            api_url_source=api_url_source,
        )

        output_payload = {
            "metadata": {
                "api_url": sync_result.api_url,
                "api_url_source": sync_result.api_url_source,
                "cache_dir": sync_result.cache_dir,
                "run_mode": sync_result.run_mode,
                "started_at": sync_result.started_at,
                "completed_at": sync_result.completed_at,
                "duration_seconds": sync_result.duration_seconds,
                "batch_size_requested": sync_result.batch_size_requested,
                "batch_size_effective": sync_result.batch_size_effective,
                "batch_fallback_count": sync_result.batch_fallback_count,
                "batch_fallback_first_error": sync_result.batch_fallback_first_error,
            },
            "summary": {
                "discovered_count": len(sync_result.discovered_ids),
                "hydrated_count": len(sync_result.hydrated_ids),
                "tombstone_count": len(sync_result.tombstone_ids),
                "redirect_count": len(sync_result.redirect_ids),
                "failed_count": len(sync_result.failed_ids),
            },
            "hydrated_ids": sync_result.hydrated_ids,
            "tombstone_ids": sync_result.tombstone_ids,
            "redirect_ids": sync_result.redirect_ids,
            "failed_ids": sync_result.failed_ids,
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2), encoding="utf-8"
            )

        # Write GitHub Actions step summary if available
        step_summary_path = Path(os.environ.get("GITHUB_STEP_SUMMARY", ""))
        if step_summary_path.name:
            summary_md = (
                "## Full-Sync Wikibase Cache Result\n\n"
                f"| Field | Value |\n"
                f"| --- | --- |\n"
                f"| API URL | `{sync_result.api_url}` |\n"
                f"| Started | `{sync_result.started_at}` |\n"
                f"| Completed | `{sync_result.completed_at}` |\n"
                f"| Duration (s) | `{sync_result.duration_seconds:.1f}` |\n"
                f"| Discovered | `{len(sync_result.discovered_ids)}` |\n"
                f"| Hydrated | `{len(sync_result.hydrated_ids)}` |\n"
                f"| Tombstones | `{len(sync_result.tombstone_ids)}` |\n"
                f"| Redirects | `{len(sync_result.redirect_ids)}` |\n"
                f"| Failed | `{len(sync_result.failed_ids)}` |\n"
                f"| Batch size | `{sync_result.batch_size_effective}` "
                f"(fallbacks: `{sync_result.batch_fallback_count}`) |\n"
            )
            with step_summary_path.open("a", encoding="utf-8") as fh:
                fh.write(summary_md)

        details: dict[str, Any] = {
            "api_url": sync_result.api_url,
            "api_url_source": sync_result.api_url_source,
            "cache_dir": sync_result.cache_dir,
            "run_mode": sync_result.run_mode,
            "started_at": sync_result.started_at,
            "completed_at": sync_result.completed_at,
            "duration_seconds": round(sync_result.duration_seconds, 1),
            "discovered_count": len(sync_result.discovered_ids),
            "hydrated_count": len(sync_result.hydrated_ids),
            "tombstone_count": len(sync_result.tombstone_ids),
            "redirect_count": len(sync_result.redirect_ids),
            "failed_count": len(sync_result.failed_ids),
            "batch_size_requested": sync_result.batch_size_requested,
            "batch_size_effective": sync_result.batch_size_effective,
            "batch_fallback_count": sync_result.batch_fallback_count,
            "failed_ids_preview": sync_result.failed_ids[:20],
        }

        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

        return {
            "command": args.command_path,
            "ok": len(sync_result.failed_ids) == 0,
            "message": (
                "✓ Full-sync complete: "
                f"{len(sync_result.hydrated_ids)} hydrated, "
                f"{len(sync_result.tombstone_ids)} tombstones, "
                f"{len(sync_result.redirect_ids)} redirects, "
                f"{len(sync_result.failed_ids)} failed"
            ),
            "details": details,
        }
    except CLIError:
        raise
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_wikibase_init(args: argparse.Namespace) -> dict[str, Any]:
    """Preview Wikibase seed compilation and dry-run init actions."""

    original_languages = gkc.get_languages()
    if args.language:
        gkc.set_languages(args.language)

    try:
        compilation = gkc.compile_wikibase_seed(
            label_language=args.language,
        )
        current_entities: dict[str, dict[str, Any]] | None = None
        entity_id_to_internal_name_identifier: dict[str, str] | None = None
        comparison_source: dict[str, Any] = {"mode": "compiled-only"}

        if args.local_root:
            (
                current_entities,
                entity_id_to_internal_name_identifier,
                comparison_source,
            ) = _load_wikibase_init_current_entities_from_local_root(
                compilation=compilation,
                local_root=args.local_root,
                api_url=args.api_url,
            )
        elif args.artifact_file:
            resolver = _load_wikibase_init_anchor_resolver(
                local_root=None,
                artifact_file=args.artifact_file,
            )
            current_entities, entity_id_to_internal_name_identifier = (
                _load_wikibase_init_current_entities_from_resolver(
                    compilation=compilation,
                    resolver=resolver,
                    api_url=args.api_url,
                )
            )
            comparison_source = {
                "mode": "live-compare-anchor-artifact",
                "api_url": args.api_url,
                "local_root": None,
                "artifact_file": resolver.artifact_path,
                "resolved_entity_count": len(current_entities),
            }

        plan = gkc.plan_wikibase_seed_baseline(
            current_entities_by_internal_name_identifier=current_entities,
            entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
            label_language=args.language,
            required_value_language="mul",
        )

        action_rows: list[dict[str, Any]] = []
        for operation in plan.operations:
            compiled_entity = compilation.by_internal_name_identifier[
                operation.internal_name_identifier
            ]
            action_rows.append(
                {
                    "action": operation.action,
                    "kind": operation.entity_type,
                    "label": _wikibase_init_entity_label(compiled_entity.payload),
                    "entity_id": operation.current_entity_id,
                    "details": operation.details,
                    "changed_fields": operation.changed_fields,
                    "request_payload": operation.payload,
                    "internal_name_identifier": operation.internal_name_identifier,
                    "key": operation.key,
                }
            )

        summary = {
            "created": sum(
                1 for operation in plan.operations if operation.action == "create"
            ),
            "updated": sum(
                1 for operation in plan.operations if operation.action == "update"
            ),
            "skipped": sum(
                1 for operation in plan.operations if operation.action == "skip"
            ),
            "dry_run": len(plan.operations),
        }

        details: dict[str, Any] = {
            "summary": summary,
            "seed_entity_count": len(compilation.entities),
            "label_language": _resolve_command_language(args.language),
            "value_language": "mul",
            "comparison_source": comparison_source,
            "actions": action_rows,
        }

        if args.show_entity:
            sample_entity = _select_wikibase_init_sample_entity(
                compilation, args.show_entity
            )
            details["sample_entity"] = {
                "key": sample_entity.key,
                "internal_name_identifier": sample_entity.internal_name_identifier,
                "payload": sample_entity.payload,
            }

        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                f"Prepared Wikibase dry-run plan for {len(plan.operations)} seed entities"
            ),
            "details": details,
        }
    except CLIError:
        raise
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        if args.language:
            gkc.set_languages(original_languages)


def _load_wikibase_init_anchor_resolver(
    *,
    local_root: str | None,
    artifact_file: str | None,
):
    """Load the semantic-anchor resolver used for live seed comparison."""

    if artifact_file:
        artifact_path = Path(artifact_file).expanduser().resolve()
        if not artifact_path.is_file():
            raise CLIError(f"Semantic anchor artifact not found at {artifact_path}")
        try:
            anchor_document = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CLIError(
                f"Failed to load semantic anchor artifact {artifact_path}: {exc}"
            ) from exc
        return build_spiritsafe_semantic_anchor_resolver(
            anchor_document,
            artifact_path=artifact_path,
        )

    raise CLIError("Anchor-artifact comparison requires --artifact-file")


def _load_wikibase_init_current_entities_from_resolver(
    *,
    compilation,
    resolver,
    api_url: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Fetch the current Wikibase entities referenced by the active anchors."""

    api_client = WikibaseApiClient(api_url=api_url)
    entity_id_to_internal_name_identifier = {
        anchor.entity_id: anchor_name
        for anchor_name, anchor in resolver.anchors.items()
    }

    entity_ids = sorted(
        {
            resolver.anchors[internal_name_identifier].entity_id
            for internal_name_identifier in compilation.by_internal_name_identifier.keys()
            if internal_name_identifier in resolver.anchors
        }
    )
    fetched_entities = api_client.get_entities(entity_ids)

    current_entities: dict[str, dict[str, Any]] = {}
    for internal_name_identifier in compilation.by_internal_name_identifier.keys():
        anchor = resolver.anchors.get(internal_name_identifier)
        if anchor is None:
            continue
        entity_payload = fetched_entities.get(anchor.entity_id)
        if isinstance(entity_payload, dict):
            current_entities[internal_name_identifier] = entity_payload

    return current_entities, entity_id_to_internal_name_identifier


def _load_wikibase_init_current_entities_from_local_root(
    *,
    compilation,
    local_root: str,
    api_url: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, Any]]:
    """Fetch current entities by internal name identifier for bootstrap-safe dry runs."""

    resolved_local_root = Path(local_root).expanduser().resolve()
    _config_path, config_values = resolve_spiritsafe_wikibase_config(
        resolved_local_root
    )
    name_identifier_property_id = config_values.get("name_identifier_property_id")
    if not name_identifier_property_id:
        raise CLIError(
            "Wikibase config is missing semantic_conventions.name_identifier_property_id"
        )

    sparql_endpoint = config_values.get("sparql_endpoint")
    if not sparql_endpoint:
        raise CLIError(
            "Wikibase config is missing sparql_endpoint, required for bootstrap dry-run comparison"
        )

    entity_id_to_internal_name_identifier = (
        _discover_wikibase_entities_by_name_identifier(
            internal_name_identifiers=sorted(
                compilation.by_internal_name_identifier.keys()
            ),
            name_identifier_property_id=name_identifier_property_id,
            sparql_endpoint=sparql_endpoint,
        )
    )
    anchor_hint_entity_id_to_internal_name_identifier = (
        _load_wikibase_init_anchor_hints_from_local_root(
            local_root=resolved_local_root,
            compilation=compilation,
        )
    )

    api_client = WikibaseApiClient(api_url=api_url)
    candidate_entity_ids = sorted(
        set(entity_id_to_internal_name_identifier.keys())
        | set(anchor_hint_entity_id_to_internal_name_identifier.keys())
    )
    fetched_entities = api_client.get_entities(candidate_entity_ids)
    current_entities: dict[str, dict[str, Any]] = {}
    validated_entity_id_to_internal_name_identifier: dict[str, str] = {}

    for entity_id, entity_payload in fetched_entities.items():
        if not isinstance(entity_payload, dict):
            continue
        name_identifier_values = _extract_name_identifier_values_from_entity(
            entity_payload,
            name_identifier_property_id=name_identifier_property_id,
        )
        for internal_name_identifier in name_identifier_values:
            if internal_name_identifier in compilation.by_internal_name_identifier:
                current_entities[internal_name_identifier] = entity_payload
                validated_entity_id_to_internal_name_identifier[entity_id] = (
                    internal_name_identifier
                )

    for (
        entity_id,
        internal_name_identifier,
    ) in anchor_hint_entity_id_to_internal_name_identifier.items():
        if internal_name_identifier in current_entities:
            continue
        entity_payload = fetched_entities.get(entity_id)
        if isinstance(entity_payload, dict):
            current_entities[internal_name_identifier] = entity_payload
            validated_entity_id_to_internal_name_identifier[entity_id] = (
                internal_name_identifier
            )

    comparison_source = {
        "mode": "live-compare-name-identifier",
        "api_url": api_url,
        "local_root": str(resolved_local_root),
        "artifact_file": None,
        "name_identifier_property_id": name_identifier_property_id,
        "sparql_endpoint": sparql_endpoint,
        "sparql_candidate_count": len(entity_id_to_internal_name_identifier),
        "anchor_hint_count": len(anchor_hint_entity_id_to_internal_name_identifier),
        "resolved_entity_count": len(current_entities),
    }
    comparison_entity_id_to_internal_name_identifier = {}
    if "_name_identifier" in compilation.by_internal_name_identifier:
        comparison_entity_id_to_internal_name_identifier[
            name_identifier_property_id
        ] = "_name_identifier"
    comparison_entity_id_to_internal_name_identifier.update(
        anchor_hint_entity_id_to_internal_name_identifier
    )
    comparison_entity_id_to_internal_name_identifier.update(
        entity_id_to_internal_name_identifier
    )
    comparison_entity_id_to_internal_name_identifier.update(
        validated_entity_id_to_internal_name_identifier
    )
    return (
        current_entities,
        comparison_entity_id_to_internal_name_identifier,
        comparison_source,
    )


def _load_wikibase_init_anchor_hints_from_local_root(
    *,
    local_root: Path,
    compilation,
) -> dict[str, str]:
    """Load non-authoritative entity-id hints from local semantic anchors when present."""

    layout = resolve_spiritsafe_layout(local_root)
    artifact_path = layout.semantic_anchors_file(local_root)
    if not artifact_path.is_file():
        return {}

    try:
        anchor_document = json.loads(artifact_path.read_text(encoding="utf-8"))
        resolver = build_spiritsafe_semantic_anchor_resolver(
            anchor_document,
            artifact_path=artifact_path,
        )
    except Exception:
        return {}

    hints: dict[str, str] = {}
    for internal_name_identifier in compilation.by_internal_name_identifier.keys():
        anchor = resolver.anchors.get(internal_name_identifier)
        if anchor is None:
            continue
        hints[anchor.entity_id] = internal_name_identifier
    return hints


def _discover_wikibase_entities_by_name_identifier(
    *,
    internal_name_identifiers: list[str],
    name_identifier_property_id: str,
    sparql_endpoint: str,
) -> dict[str, str]:
    """Resolve live entity ids by querying the configured name_identifier property."""

    if not internal_name_identifiers:
        return {}

    results: dict[str, str] = {}
    batch_size = 25
    for start in range(0, len(internal_name_identifiers), batch_size):
        batch = internal_name_identifiers[start : start + batch_size]
        values = " ".join(json.dumps(value) for value in batch)
        query = (
            "SELECT ?entity ?nameIdentifier WHERE { "
            f"VALUES ?nameIdentifier {{ {values} }} "
            f"?entity wdt:{name_identifier_property_id} ?nameIdentifier . "
            "}"
        )
        payload = execute_sparql(query, endpoint=sparql_endpoint)
        bindings = payload.get("results", {}).get("bindings", [])
        if not isinstance(bindings, list):
            continue
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            entity_value = binding.get("entity", {}).get("value")
            name_identifier = binding.get("nameIdentifier", {}).get("value")
            entity_id = _entity_id_from_wikibase_uri(entity_value)
            if entity_id and isinstance(name_identifier, str) and name_identifier:
                results[entity_id] = name_identifier

    return results


def _entity_id_from_wikibase_uri(entity_uri: Any) -> str | None:
    """Extract a Q/P identifier from a Wikibase entity URI."""

    if not isinstance(entity_uri, str) or not entity_uri:
        return None
    candidate = entity_uri.rstrip("/").split("/")[-1]
    if candidate[:1] in {"Q", "P"} and candidate[1:].isdigit():
        return candidate
    return None


def _extract_name_identifier_values_from_entity(
    entity_payload: dict[str, Any],
    *,
    name_identifier_property_id: str,
) -> set[str]:
    """Extract string name_identifier values from one fetched Wikibase entity."""

    claims = entity_payload.get("claims")
    if not isinstance(claims, dict):
        return set()

    raw_claims = claims.get(name_identifier_property_id)
    if not isinstance(raw_claims, list):
        return set()

    values: set[str] = set()
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        datavalue = claim.get("mainsnak", {}).get("datavalue", {})
        value = datavalue.get("value")
        if isinstance(value, str) and value:
            values.add(value)

    return values


def _select_wikibase_init_sample_entity(compilation, selector: str):
    """Resolve one compiled entity by key or internal name identifier."""

    sample_entity = compilation.entities.get(selector)
    if sample_entity is not None:
        return sample_entity

    sample_entity = compilation.by_internal_name_identifier.get(selector)
    if sample_entity is not None:
        return sample_entity

    raise CLIError(
        f"Unknown seed entity '{selector}'. Use a fixture key like 'entity_profile' "
        "or an internal name identifier like '_entity_profile'."
    )


def _wikibase_init_entity_label(payload: dict[str, Any]) -> str:
    """Return a human-facing label for one compiled seed payload."""

    labels = payload.get("labels")
    if isinstance(labels, dict):
        for language_payload in labels.values():
            if isinstance(language_payload, dict):
                value = language_payload.get("value")
                if isinstance(value, str) and value:
                    return value
    return ""


def _resolve_command_language(configured_language: str | None) -> str:
    """Resolve the language used by the command after optional overrides."""

    if isinstance(configured_language, str) and configured_language.strip():
        return configured_language.strip()

    current_languages = gkc.get_languages()
    if isinstance(current_languages, str):
        candidate = current_languages.strip()
        return candidate if candidate and candidate != "all" else "en"
    if isinstance(current_languages, list):
        for candidate in current_languages:
            if isinstance(candidate, str):
                candidate = candidate.strip()
                if candidate and candidate != "all":
                    return candidate
    return "en"


def _emit_output(output: dict[str, Any], json_output: bool, verbose: bool) -> None:
    if json_output:
        print(json.dumps(output))
        return

    message = output.get("message", "")
    if message:
        print(message)

    # Show details for summary format or when verbose is requested
    details = output.get("details") or {}
    command = output.get("command", "")

    if verbose and command == "wikibase.init" and details:
        if message:
            print()

        summary = details.get("summary") or {}
        print(
            "plan: "
            f"created={summary.get('created', 0)}, "
            f"updated={summary.get('updated', 0)}, "
            f"dry_run={summary.get('dry_run', 0)}, "
            f"skipped={summary.get('skipped', 0)}"
        )

        actions = details.get("actions") or []
        if isinstance(actions, list):
            max_actions = 20
            for action in actions[:max_actions]:
                if not isinstance(action, dict):
                    continue
                action_state = action.get("action", "?")
                kind = action.get("kind", "?")
                label = action.get("label", "")
                entity_id = action.get("entity_id") or "-"
                action_details = action.get("details", "")
                print(
                    f"- {action_state:8} {kind:8} {label} "
                    f"(id={entity_id}) :: {action_details}"
                )

                request_payload = action.get("request_payload")
                if request_payload:
                    print("  payload: " + json.dumps(request_payload, sort_keys=True))

            if len(actions) > max_actions:
                print(f"... ({len(actions) - max_actions} more actions)")

        if details.get("output_file"):
            print(f"output_file: {details['output_file']}")
        return

    if details and (verbose or output.get("command", "").endswith(".qid")):
        if verbose and message:
            # Add blank line before details if message was printed
            print()
        for key, value in details.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
