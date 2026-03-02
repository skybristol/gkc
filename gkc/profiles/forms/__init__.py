"""Form generation and UI components for profiles.

Plain meaning: Interactive form tools for profile-based data entry.
"""

from gkc.profiles.forms import streamlit_app
from gkc.profiles.forms.draft_manager import DraftManager

__all__ = ["DraftManager", "streamlit_app"]
