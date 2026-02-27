"""Command line interface for GKC.

Plain meaning: Run GKC tasks from the terminal.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

import gkc
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth
from gkc.mash import WikidataLoader, WikipediaLoader
from gkc.profiles import FormSchemaGenerator, ProfileLoader, ProfileValidator
from gkc.recipe import EntityCatalog


class CLIError(Exception):
    """Raised when CLI execution fails.

    Plain meaning: The CLI could not complete the requested command.
    """


def main(argv: Optional[list[str]] = None) -> int:
    """Run the GKC CLI.

    Plain meaning: Parse arguments, execute a command, and return an exit code.
    """

    parser = _build_parser()
    args = parser.parse_args(argv)

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
    profile_form.set_defaults(
        handler=_handle_profile_form_schema,
        command_path="profile.form_schema",
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
        default="https://query.wikidata.org/sparql",
        help="SPARQL endpoint URL",
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
        loader = WikidataLoader()

        # Load items (single or batch)
        if len(qids) == 1:
            templates = {qids[0]: loader.load_item(qids[0])}
        else:
            templates = loader.load_items(qids)

        # Apply filters to all templates
        for template in templates.values():
            template.filter_languages()
            if include_properties or exclude_properties:
                template.filter_properties(
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
                            catalog = EntityCatalog()
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
                            results = catalog.fetch_entities(list(entity_ids))
                            entity_labels = {
                                eid: entry.get_label(language)
                                for eid, entry in results.items()
                            }
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
        loader = WikidataLoader()

        # Load properties (single or batch)
        if len(pids) == 1:
            templates = {pids[0]: loader.load_property(pids[0])}
        else:
            templates = loader.load_properties(pids)

        # Apply filters to all templates
        for template in templates.values():
            template.filter_languages()

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
        loader = WikidataLoader()
        template = loader.load_entity_schema(eid)

        # Apply filters
        template.filter_languages()

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
            from gkc.cooperage import get_entity_uri

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

    loader = ProfileLoader()
    profile = loader.load_from_file(args.profile)

    if args.qid:
        item = WikidataLoader().load_item(args.qid)
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


def _handle_profile_form_schema(args: argparse.Namespace) -> dict[str, Any]:
    """Generate form schema from a YAML profile."""
    loader = ProfileLoader()
    profile = loader.load_from_file(args.profile)

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
        "details": {"profile": profile.name, "output": args.output or "stdout"},
    }


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


def _emit_output(output: dict[str, Any], json_output: bool, verbose: bool) -> None:
    if json_output:
        print(json.dumps(output))
        return

    message = output.get("message", "")
    if message:
        print(message)

    # Show details for summary format or when verbose is requested
    details = output.get("details") or {}
    if details and (verbose or output.get("command", "").endswith(".qid")):
        if verbose and message:
            # Add blank line before details if message was printed
            print()
        for key, value in details.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
