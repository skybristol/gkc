"""Widget factory for Wikidata datatypes in Streamlit.

Maps Wikidata datatypes to appropriate Streamlit input widgets.
MVP scope: All wikibase-item properties use QID text input (no autocomplete).
"""

import re
from typing import Any, Dict, Optional

import streamlit as st


class WidgetFactory:
    """Factory for creating Streamlit widgets for Wikidata datatypes."""

    @staticmethod
    def render_widget(
        datatype: str,
        label: str,
        value: Any = None,
        key: Optional[str] = None,
        help_text: Optional[str] = None,
        disabled: bool = False,
        **kwargs,
    ) -> Any:
        """Render appropriate widget for given datatype.

        Args:
            datatype: Wikidata datatype (e.g., 'item', 'string', 'time', 'quantity')
            label: Widget label to display
            value: Current value (optional)
            key: Unique key for widget
            help_text: Help text to display
            disabled: Whether widget is read-only
            **kwargs: Additional datatype-specific parameters

        Returns:
            User input value from widget
        """
        # Map Wikidata datatypes to widget renderers
        widget_map = {
            "item": WidgetFactory._render_item,
            "wikibase-item": WidgetFactory._render_item,
            "string": WidgetFactory._render_string,
            "url": WidgetFactory._render_url,
            "time": WidgetFactory._render_time,
            "quantity": WidgetFactory._render_quantity,
            "monolingualtext": WidgetFactory._render_monolingualtext,
            "globecoordinate": WidgetFactory._render_globecoordinate,
            "external-id": WidgetFactory._render_external_id,
            "commonsMedia": WidgetFactory._render_commons_media,
        }

        renderer = widget_map.get(datatype, WidgetFactory._render_default)
        return renderer(label, value, key, help_text, disabled, **kwargs)

    @staticmethod
    def _render_item(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for wikibase-item datatype (MVP: QID text input)."""
        qid_value = value if value else ""

        # Extract QID if value is a dict with 'id' key
        if isinstance(value, dict) and "id" in value:
            qid_value = value["id"]

        result = st.text_input(
            label,
            value=qid_value,
            key=key,
            help=help_text,
            disabled=disabled,
            placeholder="Q12345",
        )

        # Validate QID format if value provided
        if result and not disabled:
            if not re.match(r"^Q\d+$", result):
                st.warning(f"⚠️ Expected QID format (e.g., Q12345), got: {result}")

        return result

    @staticmethod
    def _render_string(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for string datatype."""
        return st.text_input(
            label,
            value=value if value else "",
            key=key,
            help=help_text,
            disabled=disabled,
        )

    @staticmethod
    def _render_url(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for URL datatype."""
        result = st.text_input(
            label,
            value=value if value else "",
            key=key,
            help=help_text,
            disabled=disabled,
            placeholder="https://example.com",
        )

        # Basic URL validation
        if result and not disabled:
            if not result.startswith(("http://", "https://")):
                st.warning("⚠️ URL should start with http:// or https://")

        return result

    @staticmethod
    def _render_time(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for time datatype.

        Accepts YYYY, YYYY-MM, or YYYY-MM-DD format.
        """
        current_value = value if value else ""

        # Extract date string from Wikidata time value if needed
        if isinstance(value, dict) and "time" in value:
            # Wikidata format: "+2000-01-15T00:00:00Z"
            time_str = value["time"]
            # Extract date part and convert to simple format
            match = re.match(r"[+-]?(\d{4})-(\d{2})-(\d{2})", time_str)
            if match:
                year, month, day = match.groups()
                if day != "00" and month != "00":
                    current_value = f"{year}-{month}-{day}"
                elif month != "00":
                    current_value = f"{year}-{month}"
                else:
                    current_value = year

        result = st.text_input(
            label,
            value=current_value,
            key=key,
            help=help_text or "Format: YYYY, YYYY-MM, or YYYY-MM-DD",
            disabled=disabled,
            placeholder="YYYY-MM-DD",
        )

        # Validate date format
        if result and not disabled:
            valid_formats = [
                r"^\d{4}$",  # YYYY
                r"^\d{4}-\d{2}$",  # YYYY-MM
                r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
            ]
            if not any(re.match(pattern, result) for pattern in valid_formats):
                st.warning("⚠️ Expected date format YYYY, YYYY-MM, or YYYY-MM-DD")

        return result

    @staticmethod
    def _render_quantity(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> Dict[str, Any]:
        """Render widget for quantity datatype."""
        # Extract current value and unit if present
        current_amount = ""
        current_unit = ""

        if isinstance(value, dict):
            current_amount = value.get("amount", "")
            current_unit = value.get("unit", "")
        elif value is not None:
            current_amount = str(value)

        col1, col2 = st.columns([3, 1])

        with col1:
            amount = st.text_input(
                label,
                value=current_amount,
                key=f"{key}_amount" if key else None,
                help=help_text,
                disabled=disabled,
                placeholder="Enter number",
            )

        with col2:
            unit = st.text_input(
                "Unit",
                value=current_unit,
                key=f"{key}_unit" if key else None,
                help="Unit QID (optional)",
                disabled=disabled,
                placeholder="Q...",
            )

        # Validate amount is numeric
        if amount and not disabled:
            try:
                float(amount)
            except ValueError:
                st.warning("⚠️ Amount must be a number")

        return {"amount": amount, "unit": unit} if amount or unit else {}

    @staticmethod
    def _render_monolingualtext(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> Dict[str, str]:
        """Render widget for monolingualtext datatype."""
        current_text = ""
        current_lang = ""

        if isinstance(value, dict):
            current_text = value.get("text", "")
            current_lang = value.get("language", "")

        col1, col2 = st.columns([3, 1])

        with col1:
            text = st.text_input(
                label,
                value=current_text,
                key=f"{key}_text" if key else None,
                help=help_text,
                disabled=disabled,
            )

        with col2:
            language = st.text_input(
                "Language",
                value=current_lang,
                key=f"{key}_lang" if key else None,
                help="Language code (e.g., en, chr)",
                disabled=disabled,
                placeholder="en",
            )

        return {"text": text, "language": language} if text or language else {}

    @staticmethod
    def _render_globecoordinate(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> Dict[str, float]:
        """Render widget for globe-coordinate datatype."""
        current_lat = ""
        current_lon = ""

        if isinstance(value, dict):
            current_lat = value.get("latitude", "")
            current_lon = value.get("longitude", "")

        col1, col2 = st.columns(2)

        with col1:
            latitude = st.text_input(
                f"{label} - Latitude",
                value=str(current_lat) if current_lat else "",
                key=f"{key}_lat" if key else None,
                help="Latitude (e.g., 36.1699)",
                disabled=disabled,
                placeholder="36.1699",
            )

        with col2:
            longitude = st.text_input(
                "Longitude",
                value=str(current_lon) if current_lon else "",
                key=f"{key}_lon" if key else None,
                help="Longitude (e.g., -86.7844)",
                disabled=disabled,
                placeholder="-86.7844",
            )

        # Validate coordinates
        result = {}
        if latitude or longitude:
            try:
                if latitude:
                    lat_float = float(latitude)
                    if not -90 <= lat_float <= 90:
                        st.warning("⚠️ Latitude must be between -90 and 90")
                    result["latitude"] = lat_float
                if longitude:
                    lon_float = float(longitude)
                    if not -180 <= lon_float <= 180:
                        st.warning("⚠️ Longitude must be between -180 and 180")
                    result["longitude"] = lon_float
            except ValueError:
                st.warning("⚠️ Coordinates must be numbers")

        return result

    @staticmethod
    def _render_external_id(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for external-id datatype."""
        return st.text_input(
            label,
            value=value if value else "",
            key=key,
            help=help_text or "External identifier",
            disabled=disabled,
        )

    @staticmethod
    def _render_commons_media(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Render widget for commonsMedia datatype."""
        return st.text_input(
            label,
            value=value if value else "",
            key=key,
            help=help_text or "Wikimedia Commons filename (e.g., Example.svg)",
            disabled=disabled,
            placeholder="Example.svg",
        )

    @staticmethod
    def _render_default(
        label: str, value: Any, key: str, help_text: str, disabled: bool, **kwargs
    ) -> str:
        """Fallback widget for unknown datatypes."""
        st.warning("⚠️ Unsupported datatype - using text input")
        return st.text_input(
            label,
            value=str(value) if value else "",
            key=key,
            help=help_text,
            disabled=disabled,
        )
