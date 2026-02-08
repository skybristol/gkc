"""
Shape Expression (ShEx) validation for Wikidata entities.

This module provides validation of Wikidata entities against ShEx schemas,
particularly EntitySchemas defined in Wikidata.
"""

from pathlib import Path
from typing import Optional

from pyshex import ShExEvaluator  # type: ignore[import-untyped]

from gkc.wd import (
    WikidataFetchError,
    fetch_entity_rdf,
    fetch_entity_schema,
    get_entity_uri,
)


class ShExValidationError(Exception):
    """Raised when ShEx validation encounters an error."""

    pass


class ShExValidator:
    """
    Validate RDF data against Shape Expression (ShEx) schemas.

    This class provides a flexible interface for validating RDF data
    against ShEx schemas, supporting multiple input sources for both
    RDF and schemas.

    Example:
        >>> # Validate a Wikidata item against an EntitySchema
        >>> validator = ShExValidator(qid='Q42', eid='E502')
        >>> result = validator.validate()
        >>> print(result.results)

        >>> # Use local schema file
        >>> validator = ShExValidator(
        ...     qid='Q42',
        ...     schema_file='schema.shex'
        ... )
        >>> validator.validate()

        >>> # Use RDF text directly
        >>> validator = ShExValidator(
        ...     rdf_text=my_rdf_data,
        ...     schema_text=my_schema
        ... )
        >>> validator.validate()
    """

    def __init__(
        self,
        qid: Optional[str] = None,
        eid: Optional[str] = None,
        user_agent: Optional[str] = None,
        schema_text: Optional[str] = None,
        schema_file: Optional[str] = None,
        rdf_text: Optional[str] = None,
        rdf_file: Optional[str] = None,
    ):
        """
        Initialize the ShEx validator.

        Args:
            qid: Wikidata entity ID (e.g., 'Q42'). Optional if rdf_text or
                rdf_file provided.
            eid: EntitySchema ID (e.g., 'E502'). Optional if schema_text or
                schema_file provided.
            user_agent: Custom user agent for Wikidata requests.
            schema_text: ShExC schema as a string (alternative to eid).
            schema_file: Path to file containing ShExC schema (alternative to eid).
            rdf_text: RDF data as a string (alternative to qid).
            rdf_file: Path to file containing RDF data (alternative to qid).
        """
        self.qid = qid
        self.eid = eid
        self.user_agent = user_agent
        self.schema_text = schema_text
        self.schema_file = schema_file
        self.rdf_text = rdf_text
        self.rdf_file = rdf_file

        self._schema: Optional[str] = None
        self._rdf: Optional[str] = None
        self.results = None

    def load_schema(self) -> "ShExValidator":
        """
        Load the ShEx schema from configured source.

        Tries sources in order: schema_text, schema_file, eid (from Wikidata).

        Returns:
            Self for method chaining

        Raises:
            ShExValidationError: If no valid schema source or loading fails
        """
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
                    "No schema source provided. "
                    "Specify eid, schema_text, or schema_file."
                )
        except WikidataFetchError as e:
            raise ShExValidationError(f"Failed to load schema: {str(e)}") from e
        except OSError as e:
            raise ShExValidationError(f"Failed to read schema file: {str(e)}") from e

        return self

    def load_rdf(self) -> "ShExValidator":
        """
        Load RDF data from configured source.

        Tries sources in order: rdf_text, rdf_file, qid (from Wikidata).

        Returns:
            Self for method chaining

        Raises:
            ShExValidationError: If no valid RDF source or loading fails
        """
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
        except WikidataFetchError as e:
            raise ShExValidationError(f"Failed to load RDF: {str(e)}") from e
        except OSError as e:
            raise ShExValidationError(f"Failed to read RDF file: {str(e)}") from e

        return self

    def evaluate(self) -> "ShExValidator":
        """
        Evaluate RDF data against the ShEx schema.

        Must call load_schema() and load_rdf() first, or use validate().

        Returns:
            Self with results populated

        Raises:
            ShExValidationError: If evaluation fails or data not loaded
        """
        if self._schema is None:
            raise ShExValidationError(
                "Schema not loaded. Call load_schema() first or use validate()."
            )
        if self._rdf is None:
            raise ShExValidationError(
                "RDF data not loaded. Call load_rdf() first or use validate()."
            )

        # Determine focus node
        focus = None
        if self.qid:
            focus = get_entity_uri(self.qid)

        try:
            self.results = ShExEvaluator(
                rdf=self._rdf, schema=self._schema, focus=focus
            ).evaluate()
        except Exception as e:
            raise ShExValidationError(f"ShEx evaluation failed: {str(e)}") from e

        return self

    def validate(self) -> "ShExValidator":
        """
        Convenience method: load schema, load RDF, and evaluate in one call.

        Returns:
            Self with results populated

        Example:
            >>> validator = ShExValidator(qid='Q42', eid='E502')
            >>> validator.validate()
            >>> if validator.results:
            ...     print("Validation passed!")
        """
        self.load_schema()
        self.load_rdf()
        self.evaluate()
        return self

    def is_valid(self) -> bool:
        """
        Check if validation passed.

        Returns:
            True if validation passed, False otherwise

        Raises:
            ShExValidationError: If validate() hasn't been called yet
        """
        if self.results is None:
            raise ShExValidationError("No validation results. Call validate() first.")

        # Handle mocked results (for testing)
        if isinstance(self.results, bool):
            return self.results

        # PyShEx returns results as a list of EvaluationResult objects
        # When validation succeeds, reason contains matching triples
        # When validation fails, reason contains error messages like
        # "Node: ... not in value set"
        # If no focus is specified, PyShEx tests all nodes;
        # we need at least one success
        if not self.results:
            return False

        # Check if at least one result succeeded (no error indicators)
        for result in self.results:
            reason = result.reason or ""
            # Common failure indicators in PyShEx error messages
            has_error = any(
                indicator in reason
                for indicator in [
                    "not in value set",
                    "does not match",
                    "Constraint violation",
                    "No matching",
                    "Failed to",
                ]
            )
            if not has_error:
                return True

        return False

    def __repr__(self) -> str:
        """String representation of validator."""
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
