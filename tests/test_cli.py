"""Tests for the GKC CLI."""

import json

from gkc import cli


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
