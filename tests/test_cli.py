"""Tests for the GKC CLI."""

import argparse
import json
from pathlib import Path

from gkc import cli
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


def test_profile_validate_with_item_json(tmp_path, capsys):
    """Profile validate accepts a local item JSON file."""
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )

    item_data = {
        "id": "Q123",
        "claims": {
            "P31": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datatype": "wikibase-item",
                        "datavalue": {
                            "type": "wikibase-entityid",
                            "value": {"id": "Q7840353"},
                        },
                    },
                    "references": [
                        {
                            "snaks": {
                                "P248": [
                                    {
                                        "snaktype": "value",
                                        "datatype": "wikibase-item",
                                        "datavalue": {
                                            "type": "wikibase-entityid",
                                            "value": {"id": "Q138391266"},
                                        },
                                    }
                                ]
                            }
                        }
                    ],
                }
            ]
        },
    }

    item_path = tmp_path / "item.json"
    item_path.write_text(json.dumps(item_data), encoding="utf-8")

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "validate",
            "--profile",
            str(profile_path),
            "--item-json",
            str(item_path),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "profile.validate"
    assert data["ok"] is True


def test_profile_form_schema(monkeypatch, capsys):
    """Profile form-schema prints schema to stdout."""
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )

    args = argparse.Namespace(
        profile=str(profile_path),
        output=None,
        command_path="profile.form_schema",
    )

    result = cli._handle_profile_form_schema(args)
    output = capsys.readouterr().out.strip()
    data = json.loads(output)

    assert result["ok"] is True
    assert data["name"] == "Federally Recognized Tribe"


def test_profile_form_schema_resolves_profile_name_local_source(capsys):
    """Profile form-schema accepts profile names via local SpiritSafe source."""
    fixtures_root = Path(__file__).parent / "fixtures"
    output_path = fixtures_root / "tmp_form_schema.json"

    try:
        exit_code = cli.main(
            [
                "--json",
                "profile",
                "form-schema",
                "--profile",
                "TribalGovernmentUS",
                "--source",
                "local",
                "--local-root",
                str(fixtures_root),
                "--output",
                str(output_path),
            ]
        )

        assert exit_code == 0
        output = capsys.readouterr().out.strip()
        data = json.loads(output)
        assert data["ok"] is True
        assert data["details"]["profile_ref"].endswith(
            "profiles/TribalGovernmentUS/profile.yaml"
        )
    finally:
        if output_path.exists():
            output_path.unlink()


def test_profile_form_launches_streamlit_app(monkeypatch):
    """Profile form command loads profile and runs Streamlit app."""
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )

    args = argparse.Namespace(
        profile=str(profile_path),
        qid="Q123",
        source=None,
        local_root=None,
        repo=None,
        github_ref=None,
        command_path="profile.form",
    )

    class FakeResult:
        returncode = 0

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    result = cli._handle_profile_form(args)
    assert result["ok"] is True
    assert result["details"]["qid"] == "Q123"


def test_profile_form_from_profile_name_with_local_source(monkeypatch):
    """Profile form command resolves profile names via local SpiritSafe source override.

    This test verifies profile resolution with local source while mocking Streamlit launch.
    """
    fixtures_root = Path(__file__).parent / "fixtures"

    class FakeResult:
        returncode = 0

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "form",
            "--profile",
            "TribalGovernmentUS",
            "--source",
            "local",
            "--local-root",
            str(fixtures_root),
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


