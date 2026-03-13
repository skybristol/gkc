from gkc.utilities import resolve_name_to_identifier


class FakeApiClient:
    def __init__(self, responses):
        self.responses = responses

    def search_entities(self, *, label, entity_type, language):
        _ = language
        return self.responses.get((entity_type, label), [])


def test_resolve_name_passthrough_identifier():
    api = FakeApiClient({})
    assert resolve_name_to_identifier("q42", api_client=api) == "Q42"


def test_resolve_name_from_map_before_search():
    api = FakeApiClient({})
    result = resolve_name_to_identifier(
        "instance of",
        api_client=api,
        label_to_id_map={"instance of": "P31"},
    )
    assert result == "P31"


def test_resolve_unique_exact_item_label():
    api = FakeApiClient(
        {("item", "GKC Entity Profile"): [{"id": "Q3", "label": "GKC Entity Profile"}]}
    )
    result = resolve_name_to_identifier("GKC Entity Profile", api_client=api)
    assert result == "Q3"


def test_resolve_ambiguous_label_returns_none():
    api = FakeApiClient(
        {
            ("item", "Entity"): [
                {"id": "Q1", "label": "Entity"},
                {"id": "Q999", "label": "Entity"},
            ],
            ("property", "Entity"): [],
        }
    )
    result = resolve_name_to_identifier("Entity", api_client=api)
    assert result is None


def test_resolve_with_entity_type_restriction():
    api = FakeApiClient(
        {
            ("property", "instance of"): [{"id": "P31", "label": "instance of"}],
            ("item", "instance of"): [{"id": "Q123", "label": "instance of"}],
        }
    )
    result = resolve_name_to_identifier(
        "instance of",
        api_client=api,
        entity_type="property",
    )
    assert result == "P31"
