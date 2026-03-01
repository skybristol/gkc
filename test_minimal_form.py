#!/usr/bin/env python3
"""Minimal Textual form to verify basic Input functionality.

This is a diagnostic tool to test if Textual Input widgets work at all.
Run: python test_minimal_form.py
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Static


class MinimalFormApp(App):
    """Bare-minimum form to test Input widget typing."""

    CSS = """
    Screen {
        align: center middle;
    }

    #form_container {
        width: 50;
        height: auto;
        border: solid $accent;
        padding: 1;
    }

    .field {
        height: auto;
        margin: 1 0;
    }

    .field-label {
        color: $accent;
        text-style: bold;
    }

    .breadcrumb {
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }

    .focus-state {
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Build the minimal form."""
        yield Header()
        yield Static("Minimal Form Test", classes="breadcrumb")
        yield Static("Focus: none", id="focus_state", classes="focus-state")

        yield Vertical(
            Vertical(
                Label("Name:", classes="field-label"),
                Input(placeholder="Enter your name", id="field_name"),
                classes="field",
            ),
            Vertical(
                Label("Email:", classes="field-label"),
                Input(placeholder="Enter your email", id="field_email"),
                classes="field",
            ),
            Vertical(
                Label("Message:", classes="field-label"),
                Input(placeholder="Enter a message", id="field_message"),
                classes="field",
            ),
            id="form_container",
        )

        yield Horizontal(
            Button("Submit", id="submit_button", variant="primary"),
            Button("Cancel", id="cancel_button"),
            id="action_buttons",
        )

        yield Footer()

    def on_key(self, event) -> None:
        """Update focus banner after any key press."""
        self.call_after_refresh(self._update_focus_state)

    def _update_focus_state(self) -> None:
        """Render current focus target in the debug focus banner."""
        focus_widget = self.focused

        if focus_widget is None:
            self.query_one("#focus_state", Static).update("Focus: none")
            return

        widget_id = getattr(focus_widget, "id", None)
        widget_name = focus_widget.__class__.__name__
        if widget_id:
            self.query_one("#focus_state", Static).update(
                f"Focus: {widget_name} (id={widget_id})"
            )
        else:
            self.query_one("#focus_state", Static).update(f"Focus: {widget_name}")

    def on_mount(self) -> None:
        """Focus the first input when the app starts."""
        first_input = self.query_one("#field_name", Input)
        self.call_after_refresh(self.set_focus, first_input)
        self.call_after_refresh(self._update_focus_state)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "submit_button":
            # Collect form data
            name = self.query_one("#field_name", Input).value
            email = self.query_one("#field_email", Input).value
            message = self.query_one("#field_message", Input).value
            print(f"\nSubmitted: name={name}, email={email}, message={message}")
            self.exit()
        elif event.button.id == "cancel_button":
            self.exit()


if __name__ == "__main__":
    app = MinimalFormApp()
    app.run()
