"""Wizard runtime components.

Plain meaning: The individual screens/pages and helpers for the wizard runtime.
"""

from gkc.wizard.step_base import Step
from gkc.wizard.steps import (
    IdentificationStep,
    SitelinksStep,
    StatementsStep,
)

__all__ = ["Step", "IdentificationStep", "SitelinksStep", "StatementsStep"]
