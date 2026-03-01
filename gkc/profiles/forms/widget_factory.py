"""Widget factories for profile form datatypes.

Plain meaning: Create appropriate input widgets for each Wikidata datatype.
"""

from __future__ import annotations

from typing import Any, Optional

from textual.containers import Horizontal, Vertical
from textual.validation import Function
from textual.widgets import Input

from gkc.profiles.forms.textual_generator import TypeAheadSelect


class WidgetFactory:
    """Factory for creating datatype-specific form widgets.

    Plain meaning: Build the right input widget for each statement type.
    """

    @staticmethod
    def create_widget(
        field_schema: dict[str, Any],
        choice_list: Optional[list[tuple[str, str]]] = None,
    ) -> Any:
        """Create widget for a statement based on its datatype.

        Args:
            field_schema: Statement schema from FormSchemaGenerator.
            choice_list: Optional pre-loaded choice list for item statements.

        Returns:
            Textual widget for the field.

        Plain meaning: Build the right input control for this statement.
        """
        value_type = field_schema["value"]["type"]
        field_label = field_schema["label"]
        prompt = _resolve_input_prompt(field_schema, default=f"Enter {field_label}")

        if value_type == "item":
            if choice_list:
                return TypeAheadSelect(
                    choices=choice_list,
                    placeholder=prompt,
                    id=f"field_{field_schema['id']}",
                )
            else:
                return Input(
                    placeholder=prompt,
                    validators=[
                        Function(_qid_validator, "Expected QID format (e.g., Q42)")
                    ],
                    id=f"field_{field_schema['id']}",
                )

        elif value_type == "url":
            return Input(
                placeholder=prompt,
                validators=[
                    Function(
                        _url_validator,
                        "Expected URL format starting with http:// or https://",
                    )
                ],
                id=f"field_{field_schema['id']}",
            )

        elif value_type == "string":
            return Input(
                placeholder=prompt,
                id=f"field_{field_schema['id']}",
            )

        elif value_type == "quantity":
            return Horizontal(
                Input(
                    placeholder=_suffix_prompt(prompt, "amount"),
                    id="quantity_amount",
                ),
                Input(
                    placeholder=_suffix_prompt(prompt, "unit QID (optional)"),
                    id="quantity_unit",
                ),
                id=f"field_{field_schema['id']}",
                classes="field_container",
            )

        elif value_type == "time":
            return Input(
                placeholder=prompt,
                validators=[
                    Function(
                        _time_validator,
                        "Expected YYYY, YYYY-MM, or YYYY-MM-DD",
                    )
                ],
                id=f"field_{field_schema['id']}",
            )

        elif value_type == "monolingualtext":
            if choice_list:
                # Language choice list available
                return Vertical(
                    Input(
                        placeholder=prompt,
                        id="monolingualtext_text",
                    ),
                    TypeAheadSelect(
                        choices=choice_list,
                        placeholder=_suffix_prompt(prompt, "language"),
                    ),
                    id=f"field_{field_schema['id']}",
                    classes="field_container",
                )
            else:
                return Vertical(
                    Input(
                        placeholder=prompt,
                        id="monolingualtext_text",
                    ),
                    Input(
                        placeholder=_suffix_prompt(prompt, "language code"),
                        id="monolingualtext_lang",
                    ),
                    id=f"field_{field_schema['id']}",
                    classes="field_container",
                )

        elif value_type == "globecoordinate":
            return Horizontal(
                Input(
                    placeholder=_suffix_prompt(prompt, "latitude"),
                    id="coord_lat",
                    validators=[
                        Function(
                            _latitude_validator,
                            "Latitude must be between -90 and 90",
                        )
                    ],
                ),
                Input(
                    placeholder=_suffix_prompt(prompt, "longitude"),
                    id="coord_lon",
                    validators=[
                        Function(
                            _longitude_validator,
                            "Longitude must be between -180 and 180",
                        )
                    ],
                ),
                id=f"field_{field_schema['id']}",
                classes="field_container",
            )

        elif value_type == "commonsMedia":
            return Input(
                placeholder=prompt,
                id=f"field_{field_schema['id']}",
            )

        elif value_type == "external-id":
            return Input(
                placeholder=prompt,
                id=f"field_{field_schema['id']}",
            )

        else:
            # Fallback for unknown types
            return Input(
                placeholder=prompt,
                id=f"field_{field_schema['id']}",
            )


def _resolve_input_prompt(field_schema: dict[str, Any], default: str) -> str:
    """Resolve preferred input prompt with sensible fallback."""
    prompt = field_schema.get("input_prompt")
    return prompt if prompt else default


def _suffix_prompt(prompt: str, suffix: str) -> str:
    """Build a sub-field placeholder from a base prompt."""
    return f"{prompt} ({suffix})"


def _qid_validator(value: str) -> bool:
    """Validate QID format."""
    return value.startswith("Q") and value[1:].isdigit()


def _url_validator(value: str) -> bool:
    """Validate URL format."""
    return value.startswith("http://") or value.startswith("https://")


def _time_validator(value: str) -> bool:
    """Validate time format (YYYY, YYYY-MM, or YYYY-MM-DD)."""
    import re

    patterns = [
        r"^\d{4}$",  # YYYY
        r"^\d{4}-\d{2}$",  # YYYY-MM
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
    ]
    return any(re.match(pattern, value) for pattern in patterns)


def _latitude_validator(value: str) -> bool:
    """Validate latitude range."""
    try:
        lat = float(value)
        return -90 <= lat <= 90
    except ValueError:
        return False


def _longitude_validator(value: str) -> bool:
    """Validate longitude range."""
    try:
        lon = float(value)
        return -180 <= lon <= 180
    except ValueError:
        return False
