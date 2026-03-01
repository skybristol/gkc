"""Profile validation utilities.

Plain meaning: Validate Wikidata items against YAML profiles.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, Field, ValidationError

from gkc.profiles.generators.pydantic_generator import ProfilePydanticGenerator
from gkc.profiles.models import ProfileDefinition
from gkc.profiles.validation.models import StatementData
from gkc.profiles.validation.wikidata_normalizer import (
    NormalizationResult,
    WikidataNormalizer,
)

ValidationPolicy = Literal["strict", "lenient"]


class ValidationIssue(BaseModel):
    """Validation issue reported by profile checks.

    Args:
        severity: "error" or "warning".
        message: Issue description.
        statement_id: Optional profile statement identifier.
        property_id: Optional Wikidata property ID.

    Example:
        >>> ValidationIssue(severity="error", message="Missing P31")

    Plain meaning: A problem found during validation.
    """

    severity: Literal["error", "warning"]
    message: str
    statement_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("statement_id", "field_id"),
        serialization_alias="statement_id",
    )
    property_id: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validating an item against a profile.

    Attributes:
        ok: Whether validation passed without errors.
        errors: Validation errors.
        warnings: Validation warnings.
        normalized: Normalized statement data.

    Plain meaning: Validation status and issues found.
    """

    ok: bool
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    normalized: Dict[str, List[StatementData]]

    def is_valid(self) -> bool:
        """Return True when validation has no errors.

        Returns:
            True if no errors are present.

        Side effects:
            None.

        Example:
            >>> result.is_valid()

        Plain meaning: Check if validation succeeded.
        """
        return self.ok


class ProfileValidator:
    """Validate Wikidata item data against a ProfileDefinition.

    Args:
        profile: Parsed ProfileDefinition instance.

    Side effects:
        None.

    Example:
        >>> validator = ProfileValidator(profile)
        >>> result = validator.validate_item(entity_data)

    Plain meaning: Apply profile rules to a Wikidata item.
    """

    def __init__(self, profile: ProfileDefinition):
        self.profile = profile
        self._generator = ProfilePydanticGenerator(profile)
        self._normalizer = WikidataNormalizer()

    def validate_item(
        self, entity_data: dict, policy: ValidationPolicy = "lenient"
    ) -> ValidationResult:
        """Validate a Wikidata item against the profile.

        Args:
            entity_data: Wikidata JSON entity data.
            policy: Validation policy ("strict" or "lenient").

        Returns:
            ValidationResult with errors, warnings, and normalized data.

        Side effects:
            None.

        Example:
            >>> result = validator.validate_item(item, policy="lenient")

        Plain meaning: Check a Wikidata item for profile compliance.
        """
        normalization = self._normalizer.normalize(entity_data, self.profile)
        model = self._generator.build_model()

        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        self._add_normalization_issues(normalization, warnings, errors)

        try:
            model.model_validate(normalization.data, context={"policy": policy})
        except ValidationError as exc:
            errors.extend(self._errors_from_validation(exc, model))

        if policy == "lenient":
            warnings.extend(self._collect_lenient_warnings(normalization))

        ok = len(errors) == 0
        return ValidationResult(
            ok=ok,
            errors=errors,
            warnings=warnings,
            normalized=normalization.data,
        )

    def _add_normalization_issues(
        self,
        normalization: NormalizationResult,
        warnings: List[ValidationIssue],
        errors: List[ValidationIssue],
    ) -> None:
        for issue in normalization.issues:
            target = warnings if issue.severity == "warning" else errors
            target.append(
                ValidationIssue(
                    severity=issue.severity,
                    message=issue.message,
                    statement_id=issue.statement_id,
                    property_id=issue.property_id,
                )
            )

    def _errors_from_validation(
        self, exc: ValidationError, model: type[BaseModel]
    ) -> list[ValidationIssue]:
        issues: List[ValidationIssue] = []
        field_aliases = {
            name: (field.alias or name) for name, field in model.model_fields.items()
        }

        for err in exc.errors():
            loc = err.get("loc", [])
            field_name = loc[0] if loc else None
            statement_id = field_aliases.get(field_name) if field_name else None
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=err.get("msg", "Validation error"),
                    statement_id=statement_id,
                )
            )
        return issues

    def _collect_lenient_warnings(
        self, normalization: NormalizationResult
    ) -> list[ValidationIssue]:
        warnings: list[ValidationIssue] = []

        for field in self.profile.statements:
            statements = normalization.data.get(field.id, [])
            violations = _evaluate_field(field, statements)
            for violation, category in violations:
                if category == "field":
                    if field.validation_policy != "allow_existing_nonconforming":
                        continue
                if category == "reference" and field.references:
                    if (
                        field.references.validation_policy
                        != "allow_existing_nonconforming"
                    ):
                        continue
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"{field.id}: {violation}",
                        statement_id=field.id,
                        property_id=field.wikidata_property,
                    )
                )

        return warnings


