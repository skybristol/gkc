"""Form schema generator for YAML profiles.

Plain meaning: Build CLI/UI-friendly field schemas from profiles.
"""

from __future__ import annotations

from typing import Any

from gkc.profiles.models import ProfileDefinition


class FormSchemaGenerator:
    """Generate form/CLI schemas from YAML profiles.

    Args:
        profile: Parsed ProfileDefinition instance.

    Side effects:
        None.

    Example:
        >>> schema = FormSchemaGenerator(profile).build_schema()

    Plain meaning: Convert a profile into a form-friendly schema.
    """

    def __init__(self, profile: ProfileDefinition):
        self.profile = profile

    def build_schema(self) -> dict[str, Any]:
        """Build a form schema dictionary for the profile.

        Returns:
            Dictionary describing fields, qualifiers, and references.

        Side effects:
            None.

        Example:
            >>> schema = FormSchemaGenerator(profile).build_schema()

        Plain meaning: Export field definitions for CLI or UI prompts.
        """
        return {
            "name": self.profile.name,
            "description": self.profile.description,
            "fields": [self._field_schema(field) for field in self.profile.fields],
        }

    def _field_schema(self, field) -> dict[str, Any]:
        value = {
            "type": field.value.type,
            "fixed": field.value.fixed,
            "label": field.value.label,
            "constraints": [c.model_dump() for c in field.value.constraints],
        }

        qualifiers = []
        for qualifier in field.qualifiers:
            qualifiers.append(
                {
                    "id": qualifier.id,
                    "label": qualifier.label,
                    "wikidata_property": qualifier.wikidata_property,
                    "required": qualifier.required,
                    "min_count": qualifier.min_count,
                    "max_count": qualifier.max_count,
                    "value": {
                        "type": qualifier.value.type,
                        "fixed": qualifier.value.fixed,
                        "label": qualifier.value.label,
                        "constraints": [
                            c.model_dump() for c in qualifier.value.constraints
                        ],
                    },
                }
            )

        references = None
        if field.references:
            references = {
                "required": field.references.required,
                "min_count": field.references.min_count,
                "validation_policy": field.references.validation_policy,
                "form_policy": field.references.form_policy,
                "allowed": [
                    self._reference_target_schema(target)
                    for target in field.references.allowed
                ],
                "target": (
                    self._reference_target_schema(field.references.target)
                    if field.references.target
                    else None
                ),
            }

        return {
            "id": field.id,
            "label": field.label,
            "wikidata_property": field.wikidata_property,
            "required": field.required,
            "max_count": field.max_count,
            "validation_policy": field.validation_policy,
            "form_policy": field.form_policy,
            "value": value,
            "qualifiers": qualifiers,
            "references": references,
        }

    @staticmethod
    def _reference_target_schema(target) -> dict[str, Any]:
        if target is None:
            return {}
        return {
            "id": target.id,
            "label": target.label,
            "wikidata_property": target.wikidata_property,
            "type": target.type,
            "description": target.description,
            "value_source": target.value_source,
            "allowed_items": (
                target.allowed_items.model_dump() if target.allowed_items else None
            ),
        }
