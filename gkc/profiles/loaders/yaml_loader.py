"""YAML profile loader for SpiritSafe profiles.

Plain meaning: Load YAML profile files into typed Python objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

import yaml
from jsonschema import Draft202012Validator

from gkc.profiles.models import ProfileDefinition


class ProfileLoader:
    """Load YAML profile definitions into ProfileDefinition objects.

    Args:
        schema_path: Optional path to the JSON schema used for validation.

    Side effects:
        Reads the JSON schema from disk during initialization.

    Example:
        >>> loader = ProfileLoader()
        >>> profile = loader.load_from_file("profiles/TribalGovernmentUS.yaml")

    Plain meaning: Read a YAML profile and validate its structure.
    """

    def __init__(self, schema_path: Optional[Path] = None):
        self._schema_path = schema_path or self._default_schema_path()
        self._validator = Draft202012Validator(self._load_schema())

    def load_from_file(self, path: Union[str, Path]) -> ProfileDefinition:
        """Load a YAML profile from a file.

        Args:
            path: Path to the YAML profile file.

        Returns:
            Parsed ProfileDefinition instance.

        Raises:
            ValueError: If the profile fails schema validation.
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML cannot be parsed.

        Side effects:
            Reads a YAML file from disk.

        Example:
            >>> profile = loader.load_from_file(".dev/TribalGovernmentUS.yaml")

        Plain meaning: Read and validate a profile file.
        """
        yaml_text = Path(path).read_text(encoding="utf-8")
        return self.load_from_text(yaml_text)

    def load_from_text(self, text: str) -> ProfileDefinition:
        """Load a YAML profile from text.

        Args:
            text: YAML text contents.

        Returns:
            Parsed ProfileDefinition instance.

        Raises:
            ValueError: If the profile fails schema validation.
            yaml.YAMLError: If the YAML cannot be parsed.

        Side effects:
            None.

        Example:
            >>> profile = loader.load_from_text("name: Example\nfields: []")

        Plain meaning: Parse YAML content into a profile object.
        """
        data = yaml.safe_load(text) or {}
        return self.load_from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> ProfileDefinition:
        """Load a profile from a Python dictionary.

        Args:
            data: Profile data dictionary.

        Returns:
            Parsed ProfileDefinition instance.

        Raises:
            ValueError: If the profile fails schema validation.

        Side effects:
            None.

        Example:
            >>> profile = loader.load_from_dict({"name": "Demo", "fields": []})

        Plain meaning: Validate and convert profile data to a typed object.
        """
        errors = list(self.validate_data(data))
        if errors:
            message = "Profile schema validation failed: " + "; ".join(errors)
            raise ValueError(message)
        return ProfileDefinition.model_validate(data)

    def validate_data(self, data: Dict[str, Any]) -> Iterable[str]:
        """Validate profile data against the JSON schema.

        Args:
            data: Profile data dictionary.

        Returns:
            Iterable of error messages (empty if valid).

        Side effects:
            None.

        Example:
            >>> errors = list(loader.validate_data({"name": "Demo"}))

        Plain meaning: Check if the profile matches the required structure.
        """
        for error in sorted(self._validator.iter_errors(data), key=str):
            path = ".".join([str(item) for item in error.path]) or "<root>"
            yield f"{path}: {error.message}"

    def _load_schema(self) -> dict[str, Any]:
        schema_text = self._schema_path.read_text(encoding="utf-8")
        return json.loads(schema_text)

    @staticmethod
    def _default_schema_path() -> Path:
        return Path(__file__).resolve().parents[1] / "schemas" / "profile.schema.json"