def test_profile_lookups_hydrate_dry_run(monkeypatch, capsys):
    """Profile lookups hydrate dry-run returns summary JSON."""

    def fake_hydrate_profile_lookups(**kwargs):
        assert kwargs["dry_run"] is True
        assert kwargs["profile_paths"] == ["profiles/example.yaml"]
        return {
            "profiles_scanned": 1,
            "lookup_specs_found": 2,
            "unique_queries": 1,
            "unique_queries_executed": 0,
            "cache_dir": "/tmp/cache",
            "cache_file_count": 0,
            "failures": [],
        }

    monkeypatch.setattr("gkc.hydrate_profile_lookups", fake_hydrate_profile_lookups)

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "lookups",
            "hydrate",
            "--profile",
            "profiles/example.yaml",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["command"] == "profile.lookups.hydrate"
    assert data["ok"] is True
    assert data["details"]["lookup_specs_found"] == 2
    assert data["details"]["unique_queries"] == 1


def test_profile_lookups_hydrate_uses_dd_wb_sparql_env_default(monkeypatch, capsys):
    """Profile lookups hydrate defaults endpoint from DD_WB_SPARQL_ENDPOINT."""

    def fake_hydrate_profile_lookups(**kwargs):
        assert kwargs["endpoint"] == "https://dd.example/query/sparql"
        return {
            "profiles_scanned": 1,
            "lookup_specs_found": 0,
            "unique_queries": 0,
            "unique_queries_executed": 0,
            "cache_dir": "/tmp/cache",
            "cache_file_count": 0,
            "failures": [],
        }

    monkeypatch.setenv("DD_WB_SPARQL_ENDPOINT", "https://dd.example/query/sparql")
    monkeypatch.setattr("gkc.hydrate_profile_lookups", fake_hydrate_profile_lookups)

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "lookups",
            "hydrate",
            "--profile",
            "profiles/example.yaml",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True


def test_profile_lookups_hydrate_local_source_override(monkeypatch, capsys):
    """Profile lookups hydrate applies local source override and restores source."""
    set_calls = []

    def fake_set_spirit_safe_source(**kwargs):
        set_calls.append(kwargs)

    def fake_hydrate_profile_lookups(**kwargs):
        return {
            "profiles_scanned": 1,
            "lookup_specs_found": 1,
            "unique_queries": 1,
            "unique_queries_executed": 1,
            "cache_dir": "/tmp/cache",
            "cache_file_count": 1,
            "failures": [],
        }

    monkeypatch.setattr("gkc.set_spirit_safe_source", fake_set_spirit_safe_source)
    monkeypatch.setattr("gkc.hydrate_profile_lookups", fake_hydrate_profile_lookups)

    exit_code = cli.main(
        [
            "--json",
            "profile",
            "lookups",
            "hydrate",
            "--profile",
            "profiles/example.yaml",
            "--source",
            "local",
            "--local-root",
            "/tmp/SpiritSafe",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True

    # First call applies override; second call restores previous source.
    assert len(set_calls) == 2
    assert set_calls[0]["mode"] == "local"
    assert set_calls[0]["local_root"] == "/tmp/SpiritSafe"


def test_profile_lookups_hydrate_profile_name_resolution(monkeypatch, capsys):
    """Profile lookups hydrate resolves simple names to registrant profile paths."""

    def fake_hydrate_profile_lookups(**kwargs):
        # Verify that simple profile names resolve to registrant paths
        assert kwargs["profile_paths"] == ["profiles/SampleProfile/profile.yaml"]
        return {
            "profiles_scanned": 1,
            "lookup_specs_found": 0,
            "unique_queries": 0,
            "unique_queries_executed": 0,
            "cache_dir": "/tmp/cache",
            "cache_file_count": 0,
            "failures": [],
        }

    monkeypatch.setattr("gkc.hydrate_profile_lookups", fake_hydrate_profile_lookups)

    # Test 1: Simple name without .yaml extension
    exit_code = cli.main(
        [
            "--json",
            "profile",
            "lookups",
            "hydrate",
            "--profile",
            "SampleProfile",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True

    # Test 2: Name with .yaml extension
    exit_code = cli.main(
        [
            "--json",
            "profile",
            "lookups",
            "hydrate",
            "--profile",
            "SampleProfile.yaml",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    data = json.loads(output)
    assert data["ok"] is True
