"""Command line interface for GKC.

Plain meaning: Run GKC tasks from the terminal.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

import gkc
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth
from gkc.mash import (
    WikibaseLoader,
    WikipediaLoader,
    apply_item_property_filters,
    apply_template_language_filter,
)
from gkc.profiles import FormSchemaGenerator, ProfileLoader, ProfileValidator
from gkc.runtime_config import get_wikibase_runtime_config
from gkc.sparql import fetch_entity_labels
from gkc.spirit_safe import (
    create_curation_packet,
    get_profile_graph,
    load_manifest,
    load_profile_package,
    validate_packet_structure,
)
from gkc.wikibase import (
    FoundationAuditError,
    FoundationInitError,
    FoundationProfileError,
    audit_wikibase_foundation,
    init_wikibase_foundation,
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
    profile_parser = subparsers.add_parser("profile", help="YAML profile utilities")
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

    profile_run_form = profile_subparsers.add_parser(
        "form", help="Launch an interactive Textual wizard for a YAML profile"
    )
    profile_run_form.add_argument(
        "--profile",
        required=True,
        help="Path to YAML profile definition",
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

    registry_search = registry_subparsers.add_parser(
        "search", help="Search profiles by keyword"
    )
    registry_search.add_argument(
        "keyword",
        help="Keyword to search for in profile names, descriptions, or tags",
    )
    _add_profile_source_args(registry_search)
    registry_search.set_defaults(
        handler=_handle_registry_search,
        command_path="registry.search",
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

    registry_graph = registry_subparsers.add_parser(
        "graph", help="Show profile graph relationships"
    )
    registry_graph.add_argument(
        "--profile",
        help="Optional profile ID to show neighbors for",
    )
    _add_profile_source_args(registry_graph)
    registry_graph.set_defaults(
        handler=_handle_registry_graph,
        command_path="registry.graph",
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

    # Wikibase commands
    wikibase_parser = subparsers.add_parser(
        "wikibase", help="Data Distillery Wikibase operations"
    )
    wikibase_subparsers = wikibase_parser.add_subparsers(dest="wikibase_command")

    wikibase_audit = wikibase_subparsers.add_parser(
        "audit", help="Audit a Wikibase instance against foundation profiles"
    )
    _add_wikiverse_args(wikibase_audit)
    wikibase_audit.add_argument(
        "--foundation-profiles",
        default=str(
            Path(__file__).resolve().parent / "wikibase" / "foundation_profiles"
        ),
        help="Path to foundation profile YAML directory",
    )
    wikibase_audit.add_argument(
        "--language",
        default="en",
        help="Language code for label matching (default: en)",
    )
    wikibase_audit.add_argument(
        "--output",
        help="Optional output path for full audit JSON report",
    )
    wikibase_audit.add_argument(
        "--require-auth",
        action="store_true",
        help="Fail if login with provided credentials does not succeed",
    )
    wikibase_audit.set_defaults(
        handler=_handle_wikibase_audit,
        command_path="wikibase.audit",
    )

    wikibase_init = wikibase_subparsers.add_parser(
        "init", help="Initialize a Wikibase instance with foundation ontology"
    )
    # Note: init is Data Distillery-only; no generic Wikiverse args
    wikibase_init.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for credentials if not found",
    )
    wikibase_init.add_argument(
        "--api-url",
        help="Override the Data Distillery API URL (default: DD_WB_API_URL env var)",
    )
    wikibase_init.add_argument(
        "--foundation-profiles",
        default=str(
            Path(__file__).resolve().parent / "wikibase" / "foundation_profiles"
        ),
        help="Path to foundation profile YAML directory",
    )
    wikibase_init.add_argument(
        "--language",
        default="en",
        help="Language code for label matching (default: en)",
    )
    wikibase_init.add_argument(
        "--output",
        help="Optional output path for full init JSON report",
    )
    wikibase_init.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without writing (default: true)",
    )
    wikibase_init.add_argument(
        "--execute",
        action="store_true",
        help="Execute writes (overrides dry-run default)",
    )
    wikibase_init.add_argument(
        "--bot",
        action="store_true",
        help="Mark edits as bot edits",
    )
    wikibase_init.add_argument(
        "--summary",
        default="initiating Data Distillery wikibase with items and properties",
        help="Edit summary used for wbeditentity writes",
    )
    wikibase_init.set_defaults(
        handler=_handle_wikibase_init,
        command_path="wikibase.init",
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
    """Launch an interactive Streamlit wizard from a YAML profile.

    Note: Starts a local Streamlit server at http://localhost:8501
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    previous_source, source_overridden = _apply_source_override(args)

    try:
        # Verify profile exists before launching Streamlit
        loader = ProfileLoader()
        profile, resolved_profile = _load_profile_from_reference(loader, args.profile)

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
        env["GKC_WIZARD_PROFILE"] = args.profile
        if args.qid:
            env["GKC_WIZARD_QID"] = args.qid

        # Launch Streamlit in subprocess
        print(f"🚀 Launching Streamlit wizard for profile: {profile.name}")
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
                "profile": profile.name,
                "profile_ref": resolved_profile,
                "qid": args.qid,
            },
        }
    finally:
        _restore_source_override(previous_source, source_overridden)


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


