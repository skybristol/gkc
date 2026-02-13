"""
Deprecated: This module has been renamed to 'spirit_safe'.

This file provides backwards compatibility during the terminology refactoring.
Please update imports to use gkc.spirit_safe instead.

Example:
    Old: from gkc.shex import ShExValidator
    New: from gkc.spirit_safe import SpiritSafeValidator
"""

from pathlib import Path
from typing import Optional

from pyshex import ShExEvaluator  # type: ignore[import-untyped]

from gkc.cooperage import CooperageError, fetch_entity_rdf, fetch_schema_specification, get_entity_uri
from gkc.spirit_safe import SpiritSafeValidationError, SpiritSafeValidator


def fetch_entity_schema(eid: str, user_agent: Optional[str] = None) -> str:
    """Backwards-compatible alias for fetching EntitySchema text."""
    return fetch_schema_specification(eid, user_agent)


ShExValidationError = SpiritSafeValidationError


class ShExValidator(SpiritSafeValidator):
    """
    Backwards-compatible ShEx validator.

    Mirrors the pre-refactor API so tests and user code can patch names under
    gkc.shex without breaking.
    """

    def load_schema(self) -> "ShExValidator":
        """Load schema from text, file, or EntitySchema (legacy name)."""
        try:
            if self.schema_text:
                self._schema = self.schema_text
            elif self.schema_file:
                schema_path = Path(self.schema_file)
                if not schema_path.exists():
                    raise ShExValidationError(
                        f"Schema file not found: {self.schema_file}"
                    )
                self._schema = schema_path.read_text(encoding="utf-8")
            elif self.eid:
                self._schema = fetch_entity_schema(self.eid, self.user_agent)
            else:
                raise ShExValidationError(
                    "No schema source provided. Specify eid, schema_text, or schema_file."
                )
        except CooperageError as e:
            raise ShExValidationError(f"Failed to load schema: {str(e)}") from e
        except OSError as e:
            raise ShExValidationError(f"Failed to read schema file: {str(e)}") from e

        return self

    def load_rdf(self) -> "ShExValidator":
        """Load RDF data from text, file, or Wikidata (legacy name)."""
        try:
            if self.rdf_text:
                self._rdf = self.rdf_text
            elif self.rdf_file:
                rdf_path = Path(self.rdf_file)
                if not rdf_path.exists():
                    raise ShExValidationError(f"RDF file not found: {self.rdf_file}")
                self._rdf = rdf_path.read_text(encoding="utf-8")
            elif self.qid:
                self._rdf = fetch_entity_rdf(
                    self.qid, format="ttl", user_agent=self.user_agent
                )
            else:
                raise ShExValidationError(
                    "No RDF source provided. Specify qid, rdf_text, or rdf_file."
                )
        except CooperageError as e:
            raise ShExValidationError(f"Failed to load RDF: {str(e)}") from e
        except OSError as e:
            raise ShExValidationError(f"Failed to read RDF file: {str(e)}") from e

        return self

    def evaluate(self) -> "ShExValidator":
        """Evaluate RDF against schema, using legacy module namespace for patching."""
        if self._schema is None:
            raise ShExValidationError(
                "Schema not loaded. Call load_schema() first or use validate()."
            )
        if self._rdf is None:
            raise ShExValidationError(
                "RDF data not loaded. Call load_rdf() first or use validate()."
            )

        focus = get_entity_uri(self.qid) if self.qid else None

        try:
            self.results = ShExEvaluator(
                rdf=self._rdf, schema=self._schema, focus=focus
            ).evaluate()
        except Exception as e:
            raise ShExValidationError(f"ShEx evaluation failed: {str(e)}") from e

        return self

    def validate(self) -> "ShExValidator":
        """Legacy convenience method: load schema, load RDF, then evaluate."""
        self.load_schema()
        self.load_rdf()
        self.evaluate()
        return self

    def __repr__(self) -> str:
        """String representation of validator (legacy name)."""
        parts = []
        if self.qid:
            parts.append(f"qid={self.qid!r}")
        if self.eid:
            parts.append(f"eid={self.eid!r}")
        if self.rdf_file:
            parts.append(f"rdf_file={self.rdf_file!r}")
        if self.schema_file:
            parts.append(f"schema_file={self.schema_file!r}")

        params = ", ".join(parts) if parts else ""
        return f"ShExValidator({params})"


__all__ = [
    "ShExValidator",
    "ShExValidationError",
    "SpiritSafeValidator",
    "SpiritSafeValidationError",
    "fetch_entity_schema",
    "fetch_entity_rdf",
    "ShExEvaluator",
]

