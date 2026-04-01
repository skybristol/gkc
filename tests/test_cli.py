"""Tests for the GKC CLI."""

import argparse
import json
from pathlib import Path

import gkc
from gkc import cli, still_charger
from gkc.mash import ClaimSummary, WikibaseItemTemplate


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


def test_osm_status_json(monkeypatch, capsys):
    """OSM status returns JSON output."""
    monkeypatch.setattr(cli, "OpenStreetMapAuth", FakeOpenStreetMapAuth)

    exit_code = cli.main(["--json", "auth", "osm", "status"])
    assert exit_code == 0

    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "auth.osm.status"
    assert data["ok"] is True


def test_wikibase_plan_write_json(monkeypatch, capsys, tmp_path):
    """wikibase plan-write returns logical path and summary output."""

    class FakeChargeReport:
        entities_charged = 1
        entities_skipped = 0
        issues = []

    class FakeBarrelReport:
        operations_created = 1
        entities_skipped = 0
        issues = []

    class FakeResult:
        packet = {"packet_id": "pkt-test", "entities": [{"id": "ent-001"}]}
        operations = [{"kind": "item", "label": "Cherokee Nation", "payload": {}}]
        charge_report = FakeChargeReport()
        barrel_report = FakeBarrelReport()
        diff_plan = None

    def fake_build_wikibase_write_plan(**kwargs):
        _ = kwargs
        return FakeResult()

    monkeypatch.setattr(
        cli, "build_wikibase_write_plan", fake_build_wikibase_write_plan
    )

    source_values_file = tmp_path / "source_values.json"
    source_values_file.write_text(
        json.dumps({"ent-001": {"labels": {"en": "Cherokee Nation"}}}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "plan-write",
            "--profile",
            "TribalGovernmentUS",
            "--source-values-file",
            str(source_values_file),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "wikibase.plan-write"
    assert data["ok"] is True
    assert "logical_path" in data["details"]
    assert data["details"]["operations_created"] == 1


def test_wikibase_plan_write_missing_source_values_file(capsys):
    """wikibase plan-write fails cleanly when source-values file is missing."""
    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "plan-write",
            "--profile",
            "TribalGovernmentUS",
            "--source-values-file",
            "/tmp/does-not-exist-source-values.json",
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is False
    assert "Source values file not found" in data["message"]


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


def test_wikibase_profile_to_cache_json(monkeypatch, capsys, tmp_path):
    """wikibase profile-to-cache exports summary output in JSON mode."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://datadistillery.wikibase.cloud/query/sparql"
        username = None
        password = None

    class FakeExportResult:
        cache_dir = str(tmp_path / "cache")
        written_ids = ["Q10", "Q50"]
        skipped_ids = ["Q1"]
        graph = type(
            "Graph",
            (),
            {"raw_items": {"Q10": {}, "Q50": {}}, "traversal_log": ["ok"]},
        )()

    def fake_export_profile_graph_to_entity_cache(**kwargs):
        _ = kwargs
        return FakeExportResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(
        cli,
        "export_profile_graph_to_entity_cache",
        fake_export_profile_graph_to_entity_cache,
    )

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "profile-to-cache",
            "--profile-id",
            "Q10",
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "wikibase.profile-to-cache"
    assert data["ok"] is True
    assert data["details"]["written_count"] == 2
    assert data["details"]["skipped_count"] == 1


def test_wikibase_check_for_revisions_json(monkeypatch, capsys, tmp_path):
    """wikibase check-for-revisions returns refresh summary in JSON mode."""

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
            "wikibase",
            "check-for-revisions",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--ignore-id",
            "Q1",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "wikibase.check-for-revisions"
    assert data["ok"] is True
    assert data["details"]["changed_count"] == 2
    assert data["details"]["refreshed_count"] == 1
    assert data["details"]["deleted_count"] == 1


def test_wikibase_cache_builder_json(monkeypatch, capsys, tmp_path):
    """wikibase cache-builder returns reconciliation summary in JSON mode."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://datadistillery.wikibase.cloud/query/sparql"
        username = None
        password = None

    class FakeBuildResult:
        cache_dir = str(tmp_path / "cache" / "entities")
        summary_path = str(tmp_path / "cache" / "refresh" / "last_run_summary.json")
        queried_ids = ["P1", "Q10", "Q3"]
        fetched_ids = ["P1", "Q10", "Q3"]
        written_ids = ["P1", "Q10", "Q3"]
        new_ids = ["Q10"]
        changed_ids = ["Q3"]
        unchanged_ids = ["P1"]
        deleted_ids = ["Q99"]
        missing_ids = []

    def fake_build_wikibase_cache(**kwargs):
        _ = kwargs
        return FakeBuildResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(cli, "build_wikibase_cache", fake_build_wikibase_cache)

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "cache-builder",
            "--cache-dir",
            str(tmp_path / "cache" / "entities"),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "wikibase.cache-builder"
    assert data["ok"] is True
    assert data["details"]["written_count"] == 3
    assert data["details"]["deleted_count"] == 1


def test_wikibase_plan_write_with_shipper_plan(monkeypatch, capsys, tmp_path):
    """wikibase plan-write can run shipper.plan_batch and include diff summary."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://query.wikidata.org/sparql"
        username = "bot-user"
        password = "bot-pass"

    class FakeAuth:
        def __init__(
            self, username=None, password=None, interactive=False, api_url=None
        ):
            self.username = username
            self.password = password
            self.interactive = interactive
            self.api_url = api_url
            self._logged_in = False

        def is_authenticated(self):
            return bool(self.username and self.password)

        def login(self):
            self._logged_in = True

        def is_logged_in(self):
            return self._logged_in

    class FakeDiffOp:
        def __init__(self, payload):
            self.payload = payload

        def to_dict(self):
            return self.payload

    class FakeDiffPlan:
        summary = {
            "total": 1,
            "create": 1,
            "update": 0,
            "noop": 0,
            "ambiguous": 0,
            "blocked": 0,
        }

        def __init__(self):
            self.operations = [
                FakeDiffOp(
                    {
                        "kind": "item",
                        "label": "Cherokee Nation",
                        "status": "create",
                    }
                )
            ]

        def to_dict(self):
            return {
                "summary": dict(self.summary),
                "operations": [op.to_dict() for op in self.operations],
            }

    class FakeChargeReport:
        entities_charged = 1
        entities_skipped = 0
        issues = []

    class FakeBarrelReport:
        operations_created = 1
        entities_skipped = 0
        issues = []

    class FakeResult:
        packet = {"packet_id": "pkt-test", "entities": [{"id": "ent-001"}]}
        operations = [{"kind": "item", "label": "Cherokee Nation", "payload": {}}]
        charge_report = FakeChargeReport()
        barrel_report = FakeBarrelReport()
        diff_plan = FakeDiffPlan()

    class FakeShipper:
        def __init__(self, auth, api_url=None, dry_run_default=True):
            self.auth = auth
            self.api_url = api_url
            self.dry_run_default = dry_run_default

    captured_kwargs: dict = {}

    def fake_build_wikibase_write_plan(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(cli, "WikiverseAuth", FakeAuth)
    monkeypatch.setattr(cli, "WikibaseShipper", FakeShipper)
    monkeypatch.setattr(
        cli, "build_wikibase_write_plan", fake_build_wikibase_write_plan
    )

    source_values_file = tmp_path / "source_values.json"
    source_values_file.write_text(
        json.dumps({"ent-001": {"labels": {"en": "Cherokee Nation"}}}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "plan-write",
            "--profile",
            "TribalGovernmentUS",
            "--source-values-file",
            str(source_values_file),
            "--with-shipper-plan",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs.get("shipper") is not None
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True
    assert data["details"]["shipper_plan_summary"]["create"] == 1
    assert data["details"]["auth_mode"] == "authenticated"


def test_wikibase_execute_write_dry_run(monkeypatch, capsys, tmp_path):
    """wikibase execute-write replays operations in dry-run mode by default."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://query.wikidata.org/sparql"
        username = "bot-user"
        password = "bot-pass"

    class FakeAuth:
        def __init__(
            self, username=None, password=None, interactive=False, api_url=None
        ):
            self.username = username
            self.password = password
            self.interactive = interactive
            self.api_url = api_url
            self._logged_in = False

        def is_authenticated(self):
            return bool(self.username and self.password)

        def login(self):
            self._logged_in = True

        def is_logged_in(self):
            return self._logged_in

    class FakeShipper:
        def __init__(self, auth, api_url=None, dry_run_default=True):
            self.auth = auth
            self.api_url = api_url
            self.dry_run_default = dry_run_default

    class FakeIssue:
        severity = "warning"
        entity_id = "ent-001"
        field = "statements.instance_of"
        message = "No property mapping for statement"

    class FakeChargeReport:
        entities_charged = 1
        entities_skipped = 0
        issues = []

    class FakeBarrelReport:
        operations_created = 1
        entities_skipped = 0
        issues = [FakeIssue()]

    class FakePlan:
        packet = {"packet_id": "pkt-test", "entities": [{"id": "ent-001"}]}
        operations = [{"kind": "item", "label": "Cherokee Nation", "payload": {}}]
        charge_report = FakeChargeReport()
        barrel_report = FakeBarrelReport()
        diff_plan = None

    class FakeWriteResult:
        def __init__(self, status):
            self.status = status

        def to_dict(self):
            return {
                "entity_id": None,
                "revision_id": None,
                "status": self.status,
                "warnings": [],
                "api_response": {},
                "request_payload": {},
                "metadata": {},
            }

    class FakeExecutionResult:
        plan = FakePlan()
        write_results = [FakeWriteResult("dry_run")]
        write_summary = {
            "total": 1,
            "submitted": 0,
            "dry_run": 1,
            "validated": 0,
            "blocked": 0,
            "error": 0,
        }

    captured_kwargs: dict = {}

    def fake_execute_wikibase_write_plan(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeExecutionResult()

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(cli, "WikiverseAuth", FakeAuth)
    monkeypatch.setattr(cli, "WikibaseShipper", FakeShipper)
    monkeypatch.setattr(
        cli, "execute_wikibase_write_plan", fake_execute_wikibase_write_plan
    )

    source_values_file = tmp_path / "source_values.json"
    source_values_file.write_text(
        json.dumps({"ent-001": {"labels": {"en": "Cherokee Nation"}}}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "execute-write",
            "--profile",
            "TribalGovernmentUS",
            "--source-values-file",
            str(source_values_file),
        ]
    )

    assert exit_code == 0
    assert captured_kwargs.get("dry_run") is True
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "wikibase.execute-write"
    assert data["ok"] is True
    assert data["details"]["dry_run"] is True
    assert data["details"]["write_summary"]["dry_run"] == 1
    assert data["details"]["auth_mode"] == "authenticated"


def test_wikibase_execute_write_requires_auth(capsys, tmp_path, monkeypatch):
    """wikibase execute-write fails cleanly when credentials are not available."""

    class FakeRuntimeConfig:
        api_url = "https://datadistillery.wikibase.cloud/w/api.php"
        sparql_endpoint = "https://query.wikidata.org/sparql"
        username = None
        password = None

    class FakeAuth:
        def __init__(
            self, username=None, password=None, interactive=False, api_url=None
        ):
            self.username = username
            self.password = password
            self.interactive = interactive
            self.api_url = api_url

        def is_authenticated(self):
            return False

    monkeypatch.setattr(cli, "get_wikibase_runtime_config", lambda: FakeRuntimeConfig())
    monkeypatch.setattr(cli, "WikiverseAuth", FakeAuth)

    source_values_file = tmp_path / "source_values.json"
    source_values_file.write_text(
        json.dumps({"ent-001": {"labels": {"en": "Cherokee Nation"}}}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--json",
            "wikibase",
            "execute-write",
            "--profile",
            "TribalGovernmentUS",
            "--source-values-file",
            str(source_values_file),
        ]
    )

    assert exit_code == 1
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is False
    assert "requires authentication" in data["message"]


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

    def test_spiritsafe_manifest_build_json(capsys, tmp_path):
        """spiritsafe manifest build writes a manifest and reports summary counts."""

        fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"
        output_path = tmp_path / "manifest.json"

        exit_code = cli.main(
            [
                "--json",
                "spiritsafe",
                "manifest",
                "build",
                "--source",
                "local",
                "--local-root",
                str(fixture_root),
                "--output",
                str(output_path),
            ]
        )

        assert exit_code == 0
        assert output_path.exists()
        output = capsys.readouterr().out.strip()
        data = json.loads(output)
        assert data["command"] == "spiritsafe.manifest.build"
        assert data["ok"] is True
        assert data["details"]["profile_count"] == 2
        assert data["details"]["entity_count"] == 1
        assert data["details"]["query_count"] == 1
        assert data["details"]["value_list_count"] == 1

    def test_registry_list_json_uses_new_manifest_shape(capsys):
        """registry list should emit QID-based profile entries from the new manifest."""

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
    (local_root / "cache" / "entities").mkdir(parents=True, exist_ok=True)

    def fake_discover_value_list_ids(cache_entities_dir):
        assert str(cache_entities_dir).endswith("SpiritSafe/cache/entities")
        return ["Q4"]

    def fake_hydrate_value_lists_from_cache(**kwargs):
        assert str(kwargs["cache_entities_dir"]).endswith("SpiritSafe/cache/entities")
        assert str(kwargs["queries_dir"]).endswith("SpiritSafe/queries")
        assert str(kwargs["cache_queries_dir"]).endswith("SpiritSafe/cache/queries")
        assert kwargs["value_list_ids"] == ["Q4"]
        return gkc.ValueListHydrationResult(
            queries_dir=str(local_root / "queries"),
            cache_queries_dir=str(local_root / "cache" / "queries"),
            discovered_ids=["Q4"],
            hydrated_ids=["Q4"],
            query_files_written=[str(local_root / "queries" / "Q4.sparql")],
            cache_files_written=[str(local_root / "cache" / "queries" / "Q4.json")],
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
