"""Concrete step implementations for the wizard.

Plain meaning: The actual form content for each step.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from gkc.profiles.forms.widgets import WidgetFactory
from gkc.profiles.forms.wizard.step_base import Step

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_profile_languages(profile) -> list[str]:
    """Extract all languages defined in the profile's identification sections.

    Args:
        profile: The loaded EntityProfile.

    Returns:
        Sorted list of unique language codes found across labels, descriptions, aliases.

    Plain meaning: Figure out which languages this profile supports.
    """
    languages = set()

    # Scan labels section
    if hasattr(profile, "labels") and isinstance(profile.labels, dict):
        languages.update(profile.labels.keys())

    # Scan descriptions section
    if hasattr(profile, "descriptions") and isinstance(profile.descriptions, dict):
        languages.update(profile.descriptions.keys())

    # Scan aliases section
    if hasattr(profile, "aliases") and isinstance(profile.aliases, dict):
        languages.update(profile.aliases.keys())

    return sorted(languages)


def _as_language_map(section: Any) -> dict[str, Any]:
    """Normalize a metadata section into a language->definition mapping."""
    if isinstance(section, dict):
        return section
    languages = getattr(section, "languages", None)
    if isinstance(languages, dict):
        return languages
    return {}


def _clean_empty_aliases(id_data: dict[str, Any]) -> dict[str, Any]:
    """Remove empty strings from alias lists in identification data.

    Used when exporting or serializing data for external systems.
    Aliases are kept as-is during editing to allow user input to persist.

    Args:
        id_data: Identification data dict with 'aliases' key

    Returns:
        Copy of id_data with empty aliases filtered out
    """
    cleaned = dict(id_data)
    if "aliases" in cleaned:
        cleaned["aliases"] = {
            lang: [a.strip() for a in aliases if a.strip()]
            for lang, aliases in cleaned["aliases"].items()
        }
    return cleaned


# ============================================================================
# STEP IMPLEMENTATIONS
# ============================================================================


class IdentificationStep(Step):
    """Collect labels, descriptions, and aliases for the entity.

    Plain meaning: The "who/what is this?" step.
    """

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        """Render labels, descriptions, and aliases by language.

        Args:
            draft_data: GKC Entity JSON object (not flat structure).

        Returns:
            The same entity object (modified in-place).
        """
        st.header("🏷️ Identification")

        # Get the profile from session state (set in streamlit_app.py)
        if "profile" not in st.session_state or st.session_state.profile is None:
            st.error("No profile loaded")
            return draft_data

        profile = st.session_state.profile

        # Show profile name and description
        st.write(f"**{profile.name}** — {profile.description}")

        # Initialize multilingual fields if not present (entity schema uses top-level keys)
        if "labels" not in draft_data:
            draft_data["labels"] = {}
        if "descriptions" not in draft_data:
            draft_data["descriptions"] = {}
        if "aliases" not in draft_data:
            draft_data["aliases"] = {}

        # Determine which languages are defined in the profile
        supported_languages = get_profile_languages(profile)

        if not supported_languages:
            st.warning("Profile has no language configuration")
            return draft_data

        # Get language maps for each section
        labels_map = _as_language_map(getattr(profile, "labels", {}))
        descriptions_map = _as_language_map(getattr(profile, "descriptions", {}))
        aliases_map = _as_language_map(getattr(profile, "aliases", {}))

        # If multiple languages, use tabs; otherwise render directly
        if len(supported_languages) > 1:
            tabs = st.tabs([lang.upper() for lang in supported_languages])
            for i, lang in enumerate(supported_languages):
                with tabs[i]:
                    self._render_language_section(
                        lang, labels_map, descriptions_map, aliases_map, draft_data
                    )
        else:
            # Single language - no tabs needed
            lang = supported_languages[0]
            self._render_language_section(
                lang, labels_map, descriptions_map, aliases_map, draft_data
            )

        return draft_data

    def _render_language_section(
        self,
        lang: str,
        labels_map: dict[str, Any],
        descriptions_map: dict[str, Any],
        aliases_map: dict[str, Any],
        entity_data: dict[str, Any],
    ) -> None:
        """Render label, description, and alias fields for a single language.

        Args:
            lang: Language code (e.g., "en", "chr")
            labels_map: Profile labels metadata
            descriptions_map: Profile descriptions metadata
            aliases_map: Profile aliases metadata
            entity_data: GKC Entity JSON object (modified in-place)

        Plain meaning: Show the input fields for one language's worth of metadata.
        """
        # ---- LABEL ----
        label_meta = labels_map.get(lang)
        if label_meta:
            field_label = getattr(label_meta, "label", "Label")
            input_prompt = getattr(label_meta, "input_prompt", "")
            guidance = getattr(label_meta, "guidance", "")

            st.write(f"**{field_label}**")
            if input_prompt:
                st.caption(input_prompt)

            current_value = entity_data["labels"].get(lang, "")
            label_value = st.text_input(
                "Label",
                value=current_value,
                key=f"label_{lang}",
                help=guidance if guidance else None,
                label_visibility="collapsed",
            )
            entity_data["labels"][lang] = label_value

        # ---- DESCRIPTION ----
        desc_meta = descriptions_map.get(lang)
        if desc_meta:
            field_label = getattr(desc_meta, "label", "Description")
            input_prompt = getattr(desc_meta, "input_prompt", "")
            guidance = getattr(desc_meta, "guidance", "")

            st.write(f"**{field_label}**")
            if input_prompt:
                st.caption(input_prompt)

            current_value = entity_data["descriptions"].get(lang, "")
            desc_value = st.text_area(
                "Description",
                value=current_value,
                height=80,
                key=f"description_{lang}",
                help=guidance if guidance else None,
                label_visibility="collapsed",
            )
            entity_data["descriptions"][lang] = desc_value

        # ---- ALIASES ----
        alias_meta = aliases_map.get(lang)
        if alias_meta:
            field_label = getattr(alias_meta, "label", "Aliases")
            input_prompt = getattr(alias_meta, "input_prompt", "")
            guidance = getattr(alias_meta, "guidance", "")

            st.divider()
            st.write(f"**{field_label}**")
            if input_prompt:
                st.caption(input_prompt)

            # Initialize aliases list if needed
            if lang not in entity_data["aliases"]:
                entity_data["aliases"][lang] = []

            current_aliases = entity_data["aliases"][lang]

            # Render alias input fields with delete buttons
            # Collect updates and save them (including empty ones for in-progress editing)
            updated_aliases = []
            for idx, alias in enumerate(current_aliases):
                col1, col2 = st.columns([5, 1])
                with col1:
                    updated_alias = st.text_input(
                        "Alias",
                        value=alias,
                        key=f"alias_{lang}_{idx}",
                        help=guidance if guidance and idx == 0 else None,
                        label_visibility="collapsed",
                    )
                    updated_aliases.append(updated_alias)
                with col2:
                    if st.button("🗑️", key=f"delete_alias_{lang}_{idx}"):
                        entity_data["aliases"][lang].pop(idx)
                        st.rerun()

            # Save ALL values to state (keep empty ones during editing, will be filtered at validation/save)
            entity_data["aliases"][lang] = updated_aliases

            # "Add" button
            if st.button("➕ Add", key=f"add_alias_{lang}"):
                entity_data["aliases"][lang].append("")
                st.rerun()

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate identification data.

        Args:
            draft_data: GKC Entity JSON object.

        Returns warnings if:
        - Required labels are missing
        - Required descriptions are missing
        """
        warnings = {}

        labels = draft_data.get("labels", {})
        descriptions = draft_data.get("descriptions", {})

        # Get profile and language configuration
        if "profile" not in st.session_state or st.session_state.profile is None:
            return warnings

        profile = st.session_state.profile
        supported_languages = get_profile_languages(profile)

        if not supported_languages:
            return warnings

        # Get metadata maps
        labels_map = _as_language_map(getattr(profile, "labels", {}))
        descriptions_map = _as_language_map(getattr(profile, "descriptions", {}))

        # Check for required labels
        missing_required_labels = []
        for lang in supported_languages:
            meta = labels_map.get(lang)
            if meta and getattr(meta, "required", False):
                if not labels.get(lang, "").strip():
                    missing_required_labels.append(lang)

        if missing_required_labels:
            warnings["labels"] = [
                f"Missing **required** labels for: {', '.join(missing_required_labels)}"
            ]

        # Check for required descriptions
        missing_required_descriptions = []
        for lang in supported_languages:
            meta = descriptions_map.get(lang)
            if meta and getattr(meta, "required", False):
                if not descriptions.get(lang, "").strip():
                    missing_required_descriptions.append(lang)

        if missing_required_descriptions:
            warnings["descriptions"] = [
                f"Missing **required** descriptions for: {', '.join(missing_required_descriptions)}"
            ]

        return warnings


