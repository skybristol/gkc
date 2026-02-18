"""Formatters for converting MashTemplate to different output formats.

Plain meaning: Convert Wikidata templates to formats like QuickStatements V1.
"""

from __future__ import annotations

from gkc.mash import MashTemplate


class QSV1Formatter:
    """Format a MashTemplate as QuickStatements V1 syntax.

    Plain meaning: Convert a template to bulk-edit format for Wikidata.
    """

    def __init__(
        self,
        exclude_properties: list[str] | None = None,
        exclude_qualifiers: bool = False,
        exclude_references: bool = False,
        property_labels: dict[str, str] | None = None,
    ):
        """Initialize the formatter.

        Args:
            exclude_properties: List of property IDs to skip (e.g., ['P31']).
            exclude_qualifiers: If True, omit all qualifiers.
            exclude_references: If True, omit all references.
            property_labels: Dict mapping property IDs to human-readable labels
                           (e.g., {'P31': 'instance of'}) for use as comments.

        Plain meaning: Configure what to include or exclude from output.
        """

        self.exclude_properties = exclude_properties or []
        self.exclude_qualifiers = exclude_qualifiers
        self.exclude_references = exclude_references
        self.property_labels = property_labels or {}

    def format(self, template: MashTemplate, for_new_item: bool = True) -> str:
        """Convert template to QuickStatements V1 format.

        Args:
            template: The MashTemplate to format.
            for_new_item: If True, use "CREATE" and "LAST" syntax for new items.
                         If False, use the QID and "P" syntax for updates.

        Returns:
            QuickStatements V1 text.

        Plain meaning: Generate editable QS text from the template.
        """

        lines: list[str] = []

        if for_new_item:
            lines.append("CREATE")
            # Add labels and descriptions
            for lang, text in template.labels.items():
                lines.append(f'LAST\t{lang}\t"{text}"')

            for lang, text in template.descriptions.items():
                lines.append(f'LAST\tDn\t"{text}"')

            # Add claims with optional comment lines
            for claim in template.claims:
                if claim.property_id in self.exclude_properties:
                    continue

                # Add comment if property label available
                if claim.property_id in self.property_labels:
                    label = self.property_labels[claim.property_id]
                    lines.append(f"/* {label} */")

                line = self._claim_to_qs_line("LAST", claim)
                if line:
                    lines.append(line)
        else:
            # For existing items
            qid = template.qid
            for lang, text in template.labels.items():
                lines.append(f'{qid}\t{lang}\t"{text}"')

            for lang, text in template.descriptions.items():
                lines.append(f'{qid}\tDn\t"{text}"')

            for claim in template.claims:
                if claim.property_id in self.exclude_properties:
                    continue

                # Add comment if property label available
                if claim.property_id in self.property_labels:
                    label = self.property_labels[claim.property_id]
                    lines.append(f"/* {label} */")

                line = self._claim_to_qs_line(qid, claim)
                if line:
                    lines.append(line)

        return "\n".join(lines)

    def _claim_to_qs_line(self, subject: str, claim) -> str:
        """Convert a single claim to a QS V1 line.

        QuickStatements V1 format for qualifiers and references:
        - Qualifiers: P1|Q2|P3|Q4 (with pipes separating property-value pairs)
        - References: S248|Q123 (source), S854|http://... (reference URL)

        Plain meaning: Format one statement with qualifiers/references in QS syntax.
        """

        parts: list[str] = [subject, claim.property_id, claim.value]

        # Add qualifiers on the same line, separated by pipes
        if not self.exclude_qualifiers and claim.qualifiers:
            for qual in claim.qualifiers:
                prop = qual.get("property", "")
                value = qual.get("value", "")
                if prop and value:
                    parts.append(prop)
                    parts.append(value)

        # Add references on the same line, separated by pipes
        if not self.exclude_references and claim.references:
            # References in QS V1 use S248 for source, S854 for URL, etc.
            # For now, we'll skip complex reference formatting
            # A full implementation would parse and reconstruct reference data
            pass

        return "\t".join(parts)


class JSONFormatter:
    """Format a MashTemplate as pretty JSON.

    Plain meaning: Export the template as JSON for debugging or scripting.
    """

    def format(
        self,
        template: MashTemplate,
        exclude_properties: list[str] | None = None,
        exclude_qualifiers: bool = False,
        exclude_references: bool = False,
    ) -> str:
        """Convert template to pretty JSON.

        Args:
            template: The MashTemplate to format.
            exclude_properties: List of property IDs to exclude.
            exclude_qualifiers: If True, omit qualifiers.
            exclude_references: If True, omit references.

        Returns:
            Formatted JSON string.

        Plain meaning: Generate readable JSON from the template.
        """

        import json

        data = template.to_dict()

        # Apply filters
        if exclude_properties:
            data["claims"] = [
                c for c in data["claims"] if c["property_id"] not in exclude_properties
            ]

        if exclude_qualifiers:
            for claim in data["claims"]:
                claim["qualifiers"] = []

        if exclude_references:
            for claim in data["claims"]:
                claim["references"] = []

        return json.dumps(data, indent=2)