def _evaluate_field(field, statements: List[StatementData]) -> List[tuple[str, str]]:
    violations: List[tuple[str, str]] = []

    if field.required and not statements:
        violations.append(("required statement missing", "field"))

    if field.max_count is not None and len(statements) > field.max_count:
        violations.append(
            (f"max_count exceeded ({len(statements)} > {field.max_count})", "field")
        )

    for index, statement in enumerate(statements):
        if statement.value.value_type != field.value.type:
            violations.append(
                (
                    f"statement {index} has value type {statement.value.value_type}",
                    "field",
                )
            )

        if field.value.fixed is not None:
            if statement.value.value != field.value.fixed:
                violations.append(
                    (f"statement {index} does not match fixed value", "field")
                )

        for constraint in field.value.constraints:
            if constraint.type == "integer_only":
                value_to_check = statement.value.value
                if isinstance(value_to_check, dict):
                    # Extract amount from quantity dict if present
                    value_to_check = value_to_check.get("amount", value_to_check)
                if not _is_integer(value_to_check):
                    violations.append(
                        (f"statement {index} violates integer_only", "field")
                    )

        for qualifier in field.qualifiers:
            qvalues = statement.qualifiers.get(qualifier.wikidata_property, [])
            if qualifier.min_count is not None and len(qvalues) < qualifier.min_count:
                violations.append(
                    (
                        "statement "
                        f"{index} missing qualifier {qualifier.wikidata_property}",
                        "field",
                    )
                )
            if qualifier.max_count is not None and len(qvalues) > qualifier.max_count:
                violations.append(
                    (
                        "statement "
                        f"{index} exceeds qualifier {qualifier.wikidata_property}",
                        "field",
                    )
                )
            if qualifier.value.fixed is not None and qvalues:
                if any(q.value != qualifier.value.fixed for q in qvalues):
                    message = (
                        "statement "
                        f"{index} qualifier "
                        f"{qualifier.wikidata_property} fixed mismatch"
                    )
                    violations.append((message, "field"))

        references = field.references
        if references:
            if (
                references.min_count is not None
                and len(statement.references) < references.min_count
            ):
                violations.append(
                    (f"statement {index} has too few references", "reference")
                )
            if references.required and not statement.references:
                violations.append(
                    (f"statement {index} missing required references", "reference")
                )

            if references.target:
                target_pid = references.target.wikidata_property
                for ref_index, reference in enumerate(statement.references):
                    if target_pid not in reference.snaks:
                        violations.append(
                            (
                                "statement "
                                f"{index} reference {ref_index} missing {target_pid}",
                                "reference",
                            )
                        )
                    if references.target.value_source == "statement_value":
                        values = reference.snaks.get(target_pid, [])
                        if values and any(
                            val.value != statement.value.value for val in values
                        ):
                            message = (
                                "statement "
                                f"{index} reference {ref_index} does not match "
                                "statement value"
                            )
                            violations.append((message, "reference"))

            if references.allowed:
                allowed_pids = {a.wikidata_property for a in references.allowed}
                for ref_index, reference in enumerate(statement.references):
                    if not allowed_pids.intersection(reference.snaks.keys()):
                        message = (
                            "statement "
                            f"{index} reference {ref_index} lacks "
                            "allowed properties"
                        )
                        violations.append((message, "reference"))

    return violations


def _is_integer(value: Union[str, int, float]) -> bool:
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return value.is_integer()
    if isinstance(value, str):
        try:
            return float(value).is_integer()
        except ValueError:
            return False
    return False
