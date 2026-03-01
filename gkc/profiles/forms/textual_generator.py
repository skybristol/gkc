"""Textual UI form generator for YAML profiles.

Plain meaning: Build interactive terminal forms from profile schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label

from gkc.profiles.generators.form_generator import FormSchemaGenerator
from gkc.profiles.models import ProfileDefinition
from gkc.profiles.validation.validator import ProfileValidator
from gkc.spirit_safe import LookupCache, LookupFetcher


class TypeAheadSelect(Vertical):
    """Type-ahead selection widget with filtered choice lists.

    Args:
        choices: List of (id, label) tuples for selection.
        max_visible: Maximum items to show at once (default 10).
        placeholder: Input placeholder text.
        search_index: Optional normalized search index for fast filtering.

    Plain meaning: A searchable dropdown that filters as you type.
    """

    def __init__(
        self,
        choices: List[tuple[str, str]],
        max_visible: int = 10,
        placeholder: str = "Start typing...",
        search_index: Optional[Dict[str, List[tuple[str, str]]]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.choices = choices
        self.max_visible = max_visible
        self.placeholder = placeholder
        self.search_index = search_index or self._build_search_index(choices)
        self.filtered_choices: List[tuple[str, str]] = []
        self.selected_id: Optional[str] = None

    def _build_search_index(
        self, choices: List[tuple[str, str]]
    ) -> Dict[str, List[tuple[str, str]]]:
        """Build normalized search index for fast prefix matching."""
        index: Dict[str, List[tuple[str, str]]] = {}
        for id_, label in choices:
            normalized = label.lower()
            for i in range(1, len(normalized) + 1):
                prefix = normalized[:i]
                if prefix not in index:
                    index[prefix] = []
                if (id_, label) not in index[prefix]:
                    index[prefix].append((id_, label))
        return index

    def compose(self) -> ComposeResult:
        """Build the type-ahead widget."""
        yield Input(placeholder=self.placeholder, id="type_ahead_input")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter choices as user types."""
        query = event.value.lower().strip()
        if not query:
            self.filtered_choices = []
        else:
            self.filtered_choices = self.search_index.get(query, [])
            self.filtered_choices.sort(key=lambda x: x[1].lower())


