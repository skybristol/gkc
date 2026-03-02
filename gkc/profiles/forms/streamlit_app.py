"""Streamlit-based wizard for entity profile data curation.

Plain meaning: Interactive web form for creating/editing Wikidata entities from profiles.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st

import gkc
from gkc.profiles import ProfileLoader
from gkc.profiles.forms.draft_manager import DraftManager
from gkc.profiles.forms.wizard import IdentificationStep, SitelinksStep, StatementsStep
from gkc.profiles.validators import EntityJSONValidator

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================


def _create_primary_entity(profile_name: str) -> dict[str, Any]:
    """Create a new primary entity following GKC Entity JSON schema.

    Args:
        profile_name: The profile name for this entity (e.g., "TribalGovernmentUS").

    Returns:
        GKC Entity JSON object for the primary entity.

    Plain meaning: Build the template for a new entity being curated.
    """
    username = os.environ.get("WIKIVERSE_USERNAME", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "packet_id": "ent-001-primary",
        "profile_name": profile_name,
        "username": username,
        "status": "in_progress",
        "created_at": timestamp,
        "creation_path": "primary",
        "labels": {},
        "descriptions": {},
        "aliases": {},
        "statements": {},
        "sitelinks": {},
    }


def init_session_state() -> None:
    """Initialize Streamlit session state with default values.

    Plain meaning: Set up the persistent data store for the wizard session.
    """
    if "draft_data" not in st.session_state:
        # Initialize empty curation packet (entity will be added once profile loads)
        st.session_state.draft_data = {
            "metadata": {
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "last_modified": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "curator": os.environ.get("WIKIVERSE_USERNAME", "unknown"),
            },
            "entities": [],
        }

    if "current_step" not in st.session_state:
        st.session_state.current_step = "plan"

    if "profile" not in st.session_state:
        st.session_state.profile = None

    if "profile_name" not in st.session_state:
        st.session_state.profile_name = None

    if "profile_metadata" not in st.session_state:
        st.session_state.profile_metadata = None

    if "validation_errors" not in st.session_state:
        st.session_state.validation_errors = {}

    if "draft_manager" not in st.session_state:
        st.session_state.draft_manager = DraftManager()

    if "current_draft_path" not in st.session_state:
        st.session_state.current_draft_path = None

    if "save_success_message" not in st.session_state:
        st.session_state.save_success_message = None


def get_primary_entity() -> dict[str, Any]:
    """Get the primary entity from the curation packet.

    Returns:
        The primary entity (packet_id "ent-001-primary").

    Plain meaning: Access the main entity being edited (for MVP, always the first/only one).
    """
    entities = st.session_state.draft_data.get("entities", [])

    # Find primary entity
    for entity in entities:
        if entity["packet_id"] == "ent-001-primary":
            return entity

    # If no primary entity exists, create one
    if st.session_state.profile_name:
        primary = _create_primary_entity(st.session_state.profile_name)
        st.session_state.draft_data["entities"].append(primary)
        return primary

    # Fallback (should not reach here in normal flow)
    return {}


# ============================================================================
# PROFILE LOADING
# ============================================================================


@st.cache_resource
def get_profile_loader() -> ProfileLoader:
    """Get cached ProfileLoader instance.

    Plain meaning: Reuse the same profile loader across reruns.
    """
    return ProfileLoader()


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_profile(profile_name: str) -> Any:
    """Load a profile by name from SpiritSafe (cached to avoid rate limits).

    Args:
        profile_name: Name of the profile to load (e.g., "TribalGovernmentUS").

    Returns:
        ProfileDefinition object.

    Plain meaning: Fetch the profile YAML and parse it, caching to avoid repeated API calls.
    """
    loader = get_profile_loader()
    resolved_profile = gkc.resolve_profile_path(profile_name)

    resolved_profile_str = str(resolved_profile)
    try:
        # First try direct path load (works for absolute/relative paths)
        return loader.load_from_file(resolved_profile_str)
    except FileNotFoundError:
        # If relative path doesn't exist, resolve via SpiritSafe source
        source = gkc.get_spirit_safe_source()
        resolved = source.resolve_relative(resolved_profile_str)

        if isinstance(resolved, str):
            # It's a GitHub URL
            response = requests.get(resolved, timeout=30)
            response.raise_for_status()
            return loader.load_from_text(response.text)
        else:
            # It's a Path
            return loader.load_from_file(resolved)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_profile_metadata(profile_name: str) -> Any:
    """Load profile metadata from metadata.yaml (cached to avoid rate limits).

    Args:
        profile_name: Name of the profile (e.g., "TribalGovernmentUS").

    Returns:
        ProfileMetadata object or None if not found.

    Plain meaning: Fetch the profile's metadata.yaml and parse it, caching to avoid repeated API calls.
    """
    try:
        return gkc.get_profile_metadata(profile_name)
    except (FileNotFoundError, ValueError) as e:
        st.warning(f"Could not load metadata for {profile_name}: {e}")
        return None


# ============================================================================
# STEP NAVIGATION
# ============================================================================


STEPS = [
    {"id": "plan", "title": "Plan", "icon": "📋"},
    {"id": "identification", "title": "Identification", "icon": "🏷️"},
    {"id": "statements", "title": "Statements", "icon": "📝"},
    {"id": "sitelinks", "title": "Sitelinks", "icon": "🔗"},
    {"id": "review", "title": "Review", "icon": "✅"},
]


def render_status_widget() -> None:
    """Render entity status widget in sidebar (Phase 7.2).

    Shows:
    - Entity label with fallback
    - Progress (X of Y completed)
    - Progress bar visualization

    Plain meaning: Display curation progress summary for quick reference.
    """
    if not st.session_state.profile:
        return

    entity = get_primary_entity()
    profile = st.session_state.profile
    profile_name = st.session_state.profile_name

    # Calculate completeness
    completeness = EntityJSONValidator.calculate_completeness(
        entity, profile, required_languages=None
    )

    # Determine display label (priority: curator label → fallback)
    entity_labels = entity.get("labels", {})
    if entity_labels:
        # Use first available label
        display_label = next(iter(entity_labels.values()))
        # Truncate if too long for sidebar
        if len(display_label) > 30:
            display_label = display_label[:27] + "..."
    else:
        display_label = f"New {profile_name}"

    # Render status widget
    st.sidebar.subheader("📊 Status")
    st.sidebar.write(f"**{display_label}**")
    st.sidebar.caption(f"Profile: {profile_name}")

    # Progress metrics
    st.sidebar.progress(completeness.progress_percentage / 100)
    st.sidebar.write(
        f"**{completeness.completed_fields} of {completeness.required_fields_total}** completed"
    )
    st.sidebar.caption(f"{completeness.progress_percentage:.0f}% complete")

    st.sidebar.divider()


def render_step_sidebar() -> None:
    """Render step navigation in sidebar.

    Plain meaning: Show clickable step buttons with visual highlighting.
    """
    st.sidebar.title("Wizard Steps")

    for step in STEPS:
        # Visual indicator for current step
        if st.session_state.current_step == step["id"]:
            button_label = f"**→ {step['icon']} {step['title']}**"
            button_type = "primary"
        else:
            button_label = f"{step['icon']} {step['title']}"
            button_type = "secondary"

        if st.sidebar.button(
            button_label,
            key=f"nav_{step['id']}",
            type=button_type,
            use_container_width=True,
        ):
            st.session_state.current_step = step["id"]
            st.rerun()


def render_step_content() -> None:
    """Render the content for the current step.

    Plain meaning: Show the form fields appropriate for the current wizard step.
    """
    current_step = st.session_state.current_step

    if current_step == "plan":
        render_plan_step()
    elif current_step == "identification":
        render_identification_step()
    elif current_step == "statements":
        render_statements_step()
    elif current_step == "sitelinks":
        render_sitelinks_step()
    elif current_step == "review":
        render_review_step()
    else:
        st.error(f"Unknown step: {current_step}")


# ============================================================================
# STEP IMPLEMENTATIONS (PHASE 2-6)
# ============================================================================


def _auto_save_draft() -> None:
    """Auto-save the current draft after step changes.

    Plain meaning: Persist data to disk so work isn't lost.
    """
    if st.session_state.profile_name and st.session_state.draft_manager:
        # Update last_modified timestamp
        st.session_state.draft_data["metadata"]["last_modified"] = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Use existing draft path or create new one
        if st.session_state.current_draft_path is None:
            draft_path = st.session_state.draft_manager.create_draft_path(
                st.session_state.profile_name
            )
            st.session_state.current_draft_path = draft_path
        else:
            draft_path = st.session_state.current_draft_path

        st.session_state.draft_manager.save(draft_path, st.session_state.draft_data)


def _save_draft_manual() -> None:
    """Manually save draft and provide user feedback.

    Plain meaning: Save the draft and show confirmation to the user.
    """
    _auto_save_draft()
    draft_path = st.session_state.current_draft_path
    if draft_path:
        st.session_state.save_success_message = f"Draft saved to: {draft_path.name}"
    else:
        st.session_state.save_success_message = "Draft saved successfully!"


def render_plan_step() -> None:
    """Render the Plan step (Phase 2).

    Plain meaning: Show planning/overview of the editing session.
    """
    if st.session_state.profile:
        profile = st.session_state.profile
        metadata = st.session_state.profile_metadata

        # Show profile name
        st.subheader(profile.name)

        # Show extended description from metadata if available, otherwise profile description
        if metadata and metadata.description:
            st.write(metadata.description)
        else:
            st.write(profile.description)

        # Show full metadata in an expander
        if metadata:
            with st.expander("📄 View Full Profile Metadata"):
                import yaml

                # Convert metadata to dict for YAML rendering
                metadata_dict = {
                    "name": metadata.name,
                    "description": metadata.description,
                    "version": metadata.version,
                    "status": metadata.status,
                    "published_date": metadata.published_date,
                }
                if metadata.authors:
                    metadata_dict["authors"] = metadata.authors
                if metadata.maintainers:
                    metadata_dict["maintainers"] = metadata.maintainers
                if metadata.source_references:
                    metadata_dict["source_references"] = metadata.source_references
                if metadata.related_profiles:
                    metadata_dict["related_profiles"] = metadata.related_profiles
                if metadata.community_feedback:
                    metadata_dict["community_feedback"] = metadata.community_feedback
                if metadata.datatypes_used:
                    metadata_dict["datatypes_used"] = metadata.datatypes_used
                if metadata.statements_count is not None:
                    metadata_dict["statements_count"] = metadata.statements_count
                if metadata.references_required is not None:
                    metadata_dict["references_required"] = metadata.references_required
                if metadata.qualifiers_used:
                    metadata_dict["qualifiers_used"] = metadata.qualifiers_used
                if metadata.sparql_sources:
                    metadata_dict["sparql_sources"] = metadata.sparql_sources

                st.code(
                    yaml.dump(metadata_dict, sort_keys=False, allow_unicode=True),
                    language="yaml",
                )

        # Show profile statements
        if hasattr(profile, "statements") and profile.statements:
            st.subheader("Profile Statements")
            for stmt in profile.statements:
                # Display statement label as clickable link to jump to Statements step
                if st.button(
                    stmt.label, key=f"goto_{stmt.id}", use_container_width=True
                ):
                    st.session_state.expand_statement = stmt.id
                    st.session_state.current_step = "statements"
                    st.rerun()
    else:
        st.warning("No profile loaded. Please select a profile from the configuration.")

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("Next: Identification →", type="primary", key="next_plan"):
            st.session_state.current_step = "identification"
            st.rerun()


def render_identification_step() -> None:
    """Render the Identification step.

    Plain meaning: Collect labels, descriptions, and aliases.
    """
    # Get primary entity from curation packet
    entity = get_primary_entity()

    step = IdentificationStep(
        id="identification",
        title="",
        description="",
    )

    # Pass entity data to step renderer (step modifies in-place)
    step.render(entity)

    # Auto-save after rendering
    _auto_save_draft()

    # Show validation warnings
    validation_errors = step.validate(entity)
    if validation_errors:
        with st.expander("⚠️ Validation Warnings"):
            for field, messages in validation_errors.items():
                for msg in messages:
                    st.warning(msg)

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Plan", type="secondary", key="back_identification"):
            st.session_state.current_step = "plan"
            st.rerun()
    with col3:
        if st.button("Next: Statements →", type="primary", key="next_identification"):
            st.session_state.current_step = "statements"
            st.rerun()


def render_statements_step() -> None:
    """Render the Statements step.

    Plain meaning: Collect statement values with qualifiers and references.
    """
    # Get primary entity from curation packet
    entity = get_primary_entity()

    # Create step instance
    step = StatementsStep(
        id="statements",
        title="",  # Title shown in step header
        description="",  # Description not needed, profile provides context
    )

    # Render step content and collect data (step modifies entity in-place)
    step.render(entity)

    # Run validation (non-blocking)
    warnings = step.validate(entity)
    if warnings:
        with st.expander("⚠️ Validation Warnings", expanded=False):
            for section, messages in warnings.items():
                st.warning(f"**{section.title()}**: " + "; ".join(messages))

    # Navigation
    st.write("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Identification", type="secondary"):
            _auto_save_draft()
            st.session_state.current_step = "identification"
            st.rerun()
    with col3:
        if st.button("Next: Sitelinks →", type="primary"):
            _auto_save_draft()
            st.session_state.current_step = "sitelinks"
            st.rerun()


def render_sitelinks_step() -> None:
    """Render the Sitelinks step.

    Plain meaning: Collect Wikipedia/sister project links.
    """
    # Get primary entity from curation packet
    entity = get_primary_entity()

    step = SitelinksStep(
        id="sitelinks",
        title="",
        description="",
    )

    step.render(entity)

    # Auto-save after rendering
    _auto_save_draft()

    # Show validation warnings
    validation_errors = step.validate(entity)
    if validation_errors:
        with st.expander("⚠️ Validation Warnings"):
            for field, messages in validation_errors.items():
                for msg in messages:
                    st.warning(msg)

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Statements", type="secondary", key="back_sitelinks"):
            st.session_state.current_step = "statements"
            st.rerun()
    with col3:
        if st.button("Next: Review →", type="primary", key="next_sitelinks"):
            st.session_state.current_step = "review"
            st.rerun()


def render_review_step() -> None:
    """Render the Review step (Phase 6 + 7.3).

    Plain meaning: Show collected data, calculate completeness, and export options.
    """
    st.header("✅ Review & Export")

    entity = get_primary_entity()
    profile = st.session_state.profile

    # Calculate completeness
    if profile:
        completeness = EntityJSONValidator.calculate_completeness(
            entity, profile, required_languages=None
        )

        # Show progress (Phase 7.3: larger format in review)
        st.subheader("Curation Progress")
        st.progress(completeness.progress_percentage / 100)
        st.write(
            f"**{completeness.progress_text}** ({completeness.progress_percentage:.0f}% complete)"
        )

        # Phase 7.3: Statement-level completeness breakdown
        st.subheader("📋 Statement Completeness")
        entity_statements = entity.get("statements", {})

        # Display all statements from profile in order
        for stmt_def in profile.statements:
            statement_id = stmt_def.id
            statement_label = stmt_def.label
            is_filled = (
                statement_id in entity_statements and entity_statements[statement_id]
            )
            is_required = stmt_def.required

            # Visual indicator
            if is_filled:
                icon = "✅"
                status = "Completed"
                status_color = "green"
            elif is_required:
                icon = "❌"
                status = "Required - Missing"
                status_color = "red"
            else:
                icon = "⚪"
                status = "Optional - Not filled"
                status_color = "gray"

            # Display row
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                st.write(icon)
            with col2:
                st.write(f"**{statement_label}**")
                if stmt_def.input_prompt:
                    st.caption(stmt_def.input_prompt)
            with col3:
                if status_color == "green":
                    st.success(status)
                elif status_color == "red":
                    st.error(status)
                else:
                    st.write(status)

        st.write("---")

        # Show language coverage
        with st.expander("🌐 Language Coverage"):
            st.write(f"**Required:** {', '.join(completeness.required_languages)}")
            st.write(
                f"**Completed:** {', '.join(completeness.completed_languages) or 'None'}"
            )
            if completeness.missing_languages:
                st.write(f"**Missing:** {', '.join(completeness.missing_languages)}")

    # Validate schema compliance (Phase 7.4: validation display)
    st.subheader("Schema Validation")
    validation_result = EntityJSONValidator.validate_schema(entity)

    if validation_result.is_valid:
        st.success("✅ Entity JSON schema is valid")
    else:
        st.error("❌ Schema validation failed")

    if validation_result.issues:
        with st.expander(
            f"⚠️ Validation Issues ({len(validation_result.issues)})", expanded=True
        ):
            for issue in validation_result.issues:
                if issue.severity == "error":
                    st.error(f"**{issue.field}**: {issue.message}")
                elif issue.severity == "warning":
                    st.warning(f"**{issue.field}**: {issue.message}")
                else:
                    st.info(f"**{issue.field}**: {issue.message}")

                if issue.suggestion:
                    st.caption(f"💡 {issue.suggestion}")

    # Save draft button
    st.subheader("Actions")

    # Show save success message if present
    if st.session_state.save_success_message:
        st.success(st.session_state.save_success_message)
        st.session_state.save_success_message = None  # Clear after displaying

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("💾 Save Draft", type="primary"):
            _save_draft_manual()
            st.rerun()

    # Show current draft path info
    if st.session_state.current_draft_path:
        with st.expander("💾 Draft File Info", expanded=False):
            st.write(f"**Location:** `{st.session_state.current_draft_path}`")
            st.write(
                f"**Last modified:** {st.session_state.draft_data.get('metadata', {}).get('last_modified', 'N/A')}"
            )
            st.caption(
                "💡 Your work is automatically saved as you navigate between steps. "
                "Drafts are stored in `~/.gkc/drafts/` (Streamlit standard approach). "
                "Use the 'Save Draft' button above to force a save at any time."
            )

    # Navigation
    st.write("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back: Sitelinks", type="secondary"):
            st.session_state.current_step = "sitelinks"
            st.rerun()


# ============================================================================
# DRAFT LOADING
# ============================================================================


def load_most_recent_draft(
    profile_name: str, draft_manager: DraftManager
) -> tuple[dict[str, Any] | None, list[str]]:
    """Load the most recent draft for a profile if one exists.

    Args:
        profile_name: Profile name to load draft for
        draft_manager: DraftManager instance

    Returns:
        Tuple of (draft_data, validation_errors). If no draft exists, returns (None, []).

    Plain meaning: Find and load the latest saved draft with validation.
    """
    # Find all drafts for this profile
    safe_name = "_".join(profile_name.split())
    draft_files = sorted(
        draft_manager.drafts_dir.glob(f"{safe_name}_*.json"), reverse=True
    )

    if not draft_files:
        return None, []

    # Load the most recent draft
    try:
        draft_path = draft_files[0]
        draft_data = draft_manager.load(draft_path)
        validation_errors = []

        # Validate structure (basic checks)
        if not isinstance(draft_data, dict):
            return None, ["Draft file is not a valid JSON object"]

        # Check for curation packet structure
        if "entities" not in draft_data:
            # Legacy format - convert to new format
            validation_errors.append(
                "Legacy draft format detected - creating new packet structure"
            )
            return None, validation_errors

        # Validate each entity's schema
        for i, entity in enumerate(draft_data.get("entities", [])):
            result = EntityJSONValidator.validate_schema(entity)
            if not result.is_valid:
                error_count = len(
                    [issue for issue in result.issues if issue.severity == "error"]
                )
                validation_errors.append(
                    f"Entity {i + 1} has {error_count} schema errors"
                )

        return draft_data, validation_errors

    except Exception as e:
        return None, [f"Failed to load draft: {str(e)}"]


# ============================================================================
# MAIN APPLICATION
# ============================================================================


def main() -> None:
    """Main Streamlit app entry point.

    Plain meaning: Run the wizard application.
    """
    # Page configuration
    st.set_page_config(
        page_title="GKC Entity Wizard",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    init_session_state()

    # Configuration sidebar
    st.sidebar.title("Configuration")

    # Check for environment variable from CLI
    env_profile = os.environ.get("GKC_WIZARD_PROFILE")
    env_qid = os.environ.get("GKC_WIZARD_QID")

    # Determine which profile to load
    # Profile is set via CLI (GKC_WIZARD_PROFILE env var) or defaults to first available
    if st.session_state.profile_name is None:
        # First run: load profile from environment or default
        if env_profile:
            profile_to_load = env_profile
        else:
            st.sidebar.warning(
                "No profile specified. Set GKC_WIZARD_PROFILE environment variable."
            )
            st.stop()

        try:
            profile = load_profile(profile_to_load)
            metadata = load_profile_metadata(profile_to_load)
            st.session_state.profile = profile
            st.session_state.profile_name = profile_to_load
            st.session_state.profile_metadata = metadata

            # Try to load existing draft for this profile
            draft_data, load_errors = load_most_recent_draft(
                profile_to_load, st.session_state.draft_manager
            )

            if draft_data:
                st.session_state.draft_data = draft_data
                # Track the loaded draft path
                draft_files = sorted(
                    st.session_state.draft_manager.drafts_dir.glob(
                        f"{('_'.join(profile_to_load.split()))}_*.json"
                    ),
                    reverse=True,
                )
                if draft_files:
                    st.session_state.current_draft_path = draft_files[0]

                if load_errors:
                    st.sidebar.warning(f"Draft loaded with {len(load_errors)} issues")
                else:
                    st.sidebar.info(
                        f"📂 Loaded draft: {draft_files[0].name if draft_files else 'N/A'}"
                    )
            else:
                # No valid draft - ensure primary entity exists
                if load_errors:
                    for error in load_errors:
                        st.sidebar.info(f"ℹ️ {error}")

                # Create primary entity if it doesn't exist
                get_primary_entity()

        except Exception as e:
            st.sidebar.error(f"Failed to load profile '{profile_to_load}': {e}")
            st.stop()

    # Show loaded profile
    st.sidebar.success(f"✓ Loaded {st.session_state.profile_name}")

    # Show QID input if editing existing item
    if env_qid:
        st.sidebar.text_input(
            "Editing QID",
            value=env_qid,
            disabled=True,
            help="Wikidata QID passed from CLI (edit mode not yet implemented)",
        )

    st.sidebar.divider()

    # Entity status widget (Phase 7.2)
    render_status_widget()

    # Step navigation sidebar
    render_step_sidebar()

    # Main content area
    if st.session_state.profile is None:
        st.warning("⚠️ No profile loaded")
    else:
        render_step_content()

    # Footer with draft info
    st.divider()
    with st.expander("🔧 Debug Info", expanded=False):
        st.write("**Current Step:**", st.session_state.current_step)
        st.write("**Profile:**", st.session_state.profile_name)
        st.write("**Working Directory:**", os.getcwd())
        st.write(
            "**Draft Path:**",
            (
                str(st.session_state.current_draft_path)
                if st.session_state.current_draft_path
                else "N/A"
            ),
        )
        st.write("**GKC Entity JSON (Curation Packet):**")

        import json

        st.code(
            json.dumps(st.session_state.draft_data, indent=2, ensure_ascii=False),
            language="json",
        )


if __name__ == "__main__":
    main()
