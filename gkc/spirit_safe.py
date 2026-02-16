"""
Spirit Safe: Validation against Barrel Schemas and quality gates.

The Spirit Safe validates transformed data against **Barrel Schemas** before
bottling for delivery to target systems. Named after the locked cabinet in
traditional distilleries where the best product is inspected and held securely.

Currently supports validation against:
- Wikidata Barrel Schema (EntitySchemas in ShEx format + property constraints)

Future support planned for:
- Wikimedia Commons Barrel Schema
- Wikipedia infobox Barrel Schema
- OpenStreetMap tagging Barrel Schema

The Spirit Safe ensures data meets target system requirements before delivery,
preventing malformed data from reaching production systems.

Plain meaning: Validate data against target system schemas and quality rules.
"""

from pathlib import Path
from typing import Optional

from pyshex import ShExEvaluator  # type: ignore[import-untyped]

from gkc.cooperage import (
    CooperageError,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
)


class SpiritSafeValidationError(Exception):
    """Raised when Spirit Safe validation encounters an error."""

    pass


class SpiritSafeValidator:
    """
    Spirit Safe Validator: Validate RDF data against Barrel Schemas.

    Validates transformed data against target system Barrel Schemas before
    bottling. Currently supports Wikidata EntitySchemas (ShEx); future support
    planned for other target systems.

    This validator ensures distilled data in the Unified Still Schema has been
    correctly transformed via Barrel Recipes and meets the target Barrel Schema
    requirements before delivery.

    Plain meaning: Check if data matches target system structure and rules.

    Example:
        >>> # Validate a Wikidata item against its Barrel Schema (EntitySchema)
        >>> validator = SpiritSafeValidator(qid='Q42', eid='E502')
        >>> result = validator.check()
        >>> print(result.results)

        >>> # Use local schema file
        >>> validator = SpiritSafeValidator(
        ...     qid='Q42',
        ...     schema_file='schema.shex'
        ... )
        >>> validator.check()

        >>> # Use RDF text directly
        >>> validator = SpiritSafeValidator(
        ...     rdf_text=my_rdf_data,
        ...     schema_text=my_schema
        ... )
        >>> validator.check()
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
        Initialize the Spirit Safe validator.

        Args:
            qid: Wikidata entity ID (e.g., 'Q42'). Optional if rdf_text or
                rdf_file provided.
            eid: EntitySchema ID for Wikidata Barrel Schema (e.g., 'E502').
                Optional if schema_text or schema_file provided.
            user_agent: Custom user agent for Wikidata requests.
            schema_text: Barrel Schema as ShExC string (alternative to eid).
            schema_file: Path to file containing Barrel Schema (alternative to eid).
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

    def load_specification(self) -> "SpiritSafeValidator":
        """
        Load the Barrel Schema specification from configured source.

        Tries sources in order: schema_text, schema_file, eid (fetch from Wikidata).

        Returns:
            Self for method chaining

        Raises:
            SpiritSafeValidationError: If no valid schema source or loading fails
        """
        try:
            if self.schema_text:
                self._schema = self.schema_text
            elif self.schema_file:
                schema_path = Path(self.schema_file)
                if not schema_path.exists():
                    raise SpiritSafeValidationError(
                        f"Schema file not found: {self.schema_file}"
                    )
                self._schema = schema_path.read_text(encoding="utf-8")
            elif self.eid:
                self._schema = fetch_schema_specification(self.eid, self.user_agent)
            else:
                raise SpiritSafeValidationError(
                    "No schema source provided. "
                    "Specify eid, schema_text, or schema_file."
                )
        except CooperageError as e:
            raise SpiritSafeValidationError(f"Failed to load schema: {str(e)}") from e
        except OSError as e:
            msg = f"Failed to read schema file: {str(e)}"
            raise SpiritSafeValidationError(msg) from e

        return self

    def load_rdf(self) -> "SpiritSafeValidator":
        """
        Load RDF data from configured source.

        Tries sources in order: rdf_text, rdf_file, qid (from Wikidata).

        Returns:
            Self for method chaining

        Raises:
            SpiritSafeValidationError: If no valid RDF source or loading fails
        """
        try:
            if self.rdf_text:
                self._rdf = self.rdf_text
            elif self.rdf_file:
                rdf_path = Path(self.rdf_file)
                if not rdf_path.exists():
                    msg = f"RDF file not found: {self.rdf_file}"
                    raise SpiritSafeValidationError(msg)
                self._rdf = rdf_path.read_text(encoding="utf-8")
            elif self.qid:
                self._rdf = fetch_entity_rdf(
                    self.qid, format="ttl", user_agent=self.user_agent
                )
            else:
                raise SpiritSafeValidationError(
                    "No RDF source provided. Specify qid, rdf_text, or rdf_file."
                )
        except CooperageError as e:
            raise SpiritSafeValidationError(f"Failed to load RDF: {str(e)}") from e
        except OSError as e:
            raise SpiritSafeValidationError(f"Failed to read RDF file: {str(e)}") from e

        return self

    def passes_inspection(self) -> bool:
        """
        Check if validation passed (alias for is_valid).

        Returns:
            True if validation passed, False otherwise

        Raises:
            SpiritSafeValidationError: If check() hasn't been called yet
        """
        return self.is_valid()

    def evaluate(self) -> "SpiritSafeValidator":
        """
        Evaluate RDF data against the Barrel Schema specification.

        Must call load_specification() and load_rdf() first, or use check().

        Returns:
            Self with results populated

        Raises:
            SpiritSafeValidationError: If evaluation fails or data not loaded
        """
        if self._schema is None:
            raise SpiritSafeValidationError(
                "Schema not loaded. Call load_specification() first or use check()."
            )
        if self._rdf is None:
            raise SpiritSafeValidationError(
                "RDF data not loaded. Call load_rdf() first or use check()."
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
            msg = f"Spirit Safe evaluation failed: {str(e)}"
            raise SpiritSafeValidationError(msg) from e

        return self

    def check(self) -> "SpiritSafeValidator":
        """
        Inspection: Load specification, load RDF, and evaluate in one call.

        This is the main entry point for validation. It loads schema and data
        from configured sources, then performs the inspection.

        Returns:
            Self with results populated

        Example:
            >>> validator = SpiritSafeValidator(qid='Q42', eid='E502')
            >>> validator.check()
            >>> if validator.passes_inspection():
            ...     print("Product meets quality standards!")
        """
        self.load_specification()
        self.load_rdf()
        self.evaluate()
        return self

    def is_valid(self) -> bool:
        """
        Check if validation passed.

        Returns:
            True if validation passed, False otherwise

        Raises:
            SpiritSafeValidationError: If check() hasn't been called yet
        """
        if self.results is None:
            msg = "No validation results. Call check() first."
            raise SpiritSafeValidationError(msg)

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
        return f"SpiritSafeValidator({params})"
