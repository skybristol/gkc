"""Widget factory for Wikidata datatypes in Streamlit.

Maps Wikidata datatypes to appropriate Streamlit input widgets.
MVP scope: All wikibase-item properties use QID text input (no autocomplete).
"""

import re
from html import escape
from typing import Any, Dict, Optional

import streamlit as st


@st.dialog(
    "Select Wikidata item",
    width="large",
    dismissible=True,
    on_dismiss="rerun",
)
def _wikidata_item_picker_dialog(
    *,
    widget_key: str,
    help_text: str | None,
    ordered_uris: list[str],
    by_uri: dict[str, dict[str, str]],
    selected_uri_key: str,
    disabled: bool,
) -> None:
    """Render modal picker for hydrated Wikidata value lists."""
    search_key = f"{widget_key}_search"
    page_key = f"{widget_key}_page"
    last_query_key = f"{widget_key}_last_query"
    page_size = 50

    search_query = st.text_input(
        "Search",
        key=search_key,
        help=help_text,
        placeholder="Type label, QID, or URI",
        disabled=disabled,
    )
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    if st.session_state.get(last_query_key) != search_query:
        st.session_state[page_key] = 0
        st.session_state[last_query_key] = search_query

    normalized_query = search_query.strip().lower()
    if normalized_query:
        filtered_uris = [
            uri
            for uri in ordered_uris
            if normalized_query
            in (
                f"{by_uri[uri].get('itemLabel', '')} "
                f"{WidgetFactory._qid_from_uri(uri) or ''} {uri}"
            ).lower()
        ]
    else:
        filtered_uris = ordered_uris

    total_filtered = len(filtered_uris)
    if total_filtered == 0:
        st.warning("No items match your search.")
        return

    max_page = max(0, (total_filtered - 1) // page_size)
    page_index = min(st.session_state.get(page_key, 0), max_page)
    st.session_state[page_key] = page_index

    start = page_index * page_size
    end = min(start + page_size, total_filtered)
    page_uris = filtered_uris[start:end]

    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button(
            "Previous",
            key=f"{widget_key}_prev_page",
            disabled=disabled or page_index <= 0,
        ):
            st.session_state[page_key] = max(0, page_index - 1)
            st.rerun()
    with nav_col2:
        st.caption(f"Showing {start + 1}-{end} of {total_filtered} matched items")
    with nav_col3:
        if st.button(
            "Next",
            key=f"{widget_key}_next_page",
            disabled=disabled or page_index >= max_page,
        ):
            st.session_state[page_key] = min(max_page, page_index + 1)
            st.rerun()

    for offset, uri in enumerate(page_uris):
        item = by_uri[uri]
        qid = WidgetFactory._qid_from_uri(uri) or uri
        label_text = item.get("itemLabel") or qid

        row_col1, row_col2, row_col3 = st.columns([1, 6, 2])
        with row_col1:
            if st.button(
                "Select",
                key=f"{widget_key}_pick_{start + offset}",
                disabled=disabled,
            ):
                st.session_state[selected_uri_key] = uri
                st.rerun()
        with row_col2:
            st.markdown(f"**{label_text}**")
            st.caption(qid)
        with row_col3:
            st.markdown(
                f'<a href="{escape(uri)}" target="_blank">Open in Wikidata</a>',
                unsafe_allow_html=True,
            )


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
    ) -> Any:
        """Render widget for wikibase-item datatype.

        Supports two modes:
        - Expert mode (default): QID text input.
        - Value-list mode: searchable selectbox returning URI+label metadata.
        """
        item_options = kwargs.get("item_options")
        if isinstance(item_options, list) and item_options:
            return WidgetFactory._render_item_value_list_mode(
                label,
                value,
                key,
                help_text,
                disabled,
                item_options,
                kwargs.get("all_item_options_count"),
            )

        return WidgetFactory._render_item_expert_mode(
            label,
            value,
            key,
            help_text,
            disabled,
        )

    @staticmethod
    def _qid_from_uri(uri: str) -> Optional[str]:
        if not isinstance(uri, str) or not uri:
            return None
        candidate = uri.rsplit("/", 1)[-1] if "/" in uri else uri
        if re.match(r"^Q\d+$", candidate):
            return candidate
        return None

    @staticmethod
    def _render_item_expert_mode(
        label: str,
        value: Any,
        key: str,
        help_text: str,
        disabled: bool,
    ) -> str:
        """Render QID text entry for unconstrained item fields."""
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
    def _render_item_value_list_mode(
        label: str,
        value: Any,
        key: str,
        help_text: str,
        disabled: bool,
        item_options: list[dict[str, str]],
        all_item_options_count: Any,
    ) -> dict[str, str]:
        """Render a value-list picker with fixed search and browse pagination."""
        by_uri: dict[str, dict[str, str]] = {}
        ordered_uris: list[str] = []
        for candidate in item_options:
            if not isinstance(candidate, dict):
                continue
            uri = candidate.get("item")
            if not isinstance(uri, str) or not uri:
                continue
            if uri in by_uri:
                continue
            by_uri[uri] = {
                "item": uri,
                "itemLabel": (
                    candidate.get("itemLabel", "")
                    if isinstance(candidate.get("itemLabel"), str)
                    else ""
                ),
            }
            ordered_uris.append(uri)

        if not ordered_uris:
            st.warning(
                "⚠️ Value list is configured but no selectable items were loaded."
            )
            return {"id": ""}

        current_uri: Optional[str] = None
        if isinstance(value, dict):
            if isinstance(value.get("item"), str):
                current_uri = value["item"]
            elif isinstance(value.get("id"), str):
                current_uri = f"http://www.wikidata.org/entity/{value['id']}"
        elif isinstance(value, str) and value.startswith(("http://", "https://")):
            current_uri = value
        elif isinstance(value, str) and value.startswith("Q"):
            current_uri = f"http://www.wikidata.org/entity/{value}"

        if current_uri and current_uri not in by_uri:
            by_uri[current_uri] = {
                "item": current_uri,
                "itemLabel": "Current value",
            }
            ordered_uris.insert(0, current_uri)

        selected_uri_key = f"{key}_selected_uri"
        if selected_uri_key not in st.session_state:
            st.session_state[selected_uri_key] = current_uri

        selected_uri = st.session_state.get(selected_uri_key)
        if selected_uri not in by_uri:
            selected_uri = current_uri if current_uri in by_uri else None
            st.session_state[selected_uri_key] = selected_uri

        if selected_uri is not None:
            selected = by_uri[selected_uri]
            selected_qid = WidgetFactory._qid_from_uri(selected_uri) or selected_uri
            st.info(
                f"Selected item: {selected.get('itemLabel') or selected_qid} ({selected_qid})"
            )
        else:
            selected = None
            st.caption("No Wikidata item selected yet.")

        button_label = (
            "Change Wikidata item"
            if selected_uri is not None
            else "Choose Wikidata item"
        )
        button_col, clear_col = st.columns([3, 1])
        with button_col:
            if st.button(button_label, key=f"{key}_open_picker", disabled=disabled):
                _wikidata_item_picker_dialog(
                    widget_key=key,
                    help_text=help_text,
                    ordered_uris=ordered_uris,
                    by_uri=by_uri,
                    selected_uri_key=selected_uri_key,
                    disabled=disabled,
                )
        with clear_col:
            if st.button(
                "Clear",
                key=f"{key}_clear_picker",
                disabled=disabled or selected_uri is None,
            ):
                st.session_state[selected_uri_key] = None
                st.rerun()

        if selected_uri is None or selected is None:
            return {}

        qid = WidgetFactory._qid_from_uri(selected_uri)
        result: dict[str, str] = {
            "item": selected_uri,
            "itemLabel": selected.get("itemLabel", ""),
        }
        if qid:
            result["id"] = qid
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
