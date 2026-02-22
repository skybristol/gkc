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
from gkc.mash import WikidataLoader, strip_entity_identifiers
from gkc.mash_formatters import QSV1Formatter
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

    # Mash commands for loading Wikidata items as templates
    mash_parser = subparsers.add_parser("mash", help="Load Wikidata items as templates")
    mash_subparsers = mash_parser.add_subparsers(dest="mash_command")

    mash_qid = mash_subparsers.add_parser(
        "qid", help="Load a Wikidata item as a template"
    )
    mash_qid.add_argument("qid", help="The Wikidata item ID (e.g., Q42)")
    mash_qid.add_argument(
        "--output",
        choices=["qsv1", "json", "summary"],
        default="summary",
        help="Output format (default: summary)",
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
    mode_group = mash_qid.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--new",
        action="store_const",
        dest="mash_mode",
        const="new",
        help="""
            Use CREATE/LAST syntax for new items and strip identifiers from JSON
        """,
    )
    mode_group.add_argument(
        "--update",
        action="store_const",
        dest="mash_mode",
        const="update",
        help="Retain identifiers for updates (default)",
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
        mash_mode="update",
    )

    # Mash commands for loading Wikidata EntitySchemas as templates
    mash_eid = mash_subparsers.add_parser(
        "eid", help="Load a Wikidata EntitySchema as a template"
    )
    mash_eid.add_argument("eid", help="The Wikidata EntitySchema ID (e.g., E502)")
    mash_eid.add_argument(
        "--output",
        choices=["summary", "json", "profile"],
        default="summary",
        help="Output format (default: summary)",
    )
    mash_eid.add_argument(
        "--save-profile",
        type=str,
        help="Directory path to save generated GKC Entity Profile JSON",
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


def _handle_mash_qid(args: argparse.Namespace) -> dict[str, Any]:
    qid = args.qid
    output_format = args.output
    mash_mode = getattr(args, "mash_mode", "update")
    include_properties = []
    exclude_properties = []

    if args.include_properties:
        include_properties = [p.strip() for p in args.include_properties.split(",")]
    if args.exclude_properties:
        exclude_properties = [p.strip() for p in args.exclude_properties.split(",")]

    try:
        loader = WikidataLoader()

        template = loader.load(qid)

        if output_format == "json":
            template.filter_properties(
                include_properties=include_properties,
                exclude_properties=exclude_properties,
            )
            if args.exclude_qualifiers:
                template.filter_qualifiers()
            if args.exclude_references:
                template.filter_references()

            entity_data = template.to_dict()
            if mash_mode == "new":
                entity_data = strip_entity_identifiers(entity_data)
            print(json.dumps(entity_data, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"JSON output for {qid}",
                "details": {"format": "json", "mode": mash_mode},
            }

        # Apply language filter (uses package-level config by default)
        template.filter_languages()

        # Apply filters
        template.filter_properties(
            include_properties=include_properties,
            exclude_properties=exclude_properties,
        )
        if args.exclude_qualifiers:
            template.filter_qualifiers()
        if args.exclude_references:
            template.filter_references()

        # Format output
        if output_format == "summary":
            summary = template.summary()
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"Template loaded: {qid}",
                "details": summary,
            }
        elif output_format == "qsv1":
            entity_labels = {}

            # Fetch entity labels for comments if requested
            if getattr(args, "include_entity_labels", True):
                # Extract all entity IDs (properties and items)
                entity_ids = set()

                # Add property IDs from claims
                for claim in template.claims:
                    entity_ids.add(claim.property_id)

                    # Add item IDs from claim values (if they're Q-IDs)
                    if claim.value.startswith("Q") and claim.value[1:].isdigit():
                        entity_ids.add(claim.value)

                    # Add property and item IDs from qualifiers
                    if not args.exclude_qualifiers:
                        for qual in claim.qualifiers:
                            qual_prop = qual.get("property", "")
                            qual_val = qual.get("value", "")
                            if qual_prop:
                                entity_ids.add(qual_prop)
                            if qual_val.startswith("Q") and qual_val[1:].isdigit():
                                entity_ids.add(qual_val)

                # Fetch labels for all entities
                if entity_ids:
                    try:
                        catalog = EntityCatalog()
                        languages = gkc.get_languages()
                        if languages == "all":
                            language = "en"
                        elif isinstance(languages, str):
                            language = languages
                        else:
                            language = languages[0] if languages else "en"
                        results = catalog.fetch_entities(list(entity_ids))
                        entity_labels = {
                            eid: entry.get_label(language)
                            for eid, entry in results.items()
                        }
                    except Exception as exc:
                        raise CLIError(
                            f"Failed to fetch entity labels: {str(exc)}. "
                            f"Use --no-entity-labels to skip label fetching."
                        ) from exc

            formatter = QSV1Formatter(
                exclude_properties=exclude_properties,
                exclude_qualifiers=args.exclude_qualifiers,
                exclude_references=args.exclude_references,
                entity_labels=entity_labels,
            )
            for_new_item = mash_mode == "new"
            qs_text = formatter.format(template, for_new_item=for_new_item)
            print(qs_text)
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"QuickStatements V1 output for {qid}",
                "details": {"format": "qsv1", "lines": len(qs_text.split("\n"))},
            }

        # This should never be reached due to choices validation
        raise CLIError(f"Unsupported output format: {output_format}")
    except Exception as exc:
        raise CLIError(f"Failed to load item {qid}: {str(exc)}") from exc


