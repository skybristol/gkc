"""Tests for the GKC CLI."""

import argparse
import json
from pathlib import Path

import gkc
from gkc import cli, still_charger
from gkc.mash import ClaimSummary, WikibaseItemTemplate
from gkc.wikibase import build_meta_wikibase_semantic_anchor_contract


class FakeWikiverseAuth:
    """Fake auth for CLI tests."""

    def __init__(self, interactive=False, api_url=None):
        self.api_url = api_url or "https://www.wikidata.org/w/api.php"
        self._logged_in = False
        self._authenticated = True
        self.interactive = interactive

    def login(self):
        self._logged_in = True

    def is_authenticated(self):
        return self._authenticated

    def is_logged_in(self):
        return self._logged_in

    def get_csrf_token(self):
        return "csrf_token"


class FakeOpenStreetMapAuth:
    """Fake OSM auth for CLI tests."""

    def __init__(self, interactive=False):
        self._authenticated = True
        self.interactive = interactive

    def is_authenticated(self):
        return self._authenticated


def _default_semantic_anchor_document() -> dict:
    contract = build_meta_wikibase_semantic_anchor_contract()
    entities: dict[str, dict[str, str]] = {}
    property_index = 300
    item_index = 300

    fixed_ids = {
        "_instance_of": ("P1", "wikibase-item"),
        "_subclass_of": ("P2", "wikibase-item"),
        "_name_identifier": ("P214", "string"),
        "_same_as": ("P5", "url"),
        "_has_statement": ("P157", "wikibase-item"),
        "_has_value": ("P161", "wikibase-item"),
        "_has_qualifier": ("P158", "wikibase-item"),
        "_has_reference": ("P211", "wikibase-item"),
        "_applies_to_profile": ("P205", "wikibase-item"),
        "_applies_to_statement": ("P163", "wikibase-item"),
        "_statement_type": ("P194", "wikibase-item"),
        "_max_count": ("P182", "quantity"),
        "_statement_prompt": ("P171", "monolingualtext"),
        "_statement_guidance": ("P169", "monolingualtext"),
        "_consequences_message": ("P170", "monolingualtext"),
        "_error_message": ("P168", "monolingualtext"),
        "_label_prompt": ("P188", "monolingualtext"),
        "_label_guidance": ("P185", "monolingualtext"),
        "_description_prompt": ("P189", "monolingualtext"),
        "_description_guidance": ("P186", "monolingualtext"),
        "_alias_prompt": ("P190", "monolingualtext"),
        "_alias_guidance": ("P187", "monolingualtext"),
        "_derives_default_value_from": ("P213", "wikibase-item"),
        "_entity": ("Q1", None),
        "_entity_profile": ("Q3", None),
        "_entity_statement": ("Q5", None),
        "_value_list": ("Q7", None),
        "_wikibase_statement_modifier": ("Q58", None),
    }

    for anchor_name, requirement in contract.requirements.items():
        fixed = fixed_ids.get(anchor_name)
        if fixed is not None:
            anchor_id, datatype = fixed
        elif requirement.kind == "property":
            property_index += 1
            anchor_id = f"P{property_index}"
            datatype = str(requirement.datatype)
        else:
            item_index += 1
            anchor_id = f"Q{item_index}"
            datatype = None

        payload = {
            "id": anchor_id,
            "entity": f"https://datadistillery.wikibase.cloud/entity/{anchor_id}",
        }
        if datatype is not None:
            payload["datatype"] = datatype
        entities[anchor_name] = payload

    return {
        "metadata": {
            "generated_at": "2026-04-04T00:00:00Z",
            "property_count": sum(
                1
                for requirement in contract.requirements.values()
                if requirement.kind == "property"
            ),
            "item_count": sum(
                1
                for requirement in contract.requirements.values()
                if requirement.kind == "item"
            ),
        },
        "entities": entities,
    }


def test_wikiverse_status_json(monkeypatch, capsys):
    """Status returns JSON with token validation."""
    monkeypatch.setattr(cli, "WikiverseAuth", FakeWikiverseAuth)

    exit_code = cli.main(["--json", "auth", "wikiverse", "status"])
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "auth.wikiverse.status"
    assert data["ok"] is True
    assert data["details"]["token_ok"] is True


def test_wikiverse_token_redacted(monkeypatch, capsys):
    """Token is redacted by default."""
    monkeypatch.setattr(cli, "WikiverseAuth", FakeWikiverseAuth)

    exit_code = cli.main(["--json", "auth", "wikiverse", "token"])
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["details"]["token"] == "<redacted>"


