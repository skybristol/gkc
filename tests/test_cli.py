"""Tests for the GKC CLI."""

import argparse
import json
from pathlib import Path

from gkc import cli
from gkc.mash import ClaimSummary, WikidataTemplate


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


def test_mash_qid_filter_properties(monkeypatch, capsys):
    """Mash output respects include/exclude property filters."""

    class FakeWikidataLoader:
        def load_item(self, qid):
            return WikidataTemplate(
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

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
            return WikidataTemplate(
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

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
    from gkc.mash import WikidataPropertyTemplate

    class FakeWikidataLoader:
        def load_property(self, pid):
            return WikidataPropertyTemplate(
                pid=pid,
                labels={"en": "instance of"},
                descriptions={"en": "test"},
                aliases={},
                datatype="wikibase-item",
                formatter_url=None,
                entity_data={"id": pid, "datatype": "wikibase-item"},
            )

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
    from gkc.mash import WikidataEntitySchemaTemplate

    class FakeWikidataLoader:
        def load_entity_schema(self, eid):
            return WikidataEntitySchemaTemplate(
                eid=eid,
                labels={"en": "Tribe"},
                descriptions={"en": "test"},
                schema_text="PREFIX : <http://www.wikidata.org/entity/>",
                entity_data={
                    "id": eid,
                    "schemaText": "PREFIX : <http://www.wikidata.org/entity/>",
                },
            )

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
            return WikidataTemplate(
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

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
            from gkc.mash import WikidataPropertyTemplate

            return WikidataPropertyTemplate(
                pid=pid,
                labels={"en": "instance of"},
                descriptions={"en": "Generic property"},
                aliases={},
                datatype="wikibase-item",
                formatter_url=None,
                entity_data={"id": pid},
            )

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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
            from gkc.mash import WikidataEntitySchemaTemplate

            return WikidataEntitySchemaTemplate(
                eid=eid,
                labels={"en": "Test Schema"},
                descriptions={"en": "A test schema"},
                schema_text="TYPE ITEM",
                entity_data={"id": eid},
            )

    monkeypatch.setattr(cli, "WikidataLoader", FakeWikidataLoader)

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


def test_profile_form_launches_textual_app(monkeypatch):
    """Profile form command loads profile and runs interactive app."""
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )

    class FakeApp:
        def __init__(self):
            self.did_run = False

        def run(self):
            self.did_run = True

    fake_app = FakeApp()

    class FakeGenerator:
        def __init__(self, profile):
            self.profile = profile

        def create_form(self, qid=None):
            self.qid = qid
            return fake_app

    monkeypatch.setattr("gkc.profiles.forms.TextualFormGenerator", FakeGenerator)

    args = argparse.Namespace(
        profile=str(profile_path),
        qid="Q123",
        command_path="profile.form",
    )

    result = cli._handle_profile_form(args)

    assert fake_app.did_run is True
    assert result["ok"] is True
    assert result["command"] == "profile.form"
    assert result["details"]["qid"] == "Q123"


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