def _handle_registry_list(args: argparse.Namespace) -> dict[str, Any]:
    """List all profiles in the SpiritSafe registry."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        profiles = []

        for profile_id in manifest.profile_ids:
            entry = manifest.get_profile_entry(profile_id)
            if entry:
                profiles.append(
                    {
                        "id": profile_id,
                        "name": entry.get("name", profile_id),
                        "description": entry.get("description", ""),
                        "version": entry.get("version", ""),
                    }
                )

        message = f"Found {len(profiles)} profiles in registry"
        details = {"profiles": profiles, "manifest_commit": manifest.commit_sha}

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


def _handle_registry_search(args: argparse.Namespace) -> dict[str, Any]:
    """Search profiles by keyword."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        keyword = args.keyword.lower()
        matching_profiles = []

        for profile_id in manifest.profile_ids:
            entry = manifest.get_profile_entry(profile_id)
            if not entry:
                continue

            # Search in name, description, tags
            searchable_text = (
                f"{profile_id} {entry.get('name', '')} "
                f"{entry.get('description', '')} "
                f"{' '.join(entry.get('tags', []))}"
            ).lower()

            if keyword in searchable_text:
                matching_profiles.append(
                    {
                        "id": profile_id,
                        "name": entry.get("name", profile_id),
                        "description": entry.get("description", ""),
                    }
                )

        message = f"Found {len(matching_profiles)} profiles matching '{args.keyword}'"
        details = {"keyword": args.keyword, "matches": matching_profiles}

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
    """Show detailed profile metadata."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        entry = manifest.get_profile_entry(args.profile)

        if not entry:
            raise CLIError(
                f"Profile '{args.profile}' not found. "
                f"Available: {', '.join(manifest.profile_ids)}"
            )

        message = f"Profile: {entry.get('name', args.profile)}"
        details = {
            "profile_id": args.profile,
            "name": entry.get("name"),
            "description": entry.get("description"),
            "version": entry.get("version"),
            "tags": entry.get("tags", []),
            "related_profiles": entry.get("related_profiles", []),
            "statement_linkages": len(entry.get("statement_linkages", [])),
            "files": entry.get("files", {}),
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
    """Validate manifest structure."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        errors = []

        # Basic validation checks
        if not manifest.profiles:
            errors.append("No profiles found in manifest")

        # Check each profile has required fields
        for profile_id in manifest.profile_ids:
            entry = manifest.get_profile_entry(profile_id)
            if not entry:
                errors.append(f"Profile {profile_id} has no entry")
                continue

            if not entry.get("name"):
                errors.append(f"Profile {profile_id} missing name")
            if not entry.get("files", {}).get("profile_yaml"):
                errors.append(f"Profile {profile_id} missing profile_yaml path")

        ok = len(errors) == 0
        message = "✓ Manifest is valid" if ok else "✗ Manifest validation failed"

        details = {
            "profile_count": len(manifest.profile_ids),
            "manifest_commit": manifest.commit_sha,
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


def _handle_registry_graph(args: argparse.Namespace) -> dict[str, Any]:
    """Show profile graph relationships."""
    previous_source, source_overridden = _apply_source_override(args)

    try:
        manifest = load_manifest()
        graph = get_profile_graph(manifest)

        if args.profile:
            # Show neighbors for specific profile
            if args.profile not in graph.nodes:
                raise CLIError(
                    f"Profile '{args.profile}' not found in graph. "
                    f"Available: {', '.join(sorted(graph.nodes.keys()))}"
                )

            neighbors = graph.get_neighbors(args.profile)
            message = f"Profile '{args.profile}' has {len(neighbors)} neighbors"
            details = {
                "profile": args.profile,
                "neighbors": list(neighbors),
                "total_nodes": len(graph.nodes),
            }
        else:
            # Show full graph summary
            edges = []
            for source_profile in graph.nodes:
                for edge in graph.get_edges(source_profile):
                    edges.append(
                        (source_profile, edge.target_profile, edge.via_statement)
                    )
            message = f"Profile graph: {len(graph.nodes)} nodes, {len(edges)} edges"
            details = {
                "nodes": list(graph.nodes.keys()),
                "edges": edges,
                "total_nodes": len(graph.nodes),
                "total_edges": len(edges),
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
            "depth": package["depth"],
            "profiles_included": list(package["profiles"].keys()),
            "manifest_commit": package["manifest_commit_sha"],
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
        manifest = load_manifest()
        package = load_profile_package(
            args.profile, depth=args.depth, manifest=manifest
        )

        # Build cardinality report from linkages
        cardinality_info = []
        for profile_id in package["profiles"].keys():
            entry = manifest.get_profile_entry(profile_id)
            if not entry:
                continue

            linkages = entry.get("statement_linkages", [])
            for linkage in linkages:
                linkage_meta = linkage.get("linkage", {})
                cardinality = linkage_meta.get("cardinality", {})
                cardinality_info.append(
                    {
                        "from": profile_id,
                        "to": linkage_meta.get("target_profile"),
                        "via": linkage.get("statement_id"),
                        "min": cardinality.get("min", 0),
                        "max": cardinality.get("max", -1),
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

        details = {
            "packet_id": packet["packet_id"],
            "operation_mode": packet["operation_mode"],
            "primary_profile": packet["primary_profile"],
            "entity_count": len(packet["entities"]),
            "cross_reference_count": len(packet["cross_references"]),
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

        message = f"Packet {packet.get('packet_id', 'unknown')}"
        details = {
            "packet_id": packet.get("packet_id"),
            "operation_mode": packet.get("operation_mode"),
            "created_at": packet.get("created_at"),
            "primary_profile": packet.get("primary_profile"),
            "entity_count": len(packet.get("entities", [])),
            "cross_reference_count": len(packet.get("cross_references", [])),
            "cardinality_constraint_count": len(
                packet.get("cardinality_constraints", [])
            ),
            "manifest_commit": packet.get("manifest_commit_sha"),
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

        message = (
            f"✓ Packet {packet.get('packet_id', 'unknown')} is valid"
            if is_valid
            else f"✗ Packet validation failed with {len(errors)} errors"
        )

        details = {
            "packet_id": packet.get("packet_id"),
            "is_valid": is_valid,
            "errors": errors,
            "entity_count": len(packet.get("entities", [])),
            "cross_reference_count": len(packet.get("cross_references", [])),
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


def _handle_wikibase_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Audit Wikibase foundation ontology conformance using profile definitions."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url

    dd_username = runtime_config.username
    dd_password = runtime_config.password
    sparql_endpoint = runtime_config.sparql_endpoint

    auth = WikiverseAuth(
        username=dd_username,
        password=dd_password,
        interactive=args.interactive,
        api_url=api_url,
    )
    session = requests.Session()
    auth_mode = "anonymous"
    auth_warning: Optional[str] = None

    try:
        if auth.is_authenticated():
            try:
                auth.login()
                session = auth.session
                auth_mode = "authenticated"
            except AuthenticationError as exc:
                if args.require_auth:
                    raise
                auth_warning = (
                    "Authentication failed; proceeding with anonymous session: "
                    f"{exc}"
                )

        report = audit_wikibase_foundation(
            api_url=api_url,
            profile_dir=args.foundation_profiles,
            language=args.language,
            session=session,
        )
    except (AuthenticationError, FoundationProfileError, FoundationAuditError) as exc:
        raise CLIError(str(exc)) from exc

    report_data = report.to_dict()
    generated_at = datetime.now(timezone.utc).isoformat()
    audit_metadata = {
        "api_url": api_url,
        "generated_at": generated_at,
    }
    output_payload = {
        "metadata": audit_metadata,
        **report_data,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    summary = report_data["summary"]
    status_prefix = "✓" if report.ok else "✗"
    message = (
        f"{status_prefix} Wikibase foundation audit: "
        f"{summary['conformant']}/{summary['total']} conformant"
    )

    details: dict[str, Any] = {
        "api_url": api_url,
        "generated_at": generated_at,
        "sparql_endpoint": sparql_endpoint,
        "foundation_profiles": args.foundation_profiles,
        "language": args.language,
        "auth_mode": auth_mode,
        **report_data,
    }

    if auth_warning:
        details["warning"] = auth_warning

    if args.output:
        details["output_file"] = str(Path(args.output).resolve())

    return {
        "command": args.command_path,
        "ok": report.ok,
        "message": message,
        "details": details,
    }


def _handle_wikibase_init(args: argparse.Namespace) -> dict[str, Any]:
    """Initialize Wikibase foundation ontology by creating missing entities/properties."""
    runtime_config = get_wikibase_runtime_config()
    api_url = args.api_url or runtime_config.api_url
    dd_username = runtime_config.username
    dd_password = runtime_config.password

    auth = WikiverseAuth(
        username=dd_username,
        password=dd_password,
        interactive=args.interactive,
        api_url=api_url,
    )

    try:
        # Attempt login with provided/env credentials
        try:
            if auth.is_authenticated():
                auth.login()
            else:
                # No credentials available; if interactive, prompt now
                if args.interactive:
                    username = input(
                        "Enter Data Distillery username (format: Username@BotName): "
                    ).strip()
                    password = getpass.getpass(
                        "Enter Data Distillery password: "
                    ).strip()
                    auth = WikiverseAuth(
                        username=username,
                        password=password,
                        interactive=False,
                        api_url=api_url,
                    )
                    auth.login()
                else:
                    raise CLIError(
                        "Wikibase init requires authentication; set DD_WB_USERNAME and DD_WB_PASSWORD or use --interactive"
                    )
        except AuthenticationError:
            # Login failed; if interactive, prompt for new credentials
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
                raise

        # Resolve dry-run flag: --dry-run is default; --execute overrides it
        dry_run = not args.execute
        default_bot = bool(getattr(auth, "should_mark_bot_edits", lambda: False)())
        bot_mode = bool(args.bot or default_bot)

        report = init_wikibase_foundation(
            auth=auth,
            api_url=api_url,
            profile_dir=args.foundation_profiles,
            language=args.language,
            dry_run=dry_run,
            bot=bot_mode,
            summary=args.summary,
        )
    except (
        AuthenticationError,
        FoundationProfileError,
        FoundationAuditError,
        FoundationInitError,
    ) as exc:
        raise CLIError(str(exc)) from exc

    report_data = report.to_dict()
    generated_at = datetime.now(timezone.utc).isoformat()
    init_metadata = {
        "api_url": api_url,
        "generated_at": generated_at,
        "dry_run": dry_run,
        "bot": bot_mode,
        "summary": args.summary,
    }
    output_payload = {
        "metadata": init_metadata,
        **report_data,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    summary = report_data["summary"]
    status_prefix = "✓" if report.ok else "✗"
    mode_label = "DRY RUN" if dry_run else "EXECUTED"
    if dry_run:
        pending = summary.get("dry_run", 0)
        if pending == 0 and summary["skipped"] == 0:
            message = (
                f"{status_prefix} Wikibase foundation init ({mode_label}): "
                "no changes required (foundation already aligned)"
            )
        else:
            message = (
                f"{status_prefix} Wikibase foundation init ({mode_label}): "
                f"{pending} would create, {summary['skipped']} skipped"
            )
    else:
        message = (
            f"{status_prefix} Wikibase foundation init ({mode_label}): "
            f"{summary['created']} created, {summary.get('updated', 0)} updated, "
            f"{summary['skipped']} skipped"
        )

    details: dict[str, Any] = {
        "api_url": api_url,
        "generated_at": generated_at,
        "foundation_profiles": args.foundation_profiles,
        "language": args.language,
        "dry_run": dry_run,
        "bot": bot_mode,
        "summary": args.summary,
        **report_data,
    }

    if args.verbose:
        actions = report_data.get("actions", [])
        if isinstance(actions, list):
            would_create_labels = [
                action.get("label")
                for action in actions
                if isinstance(action, dict)
                and action.get("action") in {"dry_run", "created"}
            ]
            skipped_labels = [
                action.get("label")
                for action in actions
                if isinstance(action, dict) and action.get("action") == "skipped"
            ]

            details["would_create_count"] = len(would_create_labels)
            details["would_create_labels_preview"] = would_create_labels[:10]
            details["skipped_labels_preview"] = skipped_labels[:10]

    if args.output:
        details["output_file"] = str(Path(args.output).resolve())

    return {
        "command": args.command_path,
        "ok": report.ok,
        "message": message,
        "details": details,
    }


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
