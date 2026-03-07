"""Tests for mash source adapter contracts and implementations."""

from gkc.mash import (
    MashSourceAdapter,
    WikibaseEntitySchemaTemplate,
    WikibaseItemTemplate,
    WikibaseMashSourceAdapter,
    WikibasePropertyTemplate,
    WikipediaMashSourceAdapter,
    WikipediaTemplate,
)


class _FakeWikibaseLoader:
    def load_item(self, qid: str) -> WikibaseItemTemplate:
        return WikibaseItemTemplate(
            qid=qid,
            labels={"en": "Item"},
            descriptions={"en": "Item description"},
            aliases={},
            claims=[],
            entity_data={"id": qid, "claims": {}},
        )

    def load_items(self, qids: list[str]) -> dict[str, WikibaseItemTemplate]:
        return {qid: self.load_item(qid) for qid in qids}

    def load_property(self, pid: str) -> WikibasePropertyTemplate:
        return WikibasePropertyTemplate(
            pid=pid,
            labels={"en": "Property"},
            descriptions={"en": "Property description"},
            aliases={},
            datatype="string",
            formatter_url=None,
            entity_data={"id": pid, "datatype": "string"},
        )

    def load_entity_schema(self, eid: str) -> WikibaseEntitySchemaTemplate:
        return WikibaseEntitySchemaTemplate(
            eid=eid,
            labels={"en": "Schema"},
            descriptions={"en": "Schema description"},
            schema_text="START=@<Entity>",
            entity_data={"id": eid, "schemaText": "START=@<Entity>"},
        )


class _FakeWikipediaLoader:
    def load_template(self, template_name: str) -> WikipediaTemplate:
        return WikipediaTemplate(
            title=template_name,
            description="Template",
            params={"name": {}},
            param_order=["name"],
            raw_data={"title": template_name},
        )


def test_wikibase_adapter_implements_protocol():
    adapter = WikibaseMashSourceAdapter(loader=_FakeWikibaseLoader())
    assert isinstance(adapter, MashSourceAdapter)


def test_wikipedia_adapter_implements_protocol():
    adapter = WikipediaMashSourceAdapter(loader=_FakeWikipediaLoader())
    assert isinstance(adapter, MashSourceAdapter)


def test_wikibase_adapter_can_load_entity_refs():
    adapter = WikibaseMashSourceAdapter(loader=_FakeWikibaseLoader())
    assert adapter.can_load("Q42") is True
    assert adapter.can_load("P31") is True
    assert adapter.can_load("E502") is True
    assert adapter.can_load("Template:Infobox settlement") is False


def test_wikibase_adapter_load_dispatches_by_prefix():
    adapter = WikibaseMashSourceAdapter(loader=_FakeWikibaseLoader())
    q_item = adapter.load("Q42")
    prop = adapter.load("P31")
    schema = adapter.load("E502")

    assert isinstance(q_item, WikibaseItemTemplate)
    assert isinstance(prop, WikibasePropertyTemplate)
    assert isinstance(schema, WikibaseEntitySchemaTemplate)


def test_wikibase_adapter_load_many_supports_mixed_refs():
    adapter = WikibaseMashSourceAdapter(loader=_FakeWikibaseLoader())
    loaded = adapter.load_many(["Q1", "Q2", "P31", "E502"])

    assert set(loaded.keys()) == {"Q1", "Q2", "P31", "E502"}
    assert isinstance(loaded["Q1"], WikibaseItemTemplate)
    assert isinstance(loaded["P31"], WikibasePropertyTemplate)
    assert isinstance(loaded["E502"], WikibaseEntitySchemaTemplate)


def test_wikipedia_adapter_normalizes_template_prefix():
    adapter = WikipediaMashSourceAdapter(loader=_FakeWikipediaLoader())
    loaded = adapter.load("Template:Infobox settlement")
    assert loaded.title == "Infobox settlement"


def test_wikipedia_adapter_load_many_returns_keyed_result():
    adapter = WikipediaMashSourceAdapter(loader=_FakeWikipediaLoader())
    refs = ["Infobox settlement", "Template:Infobox person"]
    loaded = adapter.load_many(refs)

    assert set(loaded.keys()) == set(refs)
    assert loaded["Infobox settlement"].title == "Infobox settlement"
    assert loaded["Template:Infobox person"].title == "Infobox person"
