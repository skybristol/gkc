"""Tests for Textual form generation.

ARCHIVED: 2026-03-02
This file was archived when pivoting from Textual to Streamlit.
The logic tests (especially language scoping and draft persistence) should be ported
to test_streamlit_wizard.py for use with the new Streamlit-based wizard.

See also: .github/prompts/WizardEngineer.streamlit.md (Phase 7: Integration & Testing)
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
import gkc
from gkc.profiles import ProfileLoader
from gkc.profiles.forms import TextualFormGenerator
from gkc.profiles.forms.wizard.steps import SitelinksStep
from gkc.profiles.forms.wizard.steps import resolve_language_scope


@pytest.fixture
def tribal_government_profile_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )


def test_textual_form_generator_creates_app(tribal_government_profile_path: Path):
    """TextualFormGenerator should create a WizardApp shell."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    app = generator.create_form(qid=None)

    assert app is not None
    assert app.profile == profile
    assert app.qid is None
    assert len(app.steps) == 5
    assert app.steps[0].id == "plan"
    assert app.steps[-1].id == "review"


def test_textual_form_generator_preloads_choice_lists(
    tribal_government_profile_path: Path,
):
    """TextualFormGenerator should preload choice lists from fallback items."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    # Create form triggers choice list preloading
    app = generator.create_form()

    # Check that fallback items were loaded
    # instance_of field has fallback items
    cache_key = "instance_of:ref:stated_in"
    assert cache_key in app.choice_cache
    choices = app.choice_cache[cache_key]
    assert len(choices) > 0
    assert all(isinstance(choice, tuple) and len(choice) == 2 for choice in choices)


def test_wizard_draft_path_is_timestamped(tribal_government_profile_path: Path):
    """Wizard app should initialize a timestamped draft path under .drafts/."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    app = generator.create_form()

    assert app.draft_path.parent.name == ".drafts"
    assert profile.name.replace(" ", "_") in app.draft_path.name
    assert app.draft_path.suffix == ".json"


def test_wizard_uses_identification_step_class(tribal_government_profile_path: Path):
    """Wizard step sequence should include a concrete IdentificationStep."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    app = generator.create_form()

    assert app.steps[0].__class__.__name__ == "PlanStep"
    assert app.steps[1].__class__.__name__ == "IdentificationStep"


def test_wizard_uses_concrete_sitelinks_step(tribal_government_profile_path: Path):
    """Wizard sequence should include concrete SitelinksStep."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    app = generator.create_form()

    assert app.steps[3].id == "sitelinks"
    assert app.steps[3].__class__.__name__ == "SitelinksStep"


def test_wizard_persists_identification_data_shape(tribal_government_profile_path: Path):
    """Wizard should pre-seed draft_data with expected identification keys."""
    profile = ProfileLoader().load_from_file(tribal_government_profile_path)
    generator = TextualFormGenerator(profile)

    app = generator.create_form()
    app.draft_data.setdefault("steps", {})["identification"] = {
        "labels": {"en": "Example Label"},
        "descriptions": {"en": "Example Description"},
        "aliases": {"en": ["Example Alias"]},
    }

    step_data = app.draft_data["steps"]["identification"]
    assert "labels" in step_data
    assert "descriptions" in step_data
    assert "aliases" in step_data


def test_widget_factory_creates_type_ahead_for_items():
    """WidgetFactory should create TypeAheadSelect for item fields with choice lists."""
    from gkc.profiles.forms import TypeAheadSelect
    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "test_field",
        "label": "Test Field",
        "value": {"type": "item"},
    }
    choice_list = [("Q1", "Item 1"), ("Q2", "Item 2")]

    widget = WidgetFactory.create_widget(field_schema, choice_list)

    assert isinstance(widget, TypeAheadSelect)
    assert widget.choices == choice_list


def test_widget_factory_creates_input_for_strings():
    """WidgetFactory should create Input for string fields."""
    from textual.widgets import Input

    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "test_field",
        "label": "Test Field",
        "value": {"type": "string"},
    }

    widget = WidgetFactory.create_widget(field_schema)

    assert isinstance(widget, Input)


def test_widget_factory_uses_input_prompt_for_commons_media():
    """commonsMedia widgets should use statement input_prompt text."""
    from textual.widgets import Input

    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "flag_image",
        "label": "Flag image",
        "input_prompt": "flag image for valid Wikimedia Commons file",
        "value": {"type": "commonsMedia"},
    }

    widget = WidgetFactory.create_widget(field_schema)

    assert isinstance(widget, Input)
    assert widget.placeholder == "flag image for valid Wikimedia Commons file"


def test_widget_factory_uses_input_prompt_for_quantity_subfields():
    """quantity widgets should derive both placeholders from statement input_prompt."""
    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "member_count",
        "label": "Member count",
        "input_prompt": "member count statement when a reliable source is available",
        "value": {"type": "quantity"},
    }

    widget = WidgetFactory.create_widget(field_schema)

    amount_input, unit_input = widget._pending_children
    assert amount_input.placeholder.endswith("(amount)")
    assert field_schema["input_prompt"] in amount_input.placeholder
    assert unit_input.placeholder.endswith("(unit QID (optional))")
    assert field_schema["input_prompt"] in unit_input.placeholder