class ProfileFormApp(App):
    """Bare-bones Textual form for profile-based data entry.

    Plain meaning: Terminal UI for creating/editing Wikidata items.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    Input {
        margin: 0 0;
        height: auto;
    }

    Label {
        margin: 0 0;
        height: auto;
    }

    #form_container {
        height: 1fr;
        overflow-y: auto;
        layout: vertical;
    }

    #form_container > Horizontal,
    #form_container > Vertical,
    .field_container {
        height: auto;
        width: 100%;
    }

    .statement_block {
        height: auto;
        width: 100%;
        border: solid $accent;
        padding: 1 2;
        margin: 0 0 1 0;
    }

    .statement_block > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    .metadata_block {
        height: auto;
        width: 100%;
        border: solid $success;
        padding: 1 2;
        margin: 0 0 1 0;
    }

    .metadata_block > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    .qualifier_block {
        height: auto;
        width: 100%;
        border: solid $warning;
        padding: 1 2;
        margin: 0 0 0 4;
    }

    .qualifier_block > Label {
        text-style: italic;
        margin-bottom: 0;
    }

    .reference_block {
        height: auto;
        width: 100%;
        border: solid $primary;
        padding: 1 2;
        margin: 0 0 0 4;
    }

    .reference_block > Label {
        text-style: italic;
        margin-bottom: 0;
    }

    #action_buttons {
        height: auto;
        dock: bottom;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(
        self,
        profile: ProfileDefinition,
        qid: Optional[str] = None,
        choice_cache: Optional[Dict[str, List[tuple[str, str]]]] = None,
        validator: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.profile = profile
        self.qid = qid
        self.form_schema = FormSchemaGenerator(profile).build_schema()
        self.choice_cache = choice_cache or {}
        self.validator = validator
        self.draft_data: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Build the form UI - minimal."""
        yield Header()
        yield Vertical(
            *self._build_form_fields(),
            id="form_container",
        )
        yield Horizontal(
            Button("Validate", id="validate_button", variant="primary"),
            Button("Submit", id="submit_button", variant="success"),
            id="action_buttons",
        )
        yield Footer()

    def _build_form_fields(self) -> list[Any]:
        """Build form field widgets from schema - bare minimum."""
        from gkc.profiles.forms.widget_factory import WidgetFactory

        widgets: list[Any] = []

        # Labels section
        for lang, label_def in self.profile.labels.items():
            field_label = (
                f"{label_def.label} ({lang}){'*' if label_def.required else ''}:"
            )
            widgets.append(
                Vertical(
                    Label(field_label),
                    Input(
                        placeholder=label_def.input_prompt,
                        id=f"label_{lang}",
                    ),
                    id=f"metadata_label_{lang}",
                    classes="metadata_block",
                )
            )

        # Descriptions section
        for lang, desc_def in self.profile.descriptions.items():
            field_label = (
                f"{desc_def.label} ({lang}){'*' if desc_def.required else ''}:"
            )
            widgets.append(
                Vertical(
                    Label(field_label),
                    Input(
                        placeholder=desc_def.input_prompt,
                        id=f"description_{lang}",
                    ),
                    id=f"metadata_description_{lang}",
                    classes="metadata_block",
                )
            )

        # Statements section
        statement_schemas = self.form_schema.get("statements", [])
        for field_schema in statement_schemas:
            cache_key = f"{field_schema['id']}:value"
            choice_list = self.choice_cache.get(cache_key)

            # Wrap each statement in a container for visual grouping
            statement_widgets = [
                Label(f"{field_schema['label']}:"),
                WidgetFactory.create_widget(field_schema, choice_list),
            ]

            # Add qualifiers
            for qualifier in field_schema.get("qualifiers", []):
                qualifier_cache_key = f"{field_schema['id']}:{qualifier['id']}"
                qualifier_choice_list = self.choice_cache.get(qualifier_cache_key)
                statement_widgets.append(
                    Vertical(
                        Label(f"{qualifier['label']}:"),
                        WidgetFactory.create_widget(qualifier, qualifier_choice_list),
                        id=f"qualifier_{field_schema['id']}_{qualifier['id']}",
                        classes="qualifier_block",
                    )
                )

            # Add references
            if field_schema.get("references"):
                ref_spec = field_schema["references"]
                # Create a container for all reference widgets
                ref_widgets = [Label(f"{ref_spec.get('input_prompt', 'References')}")]

                # Render allowed reference properties (array of properties)
                for ref_target in ref_spec.get("allowed", []):
                    ref_cache_key = f"{field_schema['id']}:ref:{ref_target['id']}"
                    ref_choice_list = self.choice_cache.get(ref_cache_key)

                    # Wrap reference target schema to match WidgetFactory expectations
                    ref_field_schema = {
                        "id": ref_target["id"],
                        "label": ref_target["label"],
                        "input_prompt": ref_target.get("input_prompt", ""),
                        "value": {
                            "type": ref_target["type"],
                            "fixed": None,
                            "label": "",
                            "constraints": [],
                        },
                    }

                    ref_widgets.append(Label(f"{ref_target['label']}:"))
                    ref_widgets.append(
                        WidgetFactory.create_widget(ref_field_schema, ref_choice_list)
                    )

                # Render target reference property (single property)
                if ref_spec.get("target"):
                    ref_target = ref_spec["target"]
                    ref_cache_key = f"{field_schema['id']}:ref:{ref_target['id']}"
                    ref_choice_list = self.choice_cache.get(ref_cache_key)

                    # Wrap reference target schema to match WidgetFactory expectations
                    ref_field_schema = {
                        "id": ref_target["id"],
                        "label": ref_target["label"],
                        "input_prompt": ref_target.get("input_prompt", ""),
                        "value": {
                            "type": ref_target["type"],
                            "fixed": None,
                            "label": "",
                            "constraints": [],
                        },
                    }

                    ref_widgets.append(Label(f"{ref_target['label']}:"))
                    ref_widgets.append(
                        WidgetFactory.create_widget(ref_field_schema, ref_choice_list)
                    )

                statement_widgets.append(
                    Vertical(
                        *ref_widgets,
                        id=f"references_{field_schema['id']}",
                        classes="reference_block",
                    )
                )

            widgets.append(
                Vertical(
                    *statement_widgets,
                    id=f"statement_{field_schema['id']}",
                    classes="statement_block",
                )
            )

        return widgets

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "validate_button":
            self._run_validation()
        elif event.button.id == "submit_button":
            self._submit_form()

    def on_mount(self) -> None:
        """Focus the first input field when the app starts."""
        try:
            first_input = self.query_one("#label_en", Input)
        except Exception:
            first_input = self.query_one(Input)
        self.set_focus(first_input)

    def _run_validation(self) -> None:
        """Run validation."""
        pass

    def _submit_form(self) -> None:
        """Submit form data."""
        # Collect all data
        data = {}
        for lang in self.profile.labels:
            widget = self.query_one(f"#label_{lang}", Input)
            data[f"label_{lang}"] = widget.value

        for lang in self.profile.descriptions:
            widget = self.query_one(f"#description_{lang}", Input)
            data[f"description_{lang}"] = widget.value

        print(f"\nForm data: {data}")
        self.exit()