def test_wikibase_init_preview_json_uses_language_override(capsys):
    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "init",
            "--language",
            "fr",
            "--show-entity",
            "entity_profile",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["command"] == "wikibase.init"
    assert payload["ok"] is True
    assert payload["details"]["label_language"] == "fr"
    assert payload["details"]["value_language"] == "mul"
    assert payload["details"]["summary"]["created"] > 0
    sample_payload = payload["details"]["sample_entity"]["payload"]
    assert sample_payload["labels"]["fr"]["value"] == "GKC Entity Profile"


def test_wikibase_init_preview_can_compare_live_state(monkeypatch, capsys, tmp_path):
    class FakeWikibaseApiClient:
        def __init__(self, api_url):
            self.api_url = api_url

        def get_entities(self, entity_ids):
            assert "Q50" in entity_ids
            return {
                "Q50": {
                    "id": "Q50",
                    "type": "item",
                    "labels": {"en": {"language": "en", "value": "wikibase-item"}},
                    "descriptions": {
                        "en": {
                            "language": "en",
                            "value": "wikibase item property template used to set a data type for a statement, reference, or qualifier and any additional specifications",
                        }
                    },
                    "claims": {
                        "P1": [
                            {
                                "mainsnak": {
                                    "snaktype": "value",
                                    "property": "P1",
                                    "datavalue": {
                                        "type": "wikibase-entityid",
                                        "value": {
                                            "entity-type": "item",
                                            "id": "Q99",
                                            "numeric-id": 99,
                                        },
                                    },
                                },
                                "type": "statement",
                                "rank": "normal",
                            }
                        ],
                        "P214": [
                            {
                                "mainsnak": {
                                    "snaktype": "value",
                                    "property": "P214",
                                    "datavalue": {
                                        "type": "string",
                                        "value": "_wikibase-item",
                                    },
                                },
                                "type": "statement",
                                "rank": "normal",
                            }
                        ],
                        "P168": [
                            {
                                "mainsnak": {
                                    "snaktype": "value",
                                    "property": "P168",
                                    "datavalue": {
                                        "type": "monolingualtext",
                                        "value": {
                                            "language": "mul",
                                            "text": "Item must be or resolve to a valid QID identifier.",
                                        },
                                    },
                                },
                                "type": "statement",
                                "rank": "normal",
                            }
                        ],
                    },
                }
            }

    monkeypatch.setattr(
        cli,
        "resolve_spiritsafe_meta_wikibase_config",
        lambda local_root: (
            Path(local_root) / "config" / "dd-wikibase.yaml",
            {
                "name_identifier_property_id": "P214",
                "sparql_endpoint": "https://example.org/query/sparql",
            },
        ),
    )
    monkeypatch.setattr(
        cli,
        "execute_sparql",
        lambda query, endpoint=None, format="json": {
            "results": {
                "bindings": [
                    {
                        "entity": {"value": "https://example.org/entity/P1"},
                        "nameIdentifier": {"value": "_instance_of"},
                    },
                    {
                        "entity": {"value": "https://example.org/entity/P168"},
                        "nameIdentifier": {"value": "_error_message"},
                    },
                    {
                        "entity": {"value": "https://example.org/entity/P214"},
                        "nameIdentifier": {"value": "_name_identifier"},
                    },
                    {
                        "entity": {"value": "https://example.org/entity/Q50"},
                        "nameIdentifier": {"value": "_wikibase-item"},
                    },
                    {
                        "entity": {"value": "https://example.org/entity/Q99"},
                        "nameIdentifier": {"value": "_wikibase_statement_type"},
                    },
                ]
            }
        },
    )
    monkeypatch.setattr(cli, "WikibaseApiClient", FakeWikibaseApiClient)

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "init",
            "--local-root",
            str(tmp_path / "SpiritSafe"),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert (
        payload["details"]["comparison_source"]["mode"]
        == "live-compare-name-identifier"
    )
    assert payload["details"]["summary"]["skipped"] == 1
    assert payload["details"]["summary"]["updated"] == 0


