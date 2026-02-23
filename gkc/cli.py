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
from gkc.mash import WikidataLoader
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
        "--transform",
        choices=["shell", "gkc_entity_profile"],
        help="Transform the output (shell=strip IDs, gkc_entity_profile=profile)",
    )
    mash_eid.set_defaults(
        handler=_handle_mash_eid,
        command_path="mash.eid",
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
    qids = [qid for qid in qids if not (qid in seen or seen.add(qid))]

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
                        if claim.value.startswith("Q") and claim.value[1:].isdigit():
                            entity_ids.add(claim.value)
                        if not args.exclude_qualifiers:
                            for qual in claim.qualifiers:
                                qual_prop = qual.get("property", "")
                                qual_val = qual.get("value", "")
                                if qual_prop:
                                    entity_ids.add(qual_prop)
                                if qual_val.startswith("Q") and qual_val[1:].isdigit():
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

            # Generate QSV1 for each template
            qs_outputs = []
            for qid in qids:
                if qid in templates:
                    qs_text = templates[qid].to_qsv1(
                        for_new_item=False, entity_labels=entity_labels
                    )
                    qs_outputs.append(qs_text)

            output_data = (
                "\n\n".join(qs_outputs) if len(qs_outputs) > 1 else qs_outputs[0]
            )
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
    pids = [pid for pid in pids if not (pid in seen or seen.add(pid))]

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
                "Property to GKC Entity Profile transformation is not yet implemented."
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

        # Handle transformation
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