def _handle_mash_eid(args: argparse.Namespace) -> dict[str, Any]:
    """Handle mash eid subcommand: load and display Wikidata EntitySchema."""
    eid = args.eid
    output_format = args.output
    save_profile = getattr(args, "save_profile", None)

    try:
        from gkc.recipe import RecipeBuilder

        builder = RecipeBuilder(eid=eid)
        builder.load_specification()

        if output_format == "profile":
            # Generate GKC Entity Profile
            profile_dict = builder.generate_gkc_entity_profile()

            print(json.dumps(profile_dict, indent=2))

            # Optionally save to file
            if save_profile:
                import os

                os.makedirs(save_profile, exist_ok=True)
                profile_id = profile_dict.get("id", eid.lower())
                filename = f"{profile_id}_entity_profile.json"
                filepath = os.path.join(save_profile, filename)
                with open(filepath, "w") as f:
                    json.dump(profile_dict, f, indent=2)

                return {
                    "command": args.command_path,
                    "ok": True,
                    "message": f"GKC Entity Profile generated for {eid}",
                    "details": {
                        "format": "profile",
                        "profile_id": profile_id,
                        "saved_to": filepath,
                    },
                }
            else:
                return {
                    "command": args.command_path,
                    "ok": True,
                    "message": f"GKC Entity Profile for {eid}",
                    "details": {"format": "profile"},
                }

        elif output_format == "json":
            # Fetch raw EntitySchema metadata
            from gkc.cooperage import fetch_entity_schema_json

            schema_json = fetch_entity_schema_json(eid)
            print(json.dumps(schema_json, indent=2))
            return {
                "command": args.command_path,
                "ok": True,
                "message": f"EntitySchema JSON for {eid}",
                "details": {"format": "json"},
            }

        elif output_format == "summary":
            # Generate human-readable summary
            # Get metadata
            from gkc.cooperage import fetch_entity_schema_metadata
            from gkc.recipe import SpecificationExtractor

            user_agent = None
            metadata = fetch_entity_schema_metadata(eid, user_agent=user_agent)

            # Get properties from ShEx
            schema_text = builder.schema_text
            extractor = SpecificationExtractor(schema_text)
            properties = extractor.extract()

            # Get constraints
            instance_of = extractor.get_instance_of_constraints()
            subclass_of = extractor.get_subclass_of_constraints()

            # Format summary
            p31_str = ", ".join(instance_of) if instance_of else "None"
            p279_str = ", ".join(subclass_of) if subclass_of else "None"
            summary_lines = [
                f"EntitySchema: {eid}",
                f"Label: {metadata.get('label', '<no label>')}",
                f"Description: {metadata.get('description', '<no description>')}",
                f"Properties: {len(properties)}",
                f"Classification constraints P31: {p31_str}",
                f"Classification constraints P279: {p279_str}",
            ]

            print("\n".join(summary_lines))

            return {
                "command": args.command_path,
                "ok": True,
                "message": f"EntitySchema summary for {eid}",
                "details": {
                    "format": "summary",
                    "label": metadata.get("label", ""),
                    "property_count": len(properties),
                    "p31_constraints": instance_of,
                    "p279_constraints": subclass_of,
                },
            }

        else:
            raise CLIError(f"Unsupported output format: {output_format}")

    except Exception as exc:
        raise CLIError(f"Failed to process EntitySchema {eid}: {str(exc)}") from exc


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
