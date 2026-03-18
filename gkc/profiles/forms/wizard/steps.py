"""Packet-native step implementations for the Streamlit wizard."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

import streamlit as st

import gkc
from gkc.profiles.forms.validation_bridge import validate_inline_value
from gkc.profiles.forms.widgets import WidgetFactory
from gkc.profiles.forms.wizard.step_base import Step


def _active_profile_doc() -> dict[str, Any] | None:
    packet = st.session_state.get("packet", {})
    profile_docs = st.session_state.get("profile_docs", {})
    active_entity_id = st.session_state.get("active_entity_id")

    for entity_slot in packet.get("entities", []):
        if entity_slot.get("id") == active_entity_id:
            return profile_docs.get(entity_slot.get("profile_entity"))
    return None


def _active_entity_slot() -> dict[str, Any] | None:
    packet = st.session_state.get("packet", {})
    active_entity_id = st.session_state.get("active_entity_id")
    for entity_slot in packet.get("entities", []):
        if entity_slot.get("id") == active_entity_id:
            return entity_slot
    return None


def _metadata_text(messages: dict[str, Any], key: str) -> str:
    if not isinstance(messages, dict):
        return ""
    for lang in ("mul", "en", "es"):
        lang_map = messages.get(lang)
        if isinstance(lang_map, dict) and isinstance(lang_map.get(key), str):
            return lang_map[key]
    return ""


def _identification_map(profile_doc: dict[str, Any], section: str) -> dict[str, Any]:
    identification = profile_doc.get("identification", {})
    section_map = identification.get(section, {})
    return section_map if isinstance(section_map, dict) else {}


def _profile_name(profile_doc: dict[str, Any]) -> str:
    metadata = profile_doc.get("metadata", {})
    labels = metadata.get("labels", {}) if isinstance(metadata, dict) else {}
    return labels.get("mul") or labels.get("en") or "Profile"


def _statement_key(statement_def: dict[str, Any]) -> str:
    return statement_def.get("entity", "")


def _statement_prompt(statement_def: dict[str, Any]) -> str:
    return _metadata_text(statement_def.get("messages", {}), "prompt")


def _statement_guidance(statement_def: dict[str, Any]) -> str:
    return _metadata_text(statement_def.get("messages", {}), "guidance")


def _statement_consequence(statement_def: dict[str, Any]) -> str:
    return _metadata_text(statement_def.get("messages", {}), "consequences_message")


def _statement_label(statement_def: dict[str, Any]) -> str:
    return statement_def.get("label") or _statement_key(statement_def).split("/")[-1]


def _is_fixed(statement_def: dict[str, Any]) -> bool:
    if statement_def.get("fixed") is True:
        return True
    value_block = statement_def.get("value", {})
    return (
        isinstance(value_block.get("value_list"), list)
        and len(value_block["value_list"]) > 0
    )


def _initial_fixed_value(statement_def: dict[str, Any]) -> Any:
    value_block = statement_def.get("value", {})
    value_list = value_block.get("value_list")
    if isinstance(value_list, list) and value_list:
        first = value_list[0]
        if isinstance(first, dict):
            return first.get("item") or first.get("id") or first.get("itemLabel")
        return first
    return None


def _value_datatype(value_block: dict[str, Any]) -> str:
    dtype = value_block.get("type", "string")
    if dtype == "globe-coordinate":
        return "globecoordinate"
    return dtype


def _source_root_path() -> Path | None:
    raw_source_root = st.session_state.get("source_root")
    if isinstance(raw_source_root, str) and raw_source_root:
        return Path(raw_source_root)
    if isinstance(raw_source_root, Path):
        return raw_source_root
    return None


def _wizard_value_list_cache_root() -> Path:
    """Return the local cache root used by wizard value-list operations."""
    source = gkc.get_spirit_safe_source()
    repo_slug = source.github_repo.replace("/", "_")
    if source.mode == "local" and source.local_root is not None:
        # Keep local-mode cache names deterministic by source path hash.
        source_id = str(source.local_root).replace("/", "_").strip("_")
    else:
        source_id = source.github_ref

    cache_root = Path.home() / ".cache" / "gkc" / "wizard" / repo_slug / source_id
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _materialize_value_list_cache(cache_ref: str) -> tuple[Path | None, str | None]:
    """Materialize a value-list artifact into local wizard cache.

    Returns (local_path, error_message).
    """
    cache_ref_clean = cache_ref.lstrip("/")
    local_cache_path = _wizard_value_list_cache_root() / cache_ref_clean
    local_cache_path.parent.mkdir(parents=True, exist_ok=True)

    if local_cache_path.exists():
        return local_cache_path, None

    source = gkc.get_spirit_safe_source()

    # Prefer direct local file copy when local source root is available.
    source_root = _source_root_path()
    if source_root is not None:
        candidate = source_root / cache_ref_clean
        if candidate.exists():
            local_cache_path.write_text(
                candidate.read_text(encoding="utf-8"), encoding="utf-8"
            )
            return local_cache_path, None

    # Fallback: resolve from configured SpiritSafe source (usually GitHub raw URL).
    try:
        resolved = source.resolve_relative(cache_ref_clean)
    except Exception as exc:
        return None, f"Unable to resolve value-list source for {cache_ref_clean}: {exc}"

    try:
        if isinstance(resolved, Path):
            if not resolved.exists():
                return None, f"Value list cache file not found: {resolved}"
            content = resolved.read_text(encoding="utf-8")
        else:
            with urllib.request.urlopen(str(resolved), timeout=10) as response:
                content = response.read().decode("utf-8")
        local_cache_path.write_text(content, encoding="utf-8")
        return local_cache_path, None
    except Exception as exc:
        return None, f"Failed to materialize value list cache {cache_ref_clean}: {exc}"


def _extract_value_list_candidates(cache_data: dict[str, Any]) -> list[dict[str, str]]:
    """Extract normalized item candidates from SpiritSafe cache payloads."""
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    for entry in cache_data.get("items", []):
        if not isinstance(entry, dict):
            continue
        item_uri = entry.get("item")
        if not isinstance(item_uri, str) or not item_uri or item_uri in seen:
            continue
        label = entry.get("itemLabel")
        candidates.append(
            {
                "item": item_uri,
                "itemLabel": label if isinstance(label, str) else "",
            }
        )
        seen.add(item_uri)

    for binding in cache_data.get("results", {}).get("bindings", []):
        if not isinstance(binding, dict):
            continue
        item_node = binding.get("item")
        if not isinstance(item_node, dict):
            continue
        item_uri = item_node.get("value")
        if not isinstance(item_uri, str) or not item_uri or item_uri in seen:
            continue
        label_node = binding.get("itemLabel")
        label = (
            label_node.get("value")
            if isinstance(label_node, dict) and isinstance(label_node.get("value"), str)
            else ""
        )
        candidates.append({"item": item_uri, "itemLabel": label})
        seen.add(item_uri)

    return candidates


def _value_list_search_text(candidate: dict[str, str]) -> str:
    item_uri = candidate.get("item", "")
    qid = item_uri.rsplit("/", 1)[-1] if "/" in item_uri else item_uri
    return f"{candidate.get('itemLabel', '')} {qid} {item_uri}".lower()


def _filter_value_list_candidates(
    candidates: list[dict[str, str]], query: str, limit: int | None = None
) -> list[dict[str, str]]:
    """Filter candidates for responsive type-ahead browsing."""
    normalized_query = query.strip().lower()
    if not normalized_query:
        if limit is None:
            return candidates
        return candidates[:limit]

    filtered: list[dict[str, str]] = []
    for candidate in candidates:
        if normalized_query in _value_list_search_text(candidate):
            filtered.append(candidate)
            if limit is not None and len(filtered) >= limit:
                break
    return filtered


def _statement_value_list_candidates(
    statement_def: dict[str, Any],
) -> tuple[list[dict[str, str]], str | None]:
    """Resolve and load value-list candidates for one statement.

    Returns a tuple of (candidates, error_message).
    """
    value_block = statement_def.get("value", {})
    statement_ref = _statement_key(statement_def)

    packet = st.session_state.get("packet", {})
    route_map = packet.get("value_list_routes", {}) if isinstance(packet, dict) else {}
    route = route_map.get(statement_ref, {}) if isinstance(route_map, dict) else {}

    cache_ref = value_block.get("value_list_reference")
    if not isinstance(cache_ref, str) or not cache_ref:
        cache_ref = route.get("cache_path") if isinstance(route, dict) else None

    if not isinstance(cache_ref, str) or not cache_ref:
        return [], None

    cache_path, cache_error = _materialize_value_list_cache(cache_ref)
    if cache_error:
        return [], cache_error
    if cache_path is None:
        return [], f"Value list cache for {cache_ref} could not be materialized."

    cache_store = st.session_state.setdefault("value_list_cache", {})
    cache_key = str(cache_path)
    if cache_key in cache_store:
        return cache_store[cache_key], None

    try:
        cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"Failed to read value list cache at {cache_path}: {exc}"

    if not isinstance(cache_payload, dict):
        return [], f"Value list cache payload must be a JSON object: {cache_path}"

    candidates = _extract_value_list_candidates(cache_payload)
    cache_store[cache_key] = candidates
    return candidates, None


def _value_list_widget_kwargs(statement_def: dict[str, Any]) -> dict[str, Any]:
    """Build widget kwargs for statements constrained by hydrated value lists."""
    dtype = _value_datatype(statement_def.get("value", {}))
    if dtype not in {"item", "wikibase-item"}:
        return {}

    candidates, list_error = _statement_value_list_candidates(statement_def)
    if list_error:
        st.error(list_error)
    if not candidates:
        return {}

    return {
        "item_options": candidates,
        "all_item_options_count": len(candidates),
    }


def _normalize_rendered_value(
    *,
    datatype: str,
    value: Any,
    statement_ref: str,
) -> Any:
    """Normalize widget output while preserving explicit item metadata."""
    normalized, notices = validate_inline_value(
        datatype=datatype,
        value=value,
        entity_ref=st.session_state.get("active_entity_id", "unknown"),
        statement_ref=statement_ref,
    )
    if (
        datatype in {"item", "wikibase-item"}
        and isinstance(value, dict)
        and isinstance(normalized, dict)
    ):
        if isinstance(value.get("item"), str):
            normalized["item"] = value["item"]
        if isinstance(value.get("itemLabel"), str):
            normalized["itemLabel"] = value["itemLabel"]
    del notices
    return normalized


class IdentificationStep(Step):
    """Collect labels, descriptions, and aliases from profile identification metadata."""

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        st.header("🏷️ Identification")

        profile_doc = _active_profile_doc()
        if not profile_doc:
            st.error("No profile document loaded for active entity")
            return draft_data

        st.write(f"**{_profile_name(profile_doc)}**")

        draft_data.setdefault("labels", {})
        draft_data.setdefault("descriptions", {})
        draft_data.setdefault("aliases", {})

        labels_map = _identification_map(profile_doc, "labels")
        descriptions_map = _identification_map(profile_doc, "descriptions")
        aliases_map = _identification_map(profile_doc, "aliases")

        languages = sorted(set(labels_map) | set(descriptions_map) | set(aliases_map))
        if not languages:
            st.info("No identification metadata configured in profile.")
            return draft_data

        if len(languages) > 1:
            tabs = st.tabs([lang.upper() for lang in languages])
            for idx, lang in enumerate(languages):
                with tabs[idx]:
                    self._render_language(
                        lang, labels_map, descriptions_map, aliases_map, draft_data
                    )
        else:
            self._render_language(
                languages[0], labels_map, descriptions_map, aliases_map, draft_data
            )

        return draft_data

    def _render_language(
        self,
        lang: str,
        labels_map: dict[str, Any],
        descriptions_map: dict[str, Any],
        aliases_map: dict[str, Any],
        draft_data: dict[str, Any],
    ) -> None:
        label_meta = labels_map.get(lang, {})
        if isinstance(label_meta, dict):
            st.write("**Label**")
            if label_meta.get("prompt"):
                st.caption(label_meta["prompt"])
            draft_data["labels"][lang] = st.text_input(
                f"label-{lang}",
                value=draft_data["labels"].get(lang, ""),
                key=f"label_{lang}",
                help=label_meta.get("guidance"),
                label_visibility="collapsed",
            )

        desc_meta = descriptions_map.get(lang, {})
        if isinstance(desc_meta, dict):
            st.write("**Description**")
            if desc_meta.get("prompt"):
                st.caption(desc_meta["prompt"])
            draft_data["descriptions"][lang] = st.text_area(
                f"description-{lang}",
                value=draft_data["descriptions"].get(lang, ""),
                key=f"description_{lang}",
                help=desc_meta.get("guidance"),
                height=80,
                label_visibility="collapsed",
            )

        alias_meta = aliases_map.get(lang, {})
        if isinstance(alias_meta, dict):
            st.divider()
            st.write("**Aliases**")
            if alias_meta.get("prompt"):
                st.caption(alias_meta["prompt"])

            draft_data["aliases"].setdefault(lang, [])
            aliases = draft_data["aliases"][lang]
            updated = []
            for idx, alias in enumerate(aliases):
                c1, c2 = st.columns([5, 1])
                with c1:
                    updated_alias = st.text_input(
                        f"alias-{lang}-{idx}",
                        value=alias,
                        key=f"alias_{lang}_{idx}",
                        help=alias_meta.get("guidance") if idx == 0 else None,
                        label_visibility="collapsed",
                    )
                    updated.append(updated_alias)
                with c2:
                    if st.button("🗑️", key=f"delete_alias_{lang}_{idx}"):
                        aliases.pop(idx)
                        st.rerun()

            draft_data["aliases"][lang] = updated

            if st.button("➕ Add", key=f"add_alias_{lang}"):
                draft_data["aliases"][lang].append("")
                st.rerun()

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        warnings: dict[str, list[str]] = {}
        labels = draft_data.get("labels", {})
        if not any(v.strip() for v in labels.values() if isinstance(v, str)):
            warnings["labels"] = ["No labels entered yet."]
        return warnings


class SitelinksStep(Step):
    """Collect sitelinks as optional freeform site-code/title pairs."""

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        st.header("🔗 Sitelinks")
        st.caption("Sitelinks are optional in the baseline packet wizard.")

        draft_data.setdefault("sitelinks", {})

        if "sitelink_rows" not in st.session_state:
            st.session_state.sitelink_rows = max(1, len(draft_data["sitelinks"]))

        for idx in range(st.session_state.sitelink_rows):
            c1, c2 = st.columns([2, 3])
            default_site = ""
            default_title = ""
            if idx < len(draft_data["sitelinks"]):
                site_code = list(draft_data["sitelinks"].keys())[idx]
                default_site = site_code
                default_title = draft_data["sitelinks"][site_code]

            with c1:
                site = st.text_input(
                    f"Site code {idx + 1}",
                    value=default_site,
                    key=f"sitelink_site_{idx}",
                    placeholder="enwiki",
                )
            with c2:
                title = st.text_input(
                    f"Page title {idx + 1}",
                    value=default_title,
                    key=f"sitelink_title_{idx}",
                )

        draft_data["sitelinks"] = {}
        for idx in range(st.session_state.sitelink_rows):
            site = st.session_state.get(f"sitelink_site_{idx}", "").strip()
            title = st.session_state.get(f"sitelink_title_{idx}", "").strip()
            if site and title:
                draft_data["sitelinks"][site] = title

        if st.button("➕ Add sitelink", key="add_sitelink_row"):
            st.session_state.sitelink_rows += 1
            st.rerun()

        return draft_data

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        return {}


class StatementsStep(Step):
    """Collect statement values from packet statement scaffolds."""

    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        st.header("📊 Statements")

        entity_slot = _active_entity_slot()
        if not entity_slot:
            st.error("No active entity slot loaded")
            return draft_data

        profile_doc = _active_profile_doc()
        if profile_doc:
            st.write(f"**{_profile_name(profile_doc)}**")

        draft_data.setdefault("statements", {})
        statement_defs = entity_slot.get("statements", [])
        if not statement_defs:
            st.info("No statement scaffolds found on active entity slot.")
            return draft_data

        for statement_def in statement_defs:
            if not isinstance(statement_def, dict):
                continue
            self._render_statement(statement_def, draft_data)

        return draft_data

    def _render_statement(
        self, statement_def: dict[str, Any], draft_data: dict[str, Any]
    ) -> None:
        stmt_key = _statement_key(statement_def)
        stmt_label = _statement_label(statement_def)

        draft_data["statements"].setdefault(stmt_key, [])
        current_values = draft_data["statements"][stmt_key]

        if _is_fixed(statement_def) and not current_values:
            current_values.append(
                {
                    "value": _initial_fixed_value(statement_def),
                    "qualifiers": {},
                    "references": [],
                }
            )

        auto_expand = (
            st.session_state.get("expand_statement") == stmt_key
            or len(current_values) > 0
        )
        if st.session_state.get("expand_statement") == stmt_key:
            st.session_state.expand_statement = None

        with st.expander(f"**{stmt_label}**", expanded=auto_expand):
            prompt = _statement_prompt(statement_def)
            if prompt:
                st.caption(prompt)

            guidance = _statement_guidance(statement_def)
            if guidance:
                with st.popover("ℹ️ Guidance"):
                    st.write(guidance)

            is_fixed = _is_fixed(statement_def)
            if is_fixed:
                st.caption("This value is fixed for this profile.")

            for idx, value_data in enumerate(current_values):
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"**Value {idx + 1}**")
                    with c2:
                        if not is_fixed and st.button(
                            "🗑️", key=f"delete_{stmt_key}_{idx}"
                        ):
                            current_values.pop(idx)
                            st.rerun()

                    self._render_value_input(statement_def, value_data, idx, is_fixed)
                    self._render_qualifiers(statement_def, value_data, idx)
                    self._render_references(statement_def, value_data, idx)

            max_count = statement_def.get("max_count")
            can_add_more = (max_count is None) or (len(current_values) < max_count)
            if not is_fixed and can_add_more:
                if st.button(f"➕ Add {stmt_label}", key=f"add_stmt_{stmt_key}"):
                    current_values.append(
                        {"value": None, "qualifiers": {}, "references": []}
                    )
                    st.rerun()

    def _render_value_input(
        self,
        statement_def: dict[str, Any],
        value_data: dict[str, Any],
        idx: int,
        is_fixed: bool,
    ) -> None:
        value_block = statement_def.get("value", {})
        dtype = _value_datatype(value_block)
        current_value = value_data.get("value")

        if is_fixed:
            fixed_value = _initial_fixed_value(statement_def)
            st.text_input(
                "Value",
                value=str(fixed_value or ""),
                key=f"fixed_{_statement_key(statement_def)}_{idx}",
                disabled=True,
            )
            value_data["value"] = fixed_value
            return

        widget_kwargs = _value_list_widget_kwargs(statement_def)

        original_value = WidgetFactory.render_widget(
            datatype=dtype,
            label="Value",
            value=current_value,
            key=f"value_{_statement_key(statement_def)}_{idx}",
            help_text=_statement_prompt(statement_def),
            **widget_kwargs,
        )
        value_data["value"] = _normalize_rendered_value(
            datatype=dtype,
            value=original_value,
            statement_ref=_statement_key(statement_def),
        )

    def _render_qualifiers(
        self, statement_def: dict[str, Any], value_data: dict[str, Any], idx: int
    ) -> None:
        qualifiers = statement_def.get("qualifiers", [])
        if not qualifiers:
            return

        st.write("**Qualifiers**")
        value_data.setdefault("qualifiers", {})

        for qualifier_def in qualifiers:
            if not isinstance(qualifier_def, dict):
                continue
            qual_key = _statement_key(qualifier_def)
            qual_label = _statement_label(qualifier_def)
            qual_dtype = _value_datatype(qualifier_def.get("value", {}))
            current = value_data["qualifiers"].get(qual_key)

            widget_kwargs = _value_list_widget_kwargs(qualifier_def)
            original_value = WidgetFactory.render_widget(
                datatype=qual_dtype,
                label=qual_label,
                value=current,
                key=f"qual_{_statement_key(statement_def)}_{qual_key}_{idx}",
                help_text=_statement_prompt(qualifier_def),
                **widget_kwargs,
            )
            value_data["qualifiers"][qual_key] = _normalize_rendered_value(
                datatype=qual_dtype,
                value=original_value,
                statement_ref=qual_key,
            )

    def _render_references(
        self, statement_def: dict[str, Any], value_data: dict[str, Any], idx: int
    ) -> None:
        references = statement_def.get("references", [])
        if not references:
            return

        st.write("**References**")
        value_data.setdefault("references", [])

        by_ref_key = {
            r.get("property"): r
            for r in value_data["references"]
            if isinstance(r, dict)
        }

        updated: list[dict[str, Any]] = []
        for ref_def in references:
            if not isinstance(ref_def, dict):
                continue

            ref_key = _statement_key(ref_def)
            ref_label = _statement_label(ref_def)
            ref_dtype = _value_datatype(ref_def.get("value", {}))
            existing = by_ref_key.get(ref_key, {"property": ref_key, "value": None})
            widget_kwargs = _value_list_widget_kwargs(ref_def)

            ref_value = WidgetFactory.render_widget(
                datatype=ref_dtype,
                label=ref_label,
                value=existing.get("value"),
                key=f"ref_{_statement_key(statement_def)}_{ref_key}_{idx}",
                help_text=_statement_prompt(ref_def),
                **widget_kwargs,
            )
            updated.append({"property": ref_key, "value": ref_value})
            updated[-1]["value"] = _normalize_rendered_value(
                datatype=ref_dtype,
                value=ref_value,
                statement_ref=ref_key,
            )

        value_data["references"] = updated

    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        warnings: dict[str, list[str]] = {}
        statements = draft_data.get("statements", {})
        if not any(values for values in statements.values()):
            warnings["statements"] = ["No statement values added yet."]
        return warnings
