"""Streamlit-based packet-native wizard for JSON entity profile curation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import streamlit as st

import gkc
from gkc.profiles.forms.draft_manager import DraftManager
from gkc.profiles.forms.validation_bridge import validate_entity_packet_data
from gkc.profiles.forms.wizard import IdentificationStep, SitelinksStep, StatementsStep
from gkc.spirit_safe import load_profile
from gkc.still_charger import build_curation_packet_from_json_profile

STEPS = [
    {"id": "plan", "title": "Plan", "icon": "📋"},
    {"id": "identification", "title": "Identification", "icon": "🏷️"},
    {"id": "statements", "title": "Statements", "icon": "📝"},
    {"id": "sitelinks", "title": "Sitelinks", "icon": "🔗"},
    {"id": "review", "title": "Review", "icon": "✅"},
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entity_id_from_uri(entity_uri: str) -> str:
    if "/" in entity_uri:
        return entity_uri.split("/")[-1]
    return entity_uri


def _profile_display_name(profile_doc: dict[str, Any]) -> str:
    metadata = profile_doc.get("metadata", {})
    labels = metadata.get("labels", {})
    return (
        labels.get("mul")
        or labels.get("en")
        or _entity_id_from_uri(profile_doc.get("entity", "unknown"))
    )


def _profile_description(profile_doc: dict[str, Any]) -> str:
    metadata = profile_doc.get("metadata", {})
    descriptions = metadata.get("descriptions", {})
    return descriptions.get("mul") or descriptions.get("en") or ""


def _metadata_text(messages: dict[str, Any], key: str) -> str:
    if not isinstance(messages, dict):
        return ""
    for lang in ("mul", "en", "es"):
        lang_map = messages.get(lang)
        if isinstance(lang_map, dict) and isinstance(lang_map.get(key), str):
            return lang_map[key]
    return ""


def _statement_label(statement_def: dict[str, Any]) -> str:
    label = statement_def.get("label")
    if isinstance(label, str) and label.strip():
        return label
    entity_ref = statement_def.get("entity", "statement")
    return _entity_id_from_uri(str(entity_ref))


def _statement_label_map(entity_slot: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for statement_def in entity_slot.get("statements", []):
        if not isinstance(statement_def, dict):
            continue
        statement_ref = statement_def.get("entity")
        if not isinstance(statement_ref, str) or not statement_ref:
            continue
        labels[statement_ref] = _statement_label(statement_def)
    return labels


def _collect_review_consequences(entity_slot: dict[str, Any]) -> dict[str, str]:
    statements = entity_slot.get("statements", [])
    data = entity_slot.get("data", {})
    data_statements = data.get("statements", {}) if isinstance(data, dict) else {}

    consequences: dict[str, str] = {}
    for statement_def in statements:
        if not isinstance(statement_def, dict):
            continue

        statement_ref = statement_def.get("entity")
        if not isinstance(statement_ref, str) or not statement_ref:
            continue

        configured_values = data_statements.get(statement_ref, [])
        has_value = isinstance(configured_values, list) and len(configured_values) > 0
        if has_value:
            continue

        consequence = _metadata_text(
            statement_def.get("messages", {}),
            "consequences_message",
        )
        if consequence:
            consequences[statement_ref] = consequence

    return consequences


def _group_review_items(
    *,
    entity_slot: dict[str, Any],
    notices: list[Any],
) -> tuple[list[dict[str, Any]], list[Any]]:
    statement_labels = _statement_label_map(entity_slot)
    consequences = _collect_review_consequences(entity_slot)
    entity_ref = entity_slot.get("id") or entity_slot.get("profile_entity")

    grouped: dict[str, dict[str, Any]] = {}
    for statement_ref, label in statement_labels.items():
        grouped[statement_ref] = {
            "statement_ref": statement_ref,
            "label": label,
            "consequence": consequences.get(statement_ref),
            "notices": [],
        }

    ungrouped: list[Any] = []
    for notice in notices:
        if entity_ref and notice.entity_ref != entity_ref:
            ungrouped.append(notice)
            continue

        statement_ref = notice.statement_ref
        if isinstance(statement_ref, str) and statement_ref in grouped:
            grouped[statement_ref]["notices"].append(notice)
        else:
            ungrouped.append(notice)

    ordered_sections = [
        grouped[statement_ref]
        for statement_ref in statement_labels
        if grouped[statement_ref]["consequence"] or grouped[statement_ref]["notices"]
    ]
    return ordered_sections, ungrouped


def _normalize_profile_ref(profile_ref: str) -> str:
    if profile_ref.startswith("http://") or profile_ref.startswith("https://"):
        return profile_ref
    if profile_ref.startswith("Q"):
        return f"https://datadistillery.wikibase.cloud/entity/{profile_ref}"
    raise ValueError(
        f"Invalid profile reference '{profile_ref}'. Use QID or full entity URI."
    )


def _build_initial_packet(
    profile_ref: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    profile_entity = _normalize_profile_ref(profile_ref)
    primary_doc = load_profile(profile_entity)

    source = gkc.get_spirit_safe_source()
    source_root: Optional[Path] = (
        source.local_root if source.mode == "local" and source.local_root else None
    )

    packet = build_curation_packet_from_json_profile(
        profile_entity=profile_entity,
        json_profile_doc=primary_doc,
        source_root=source_root,
    )

    profile_docs: dict[str, dict[str, Any]] = {}
    for entity_slot in packet.get("entities", []):
        slot_uri = entity_slot.get("profile_entity")
        if not isinstance(slot_uri, str) or not slot_uri:
            continue
        try:
            profile_docs[slot_uri] = load_profile(slot_uri)
        except Exception:
            pass

    # Ensure primary profile doc is always present.
    profile_docs.setdefault(profile_entity, primary_doc)

    # Ensure packet metadata exists for draft persistence.
    packet.setdefault(
        "metadata",
        {
            "created_at": _utc_now_iso(),
            "last_modified": _utc_now_iso(),
            "curator": os.environ.get("WIKIVERSE_USERNAME", "unknown"),
            "profile_entity": profile_entity,
        },
    )

    return packet, profile_docs


def _entity_sort_key(entity_slot: dict[str, Any]) -> tuple[int, str]:
    entity_id = str(entity_slot.get("id", ""))
    # Primary packet slot tends to be ent-001; keep deterministic order.
    is_primary = 0 if entity_id == "ent-001" else 1
    return (is_primary, entity_id)


def _entity_label(entity_slot: dict[str, Any], profile_doc: dict[str, Any]) -> str:
    entity_uri = entity_slot.get("profile_entity", "")
    entity_id = entity_slot.get("id", "unknown")
    profile_name = _profile_display_name(profile_doc)
    data = entity_slot.get("data", {})
    labels = data.get("labels", {}) if isinstance(data, dict) else {}
    chosen = labels.get("mul") or labels.get("en")
    if chosen:
        return f"{entity_id} - {chosen} ({profile_name})"
    return f"{entity_id} - New {profile_name} ({_entity_id_from_uri(entity_uri)})"


def init_session_state() -> None:
    if "packet" not in st.session_state:
        st.session_state.packet = None
    if "profile_docs" not in st.session_state:
        st.session_state.profile_docs = {}
    if "root_profile_entity" not in st.session_state:
        st.session_state.root_profile_entity = None
    if "current_step" not in st.session_state:
        st.session_state.current_step = "plan"
    if "active_entity_id" not in st.session_state:
        st.session_state.active_entity_id = None
    if "draft_manager" not in st.session_state:
        st.session_state.draft_manager = DraftManager()
    if "current_draft_path" not in st.session_state:
        st.session_state.current_draft_path = None
    if "save_success_message" not in st.session_state:
        st.session_state.save_success_message = None
    if "source_root" not in st.session_state:
        st.session_state.source_root = None
    if "conformance_notices" not in st.session_state:
        st.session_state.conformance_notices = []


def _find_active_entity_slot() -> Optional[dict[str, Any]]:
    packet = st.session_state.packet or {}
    entities = packet.get("entities", [])
    if not entities:
        return None

    active_id = st.session_state.active_entity_id
    if active_id:
        for entity_slot in entities:
            if entity_slot.get("id") == active_id:
                return entity_slot

    entities_sorted = sorted(entities, key=_entity_sort_key)
    chosen = entities_sorted[0]
    st.session_state.active_entity_id = chosen.get("id")
    return chosen


def _active_profile_doc() -> Optional[dict[str, Any]]:
    entity_slot = _find_active_entity_slot()
    if not entity_slot:
        return None
    entity_uri = entity_slot.get("profile_entity")
    return st.session_state.profile_docs.get(entity_uri)


def _active_entity_data() -> dict[str, Any]:
    entity_slot = _find_active_entity_slot()
    if entity_slot is None:
        return {}
    if "data" not in entity_slot or not isinstance(entity_slot["data"], dict):
        entity_slot["data"] = {}
    data = entity_slot["data"]
    data.setdefault("labels", {})
    data.setdefault("descriptions", {})
    data.setdefault("aliases", {})
    data.setdefault("statements", {})
    data.setdefault("sitelinks", {})
    return data


def _auto_save_draft() -> None:
    packet = st.session_state.packet
    if not isinstance(packet, dict):
        return

    metadata = packet.setdefault("metadata", {})
    metadata["last_modified"] = _utc_now_iso()

    root_entity = st.session_state.root_profile_entity or "packet"
    draft_name = _entity_id_from_uri(root_entity)

    if st.session_state.current_draft_path is None:
        st.session_state.current_draft_path = (
            st.session_state.draft_manager.create_draft_path(draft_name)
        )

    st.session_state.draft_manager.save(st.session_state.current_draft_path, packet)


def _save_draft_manual() -> None:
    _auto_save_draft()
    draft_path = st.session_state.current_draft_path
    if draft_path:
        st.session_state.save_success_message = f"Draft saved to: {draft_path.name}"


def _run_packet_validation() -> list[Any]:
    packet = st.session_state.packet or {}
    source_root = st.session_state.source_root
    if isinstance(source_root, str) and source_root:
        source_root = Path(source_root)
    if not isinstance(source_root, Path):
        source_root = None

    notices = []
    for entity_slot in packet.get("entities", []):
        notices.extend(
            validate_entity_packet_data(
                entity_slot=entity_slot,
                packet=packet,
                source_root=source_root,
            )
        )

    st.session_state.conformance_notices = notices
    return notices


def _render_conformance_notices(notices: list[Any]) -> None:
    if not notices:
        st.success("No conformance notices detected.")
        return

    error_count = sum(1 for n in notices if n.severity == "error")
    warning_count = sum(1 for n in notices if n.severity == "warning")
    info_count = sum(1 for n in notices if n.severity == "info")

    st.write(
        f"Errors: **{error_count}** | Warnings: **{warning_count}** | Info: **{info_count}**"
    )

    for notice in notices:
        message = (
            f"[{notice.code}] {notice.message} "
            f"(entity={notice.entity_ref}, statement={notice.statement_ref or 'n/a'})"
        )
        if notice.severity == "error":
            st.error(message)
        elif notice.severity == "warning":
            st.warning(message)
        else:
            st.info(message)


def _render_grouped_review_sections(
    sections: list[dict[str, Any]],
    ungrouped_notices: list[Any],
) -> None:
    if not sections and not ungrouped_notices:
        st.success(
            "No statement-level consequences or conformance notices for the active entity."
        )
        return

    for section in sections:
        label = section["label"]
        statement_ref = section["statement_ref"]
        consequence = section["consequence"]
        section_notices = section["notices"]

        with st.expander(
            f"{label} ({_entity_id_from_uri(statement_ref)})", expanded=True
        ):
            if consequence:
                st.warning(f"Consequence: {consequence}")

            if not section_notices:
                st.info("No conformance notices for this statement.")
                continue

            for notice in section_notices:
                message = f"[{notice.code}] {notice.message}"
                if notice.severity == "error":
                    st.error(message)
                elif notice.severity == "warning":
                    st.warning(message)
                else:
                    st.info(message)

    if ungrouped_notices:
        with st.expander("Other Notices", expanded=False):
            _render_conformance_notices(ungrouped_notices)


def render_entity_sidebar() -> None:
    packet = st.session_state.packet or {}
    entities = packet.get("entities", [])
    if not entities:
        return

    st.sidebar.subheader("Entities")

    entities_sorted = sorted(entities, key=_entity_sort_key)
    options = []
    labels = []
    for entity_slot in entities_sorted:
        entity_id = entity_slot.get("id")
        profile_uri = entity_slot.get("profile_entity")
        profile_doc = st.session_state.profile_docs.get(profile_uri, {})
        options.append(entity_id)
        labels.append(_entity_label(entity_slot, profile_doc))

    label_by_id = dict(zip(options, labels))
    active = st.session_state.active_entity_id or options[0]

    selected = st.sidebar.selectbox(
        "Active entity",
        options,
        format_func=lambda x: label_by_id.get(x, x),
        index=options.index(active) if active in options else 0,
    )

    if selected != st.session_state.active_entity_id:
        st.session_state.active_entity_id = selected
        st.rerun()

    st.sidebar.divider()


def render_step_sidebar() -> None:
    st.sidebar.title("Wizard Steps")

    for step in STEPS:
        is_current = st.session_state.current_step == step["id"]
        button_label = (
            f"**-> {step['icon']} {step['title']}**"
            if is_current
            else f"{step['icon']} {step['title']}"
        )
        button_type = "primary" if is_current else "secondary"
        if st.sidebar.button(
            button_label,
            key=f"nav_{step['id']}",
            type=button_type,
            use_container_width=True,
        ):
            st.session_state.current_step = step["id"]
            st.rerun()


def render_plan_step() -> None:
    st.header("📋 Plan")

    profile_doc = _active_profile_doc()
    entity_slot = _find_active_entity_slot()
    if not profile_doc or not entity_slot:
        st.warning("No active profile/entity loaded")
        return

    st.subheader(_profile_display_name(profile_doc))
    description = _profile_description(profile_doc)
    if description:
        st.write(description)

    statements = entity_slot.get("statements", [])
    st.subheader("Profile Statements")
    for statement_def in statements:
        label = statement_def.get("label") or _entity_id_from_uri(
            statement_def.get("entity", "statement")
        )
        if st.button(
            label,
            key=f"goto_stmt_{statement_def.get('entity')}",
            use_container_width=True,
        ):
            st.session_state.current_step = "statements"
            st.session_state.expand_statement = statement_def.get("entity")
            st.rerun()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("Next: Identification ->", type="primary", key="next_plan"):
            st.session_state.current_step = "identification"
            st.rerun()


def render_identification_step() -> None:
    entity_data = _active_entity_data()
    step = IdentificationStep(id="identification", title="", description="")
    step.render(entity_data)
    _auto_save_draft()

    warnings = step.validate(entity_data)
    if warnings:
        with st.expander("⚠️ Validation Warnings"):
            for messages in warnings.values():
                for message in messages:
                    st.warning(message)

    col1, _, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("<- Back: Plan", type="secondary", key="back_identification"):
            st.session_state.current_step = "plan"
            st.rerun()
    with col3:
        if st.button("Next: Statements ->", type="primary", key="next_identification"):
            st.session_state.current_step = "statements"
            st.rerun()


def render_statements_step() -> None:
    entity_data = _active_entity_data()
    step = StatementsStep(id="statements", title="", description="")
    step.render(entity_data)
    _auto_save_draft()

    warnings = step.validate(entity_data)
    if warnings:
        with st.expander("⚠️ Validation Warnings", expanded=False):
            for section, messages in warnings.items():
                st.warning(f"{section}: {'; '.join(messages)}")

    col1, _, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button(
            "<- Back: Identification", type="secondary", key="back_statements"
        ):
            st.session_state.current_step = "identification"
            st.rerun()
    with col3:
        if st.button("Next: Sitelinks ->", type="primary", key="next_statements"):
            st.session_state.current_step = "sitelinks"
            st.rerun()


def render_sitelinks_step() -> None:
    entity_data = _active_entity_data()
    step = SitelinksStep(id="sitelinks", title="", description="")
    step.render(entity_data)
    _auto_save_draft()

    col1, _, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("<- Back: Statements", type="secondary", key="back_sitelinks"):
            st.session_state.current_step = "statements"
            st.rerun()
    with col3:
        if st.button("Next: Review ->", type="primary", key="next_sitelinks"):
            st.session_state.current_step = "review"
            st.rerun()


def render_review_step() -> None:
    st.header("✅ Review")

    packet = st.session_state.packet or {}
    entity_slot = _find_active_entity_slot()
    entity_data = _active_entity_data()

    if entity_slot:
        st.subheader(
            f"Active Entity: {entity_slot.get('id')} ({_entity_id_from_uri(entity_slot.get('profile_entity', ''))})"
        )

    if st.session_state.save_success_message:
        st.success(st.session_state.save_success_message)
        st.session_state.save_success_message = None

    col1, col2, _ = st.columns([1, 1, 1])
    with col1:
        if st.button("💾 Save Draft", type="primary", key="save_review"):
            _save_draft_manual()
            st.rerun()

    with col2:
        if st.button("Re-run Session Validation", key="rerun_validation"):
            _run_packet_validation()
            st.rerun()

    notices = st.session_state.conformance_notices
    if not notices:
        notices = _run_packet_validation()

    st.write("### Statement Review")
    sections: list[dict[str, Any]] = []
    ungrouped_notices: list[Any] = notices
    if entity_slot:
        sections, ungrouped_notices = _group_review_items(
            entity_slot=entity_slot,
            notices=notices,
        )
    _render_grouped_review_sections(sections, ungrouped_notices)

    blocking_errors = [n for n in notices if n.severity == "error"]
    if blocking_errors:
        st.error("Submission is currently blocked because error-level notices exist.")
    else:
        st.success("No error-level notices. Submission would be allowed.")

    st.write("### Active Entity Data")
    st.code(json.dumps(entity_data, indent=2, ensure_ascii=False), language="json")

    st.write("### Full Curation Packet")
    st.code(json.dumps(packet, indent=2, ensure_ascii=False), language="json")

    col1, _, _ = st.columns([1, 1, 1])
    with col1:
        if st.button("<- Back: Sitelinks", type="secondary", key="back_review"):
            st.session_state.current_step = "sitelinks"
            st.rerun()


def render_step_content() -> None:
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


def _load_packet_from_env_or_profile() -> None:
    source_mode = os.environ.get("GKC_SPIRIT_SAFE_SOURCE_MODE")
    if source_mode in {"github", "local"}:
        source_kwargs: dict[str, Any] = {
            "mode": source_mode,
            "github_repo": os.environ.get(
                "GKC_SPIRIT_SAFE_GITHUB_REPO", gkc.DEFAULT_SPIRIT_SAFE_GITHUB_REPO
            ),
            "github_ref": os.environ.get("GKC_SPIRIT_SAFE_GITHUB_REF", "main"),
        }
        if source_mode == "local":
            local_root = os.environ.get("GKC_SPIRIT_SAFE_LOCAL_ROOT")
            if local_root:
                source_kwargs["local_root"] = local_root

        gkc.set_spirit_safe_source(**source_kwargs)

    env_packet = os.environ.get("GKC_WIZARD_PACKET")
    env_profile = os.environ.get("GKC_WIZARD_PROFILE")

    if env_packet:
        packet_path = Path(env_packet)
        if not packet_path.exists():
            st.sidebar.error(f"Packet file not found: {packet_path}")
            st.stop()

        try:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
        except Exception as exc:
            st.sidebar.error(f"Failed to load packet JSON: {exc}")
            st.stop()

        profile_docs: dict[str, dict[str, Any]] = {}
        for entity_slot in packet.get("entities", []):
            profile_uri = entity_slot.get("profile_entity")
            if not profile_uri:
                continue
            try:
                profile_docs[profile_uri] = load_profile(profile_uri)
            except Exception:
                pass

        st.session_state.packet = packet
        st.session_state.profile_docs = profile_docs
        st.session_state.root_profile_entity = packet.get("profile_entity")
        source = gkc.get_spirit_safe_source()
        st.session_state.source_root = (
            str(source.local_root)
            if source.mode == "local" and source.local_root is not None
            else None
        )
        if packet.get("entities"):
            st.session_state.active_entity_id = packet["entities"][0].get("id")

        st.sidebar.success(f"Loaded packet: {packet_path.name}")
        return

    if not env_profile:
        st.sidebar.warning(
            "No profile specified. Set GKC_WIZARD_PROFILE or GKC_WIZARD_PACKET."
        )
        st.stop()

    profile_ref = str(env_profile)

    try:
        packet, profile_docs = _build_initial_packet(profile_ref)
    except Exception as exc:
        st.sidebar.error(f"Failed to build packet: {exc}")
        st.stop()

    st.session_state.packet = packet
    st.session_state.profile_docs = profile_docs
    st.session_state.root_profile_entity = packet.get("profile_entity")
    source = gkc.get_spirit_safe_source()
    st.session_state.source_root = (
        str(source.local_root)
        if source.mode == "local" and source.local_root is not None
        else None
    )
    if packet.get("entities"):
        st.session_state.active_entity_id = packet["entities"][0].get("id")

    root_qid = _entity_id_from_uri(packet.get("profile_entity", env_profile))
    st.sidebar.success(f"Built uncharged packet from {root_qid}")


def main() -> None:
    st.set_page_config(
        page_title="GKC Packet Wizard",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    st.sidebar.title("Configuration")

    if st.session_state.packet is None:
        _load_packet_from_env_or_profile()

    packet = st.session_state.packet or {}
    st.sidebar.caption(f"Packet: {packet.get('packet_id', 'unknown')}")
    st.sidebar.caption(
        f"Root: {_entity_id_from_uri(packet.get('profile_entity', 'unknown'))}"
    )
    st.sidebar.divider()

    render_entity_sidebar()
    render_step_sidebar()

    render_step_content()

    st.divider()
    with st.expander("Debug", expanded=False):
        st.write("Current step:", st.session_state.current_step)
        st.write("Active entity:", st.session_state.active_entity_id)
        st.write("Draft path:", str(st.session_state.current_draft_path or "N/A"))


if __name__ == "__main__":
    main()
