"""Formatters for converting WikidataTemplate to different output formats.

Plain meaning: Convert Wikidata templates to formats like QuickStatements V1.
"""

from __future__ import annotations

from gkc.mash import WikidataTemplate


class QSV1Formatter:
    """Format a WikidataTemplate as QuickStatements V1 syntax.

    Plain meaning: Convert a template to bulk-edit format for Wikidata.
    """

    def __init__(
        self,
        exclude_properties: list[str] | None = None,
        exclude_qualifiers: bool = False,
        exclude_references: bool = False,
        entity_labels: dict[str, str] | None = None,
    ):
        """Initialize the formatter.

        Args:
            exclude_properties: List of property IDs to skip (e.g., ['P31']).
            exclude_qualifiers: If True, omit all qualifiers.
            exclude_references: If True, omit all references.
            entity_labels: Dict mapping entity IDs (properties and items) to labels
                          (e.g., {'P31': 'instance of', 'Q5': 'human'}) for comments.

        Plain meaning: Configure what to include or exclude from output.
        """

        self.exclude_properties = exclude_properties or []
        self.exclude_qualifiers = exclude_qualifiers
        self.exclude_references = exclude_references
        self.entity_labels = entity_labels or {}

    def format(self, template: WikidataTemplate, for_new_item: bool = True) -> str:
        """Convert template to QuickStatements V1 format.

        Args:
            template: The WikidataTemplate to format.
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
                lines.append(f'LAST\tL{lang}\t"{text}"')

            for lang, text in template.descriptions.items():
                lines.append(f'LAST\tD{lang}\t"{text}"')

            # Add aliases
            for lang, alias_list in template.aliases.items():
                for alias in alias_list:
                    lines.append(f'LAST\tA{lang}\t"{alias}"')

            # Add claims with inline comments
            for claim in template.claims:
                if claim.property_id in self.exclude_properties:
                    continue

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

                line = self._claim_to_qs_line(qid, claim)
                if line:
                    lines.append(line)

        return "\n".join(lines)

    def _claim_to_qs_line(self, subject: str, claim) -> str:
        """Convert a single claim to a QS V1 line with optional comment.

        QuickStatements V1 format for qualifiers and references:
        - Qualifiers: P1|Q2|P3|Q4 (with pipes separating property-value pairs)
        - References: S248|Q123 (source), S854|http://... (reference URL)
        - Comments: /* comment text */ at end of line
        - Time values with precision: +2001-01-15T00:00:00Z/11
          (where /11 is day precision)

        Plain meaning: Format one statement with qualifiers/references/comments.
        """

        # Format the main value with metadata (e.g., precision for dates)
        value_str = claim.value
        if hasattr(claim, "value_metadata") and claim.value_metadata:
            if "precision" in claim.value_metadata:
                precision = claim.value_metadata["precision"]
                value_str = f"{claim.value}/{precision}"

        parts: list[str] = [subject, claim.property_id, value_str]

        # Build comment parts for main claim
        comment_parts: list[str] = []
        if self.entity_labels:
            prop_label = self.entity_labels.get(claim.property_id)
            if prop_label:
                # Check if value is an entity (Q-ID) or other type
                if claim.value.startswith("Q") and claim.value[1:].isdigit():
                    value_label = self.entity_labels.get(claim.value, claim.value)
                    comment_parts.append(f"{prop_label} is {value_label}")
                else:
                    # For non-entity values (strings, dates, etc.), show the value
                    comment_parts.append(f"{prop_label} is {claim.value}")

        # Add qualifiers on the same line, separated by pipes
        if not self.exclude_qualifiers and claim.qualifiers:
            for qual in claim.qualifiers:
                prop = qual.get("property", "")
                value = qual.get("value", "")
                if prop and value:
                    # Format qualifier value with metadata if present
                    qual_value_str = value
                    if "metadata" in qual and qual["metadata"]:
                        if "precision" in qual["metadata"]:
                            precision = qual["metadata"]["precision"]
                            qual_value_str = f"{value}/{precision}"

                    parts.append(prop)
                    parts.append(qual_value_str)

                    if self.entity_labels:
                        qual_prop_label = self.entity_labels.get(prop)
                        if qual_prop_label:
                            if value.startswith("Q") and value[1:].isdigit():
                                qual_value_label = self.entity_labels.get(value, value)
                                comment_parts.append(
                                    f"{qual_prop_label} is {qual_value_label}"
                                )
                            else:
                                comment_parts.append(f"{qual_prop_label} is {value}")

        # Add references on the same line, separated by pipes
        # References in QS V1 use S prefix (e.g., S248 for 'stated in')
        # For now, we'll skip complex reference formatting
        # A full implementation would parse and reconstruct reference data
        if not self.exclude_references and claim.references:
            pass

        # Build final line with optional comment
        line = "\t".join(parts)
        if comment_parts:
            comment = "; ".join(comment_parts)
            line += f"\t/* {comment} */"

        return line