class SitelinksStep(Step):
    """Collect Wikipedia/Wikimedia sitelinks.

    Plain meaning: The "where is this on Wikipedia?" step.
    """

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        """Render sitelinks selector and title entry.

        Args:
            draft_data: GKC Entity JSON object.

        Returns:
            The same entity object (modified in-place).
        """
        st.header("🔗 Sitelinks")

        if "profile" not in st.session_state or st.session_state.profile is None:
            st.error("No profile loaded")
            return draft_data

        profile = st.session_state.profile

        # Show profile name and description
        st.write(f"**{profile.name}** — {profile.description}")

        # Initialize sitelinks field if not present
        if "sitelinks" not in draft_data:
            draft_data["sitelinks"] = {}

        # Get sitelinks configuration from profile
        if not hasattr(profile, "sitelinks") or not profile.sitelinks:
            st.warning("Profile has no sitelinks configuration")
            return draft_data

        # Get top-level guidance if present
        sitelinks_guidance = getattr(profile.sitelinks, "guidance", "")
        if sitelinks_guidance:
            st.info(sitelinks_guidance)

        # Get available languages from profile.sitelinks.languages
        available_langs = _as_language_map(profile.sitelinks)

        if not available_langs:
            st.warning("No sitelinks languages configured in profile")
            return draft_data

        # Determine which languages are currently configured
        current_site_codes = list(draft_data["sitelinks"].keys())
        current_langs = [
            code.replace("wiki", "")
            for code in current_site_codes
            if code.endswith("wiki")
        ]

        # Language selector
        st.subheader("Select Languages")
        selected_langs = st.multiselect(
            "Which language editions should have articles/links?",
            options=list(available_langs.keys()),
            default=current_langs,
            help="Select languages where this entity has Wikipedia articles or other wiki links",
        )

        # Title entry for selected languages
        if selected_langs:
            st.subheader("Article Titles")

            for lang in selected_langs:
                lang_meta = available_langs.get(lang)
                site_code = f"{lang}wiki"  # e.g., "enwiki", "chrwiki"

                if lang_meta:
                    field_label = getattr(
                        lang_meta, "description", f"{lang.upper()} article title"
                    )
                    input_prompt = getattr(lang_meta, "input_prompt", "")
                    guidance = getattr(lang_meta, "guidance", "")

                    if input_prompt:
                        st.write(input_prompt)

                    current_title = draft_data["sitelinks"].get(site_code, "")
                    title = st.text_input(
                        field_label,
                        value=current_title,
                        key=f"sitelink_{lang}",
                        help=guidance if guidance else None,
                    )

                    # Store in entity sitelinks using standard Wikidata format
                    if title.strip():
                        draft_data["sitelinks"][site_code] = title
                    elif site_code in draft_data["sitelinks"]:
                        # Remove if emptied
                        del draft_data["sitelinks"][site_code]

        # Remove sitelinks for languages that were deselected
        for site_code in list(draft_data["sitelinks"].keys()):
            lang_code = site_code.replace("wiki", "")
            if lang_code not in selected_langs:
                del draft_data["sitelinks"][site_code]

        return draft_data

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate sitelinks data.

        Args:
            draft_data: GKC Entity JSON object.

        Returns:
            Dictionary of validation warnings.
        """
        warnings = {}

        sitelinks_data = draft_data.get("sitelinks", {})

        # Warn if no sitelinks provided (may be acceptable for some entities)
        if not sitelinks_data:
            warnings["sitelinks"] = ["No sitelinks provided"]

        return warnings


class StatementsStep(Step):
    """Collect structured statements about the entity.

    Plain meaning: The "what do we know about this thing?" step.

    Handles complex statement rendering with qualifiers and references.
    """

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        """Render statements collection interface."""
        st.header("📊 Statements")

        if "profile" not in st.session_state or st.session_state.profile is None:
            st.error("No profile loaded")
            return draft_data

        profile = st.session_state.profile

        # Show profile name and description
        st.write(f"**{profile.name}** — {profile.description}")

        # Initialize statements section
        if "statements" not in draft_data:
            draft_data["statements"] = {}

        # Check if profile has statements
        if not hasattr(profile, "statements") or not profile.statements:
            st.warning("Profile has no statements configuration")
            return draft_data

        # Group statements (for MVP, just show as tabs)
        statement_ids = [stmt.id for stmt in profile.statements]

        if not statement_ids:
            st.info("No statements configured in this profile")
            return draft_data

        # For MVP: Show all statements in one screen with expanders for each
        st.write("Add structured data about this entity:")

        for statement_def in profile.statements:
            self._render_statement(statement_def, draft_data)

        return draft_data

    def _render_statement(self, statement_def: Any, draft_data: dict[str, Any]) -> None:
        """Render a single statement property.

        Args:
            statement_def: Statement definition from profile
            draft_data: Current draft data being edited
        """
        stmt_id = statement_def.id

        # Initialize statement data if needed
        if stmt_id not in draft_data["statements"]:
            draft_data["statements"][stmt_id] = []

        # Get current values for this statement
        current_values = draft_data["statements"][stmt_id]

        # Check if this statement should be auto-expanded
        # Expand if: (1) coming from Plan screen, (2) after Add/Delete, or (3) has values entered
        auto_expand = (
            (
                hasattr(st.session_state, "expand_statement")
                and st.session_state.expand_statement == stmt_id
            )
            or (
                hasattr(st.session_state, "keep_expanded")
                and st.session_state.keep_expanded == stmt_id
            )
            or (len(current_values) > 0)  # Keep open if user is working on it
        )

        # Clear the flags after using them
        if hasattr(st.session_state, "expand_statement"):
            st.session_state.expand_statement = None
        if hasattr(st.session_state, "keep_expanded"):
            st.session_state.keep_expanded = None

        # Create expander for this statement (removed PID from title)
        with st.expander(f"**{statement_def.label}**", expanded=auto_expand):
            # Show input prompt/guidance if present
            if hasattr(statement_def, "input_prompt") and statement_def.input_prompt:
                st.caption(statement_def.input_prompt)

            if hasattr(statement_def, "guidance") and statement_def.guidance:
                with st.popover("ℹ️ Help"):
                    st.write(statement_def.guidance)

            # Check for form_policy
            form_policy = getattr(statement_def, "form_policy", None)
            entity_profile = getattr(statement_def, "entity_profile", None)

            if form_policy == "target_only" and entity_profile:
                st.info(
                    f"🔗 This property references items from the **{entity_profile}** profile. "
                    f"For MVP, enter the QID directly. Sub-wizard creation coming soon."
                )

            # Check behavior (fixed value vs editable)
            behavior = getattr(statement_def, "behavior", None)
            value_behavior = (
                getattr(behavior, "value", "editable") if behavior else "editable"
            )

            if value_behavior == "fixed":
                # Show fixed value read-only
                self._render_fixed_value(statement_def)
            else:
                # Show editable values
                self._render_editable_values(statement_def, current_values, draft_data)

            # Show add button if not at max count
            max_count = getattr(statement_def, "max_count", None)
            can_add_more = max_count is None or len(current_values) < max_count

            if can_add_more and value_behavior != "fixed":
                if st.button(f"➕ Add {statement_def.label}", key=f"add_{stmt_id}"):
                    # Add empty statement to trigger form display
                    current_values.append(self._create_empty_statement(statement_def))
                    # Keep this expander open after rerun
                    st.session_state.keep_expanded = stmt_id
                    st.rerun()

    def _render_fixed_value(self, statement_def: Any) -> None:
        """Render a fixed value statement (read-only).

        Args:
            statement_def: Statement definition from profile
        """
        # Get fixed value from definition
        value_config = getattr(statement_def, "value", None)
        fixed_value = getattr(value_config, "fixed", None) if value_config else None
        if fixed_value is not None:
            fixed_label = getattr(value_config, "label", fixed_value)

            st.markdown(f"**Value (fixed):** {fixed_label} `({fixed_value})`")
            st.caption("This value is fixed by the profile and cannot be changed.")

            # Still show references section (editable for fixed values)
            st.write("---")
            st.write("**References**")
            st.caption("Add source references for this statement:")
            st.info("References rendering coming in next update")
        else:
            st.warning("Fixed value configured but no value specified in profile")

    def _render_editable_values(
        self, statement_def: Any, current_values: list, draft_data: dict[str, Any]
    ) -> None:
        """Render editable value inputs for a statement.

        Args:
            statement_def: Statement definition from profile
            current_values: List of current statement values
            draft_data: Current draft data
        """
        stmt_id = statement_def.id

        if not current_values:
            st.caption("_No values added yet. Click 'Add' below to create one._")
            return

        # Render each value
        for idx, value_data in enumerate(current_values):
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])

                with col1:
                    st.markdown(f"**Value {idx + 1}**")

                with col2:
                    if st.button(
                        "🗑️", key=f"delete_{stmt_id}_{idx}", help="Delete this value"
                    ):
                        current_values.pop(idx)
                        # Keep this expander open after rerun
                        st.session_state.keep_expanded = stmt_id
                        st.rerun()

                # Render main value
                self._render_value_input(statement_def, value_data, idx)

                # Render qualifiers if defined
                if hasattr(statement_def, "qualifiers") and statement_def.qualifiers:
                    st.write("**Qualifiers**")
                    self._render_qualifiers(statement_def, value_data, idx)

                # Render references if defined
                if hasattr(statement_def, "references") and statement_def.references:
                    st.write("**References**")
                    self._render_references(statement_def, value_data, idx)

    def _render_value_input(
        self, statement_def: Any, value_data: dict, idx: int
    ) -> None:
        """Render the main value input widget.

        Args:
            statement_def: Statement definition from profile
            value_data: Current value data
            idx: Index of this value in the list
        """
        value_config = getattr(statement_def, "value", None)
        if not value_config:
            st.warning("No value configuration in statement definition")
            return

        datatype = getattr(value_config, "type", "string")

        # Get current value
        current_value = value_data.get("value", None)

        # Render widget based on datatype
        widget_key = f"{statement_def.id}_value_{idx}"
        new_value = WidgetFactory.render_widget(
            datatype=datatype,
            label="Value",
            value=current_value,
            key=widget_key,
            help_text=getattr(statement_def, "input_prompt", None),
        )

        # Store value
        value_data["value"] = new_value

    def _render_qualifiers(
        self, statement_def: Any, value_data: dict, idx: int
    ) -> None:
        """Render qualifiers for a statement value.

        Args:
            statement_def: Statement definition from profile
            value_data: Current value data
            idx: Index of this value in the list
        """
        if "qualifiers" not in value_data:
            value_data["qualifiers"] = {}

        qualifiers_def = statement_def.qualifiers

        for qualifier_def in qualifiers_def:
            qual_id = qualifier_def.id

            # Get current qualifier value
            current_qual_value = value_data["qualifiers"].get(qual_id, None)

            # Check if this qualifier has a fixed value (must be non-None)
            qual_value_config = getattr(qualifier_def, "value", None)
            fixed_value = (
                getattr(qual_value_config, "fixed", None) if qual_value_config else None
            )

            if fixed_value is not None:
                # Fixed qualifier value - show read-only
                fixed_label = getattr(qual_value_config, "label", fixed_value)
                st.markdown(
                    f"**{qualifier_def.label}** (fixed): {fixed_label} `({fixed_value})`"
                )
            else:
                # Editable qualifier
                datatype = (
                    getattr(qual_value_config, "type", "string")
                    if qual_value_config
                    else "string"
                )

                widget_key = f"{statement_def.id}_qual_{qual_id}_{idx}"
                new_qual_value = WidgetFactory.render_widget(
                    datatype=datatype,
                    label=qualifier_def.label,
                    value=current_qual_value,
                    key=widget_key,
                    help_text=getattr(qualifier_def, "input_prompt", None),
                )

                value_data["qualifiers"][qual_id] = new_qual_value

    def _render_references(
        self, statement_def: Any, value_data: dict, idx: int
    ) -> None:
        """Render references for a statement value.

        Args:
            statement_def: Statement definition from profile
            value_data: Current value data
            idx: Index of this value in the list
        """
        refs_config = getattr(statement_def, "references", None)
        if not refs_config:
            return

        # Initialize references list if needed
        if "references" not in value_data:
            value_data["references"] = []

        stmt_id = statement_def.id

        # Show input prompt if present
        if hasattr(refs_config, "input_prompt") and refs_config.input_prompt:
            st.caption(refs_config.input_prompt)

        # Check for min_count requirement
        min_count = getattr(refs_config, "min_count", None)
        if min_count and min_count > 0:
            st.caption(f"_Minimum {min_count} reference(s) required_")

        # Get allowed reference types (can be from 'allowed' or 'target')
        allowed_refs = []
        if hasattr(refs_config, "allowed") and refs_config.allowed:
            allowed_refs = refs_config.allowed
        elif hasattr(refs_config, "target") and refs_config.target:
            allowed_refs = [refs_config.target]

        if not allowed_refs:
            st.caption("_No reference types configured_")
            return

        # For MVP, render all allowed reference types as separate inputs
        # (Not implementing full Wikidata reference "groups" yet - one snak per reference)
        for ref_idx, ref_target in enumerate(allowed_refs):
            ref_id = ref_target.id
            ref_label = ref_target.label
            ref_type = ref_target.type

            # Find existing reference value for this type
            existing_ref = next(
                (r for r in value_data["references"] if r.get("property") == ref_id),
                None,
            )

            # Initialize if needed
            if existing_ref is None:
                existing_ref = {"property": ref_id, "value": None}
                value_data["references"].append(existing_ref)

            # Render input widget
            key = f"ref_{stmt_id}_{idx}_{ref_id}"

            # Render widget based on datatype
            existing_ref["value"] = WidgetFactory.render_widget(
                datatype=ref_type,
                label=ref_label,
                value=existing_ref.get("value"),
                key=key,
                help_text=getattr(ref_target, "input_prompt", None),
            )

    def _create_empty_statement(self, statement_def: Any) -> dict:
        """Create an empty statement value structure.

        Args:
            statement_def: Statement definition from profile

        Returns:
            Empty statement value dict
        """
        return {"value": None, "qualifiers": {}, "references": []}

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate statements data.

        Args:
            draft_data: Current draft data

        Returns:
            Dict of warnings by section
        """
        warnings = {}

        statements_data = draft_data.get("statements", {})

        # Check if any statements were added
        if not any(values for values in statements_data.values()):
            warnings["statements"] = [
                "No statements added yet - consider adding at least one"
            ]

        # TODO: Add more sophisticated validation:
        # - Required statements from profile
        # - Format validation for each value type
        # - Qualifier requirements
        # - Reference requirements

        return warnings