def test_wikibase_init_uses_anchor_hints_when_sparql_misses_entity(
    monkeypatch, capsys, tmp_path
):
    local_root = tmp_path / "SpiritSafe"
    artifact_path = local_root / "config" / "semantic_anchors.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "metadata": {},
                "entities": {
                    "_alias_guidance": {
                        "id": "P187",
                        "entity": "https://example.org/entity/P187",
                        "datatype": "monolingualtext",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeWikibaseApiClient:
        def __init__(self, api_url):
            self.api_url = api_url

        def get_entities(self, entity_ids):
            assert "P187" in entity_ids
            return {
                "P187": {
                    "id": "P187",
                    "type": "property",
                    "datatype": "monolingualtext",
                    "labels": {"en": {"language": "en", "value": "alias guidance"}},
                    "descriptions": {
                        "en": {
                            "language": "en",
                            "value": "longer guidance statement provided as instructions for creating aliases for a GKC Entity",
                        }
                    },
                    "claims": {
                        "P214": [
                            {
                                "mainsnak": {
                                    "snaktype": "value",
                                    "property": "P214",
                                    "datavalue": {
                                        "type": "string",
                                        "value": "_alias_guidance",
                                    },
                                },
                                "type": "statement",
                                "rank": "normal",
                            }
                        ]
                    },
                }
            }

    monkeypatch.setattr(
        cli,
        "resolve_spiritsafe_meta_wikibase_config",
        lambda local_root: (
            Path(local_root) / "config" / "dd-wikibase.yaml",
            {
                "name_identifier_property_id": "P214",
                "sparql_endpoint": "https://example.org/query/sparql",
            },
        ),
    )
    monkeypatch.setattr(
        cli,
        "execute_sparql",
        lambda query, endpoint=None, format="json": {"results": {"bindings": []}},
    )
    monkeypatch.setattr(cli, "WikibaseApiClient", FakeWikibaseApiClient)

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "init",
            "--local-root",
            str(local_root),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["details"]["comparison_source"]["anchor_hint_count"] == 1
    alias_guidance_action = next(
        action
        for action in payload["details"]["actions"]
        if action["internal_name_identifier"] == "_alias_guidance"
    )
    assert alias_guidance_action["action"] == "skip"


def test_osm_status_json(monkeypatch, capsys):
    """OSM status returns JSON output."""
    monkeypatch.setattr(cli, "OpenStreetMapAuth", FakeOpenStreetMapAuth)

    exit_code = cli.main(["--json", "auth", "osm", "status"])
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "auth.osm.status"
    assert data["ok"] is True


def test_mash_check_wikibase_revisions_json(monkeypatch, capsys):
    """mash check-wikibase-revisions returns change summary in JSON mode."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://datadistillery.wikibase.cloud/query/sparql"
        username = None
        password = None

    class FakeRecentResult:
        since = "2026-03-13T16:00:00Z"
        next_since = "2026-03-13T17:00:00Z"
        changed_ids = ["Q4", "Q39"]
        ignored_ids = ["Q1"]
        recentchanges = [{"title": "Item:Q4"}]

    def fake_fetch_recent_entity_changes(**kwargs):
        _ = kwargs
        return FakeRecentResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(
        cli, "fetch_recent_entity_changes", fake_fetch_recent_entity_changes
    )

    exit_code = cli.main(
        [
            "--json",
            "mash",
            "check-wikibase-revisions",
            "--since",
            "2026-03-13T16:00:00Z",
            "--ignore-id",
            "Q1",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "mash.check-wikibase-revisions"
    assert data["ok"] is True
    assert data["details"]["changed_count"] == 2
    assert data["details"]["ignored_count"] == 1


def test_mash_cache_wikibase_revisions_json(monkeypatch, capsys, tmp_path):
    """mash cache-wikibase-revisions refreshes cache and returns summary in JSON mode."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://datadistillery.wikibase.cloud/query/sparql"
        username = None
        password = None

    class FakeRefreshResult:
        cache_dir = str(tmp_path / "cache")
        since = "2026-03-13T16:00:00Z"
        next_since = "2026-03-13T17:00:00Z"
        changed_ids = ["Q4", "Q39"]
        ignored_ids = ["Q1"]
        refreshed_ids = ["Q4"]
        deleted_ids = ["Q39"]
        missing_ids = ["Q39"]

    def fake_refresh_entity_cache_from_recentchanges(**kwargs):
        _ = kwargs
        return FakeRefreshResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(
        cli, "get_latest_cache_timestamp", lambda path: "2026-03-13T16:00:00Z"
    )
    monkeypatch.setattr(
        cli,
        "refresh_entity_cache_from_recentchanges",
        fake_refresh_entity_cache_from_recentchanges,
    )

    exit_code = cli.main(
        [
            "--json",
            "mash",
            "cache-wikibase-revisions",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--ignore-id",
            "Q1",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "mash.cache-wikibase-revisions"
    assert data["ok"] is True
    assert data["details"]["changed_count"] == 2
    assert data["details"]["refreshed_count"] == 1
    assert data["details"]["deleted_count"] == 1


def test_mash_full_sync_wikibase_json(monkeypatch, capsys, tmp_path):
    """mash full-sync-wikibase returns summary in JSON mode."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://datadistillery.wikibase.cloud/query/sparql"
        username = None
        password = None

    class FakeAuth:
        def __init__(self, api_url=None):
            self.api_url = api_url
            self.username = None
            self.password = None

    class FakeSyncResult:
        cache_dir = str(tmp_path / "cache")
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        api_url_source = "runtime_config"
        run_mode = "full_sync_baseline"
        started_at = "2026-03-13T16:00:00Z"
        completed_at = "2026-03-13T16:05:00Z"
        duration_seconds = 300.0
        discovered_ids = ["Q4", "Q39", "P211"]
        hydrated_ids = ["P211", "Q4"]
        tombstone_ids = ["Q39"]
        redirect_ids = []
        failed_ids = []
        batch_size_requested = 50
        batch_size_effective = 50
        batch_fallback_count = 0
        batch_fallback_first_error = None

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(cli, "WikibaseApiClient", lambda api_url: object())
    monkeypatch.setattr(cli, "WikiverseAuth", FakeAuth)
    monkeypatch.setattr(
        cli,
        "full_sync_wikibase_entity_cache",
        lambda **kwargs: FakeSyncResult(),
    )

    output_path = tmp_path / "full-sync.json"
    exit_code = cli.main(
        [
            "--json",
            "mash",
            "full-sync-wikibase",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--items-only",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "mash.full-sync-wikibase"
    assert data["ok"] is True
    assert data["details"]["hydrated_count"] == 2
    assert data["details"]["tombstone_count"] == 1
    assert output_path.exists()


def test_packet_build_supports_github_source(monkeypatch, capsys):
    """packet build should load profile via source config when source=github."""

    captured: dict[str, object] = {}

    def fake_load_profile(profile_ref, manifest=None):
        _ = manifest
        captured["profile_ref"] = profile_ref
        captured["source_mode"] = gkc.get_spirit_safe_source().mode
        return {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
            "statements": [],
            "metadata": {},
        }

    def fake_build_packet(profile_entity, json_profile_doc, source_root=None):
        captured["profile_entity"] = profile_entity
        captured["source_root"] = source_root
        _ = json_profile_doc
        return {
            "packet_id": "pkt-test",
            "profile_entity": profile_entity,
            "entities": [],
            "cross_references": [],
            "value_list_routes": {},
        }

    monkeypatch.setattr(cli, "load_profile", fake_load_profile)
    monkeypatch.setattr(
        still_charger,
        "build_curation_packet_from_json_profile",
        fake_build_packet,
    )

    exit_code = cli.main(
        [
            "--json",
            "packet",
            "build",
            "--profile",
            "Q4",
            "--source",
            "github",
            "--repo",
            "skybristol/SpiritSafe",
            "--ref",
            "main",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "packet.build"
    assert data["ok"] is True
    assert captured["profile_ref"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    assert captured["source_mode"] == "github"
    assert captured["source_root"] is None


def test_mash_qid_filter_properties(monkeypatch, capsys):
    """Mash output respects include/exclude property filters."""

    class FakeWikidataLoader:
        def load_item(self, qid):
            return WikibaseItemTemplate(
                qid=qid,
                labels={"en": "Test"},
                descriptions={"en": "Test"},
                aliases={},
                claims=[
                    ClaimSummary(
                        property_id="P31", value="Q5", qualifiers=[], references=[]
                    ),
                    ClaimSummary(
                        property_id="P21",
                        value="Q6581097",
                        qualifiers=[],
                        references=[],
                    ),
                ],
                entity_data={
                    "id": qid,
                    "claims": {
                        "P31": [{"mainsnak": {}}],
                        "P21": [{"mainsnak": {}}],
                    },
                },
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        qid="Q42",
        qids=None,
        qid_list=None,
        output=None,
        raw=False,
        transform=None,
        include_properties="P31,P21",
        exclude_properties="P21",
        exclude_qualifiers=False,
        exclude_references=False,
        include_entity_labels=True,
        command_path="mash.qid",
    )

    result = cli._handle_mash_qid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert "P31" in data["claims"]
    assert "P21" not in data["claims"]


def test_mash_qid_shell_transform(monkeypatch, capsys):
    """Mash qid with shell transform strips identifiers."""

    class FakeWikidataLoader:
        def load_item(self, qid):
            return WikibaseItemTemplate(
                qid=qid,
                labels={"en": "Test"},
                descriptions={"en": "Test"},
                aliases={},
                claims=[],
                entity_data={
                    "id": qid,
                    "pageid": 123,
                    "ns": 0,
                    "title": "Q42",
                    "labels": {"en": {"value": "Test"}},
                    "claims": {},
                },
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        qid="Q42",
        qids=None,
        qid_list=None,
        output=None,
        raw=False,
        transform="shell",
        include_properties=None,
        exclude_properties=None,
        exclude_qualifiers=False,
        exclude_references=False,
        include_entity_labels=True,
        command_path="mash.qid",
    )

    result = cli._handle_mash_qid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data.get("id") is None
    assert data.get("pageid") is None
    assert data.get("ns") is None
    assert data.get("title") is None


def test_mash_pid_basic(monkeypatch, capsys):
    """Mash pid loads a property."""
    from gkc.mash import WikibasePropertyTemplate

    class FakeWikidataLoader:
        def load_property(self, pid):
            return WikibasePropertyTemplate(
                pid=pid,
                labels={"en": "instance of"},
                descriptions={"en": "test"},
                aliases={},
                datatype="wikibase-item",
                formatter_url=None,
                entity_data={"id": pid, "datatype": "wikibase-item"},
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        pid="P31",
        pids=None,
        pid_list=None,
        output=None,
        raw=False,
        transform=None,
        command_path="mash.pid",
    )

    result = cli._handle_mash_pid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["id"] == "P31"
    assert data["datatype"] == "wikibase-item"


def test_mash_eid_basic(monkeypatch, capsys):
    """Mash eid loads an EntitySchema."""
    from gkc.mash import WikibaseEntitySchemaTemplate

    class FakeWikidataLoader:
        def load_entity_schema(self, eid):
            return WikibaseEntitySchemaTemplate(
                eid=eid,
                labels={"en": "Tribe"},
                descriptions={"en": "test"},
                schema_text="PREFIX : <http://www.wikidata.org/entity/>",
                entity_data={
                    "id": eid,
                    "schemaText": "PREFIX : <http://www.wikidata.org/entity/>",
                },
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        eid="E502",
        output=None,
        raw=False,
        transform=None,
        command_path="mash.eid",
    )

    result = cli._handle_mash_eid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["id"] == "E502"


def test_registry_list_json_uses_profile_documents(capsys):
    """registry list should emit QID-based profile entries from JSON profiles."""

    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    exit_code = cli.main(
        [
            "--json",
            "registry",
            "list",
            "--source",
            "local",
            "--local-root",
            str(fixture_root),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "registry.list"
    assert data["ok"] is True
    assert data["details"]["profiles"] == [
        {
            "qid": "Q4",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
            "label": "Tribal Government in the United States",
            "description": "Profile for tribal government entities in the United States",
            "statement_count": 2,
        },
        {
            "qid": "Q39",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q39",
            "label": "Office Held by Head of Government",
            "description": "Profile for head-of-government office entities",
            "statement_count": 2,
        },
    ]


def test_registry_info_json_reads_profile_metadata(capsys):
    """registry info should read metadata directly from the selected profile JSON."""

    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    exit_code = cli.main(
        [
            "--json",
            "registry",
            "info",
            "--profile",
            "Q4",
            "--source",
            "local",
            "--local-root",
            str(fixture_root),
        ]
    )

    assert exit_code == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["command"] == "registry.info"
    assert data["ok"] is True
    assert data["details"]["qid"] == "Q4"
    assert data["details"]["statement_count"] == 2
    assert len(data["details"]["profile_graph"]) == 1


def test_registry_validate_json_reads_profile_documents(capsys):
    """registry validate should validate the set of discovered profile JSON files."""

    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    exit_code = cli.main(
        [
            "--json",
            "registry",
            "validate",
            "--source",
            "local",
            "--local-root",
            str(fixture_root),
        ]
    )

    assert exit_code == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["command"] == "registry.validate"
    assert data["ok"] is True
    assert data["details"]["profile_count"] == 2
    assert data["details"]["errors"] == []


def test_mash_qid_summary(monkeypatch, capsys):
    """Mash qid with --summary flag returns summary."""

    class FakeWikidataLoader:
        def load_item(self, qid):
            return WikibaseItemTemplate(
                qid=qid,
                labels={"en": "Test Item"},
                descriptions={"en": "A test"},
                aliases={},
                claims=[
                    ClaimSummary(
                        property_id="P31", value="Q5", qualifiers=[], references=[]
                    ),
                ],
                entity_data={"id": qid, "claims": {"P31": [{"mainsnak": {}}]}},
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        qid="Q42",
        qids=None,
        qid_list=None,
        output=None,
        raw=False,
        summary=True,
        transform=None,
        include_properties=None,
        exclude_properties=None,
        exclude_qualifiers=False,
        exclude_references=False,
        include_entity_labels=True,
        command_path="mash.qid",
    )

    result = cli._handle_mash_qid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["qid"] == "Q42"
    assert "total_statements" in data


def test_mash_pid_summary(monkeypatch, capsys):
    """Mash pid with --summary flag returns summary."""

    class FakeWikidataLoader:
        def load_property(self, pid):
            from gkc.mash import WikibasePropertyTemplate

            return WikibasePropertyTemplate(
                pid=pid,
                labels={"en": "instance of"},
                descriptions={"en": "Generic property"},
                aliases={},
                datatype="wikibase-item",
                formatter_url=None,
                entity_data={"id": pid},
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        pid="P31",
        pids=None,
        pid_list=None,
        output=None,
        raw=False,
        summary=True,
        transform=None,
        command_path="mash.pid",
    )

    result = cli._handle_mash_pid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["pid"] == "P31"
    assert "datatype" in data


def test_mash_eid_summary(monkeypatch, capsys):
    """Mash eid with --summary flag returns summary."""

    class FakeWikidataLoader:
        def load_entity_schema(self, eid):
            from gkc.mash import WikibaseEntitySchemaTemplate

            return WikibaseEntitySchemaTemplate(
                eid=eid,
                labels={"en": "Test Schema"},
                descriptions={"en": "A test schema"},
                schema_text="TYPE ITEM",
                entity_data={"id": eid},
            )

    monkeypatch.setattr(cli, "WikibaseLoader", FakeWikidataLoader)

    args = argparse.Namespace(
        eid="E502",
        output=None,
        raw=False,
        summary=True,
        transform=None,
        command_path="mash.eid",
    )

    result = cli._handle_mash_eid(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["eid"] == "E502"
    assert "schema_text_length" in data


def test_mash_wp_template_summary(monkeypatch, capsys):
    """Mash wp_template with no flags returns summary by default."""

    from gkc.mash import WikipediaTemplate

    def mock_load_template(self, template_name):
        return WikipediaTemplate(
            title=template_name,
            description="Test infobox template",
            params={"name": {}, "image": {}, "location": {}},
            param_order=["name", "image", "location"],
            raw_data={},
        )

    monkeypatch.setattr(cli.WikipediaLoader, "load_template", mock_load_template)

    args = argparse.Namespace(
        template_name="Infobox_settlement",
        output=None,
        raw=False,
        command_path="mash.wp_template",
    )

    result = cli._handle_mash_wp_template(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["title"] == "Infobox_settlement"
    assert data["param_count"] == 3
    assert data["description"] == "Test infobox template"


def test_mash_wp_template_raw(monkeypatch, capsys):
    """Mash wp_template with --raw returns full template."""

    from gkc.mash import WikipediaTemplate

    def mock_load_template(self, template_name):
        return WikipediaTemplate(
            title=template_name,
            description="Test infobox template",
            params={"name": {"label": "Name"}, "image": {"label": "Image"}},
            param_order=["name", "image"],
            raw_data={"title": template_name},
        )

    monkeypatch.setattr(cli.WikipediaLoader, "load_template", mock_load_template)

    args = argparse.Namespace(
        template_name="Infobox_settlement",
        output=None,
        raw=True,
        command_path="mash.wp_template",
    )

    result = cli._handle_mash_wp_template(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["title"] == "Infobox_settlement"
    assert "params" in data
    assert "paramOrder" in data


def test_shex_validate_missing_args(capsys):
    """ShEx validate requires proper argument combinations."""
    exit_code = cli.main(["shex", "validate"])
    assert exit_code == 1  # Error exit code


def test_shex_validate_success(monkeypatch, capsys):
    """ShEx validate returns success when validation passes."""

    class FakeShexValidator:
        def __init__(self, **kwargs):
            self.qid = kwargs.get("qid")
            self.eid = kwargs.get("eid")
            self.schema_file = kwargs.get("schema_file")
            self.rdf_file = kwargs.get("rdf_file")
            self.results = []

        def check(self):
            return self

        def is_valid(self):
            return True

    monkeypatch.setattr("gkc.shex.ShexValidator", FakeShexValidator)

    exit_code = cli.main(
        ["--json", "shex", "validate", "--qid", "Q42", "--eid", "E502"]
    )
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "shex.validate"
    assert data["ok"] is True
    assert data["details"]["entity"] == "Q42"
    assert data["details"]["schema"] == "E502"
    assert data["details"]["valid"] is True


def test_shex_validate_failure(monkeypatch, capsys):
    """ShEx validate returns failure when validation fails."""

    class MockResult:
        def __init__(self):
            self.reason = "Node: http://example.org not in value set [wd:Q123]"

    class FakeShexValidator:
        def __init__(self, **kwargs):
            self.qid = kwargs.get("qid")
            self.eid = kwargs.get("eid")
            self.results = [MockResult()]

        def check(self):
            return self

        def is_valid(self):
            return False

    monkeypatch.setattr("gkc.shex.ShexValidator", FakeShexValidator)

    exit_code = cli.main(
        ["--json", "shex", "validate", "--qid", "Q42", "--eid", "E502"]
    )
    assert exit_code == 1  # Validation failed

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "shex.validate"
    assert data["ok"] is False
    assert data["details"]["valid"] is False
    assert "error_summary" in data["details"]


def test_wizard_cli_launches_streamlit(monkeypatch):
    """gkc wizard launches Streamlit wizard app with correct args."""
    local_root = Path(__file__).parent / "fixtures" / "spiritsafe"

    class FakeResult:
        returncode = 0

    def fake_run(cmd, env=None, **kwargs):
        assert cmd[1:3] == ["-m", "streamlit"]
        assert "run" in cmd
        assert any("streamlit_app.py" in str(arg) for arg in cmd)
        assert env["GKC_WIZARD_PROFILE"].endswith("/Q4")
        assert env["GKC_SPIRIT_SAFE_SOURCE_MODE"] == "local"
        assert env["GKC_SPIRIT_SAFE_LOCAL_ROOT"] == str(local_root)
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    exit_code = cli.main(
        [
            "--json",
            "wizard",
            "--profile",
            "Q4",
            "--source",
            "local",
            "--local-root",
            str(local_root),
        ]
    )
    assert exit_code == 0


def test_shex_validate_local_files(monkeypatch, capsys):
    """ShEx validate works with local files."""

    class FakeShexValidator:
        def __init__(self, **kwargs):
            self.rdf_file = kwargs.get("rdf_file")
            self.schema_file = kwargs.get("schema_file")
            self.results = []

        def check(self):
            return self

        def is_valid(self):
            return True

    monkeypatch.setattr("gkc.shex.ShexValidator", FakeShexValidator)

    exit_code = cli.main(
        [
            "--json",
            "shex",
            "validate",
            "--rdf-file",
            "/tmp/data.ttl",
            "--schema-file",
            "/tmp/schema.shex",
        ]
    )
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True
    assert data["details"]["rdf_file"] == "/tmp/data.ttl"
    assert data["details"]["schema_file"] == "/tmp/schema.shex"


def test_profile_export_json_writes_output_directory(capsys, tmp_path):
    """profile export-json writes one JSON file per profile to output directory."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "semantic_anchors.json").write_text(
        json.dumps(_default_semantic_anchor_document(), indent=2),
        encoding="utf-8",
    )
    output_dir = tmp_path / "profiles"

    cache_entities_dir.joinpath("Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {
                    "labels": {
                        "mul": {"value": "Tribal Government in the United States"},
                        "en": {"value": "Tribal Government in the United States"},
                    },
                    "descriptions": {"en": {"value": "Example profile"}},
                    "aliases": {},
                    "claims": {
                        "P1": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "id": "Q3",
                                        }
                                    }
                                }
                            }
                        ],
                        "P188": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "text": "Enter label",
                                            "language": "mul",
                                        }
                                    }
                                }
                            }
                        ],
                        "P189": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "text": "Enter description",
                                            "language": "mul",
                                        }
                                    }
                                }
                            }
                        ],
                        "P190": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "text": "Enter aliases",
                                            "language": "mul",
                                        }
                                    }
                                }
                            }
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "export-json",
            "--cache-entities-dir",
            str(cache_entities_dir),
            "--output",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["command"] == "profile.export_json"
    assert payload["ok"] is True
    assert payload["details"]["written_count"] == 1

    exported_file = output_dir / "Q4.json"
    assert exported_file.exists()
    exported_payload = json.loads(exported_file.read_text(encoding="utf-8"))
    assert exported_payload["entity"].endswith("/Q4")