def test_widget_factory_uses_input_prompt_for_globecoordinate_subfields():
    """globecoordinate widgets should derive lat/lon placeholders from input_prompt."""
    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "coordinate_location",
        "label": "Coordinate location",
        "input_prompt": "latitude and longitude for the headquarters location",
        "value": {"type": "globecoordinate"},
    }

    widget = WidgetFactory.create_widget(field_schema)

    lat_input, lon_input = widget._pending_children
    assert lat_input.placeholder.endswith("(latitude)")
    assert field_schema["input_prompt"] in lat_input.placeholder
    assert lon_input.placeholder.endswith("(longitude)")
    assert field_schema["input_prompt"] in lon_input.placeholder


def test_widget_factory_uses_input_prompt_for_monolingual_subfields():
    """monolingualtext widgets should derive language placeholders from input_prompt."""
    from gkc.profiles.forms.widget_factory import WidgetFactory

    field_schema = {
        "id": "native_name",
        "label": "Native name",
        "input_prompt": "native label in the language used by the tribe",
        "value": {"type": "monolingualtext"},
    }

    widget = WidgetFactory.create_widget(field_schema)

    text_input, lang_input = widget._pending_children
    assert text_input.placeholder == field_schema["input_prompt"]
    assert lang_input.placeholder.endswith("(language code)")
    assert field_schema["input_prompt"] in lang_input.placeholder


def test_type_ahead_search_index_builds_correctly():
    """TypeAheadSelect should build search index for fast filtering."""
    from gkc.profiles.forms import TypeAheadSelect

    choices = [
        ("Q1", "Apache"),
        ("Q2", "Navajo"),
        ("Q3", "Navajo Nation"),
    ]

    widget = TypeAheadSelect(choices)

    # Index should have entries for all prefixes
    assert "a" in widget.search_index
    assert "ap" in widget.search_index
    assert "apa" in widget.search_index
    assert "n" in widget.search_index
    assert "na" in widget.search_index
    assert "nav" in widget.search_index

    # Prefix "nav" should match both Navajo entries
    assert len(widget.search_index["nav"]) == 2
    assert ("Q2", "Navajo") in widget.search_index["nav"]
    assert ("Q3", "Navajo Nation") in widget.search_index["nav"]


def test_resolve_language_scope_defaults_to_single_language_en():
    """Resolver should return only configured default single language."""
    original_languages = gkc.get_languages()
    try:
        gkc.set_languages("en")
        available = {"en": object(), "es": object(), "fr": object()}

        scoped = resolve_language_scope(available)

        assert scoped == ["en"]
    finally:
        gkc.set_languages(original_languages)


def test_resolve_language_scope_uses_language_list_order():
    """Resolver should preserve configured order and skip unavailable languages."""
    original_languages = gkc.get_languages()
    try:
        gkc.set_languages(["es", "en", "de"])
        available = {"en": object(), "es": object(), "fr": object()}

        scoped = resolve_language_scope(available)

        assert scoped == ["es", "en"]
    finally:
        gkc.set_languages(original_languages)


def test_resolve_language_scope_all_returns_all_profile_languages():
    """Resolver should return all available languages when configured to all."""
    original_languages = gkc.get_languages()
    try:
        gkc.set_languages("all")
        available = {"en": object(), "es": object(), "fr": object()}

        scoped = resolve_language_scope(available)

        assert scoped == ["en", "es", "fr"]
    finally:
        gkc.set_languages(original_languages)


def test_sitelinks_step_collect_data_respects_package_language_scope():
    """Sitelinks collection should only include languages in package scope."""
    original_languages = gkc.get_languages()
    try:
        gkc.set_languages("en")

        sitelinks_languages = {
            "en": SimpleNamespace(
                project="wikipedia",
                description="English Wikipedia article",
                required=False,
                guidance="Add if available",
            ),
            "es": SimpleNamespace(
                project="wikipedia",
                description="Spanish Wikipedia article",
                required=False,
                guidance="Agrega si existe",
            ),
        }

        class FakeApp:
            def __init__(self) -> None:
                self.profile = SimpleNamespace(
                    sitelinks=SimpleNamespace(
                        guidance="",
                        languages=sitelinks_languages,
                    )
                )
                self.draft_data = {"steps": {"sitelinks": {"sitelinks": {}}}}
                self._inputs = {
                    "#sitelink_en": SimpleNamespace(value="Example_English_Article"),
                    "#sitelink_es": SimpleNamespace(value="Articulo_Ejemplo"),
                }

            def query_one(self, selector: str, _widget_type: object) -> SimpleNamespace:
                return self._inputs[selector]

        step = SitelinksStep(
            id="sitelinks",
            title="Cross-platform Links",
            description="Add sitelinks",
        )
        app = FakeApp()

        collected = step.collect_data(app)

        assert collected == {"sitelinks": {"en": "Example_English_Article"}}
    finally:
        gkc.set_languages(original_languages)