class TextualFormGenerator:
    """Generate Textual UI forms from YAML profiles.

    Args:
        profile: ProfileDefinition describing the form structure.
        cache_dir: Optional cache directory for pre-hydrated choice lists.

    Example:
        >>> generator = TextualFormGenerator(profile)
        >>> app = generator.create_form(qid="Q123456")
        >>> result = app.run()

    Plain meaning: Convert a profile into an interactive terminal form.
    """

    def __init__(
        self,
        profile: ProfileDefinition,
        cache_dir: Optional[Path] = None,
    ):
        self.profile = profile
        self.cache = LookupCache(cache_dir)
        self.fetcher = LookupFetcher(cache=self.cache)
        self.choice_cache: Dict[str, List[tuple[str, str]]] = {}
        self.validator = ProfileValidator(profile)

    def create_form(self, qid: Optional[str] = None) -> ProfileFormApp:
        """Create a Textual App instance for the profile.

        Args:
            qid: Optional QID for editing existing items.

        Returns:
            ProfileFormApp instance ready to run.

        Example:
            >>> app = generator.create_form()
            >>> result = app.run()

        Plain meaning: Build a runnable form app from the profile.
        """
        # Pre-load all choice lists
        self._preload_choice_lists()

        return ProfileFormApp(
            profile=self.profile,
            qid=qid,
            choice_cache=self.choice_cache,
            validator=self.validator,
        )

    def _preload_choice_lists(self) -> None:
        """Load all choice lists from cache into memory."""
        # Load choice lists for fields with allowed_items
        for field in self.profile.statements:
            # Main field value
            if hasattr(field.value, "allowed_items") and field.value.allowed_items:
                choice_spec = field.value.allowed_items
                choices = self._load_choice_list_from_spec(choice_spec)
                cache_key = f"{field.id}:value"
                self.choice_cache[cache_key] = choices

            # Qualifiers with allowed_items
            for qualifier in field.qualifiers:
                if (
                    hasattr(qualifier.value, "allowed_items")
                    and qualifier.value.allowed_items
                ):
                    choice_spec = qualifier.value.allowed_items
                    choices = self._load_choice_list_from_spec(choice_spec)
                    cache_key = f"{field.id}:{qualifier.id}"
                    self.choice_cache[cache_key] = choices

            # References with allowed_items
            if field.references:
                # Handle allowed array (multiple reference properties)
                for ref_target in field.references.allowed:
                    if (
                        hasattr(ref_target, "allowed_items")
                        and ref_target.allowed_items
                    ):
                        choice_spec = ref_target.allowed_items
                        choices = self._load_choice_list_from_spec(choice_spec)
                        cache_key = f"{field.id}:ref:{ref_target.id}"
                        self.choice_cache[cache_key] = choices

                # Handle target (single reference property)
                if field.references.target:
                    ref_target = field.references.target
                    if (
                        hasattr(ref_target, "allowed_items")
                        and ref_target.allowed_items
                    ):
                        choice_spec = ref_target.allowed_items
                        choices = self._load_choice_list_from_spec(choice_spec)
                        cache_key = f"{field.id}:ref:{ref_target.id}"
                        self.choice_cache[cache_key] = choices

    def _load_choice_list_from_spec(self, choice_spec: Any) -> List[tuple[str, str]]:
        """Load choice list from a ChoiceListSpec.

        Args:
            choice_spec: ChoiceListSpec from profile.

        Returns:
            List of (id, label) tuples for selection.

        Plain meaning: Turn a choice spec into actual dropdown options.
        """
        # Use fallback items if available
        if choice_spec.fallback_items:
            return [(item.id, item.label) for item in choice_spec.fallback_items]

        # Try to load from cache if query_ref is provided
        if choice_spec.query_ref:
            # For now, use fallback items
            return []

        return []
