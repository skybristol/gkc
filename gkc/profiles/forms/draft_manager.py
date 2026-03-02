"""Persist and restore wizard draft state to JSON files.

Plain meaning: Save and load in-progress wizard data.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class DraftManager:
    """Persist and restore wizard draft state to JSON files.

    Plain meaning: Save and load in-progress wizard data.
    """

    def __init__(self, drafts_dir: Path | None = None) -> None:
        # Use home directory for drafts (Streamlit-standard approach)
        # This keeps drafts persistent across sessions and separate from repo
        if drafts_dir is None:
            drafts_dir = Path.home() / ".gkc" / "drafts"
        self.drafts_dir = drafts_dir
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def create_draft_path(self, profile_name: str) -> Path:
        """Build a timestamped draft filepath for a profile."""
        safe_name = "_".join(profile_name.split())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.drafts_dir / f"{safe_name}_{timestamp}.json"

    def save(self, path: Path, payload: dict[str, Any]) -> None:
        """Write draft payload to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: Path) -> dict[str, Any]:
        """Load draft payload from disk."""
        return json.loads(path.read_text(encoding="utf-8"))
