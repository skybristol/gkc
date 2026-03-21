"""Command line interface for GKC.

Plain meaning: Run GKC tasks from the terminal.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any, Optional

import requests

import gkc
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth
from gkc.mash import (
    WikibaseApiClient,
    WikibaseLoader,
    WikipediaLoader,
    apply_item_property_filters,
    apply_template_language_filter,
    get_latest_cache_timestamp,
    refresh_entity_cache_from_recentchanges,
)
from gkc.profiles import FormSchemaGenerator, ProfileLoader, ProfileValidator
from gkc.runtime_config import get_wikibase_runtime_config
from gkc.shipper import WikibaseShipper
from gkc.sparql import fetch_entity_labels
from gkc.spirit_safe import (
    build_entity_profile_json_documents,
    export_entity_profile_json_documents,
    export_spiritsafe_entity_index,
    export_spiritsafe_manifest,
    get_spirit_safe_source,
    load_manifest,
    load_profile,
    load_profile_package,
    validate_packet_structure,
)
from gkc.still_charger import create_curation_packet
from gkc.wikibase import (
    build_wikibase_cache,
    build_wikibase_write_plan,
    execute_wikibase_write_plan,
    export_profile_graph_to_entity_cache,
)


class CLIError(Exception):
    """Raised when CLI execution fails.

    Plain meaning: The CLI could not complete the requested command.
    """


def _normalize_global_flag_positions(argv: list[str]) -> list[str]:
    """Allow global flags to be passed after nested subcommands.

    Moves known global flags to the front while preserving relative order,
    so invocations like ``gkc wikibase init --verbose`` are accepted.
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

    profile_validate = profile_subparsers.add_parser(
        "validate", help="Validate a Wikidata item against a YAML profile"
    )
    profile_validate.add_argument(
        "--profile",
        required=True,
        help="Path to YAML profile definition",
    )
    profile_validate.add_argument(
        "--qid",
        help="Wikidata item ID to fetch and validate",
    )
    profile_validate.add_argument(
        "--item-json",
        help="Path to Wikidata item JSON file",
    )
    profile_validate.add_argument(
        "--policy",
        choices=["strict", "lenient"],
        default="lenient",
        help="Validation policy (default: lenient)",
    )
    _add_profile_source_args(profile_validate)
    profile_validate.set_defaults(
        handler=_handle_profile_validate,
        command_path="profile.validate",
    )

    profile_form = profile_subparsers.add_parser(
        "form-schema", help="Generate a form schema from a YAML profile"
    )
    profile_form.add_argument(
        "--profile",
        required=True,
        help="Path to YAML profile definition",
    )
    profile_form.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write output to file instead of stdout",
    )
    _add_profile_source_args(profile_form)
    profile_form.set_defaults(
        handler=_handle_profile_form_schema,
        command_path="profile.form_schema",
    )

    profile_export_json = profile_subparsers.add_parser(
        "export-json",
        help="Build JSON entity profiles from SpiritSafe cache entities",
    )
    profile_export_json.add_argument(
        "--cache-entities-dir",
        help=(
            "Directory containing SpiritSafe cache entity JSON files "
            "(defaults to <local_root>/cache/entities when using --source local)"
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
            "(defaults to <cache_entities_dir>/../refresh/last_run_summary.json)"
        ),
    )
    _add_profile_source_args(profile_export_json)
    profile_export_json.set_defaults(
        handler=_handle_profile_export_json,
        command_path="profile.export_json",
    )

    profile_run_form = profile_subparsers.add_parser(
        "form", help="Launch an interactive Streamlit wizard for a JSON profile"
    )
    profile_run_form.add_argument(
        "--profile",
        required=True,
        help="Profile reference (QID or full profile entity URI)",
    )
    profile_run_form.add_argument(
        "--qid",
        help="Optional Wikidata item ID for editing an existing item",
    )
    profile_run_form.add_argument(
        "--packet",
        help="Path to curation packet JSON file for multi-entity workflow",
    )
    profile_run_form.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Related profile depth when creating packet on-the-fly (default: 1)",
    )
    _add_profile_source_args(profile_run_form)
    profile_run_form.set_defaults(
        handler=_handle_profile_form,
        command_path="profile.form",
    )

    profile_lookups = profile_subparsers.add_parser(
        "lookups", help="Profile lookup hydration utilities"
    )
    profile_lookups_subparsers = profile_lookups.add_subparsers(
        dest="profile_lookups_command"
    )

    profile_lookups_hydrate = profile_lookups_subparsers.add_parser(
        "hydrate", help="Hydrate SPARQL lookup caches from profile definitions"
    )
    profile_lookups_hydrate.add_argument(
        "--profile",
        action="append",
        required=True,
        help="Path to profile YAML (repeatable)",
    )
    profile_lookups_hydrate.add_argument(
        "--refresh",
        choices=["manual", "daily", "weekly", "on_release"],
        help="Optional refresh policy override",
    )
    profile_lookups_hydrate.add_argument(
        "--force-refresh",
        action="store_true",
        help="Refresh queries even when cache appears fresh",
    )
    profile_lookups_hydrate.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Query page size for pagination (default: 1000)",
    )
    profile_lookups_hydrate.add_argument(
        "--max-results",
        type=int,
        help="Maximum total results per query",
    )
    profile_lookups_hydrate.add_argument(
        "--endpoint",
        default=runtime_config.sparql_endpoint,
        help=(
            "SPARQL endpoint URL "
            "(default: DD_WB_SPARQL_ENDPOINT env var or Wikidata Query Service)"
        ),
    )
    profile_lookups_hydrate.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and summarize lookups without executing queries",
    )
    profile_lookups_hydrate.add_argument(
        "--fail-on-query-error",
        action="store_true",
        help="Fail immediately when any query preparation/execution errors occur",
    )
    profile_lookups_hydrate.add_argument(
        "--source",
        choices=["github", "local"],
        help="Override SpiritSafe source mode for this command",
    )
    profile_lookups_hydrate.add_argument(
        "--local-root",
        help="Local SpiritSafe root (required with --source local)",
    )
    profile_lookups_hydrate.add_argument(
        "--repo",
        help="GitHub repo slug when --source github (e.g., owner/SpiritSafe)",
    )
    profile_lookups_hydrate.add_argument(
        "--ref",
        dest="github_ref",
        help="Git reference when --source github (default: main)",
    )
    profile_lookups_hydrate.set_defaults(
        handler=_handle_profile_lookups_hydrate,
        command_path="profile.lookups.hydrate",
    )

    profile_value_lists = profile_subparsers.add_parser(
        "value-lists", help="Value-list query extraction and hydration utilities"
    )
    profile_value_lists_subparsers = profile_value_lists.add_subparsers(
        dest="profile_value_lists_command"
    )

    profile_value_lists_hydrate = profile_value_lists_subparsers.add_parser(
        "hydrate",
        help="Extract talk-page SPARQL queries for GKC Value Lists and hydrate cache",
    )
    profile_value_lists_hydrate.add_argument(
        "--cache-entities-dir",
        help=(
            "Directory containing SpiritSafe cache entity JSON files "
            "(defaults to <local_root>/cache/entities when using --source local)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--queries-dir",
        help=(
            "Directory to write SPARQL query files "
            "(defaults to <local_root>/queries when using --source local)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--cache-queries-dir",
        help=(
            "Directory to write hydrated value-list cache JSON "
            "(defaults to <local_root>/cache/queries when using --source local)"
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
            "(default: DD_WB_API_URL or Data Distillery API)"
        ),
    )
    profile_value_lists_hydrate.add_argument(
        "--endpoint",
        default=runtime_config.sparql_endpoint,
        help=(
            "SPARQL endpoint URL used for hydration "
            "(default: DD_WB_SPARQL_ENDPOINT env var or Wikidata Query Service)"
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

    profile_package_cardinality = profile_package_subparsers.add_parser(
        "cardinality", help="Show cardinality report for profile linkages"
    )
    profile_package_cardinality.add_argument(
        "--profile",
        required=True,
        help="Profile ID to analyze",
    )
    profile_package_cardinality.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Depth of related profiles to include (default: 1)",
    )
    _add_profile_source_args(profile_package_cardinality)
    profile_package_cardinality.set_defaults(
        handler=_handle_profile_package_cardinality,
        command_path="profile.package.cardinality",
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
        "validate", help="Validate manifest structure"
    )
    _add_profile_source_args(registry_validate)
    registry_validate.set_defaults(
        handler=_handle_registry_validate,
        command_path="registry.validate",
    )

    spiritsafe_parser = subparsers.add_parser(
        "spiritsafe", help="SpiritSafe artifact operations"
    )
    spiritsafe_subparsers = spiritsafe_parser.add_subparsers(dest="spiritsafe_command")

    spiritsafe_manifest = spiritsafe_subparsers.add_parser(
        "manifest", help="Build and inspect SpiritSafe manifests"
    )
    spiritsafe_manifest_subparsers = spiritsafe_manifest.add_subparsers(
        dest="spiritsafe_manifest_command"
    )

    spiritsafe_manifest_build = spiritsafe_manifest_subparsers.add_parser(
        "build", help="Build cache/manifest.json from local SpiritSafe artifacts"
    )
    spiritsafe_manifest_build.add_argument(
        "-o",
        "--output",
        help="Optional output path for the manifest JSON file",
    )
    _add_profile_source_args(spiritsafe_manifest_build)
    spiritsafe_manifest_build.set_defaults(
        handler=_handle_spiritsafe_manifest_build,
        command_path="spiritsafe.manifest.build",
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
        required=True,
        help="Path to curation packet JSON file",
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
        help="JSON file mapping entity IDs to QIDs (optional)",
    )
    packet_charge.add_argument(
        "-o",
        "--output",
        help="Write charged packet to file (JSON) instead of stdout",
    )
    packet_charge.set_defaults(
        handler=_handle_packet_charge,
        command_path="packet.charge",
    )

    # Wikibase commands
    wikibase_parser = subparsers.add_parser(
        "wikibase", help="Data Distillery Wikibase operations"
    )
    wikibase_subparsers = wikibase_parser.add_subparsers(dest="wikibase_command")

    wikibase_plan_write = wikibase_subparsers.add_parser(
        "plan-write",
        help="Build and inspect packet->charge->barrel write plan",
    )
    wikibase_plan_write.add_argument(
        "--profile",
        required=True,
        help="Primary profile ID for packet generation",
    )
    wikibase_plan_write.add_argument(
        "--source-values-file",
        required=True,
        help="Path to JSON mapping of entity/profile IDs to values for charging",
    )
    wikibase_plan_write.add_argument(
        "--property-map-file",
        help="Optional path to JSON mapping statement IDs to property IDs",
    )
    wikibase_plan_write.add_argument(
        "--mode",
        choices=["single", "bulk"],
        default="single",
        help="Packet operation mode (default: single)",
    )
    wikibase_plan_write.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Related profile depth when mode=bulk (default: 1)",
    )
    wikibase_plan_write.add_argument(
        "--strict-charging",
        action="store_true",
        help="Disable specificationless charging (unknown statements become errors)",
    )
    wikibase_plan_write.add_argument(
        "--with-shipper-plan",
        action="store_true",
        help="Also run shipper.plan_batch and include diff summary",
    )
    wikibase_plan_write.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_plan_write.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for Data Distillery credentials if not found",
    )
    wikibase_plan_write.add_argument(
        "--require-auth",
        action="store_true",
        help="Fail if authenticated shipper planning cannot be established",
    )
    wikibase_plan_write.add_argument(
        "--output",
        help="Optional path to write full plan JSON",
    )
    _add_profile_source_args(wikibase_plan_write)
    wikibase_plan_write.set_defaults(
        handler=_handle_wikibase_plan_write,
        command_path="wikibase.plan-write",
    )

    wikibase_execute_write = wikibase_subparsers.add_parser(
        "execute-write",
        help="Replay packet->charge->barrel operations through shipper writes",
    )
    wikibase_execute_write.add_argument(
        "--profile",
        required=True,
        help="Primary profile ID for packet generation",
    )
    wikibase_execute_write.add_argument(
        "--source-values-file",
        required=True,
        help="Path to JSON mapping of entity/profile IDs to values for charging",
    )
    wikibase_execute_write.add_argument(
        "--property-map-file",
        help="Optional path to JSON mapping statement IDs to property IDs",
    )
    wikibase_execute_write.add_argument(
        "--mode",
        choices=["single", "bulk"],
        default="single",
        help="Packet operation mode (default: single)",
    )
    wikibase_execute_write.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Related profile depth when mode=bulk (default: 1)",
    )
    wikibase_execute_write.add_argument(
        "--strict-charging",
        action="store_true",
        help="Disable specificationless charging (unknown statements become errors)",
    )
    wikibase_execute_write.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_execute_write.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for Data Distillery credentials if not found",
    )
    wikibase_execute_write.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview write submissions without posting changes (default: true)",
    )
    wikibase_execute_write.add_argument(
        "--execute",
        action="store_true",
        help="Submit writes to Wikibase (overrides dry-run default)",
    )
    wikibase_execute_write.add_argument(
        "--bot",
        action="store_true",
        help="Mark writes as bot edits",
    )
    wikibase_execute_write.add_argument(
        "--summary",
        default="gkc wikibase execute-write",
        help="Edit summary prefix used for each write operation",
    )
    wikibase_execute_write.add_argument(
        "--output",
        help="Optional path to write full execute JSON",
    )
    _add_profile_source_args(wikibase_execute_write)
    wikibase_execute_write.set_defaults(
        handler=_handle_wikibase_execute_write,
        command_path="wikibase.execute-write",
    )

    wikibase_profile_to_cache = wikibase_subparsers.add_parser(
        "profile-to-cache",
        help="Fetch profile-linked Wikibase entities and write per-entity cache files",
    )
    wikibase_profile_to_cache.add_argument(
        "--profile-id",
        action="append",
        dest="profile_ids",
        required=True,
        help="Root profile QID (repeatable)",
    )
    wikibase_profile_to_cache.add_argument(
        "--cache-dir",
        required=True,
        help="Output directory for per-entity cache files",
    )
    wikibase_profile_to_cache.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_profile_to_cache.add_argument(
        "--source-endpoint",
        help="Optional source endpoint label recorded in cache metadata",
    )
    wikibase_profile_to_cache.add_argument(
        "--default-language",
        default="mul",
        help="Default language used for traversal diagnostics (default: mul)",
    )
    wikibase_profile_to_cache.add_argument(
        "--max-hops",
        type=int,
        default=5,
        help="Maximum traversal depth from profile roots (default: 5)",
    )
    wikibase_profile_to_cache.add_argument(
        "--workflow-mode",
        default="profile-entry",
        help="Workflow mode label stored in cache metadata",
    )
    wikibase_profile_to_cache.add_argument(
        "--output",
        help="Optional output path for export summary JSON",
    )
    wikibase_profile_to_cache.set_defaults(
        handler=_handle_wikibase_profile_to_cache,
        command_path="wikibase.profile-to-cache",
    )

    wikibase_cache_builder = wikibase_subparsers.add_parser(
        "cache-builder",
        help=(
            "Build and reconcile per-entity cache files from SPARQL-derived "
            "profile-linked identifiers"
        ),
    )
    wikibase_cache_builder.add_argument(
        "--cache-dir",
        required=True,
        help="Directory containing per-entity cache files",
    )
    wikibase_cache_builder.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_cache_builder.add_argument(
        "--sparql-endpoint",
        default=runtime_config.sparql_endpoint,
        help=(
            "SPARQL endpoint URL "
            "(default: DD_WB_SPARQL_ENDPOINT env var or Wikidata Query Service)"
        ),
    )
    wikibase_cache_builder.add_argument(
        "--wikibase-base-uri",
        default="https://datadistillery.wikibase.cloud",
        help="Wikibase base URI used to identify local Q/P IDs",
    )
    wikibase_cache_builder.add_argument(
        "--profile-class-id",
        default="Q3",
        help="Profile class item ID used as SPARQL root classifier (default: Q3)",
    )
    wikibase_cache_builder.add_argument(
        "--source-endpoint",
        help="Optional source endpoint label recorded in cache metadata",
    )
    wikibase_cache_builder.add_argument(
        "--workflow-mode",
        default="cache-builder",
        help="Workflow mode label stored in cache metadata",
    )
    wikibase_cache_builder.add_argument(
        "--output",
        help="Optional output path for cache build summary JSON",
    )
    wikibase_cache_builder.set_defaults(
        handler=_handle_wikibase_cache_builder,
        command_path="wikibase.cache-builder",
    )

    wikibase_check_for_revisions = wikibase_subparsers.add_parser(
        "check-for-revisions",
        help="Poll recentchanges and refresh per-entity cache files",
    )
    wikibase_check_for_revisions.add_argument(
        "--cache-dir",
        required=True,
        help="Directory containing per-entity cache files",
    )
    wikibase_check_for_revisions.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_check_for_revisions.add_argument(
        "--source-endpoint",
        help="Optional source endpoint label recorded in refreshed cache metadata",
    )
    wikibase_check_for_revisions.add_argument(
        "--since",
        help="Explicit recentchanges watermark timestamp (ISO 8601)",
    )
    wikibase_check_for_revisions.add_argument(
        "--overlap-seconds",
        type=int,
        default=60,
        help="Safety overlap window applied to watermark polling (default: 60)",
    )
    wikibase_check_for_revisions.add_argument(
        "--ignore-id",
        action="append",
        dest="ignore_ids",
        help="Entity ID to ignore during change refresh (repeatable)",
    )
    wikibase_check_for_revisions.add_argument(
        "--output",
        help="Optional output path for refresh summary JSON",
    )
    wikibase_check_for_revisions.set_defaults(
        handler=_handle_wikibase_check_for_revisions,
        command_path="wikibase.check-for-revisions",
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


def _add_profile_source_args(parser: argparse.ArgumentParser) -> None:
    """Add SpiritSafe source override args for profile-loading commands."""
    parser.add_argument(
        "--source",
        choices=["github", "local"],
        help="Override SpiritSafe source mode for this command",
    )
    parser.add_argument(
        "--local-root",
        help="Local SpiritSafe root (required with --source local)",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo slug when --source github (e.g., owner/SpiritSafe)",
    )
    parser.add_argument(
        "--ref",
        dest="github_ref",
        help="Git reference when --source github (default: main)",
    )


def _apply_source_override(args: argparse.Namespace) -> tuple[Any, bool]:
    """Apply temporary SpiritSafe source override from CLI args."""
    previous_source = gkc.get_spirit_safe_source()
    source_overridden = getattr(args, "source", None) is not None

    if source_overridden:
        if args.source == "local":
            if not args.local_root:
                raise CLIError("--local-root is required when --source local")
            gkc.set_spirit_safe_source(mode="local", local_root=args.local_root)
        else:
            gkc.set_spirit_safe_source(
                mode="github",
                github_repo=args.repo or previous_source.github_repo,
                github_ref=args.github_ref or previous_source.github_ref,
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


def _preferred_manifest_text(values: Any) -> str:
    """Pick a curator-facing string from a multilingual manifest text map."""

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


def _load_profile_from_reference(
    loader: ProfileLoader,
    profile_ref: str,
) -> tuple[Any, str]:
    """Load profile from path or SpiritSafe profile reference.

    Returns:
        Tuple of (ProfileDefinition, resolved profile reference).
    """
    resolved_profile = gkc.resolve_profile_path(profile_ref)
    resolved_profile_str = str(resolved_profile)

    try:
        profile = loader.load_from_file(resolved_profile_str)
        return profile, resolved_profile_str
    except FileNotFoundError:
        source = gkc.get_spirit_safe_source()
        resolved = source.resolve_relative(resolved_profile_str)

        if isinstance(resolved, Path):
            profile = loader.load_from_file(resolved)
            return profile, str(resolved)

        response = requests.get(resolved, timeout=30)
        response.raise_for_status()
        profile = loader.load_from_text(response.text)
        return profile, resolved_profile_str


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


def _handle_profile_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate a Wikidata item against a YAML profile."""
    if not args.qid and not args.item_json:
        raise CLIError("Provide either --qid or --item-json")
    if args.qid and args.item_json:
        raise CLIError("Use only one of --qid or --item-json")

    previous_source, source_overridden = _apply_source_override(args)

    try:
        loader = ProfileLoader()
        profile, resolved_profile = _load_profile_from_reference(loader, args.profile)

        if args.qid:
            item = WikibaseLoader().load_item(args.qid)
            entity_data = item.to_dict()
            source = args.qid
        else:
            with open(args.item_json, "r") as f:
                entity_data = json.load(f)
            source = args.item_json

        validator = ProfileValidator(profile)
        result = validator.validate_item(entity_data, policy=args.policy)

        details = {
            "profile": profile.name,
            "profile_ref": resolved_profile,
            "policy": args.policy,
            "source": source,
            "errors": [issue.model_dump() for issue in result.errors],
            "warnings": [issue.model_dump() for issue in result.warnings],
        }

        if result.ok:
            message = "✓ Profile validation passed"
        else:
            message = "✗ Profile validation failed"

        return {
            "command": args.command_path,
            "ok": result.ok,
            "message": message,
            "details": details,
        }
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_profile_form_schema(args: argparse.Namespace) -> dict[str, Any]:
    """Generate form schema from a YAML profile."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        loader = ProfileLoader()
        profile, resolved_profile = _load_profile_from_reference(loader, args.profile)

        schema = FormSchemaGenerator(profile).build_schema()

        if args.output:
            with open(args.output, "w") as f:
                json.dump(schema, f, indent=2)
            message = f"Wrote form schema to {args.output}"
        else:
            print(json.dumps(schema))
            message = "Form schema generated"

        return {
            "command": args.command_path,
            "ok": True,
            "message": message,
            "details": {
                "profile": profile.name,
                "profile_ref": resolved_profile,
                "output": args.output or "stdout",
            },
        }
    finally:
        _restore_source_override(previous_source, source_overridden)


def _handle_profile_form(args: argparse.Namespace) -> dict[str, Any]:
    """Launch an interactive Streamlit wizard from a JSON profile or packet.

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
            from gkc.profiles.forms import streamlit_app
        except ImportError as exc:
            raise CLIError(
                "Streamlit UI dependencies are unavailable. Install `streamlit` to use "
                "`gkc profile form`."
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
                cache_entities_dir = source.local_root / "cache" / "entities"
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


def _handle_profile_lookups_hydrate(args: argparse.Namespace) -> dict[str, Any]:
    """Hydrate SPARQL lookup caches from one or more profile YAML files."""
    if not args.profile:
        raise CLIError("Provide at least one --profile path")

    previous_source = gkc.get_spirit_safe_source()
    source_overridden = args.source is not None

    try:
        if source_overridden:
            if args.source == "local":
                if not args.local_root:
                    raise CLIError("--local-root is required when --source local")
                gkc.set_spirit_safe_source(mode="local", local_root=args.local_root)
            else:
                gkc.set_spirit_safe_source(
                    mode="github",
                    github_repo=args.repo or previous_source.github_repo,
                    github_ref=args.github_ref or previous_source.github_ref,
                )

        # Resolve profile names to full paths
        resolved_profiles = [gkc.resolve_profile_path(p) for p in args.profile]

        summary = gkc.hydrate_profile_lookups(
            profile_paths=resolved_profiles,
            refresh_policy=args.refresh,
            force_refresh=args.force_refresh,
            page_size=args.page_size,
            max_results=args.max_results,
            endpoint=args.endpoint,
            dry_run=args.dry_run,
            fail_on_query_error=args.fail_on_query_error,
        )
    except Exception as exc:
        raise CLIError(str(exc)) from exc
    finally:
        if source_overridden:
            gkc.set_spirit_safe_source(
                mode=previous_source.mode,
                github_repo=previous_source.github_repo,
                github_ref=previous_source.github_ref,
                local_root=previous_source.local_root,
            )

    failures = summary.get("failures", [])
    ok = len(failures) == 0

    if args.dry_run:
        message = (
            "Dry run complete: "
            f"{summary['lookup_specs_found']} lookup specs, "
            f"{summary['unique_queries']} unique queries"
        )
    else:
        message = (
            "Hydration complete: "
            f"{summary['unique_queries_executed']} unique queries executed"
        )

    if failures:
        message += f" ({len(failures)} failures)"

    details = {
        "profiles_scanned": summary.get("profiles_scanned"),
        "lookup_specs_found": summary.get("lookup_specs_found"),
        "unique_queries": summary.get("unique_queries"),
        "unique_queries_executed": summary.get("unique_queries_executed"),
        "cache_dir": summary.get("cache_dir"),
        "cache_file_count": summary.get("cache_file_count"),
        "failures": failures,
    }

    return {
        "command": args.command_path,
        "ok": ok,
        "message": message,
        "details": details,
    }


def _handle_profile_value_lists_hydrate(args: argparse.Namespace) -> dict[str, Any]:
    """Extract value-list SPARQL and hydrate cache/queries artifacts."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        cache_entities_dir: Optional[Path]
        queries_dir: Optional[Path]
        cache_queries_dir: Optional[Path]

        if args.cache_entities_dir:
            cache_entities_dir = Path(args.cache_entities_dir)
        else:
            source = gkc.get_spirit_safe_source()
            cache_entities_dir = (
                source.local_root / "cache" / "entities"
                if source.mode == "local" and source.local_root is not None
                else None
            )

        if args.queries_dir:
            queries_dir = Path(args.queries_dir)
        else:
            source = gkc.get_spirit_safe_source()
            queries_dir = (
                source.local_root / "queries"
                if source.mode == "local" and source.local_root is not None
                else None
            )

        if args.cache_queries_dir:
            cache_queries_dir = Path(args.cache_queries_dir)
        else:
            source = gkc.get_spirit_safe_source()
            cache_queries_dir = (
                source.local_root / "cache" / "queries"
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
    """List all profiles in the SpiritSafe artifact manifest."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        profiles = []

        for profile_id in manifest.profile_qids:
            entry = manifest.get_profile_entry(profile_id)
            if entry:
                profiles.append(
                    {
                        "qid": profile_id,
                        "entity": entry.get("entity"),
                        "label": _preferred_manifest_text(entry.get("labels", {})),
                        "description": _preferred_manifest_text(
                            entry.get("descriptions", {})
                        ),
                        "statement_count": entry.get("statement_count", 0),
                    }
                )

        message = f"Found {len(profiles)} profiles in registry"
        details = {
            "profiles": profiles,
            "generated_at": manifest.generated_at,
            "source": manifest.source,
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
    """Show detailed profile metadata from the artifact manifest."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        entry = manifest.get_profile_entry(args.profile)

        if not entry:
            raise CLIError(
                f"Profile '{args.profile}' not found. "
                f"Available: {', '.join(manifest.profile_qids)}"
            )

        profile_qid = entry.get("qid") or args.profile
        message = f"Profile: {_preferred_manifest_text(entry.get('labels', {})) or profile_qid}"
        details = {
            "qid": profile_qid,
            "entity": entry.get("entity"),
            "labels": entry.get("labels", {}),
            "descriptions": entry.get("descriptions", {}),
            "statement_count": entry.get("statement_count", 0),
            "profile_graph": entry.get("profile_graph", []),
            "value_list_graph": entry.get("value_list_graph", []),
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


def _handle_registry_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate artifact manifest structure."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        errors = []

        if not manifest.profiles:
            errors.append("No profiles found in manifest")

        for profile_id in manifest.profile_qids:
            entry = manifest.get_profile_entry(profile_id)
            if not entry:
                errors.append(f"Profile {profile_id} has no entry")
                continue

            if not entry.get("entity"):
                errors.append(f"Profile {profile_id} missing entity URI")
            if not isinstance(entry.get("profile_graph", []), list):
                errors.append(f"Profile {profile_id} has invalid profile_graph")
            if not isinstance(entry.get("value_list_graph", []), list):
                errors.append(f"Profile {profile_id} has invalid value_list_graph")

        if manifest.entities.get("count") != len(manifest.entities.get("qids", [])):
            errors.append("Manifest entities.count does not match entities.qids length")

        ok = len(errors) == 0
        message = "✓ Manifest is valid" if ok else "✗ Manifest validation failed"

        details = {
            "profile_count": len(manifest.profile_qids),
            "entity_count": manifest.entities.get("count", 0),
            "query_count": len(manifest.queries),
            "value_list_count": len(manifest.value_lists),
            "generated_at": manifest.generated_at,
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


def _handle_spiritsafe_manifest_build(args: argparse.Namespace) -> dict[str, Any]:
    """Build cache/manifest.json and cache/entity_index.json from local artifacts."""

    if args.source != "local" or not args.local_root:
        raise CLIError(
            "spirit_safe manifest build requires --source local --local-root /path/to/SpiritSafe"
        )

    try:
        local_root = Path(args.local_root).expanduser().resolve()
        output_path = (
            Path(args.output).expanduser().resolve()
            if args.output
            else local_root / "cache" / "manifest.json"
        )
        index_output_path = local_root / "cache" / "entity_index.json"
        manifest_document = export_spiritsafe_manifest(local_root, output_path)
        index_document = export_spiritsafe_entity_index(local_root, index_output_path)
        details = {
            "output_path": str(output_path),
            "entity_index_output_path": str(index_output_path),
            "profile_count": len(manifest_document.get("profiles", [])),
            "entity_count": manifest_document.get("entities", {}).get("count", 0),
            "query_count": len(manifest_document.get("queries", [])),
            "value_list_count": len(manifest_document.get("value_lists", [])),
            "indexed_entity_count": index_document.get("entity_count", 0),
            "indexed_class_count": index_document.get("class_count", 0),
        }
        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                f"Built SpiritSafe manifest at {output_path} "
                f"and entity index at {index_output_path}"
            ),
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


def _handle_profile_package_cardinality(args: argparse.Namespace) -> dict[str, Any]:
    """Show cardinality report for profile linkages."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        package = load_profile_package(args.profile, depth=args.depth)
        cardinality_info = []
        graph = package["graph"]
        for profile_id in package["profiles"].keys():
            for edge in graph.get_edges(profile_id):
                cardinality_info.append(
                    {
                        "from": profile_id,
                        "to": edge.target_profile,
                        "via": edge.via_statement,
                        "min": edge.cardinality.get("min", 0),
                        "max": edge.cardinality.get("max", -1),
                    }
                )

        message = f"Found {len(cardinality_info)} linkages with cardinality constraints"
        details = {
            "primary_profile": args.profile,
            "depth": args.depth,
            "cardinality_constraints": cardinality_info,
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
        if "graph" not in package:
            errors.append("Missing graph field")

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

    from gkc.still_charger import charge_packet_from_wikidata_items

    try:
        # Load the packet
        packet_path = Path(args.packet_file)
        if not packet_path.exists():
            raise CLIError(f"Packet file not found: {packet_path}")

        try:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CLIError(f"Invalid JSON in packet file: {exc}") from exc

        # Build QID mapping
        qid_map = {}

        if args.source == "wikidata":
            if args.qid:
                # Map all entities to the single QID
                for entity in packet.get("entities", []):
                    entity_id = entity.get("id")
                    profile_entity = entity.get("profile_entity")
                    if entity_id:
                        qid_map[entity_id] = args.qid
                    if profile_entity:
                        qid_map[profile_entity] = args.qid
            elif args.mapping_file:
                # Load mapping from file
                mapping_path = Path(args.mapping_file)
                if not mapping_path.exists():
                    raise CLIError(f"Mapping file not found: {mapping_path}")
                try:
                    qid_map = json.loads(mapping_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise CLIError(f"Invalid JSON in mapping file: {exc}") from exc
            else:
                raise CLIError(
                    "Either --qid or --mapping-file required for source=wikidata"
                )

        # Charge the packet
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
            "entities_charged": sum(
                1
                for e in charged_packet.get("entities", [])
                if e.get("data", {}).get("statements")
            ),
            "notices_error": error_count,
            "notices_warning": warning_count,
            "notices_info": info_count,
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


def _handle_wikibase_plan_write(args: argparse.Namespace) -> dict[str, Any]:
    """Build packet->charge->barrel write plan and show logical path."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        source_values_path = Path(args.source_values_file)
        if not source_values_path.exists():
            raise CLIError(f"Source values file not found: {source_values_path}")

        try:
            source_values = json.loads(source_values_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CLIError(f"Invalid JSON in source values file: {exc}") from exc

        if not isinstance(source_values, dict):
            raise CLIError("Source values JSON must be an object mapping IDs to values")

        property_id_map = None
        if args.property_map_file:
            property_map_path = Path(args.property_map_file)
            if not property_map_path.exists():
                raise CLIError(f"Property map file not found: {property_map_path}")
            try:
                raw_property_map = json.loads(
                    property_map_path.read_text(encoding="utf-8")
                )
            except json.JSONDecodeError as exc:
                raise CLIError(f"Invalid JSON in property map file: {exc}") from exc

            if not isinstance(raw_property_map, dict):
                raise CLIError("Property map JSON must be an object")

            property_id_map = {
                str(key).casefold(): str(value).upper()
                for key, value in raw_property_map.items()
            }

        shipper = None
        auth_mode = "anonymous"
        auth_warning: Optional[str] = None
        api_url = None

        if args.with_shipper_plan:
            runtime_config = get_wikibase_runtime_config()
            api_url = args.api_url or runtime_config.api_url

            auth = WikiverseAuth(
                username=runtime_config.username,
                password=runtime_config.password,
                interactive=args.interactive,
                api_url=api_url,
            )
            if auth.is_authenticated():
                try:
                    auth.login()
                    auth_mode = "authenticated"
                except AuthenticationError as exc:
                    if args.require_auth:
                        raise CLIError(str(exc)) from exc
                    auth_warning = (
                        "Authentication failed; shipper planning ran anonymously: "
                        f"{exc}"
                    )
            elif args.require_auth:
                raise CLIError(
                    "Authenticated shipper planning requested but no credentials "
                    "were provided (set DD_WB_USERNAME/DD_WB_PASSWORD or use --interactive)."
                )

            shipper = WikibaseShipper(auth=auth, api_url=api_url, dry_run_default=True)

        result = build_wikibase_write_plan(
            profile_id=args.profile,
            source_values=source_values,
            operation_mode=args.mode,
            depth=args.depth,
            specificationless=not args.strict_charging,
            property_id_map=property_id_map,
            shipper=shipper,
        )

        logical_path = [
            "still_charger.create_curation_packet",
            (
                "still_charger.charge_curation_packet"
                + (" [specificationless]" if not args.strict_charging else " [strict]")
            ),
            "wikibase.orchestration.barrel_curation_packet_to_wikibase_plan",
        ]

        if args.with_shipper_plan:
            logical_path.append("shipper.plan_batch")
        else:
            logical_path.append(
                "shipper.plan_batch (optional; not executed in this command)"
            )

        summary = {
            "packet_id": result.packet.get("packet_id"),
            "profile": args.profile,
            "operation_mode": args.mode,
            "depth": args.depth,
            "entities_in_packet": len(result.packet.get("entities", [])),
            "entities_charged": result.charge_report.entities_charged,
            "entities_skipped": result.charge_report.entities_skipped,
            "charge_issues": len(result.charge_report.issues),
            "operations_created": result.barrel_report.operations_created,
            "barrel_issues": len(result.barrel_report.issues),
        }

        operations_preview = result.operations[:10]
        output_payload = {
            "logical_path": logical_path,
            "summary": summary,
            "operations": result.operations,
            "charge_report": {
                "entities_charged": result.charge_report.entities_charged,
                "entities_skipped": result.charge_report.entities_skipped,
                "issues": [
                    {
                        "severity": issue.severity,
                        "entity_id": issue.entity_id,
                        "field": issue.field,
                        "message": issue.message,
                    }
                    for issue in result.charge_report.issues
                ],
            },
            "barrel_report": {
                "operations_created": result.barrel_report.operations_created,
                "entities_skipped": result.barrel_report.entities_skipped,
                "issues": [
                    {
                        "severity": issue.severity,
                        "entity_id": issue.entity_id,
                        "field": issue.field,
                        "message": issue.message,
                    }
                    for issue in result.barrel_report.issues
                ],
            },
        }

        if result.diff_plan is not None:
            output_payload["shipper_plan"] = result.diff_plan.to_dict()

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2), encoding="utf-8"
            )

        message = (
            "✓ Built write plan via shared pipeline "
            f"({summary['operations_created']} operation(s))"
        )

        details: dict[str, Any] = {
            "logical_path": logical_path,
            **summary,
            "operations_preview": operations_preview,
        }
        if result.diff_plan is not None:
            details["shipper_plan_summary"] = dict(result.diff_plan.summary)
            details["shipper_plan_preview"] = [
                operation.to_dict() for operation in result.diff_plan.operations[:10]
            ]
            details["auth_mode"] = auth_mode
            if api_url:
                details["api_url"] = api_url
            if auth_warning:
                details["warning"] = auth_warning
        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

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


def _handle_wikibase_execute_write(args: argparse.Namespace) -> dict[str, Any]:
    """Replay write operations from shared planning pipeline through shipper."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        source_values_path = Path(args.source_values_file)
        if not source_values_path.exists():
            raise CLIError(f"Source values file not found: {source_values_path}")

        try:
            source_values = json.loads(source_values_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CLIError(f"Invalid JSON in source values file: {exc}") from exc

        if not isinstance(source_values, dict):
            raise CLIError("Source values JSON must be an object mapping IDs to values")

        property_id_map = None
        if args.property_map_file:
            property_map_path = Path(args.property_map_file)
            if not property_map_path.exists():
                raise CLIError(f"Property map file not found: {property_map_path}")

            try:
                raw_property_map = json.loads(
                    property_map_path.read_text(encoding="utf-8")
                )
            except json.JSONDecodeError as exc:
                raise CLIError(f"Invalid JSON in property map file: {exc}") from exc

            if not isinstance(raw_property_map, dict):
                raise CLIError("Property map JSON must be an object")

            property_id_map = {
                str(key).casefold(): str(value).upper()
                for key, value in raw_property_map.items()
            }

        runtime_config = get_wikibase_runtime_config()
        api_url = args.api_url or runtime_config.api_url

        auth = WikiverseAuth(
            username=runtime_config.username,
            password=runtime_config.password,
            interactive=args.interactive,
            api_url=api_url,
        )

        # Execute-write is an authenticated promotion step by design.
        try:
            if auth.is_authenticated():
                auth.login()
            elif args.interactive:
                username = input(
                    "Enter Data Distillery username (format: Username@BotName): "
                ).strip()
                password = getpass.getpass("Enter Data Distillery password: ").strip()
                auth = WikiverseAuth(
                    username=username,
                    password=password,
                    interactive=False,
                    api_url=api_url,
                )
                auth.login()
            else:
                raise CLIError(
                    "Wikibase execute-write requires authentication; set DD_WB_USERNAME and DD_WB_PASSWORD or use --interactive"
                )
        except AuthenticationError as exc:
            if args.interactive:
                print("Authentication failed. Please enter new credentials.")
                username = input(
                    "Enter Data Distillery username (format: Username@BotName): "
                ).strip()
                password = getpass.getpass("Enter Data Distillery password: ").strip()
                auth = WikiverseAuth(
                    username=username,
                    password=password,
                    interactive=False,
                    api_url=api_url,
                )
                auth.login()
            else:
                raise CLIError(str(exc)) from exc

        shipper = WikibaseShipper(auth=auth, api_url=api_url, dry_run_default=True)
        dry_run = not args.execute

        result = execute_wikibase_write_plan(
            profile_id=args.profile,
            source_values=source_values,
            shipper=shipper,
            operation_mode=args.mode,
            depth=args.depth,
            specificationless=not args.strict_charging,
            property_id_map=property_id_map,
            write_summary=args.summary,
            dry_run=dry_run,
            bot=args.bot,
        )

        logical_path = [
            "still_charger.create_curation_packet",
            (
                "still_charger.charge_curation_packet"
                + (" [specificationless]" if not args.strict_charging else " [strict]")
            ),
            "wikibase.orchestration.barrel_curation_packet_to_wikibase_plan",
            "shipper.write_item/write_property",
        ]

        write_results_preview = [
            write_result.to_dict() for write_result in result.write_results[:10]
        ]

        summary = {
            "packet_id": result.plan.packet.get("packet_id"),
            "profile": args.profile,
            "operation_mode": args.mode,
            "depth": args.depth,
            "entities_in_packet": len(result.plan.packet.get("entities", [])),
            "entities_charged": result.plan.charge_report.entities_charged,
            "entities_skipped": result.plan.charge_report.entities_skipped,
            "charge_issues": len(result.plan.charge_report.issues),
            "operations_created": result.plan.barrel_report.operations_created,
            "barrel_issues": len(result.plan.barrel_report.issues),
            "write_summary": dict(result.write_summary),
            "dry_run": dry_run,
            "auth_mode": "authenticated",
            "api_url": api_url,
            "bot": bool(args.bot),
            "summary": args.summary,
        }

        output_payload = {
            "logical_path": logical_path,
            "summary": summary,
            "operations": result.plan.operations,
            "write_results": [
                write_result.to_dict() for write_result in result.write_results
            ],
            "charge_report": {
                "entities_charged": result.plan.charge_report.entities_charged,
                "entities_skipped": result.plan.charge_report.entities_skipped,
                "issues": [
                    {
                        "severity": issue.severity,
                        "entity_id": issue.entity_id,
                        "field": issue.field,
                        "message": issue.message,
                    }
                    for issue in result.plan.charge_report.issues
                ],
            },
            "barrel_report": {
                "operations_created": result.plan.barrel_report.operations_created,
                "entities_skipped": result.plan.barrel_report.entities_skipped,
                "issues": [
                    {
                        "severity": issue.severity,
                        "entity_id": issue.entity_id,
                        "field": issue.field,
                        "message": issue.message,
                    }
                    for issue in result.plan.barrel_report.issues
                ],
            },
        }

        if result.plan.diff_plan is not None:
            output_payload["shipper_plan"] = result.plan.diff_plan.to_dict()

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2), encoding="utf-8"
            )

        if dry_run:
            message = (
                "✓ Replayed write operations in DRY RUN mode "
                f"({result.write_summary['dry_run']} operation(s))"
            )
        else:
            message = (
                "✓ Submitted write operations "
                f"({result.write_summary['submitted']} submitted, "
                f"{result.write_summary['error']} error, "
                f"{result.write_summary['blocked']} blocked)"
            )

        details: dict[str, Any] = {
            "logical_path": logical_path,
            **summary,
            "operations_preview": result.plan.operations[:10],
            "write_results_preview": write_results_preview,
        }

        if result.plan.diff_plan is not None:
            details["shipper_plan_summary"] = dict(result.plan.diff_plan.summary)
            details["shipper_plan_preview"] = [
                operation.to_dict()
                for operation in result.plan.diff_plan.operations[:10]
            ]

        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

        ok = result.write_summary["error"] == 0 and result.write_summary["blocked"] == 0

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


def _handle_wikibase_profile_to_cache(args: argparse.Namespace) -> dict[str, Any]:
    """Export profile-linked Wikibase entities into per-entity cache files."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url

    try:
        api_client = WikibaseApiClient(api_url=api_url)
        export_result = export_profile_graph_to_entity_cache(
            profile_ids=list(args.profile_ids),
            api_client=api_client,
            cache_dir=args.cache_dir,
            default_language=args.default_language,
            max_hops=args.max_hops,
            source_endpoint=args.source_endpoint,
            workflow_mode=args.workflow_mode,
        )

        output_payload = {
            "metadata": {
                "api_url": api_url,
                "cache_dir": export_result.cache_dir,
                "profile_ids": list(args.profile_ids),
                "workflow_mode": args.workflow_mode,
                "default_language": args.default_language,
                "max_hops": args.max_hops,
            },
            "summary": {
                "written_count": len(export_result.written_ids),
                "skipped_count": len(export_result.skipped_ids),
                "fetched_count": len(export_result.graph.raw_items),
                "traversal_log_count": len(export_result.graph.traversal_log),
            },
            "written_ids": export_result.written_ids,
            "skipped_ids": export_result.skipped_ids,
            "traversal_log": export_result.graph.traversal_log,
        }

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(output_payload, indent=2),
                encoding="utf-8",
            )

        details: dict[str, Any] = {
            "api_url": api_url,
            "cache_dir": export_result.cache_dir,
            "profile_ids": list(args.profile_ids),
            "workflow_mode": args.workflow_mode,
            "default_language": args.default_language,
            "max_hops": args.max_hops,
            "written_count": len(export_result.written_ids),
            "skipped_count": len(export_result.skipped_ids),
            "fetched_count": len(export_result.graph.raw_items),
            "written_ids_preview": export_result.written_ids[:20],
            "skipped_ids_preview": export_result.skipped_ids[:20],
            "traversal_log_preview": export_result.graph.traversal_log[:20],
        }

        if args.output:
            details["output_file"] = str(Path(args.output).resolve())

        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                "✓ Profile-to-cache export complete: "
                f"{len(export_result.written_ids)} cached, "
                f"{len(export_result.skipped_ids)} skipped"
            ),
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_wikibase_cache_builder(args: argparse.Namespace) -> dict[str, Any]:
    """Run SPARQL-driven full cache build and reconciliation."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url

    summary_output = args.output
    if not summary_output:
        summary_output = str(
            Path(args.cache_dir).parent / "refresh" / "last_run_summary.json"
        )

    auth: Optional[WikiverseAuth] = None
    auth_mode = "anonymous"
    auth_warning: Optional[str] = None

    runtime_has_creds = bool(runtime_config.username and runtime_config.password)
    if runtime_has_creds:
        candidate = WikiverseAuth(
            username=runtime_config.username,
            password=runtime_config.password,
            interactive=False,
            api_url=api_url,
        )
        if candidate.is_authenticated():
            try:
                candidate.login()
                auth = candidate
                auth_mode = "authenticated"
            except AuthenticationError as exc:
                auth_warning = (
                    "Authentication failed; continuing anonymously for cache build: "
                    f"{exc}"
                )

    try:
        build_result = build_wikibase_cache(
            sparql_endpoint=args.sparql_endpoint,
            api_url=api_url,
            cache_dir=args.cache_dir,
            wikibase_base_uri=args.wikibase_base_uri,
            profile_class_id=args.profile_class_id,
            source_endpoint=args.source_endpoint,
            workflow_mode=args.workflow_mode,
            summary_output=summary_output,
            auth=auth,
        )

        details: dict[str, Any] = {
            "api_url": api_url,
            "sparql_endpoint": args.sparql_endpoint,
            "wikibase_base_uri": args.wikibase_base_uri,
            "profile_class_id": args.profile_class_id,
            "cache_dir": build_result.cache_dir,
            "summary_path": build_result.summary_path,
            "auth_mode": auth_mode,
            "queried_count": len(build_result.queried_ids),
            "fetched_count": len(build_result.fetched_ids),
            "written_count": len(build_result.written_ids),
            "new_count": len(build_result.new_ids),
            "changed_count": len(build_result.changed_ids),
            "unchanged_count": len(build_result.unchanged_ids),
            "deleted_count": len(build_result.deleted_ids),
            "missing_count": len(build_result.missing_ids),
            "new_ids_preview": build_result.new_ids[:20],
            "changed_ids_preview": build_result.changed_ids[:20],
            "deleted_ids_preview": build_result.deleted_ids[:20],
            "missing_ids_preview": build_result.missing_ids[:20],
        }
        if auth_warning:
            details["auth_warning"] = auth_warning

        return {
            "command": args.command_path,
            "ok": True,
            "message": (
                "✓ Wikibase cache build complete: "
                f"{len(build_result.written_ids)} written, "
                f"{len(build_result.deleted_ids)} deleted"
            ),
            "details": details,
        }
    except Exception as exc:
        raise CLIError(str(exc)) from exc


def _handle_wikibase_check_for_revisions(args: argparse.Namespace) -> dict[str, Any]:
    """Refresh entity cache files from MediaWiki recentchanges."""
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
