"""Abstract base class for wizard steps.

Plain meaning: Interface that all wizard steps follow.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Step(ABC):
    """Abstract base class for all wizard steps.

    Plain meaning: Blueprint for what each step needs to do.
    """

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
    ) -> None:
        """Initialize a step.

        Args:
            id: Unique identifier for this step (e.g., "identification").
            title: Display title (e.g., "Basic Identification").
            description: Help text describing what this step is for.
        """
        self.id = id
        self.title = title
        self.description = description

    @abstractmethod
    def render(self, draft_data: dict[str, Any]) -> dict[str, Any]:
        """Render step widgets and collect data.

        Args:
            draft_data: The shared draft data dictionary (may be modified by this step).

        Returns:
            Updated draft_data with this step's collected values.

        Plain meaning: Show the form fields for this step and return collected data.
        """
        pass

    @abstractmethod
    def validate(self, draft_data: dict[str, Any]) -> dict[str, list[str]]:
        """Validate data collected by this step.

        Args:
            draft_data: The draft data to validate.

        Returns:
            Dictionary mapping field names to lists of validation warning messages.
            Empty dict if all validations pass.

        Plain meaning: Check if the collected data looks reasonable.
        """
        pass