def test_profile_value_lists_hydrate_local_source_defaults(
    monkeypatch, capsys, tmp_path
):
    """profile value-lists hydrate resolves local default directories."""

    local_root = tmp_path / "SpiritSafe"
    (local_root / "config").mkdir(parents=True, exist_ok=True)
    (local_root / "still" / "entities").mkdir(parents=True, exist_ok=True)
    (local_root / "config" / "dd-wikibase.yaml").write_text(
        """
meta_wikibase:
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
spiritsafe:
  layout_version: 2
  roots:
    materialized: still
    partners: partners
  paths:
    entities: still/entities
    profiles: still/profiles
    value_list_queries: still/value_lists/queries
    value_list_cache: still/value_lists/cache
    semantic_anchors: config/semantic_anchors.json
    logs: still/logs
    wikimedia_sites: partners/wikimedia_sites.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_discover_value_list_ids(cache_entities_dir):
        assert str(cache_entities_dir).endswith("SpiritSafe/still/entities")
        return ["Q4"]

    def fake_hydrate_value_lists_from_cache(**kwargs):
        assert str(kwargs["cache_entities_dir"]).endswith("SpiritSafe/still/entities")
        assert str(kwargs["queries_dir"]).endswith(
            "SpiritSafe/still/value_lists/queries"
        )
        assert str(kwargs["cache_queries_dir"]).endswith(
            "SpiritSafe/still/value_lists/cache"
        )
        assert kwargs["value_list_ids"] == ["Q4"]
        return gkc.ValueListHydrationResult(
            queries_dir=str(local_root / "still" / "value_lists" / "queries"),
            cache_queries_dir=str(local_root / "still" / "value_lists" / "cache"),
            discovered_ids=["Q4"],
            hydrated_ids=["Q4"],
            query_files_written=[
                str(local_root / "still" / "value_lists" / "queries" / "Q4.sparql")
            ],
            cache_files_written=[
                str(local_root / "still" / "value_lists" / "cache" / "Q4.json")
            ],
            failures=[],
        )

    monkeypatch.setattr("gkc.discover_value_list_ids", fake_discover_value_list_ids)
    monkeypatch.setattr(
        "gkc.hydrate_value_lists_from_cache", fake_hydrate_value_lists_from_cache
    )

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "value-lists",
            "hydrate",
            "--source",
            "local",
            "--local-root",
            str(local_root),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["command"] == "profile.value_lists.hydrate"
    assert payload["ok"] is True
    assert payload["details"]["hydrated_count"] == 1


def test_profile_value_lists_hydrate_reports_failures(monkeypatch, capsys, tmp_path):
    """profile value-lists hydrate marks command as failed when failures occur."""
    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("gkc.discover_value_list_ids", lambda _: ["Q4"])

    def fake_hydrate_value_lists_from_cache(**kwargs):
        _ = kwargs
        return gkc.ValueListHydrationResult(
            queries_dir=str(tmp_path / "queries"),
            cache_queries_dir=str(tmp_path / "cache" / "queries"),
            discovered_ids=["Q4"],
            hydrated_ids=[],
            query_files_written=[],
            cache_files_written=[],
            failures=[{"value_list_id": "Q4", "error": "No <sparql> block found"}],
        )

    monkeypatch.setattr(
        "gkc.hydrate_value_lists_from_cache", fake_hydrate_value_lists_from_cache
    )

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "value-lists",
            "hydrate",
            "--cache-entities-dir",
            str(cache_entities_dir),
            "--queries-dir",
            str(tmp_path / "queries"),
            "--cache-queries-dir",
            str(tmp_path / "cache" / "queries"),
            "--continue-on-error",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert len(payload["details"]["failures"]) == 1
