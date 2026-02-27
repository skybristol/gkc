"""Pydantic model generator for YAML profiles.

Plain meaning: Build runtime validation models from YAML profiles.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    create_model,
    field_validator,
)

from gkc.profiles.models import ProfileDefinition
from gkc.profiles.validation.models import StatementData


class ProfilePydanticGenerator:
    """Generate Pydantic models for YAML profile validation.

    Args:
        profile: Parsed ProfileDefinition instance.
        model_name: Optional model class name override.

    Side effects:
        None.

    Example:
        >>> generator = ProfilePydanticGenerator(profile)
        >>> Model = generator.build_model()

    Plain meaning: Create a Pydantic class that validates profile statements.
    """

    def __init__(self, profile: ProfileDefinition, model_name: Optional[str] = None):
        self.profile = profile
        self.model_name = model_name or self._default_model_name()

    def build_model(self) -> type[BaseModel]:
        """Build a Pydantic model class for this profile.

        Returns:
            Dynamically generated Pydantic model class.

        Side effects:
            None.

        Example:
            >>> Model = ProfilePydanticGenerator(profile).build_model()

        Plain meaning: Generate a validation class for profile statements.
        """
        field_definitions = {}
        validators: Dict[str, Callable] = {}

        for field in self.profile.fields:
            safe_name = self._safe_field_name(field.id)
            field_definitions[safe_name] = (
                list[StatementData],
                Field(
                    default_factory=list,
                    description=(
                        f"Statements for {field.label} ({field.wikidata_property})"
                    ),
                    alias=field.id,
                ),
            )

            validators[f"validate_{safe_name}"] = field_validator(safe_name)(
                self._make_field_validator(field)
            )

        model_config = ConfigDict(
            populate_by_name=True,
            extra="forbid",
        )

        return create_model(
            self.model_name,
            __base__=_ProfileModelBase,
            __config__=model_config,
            __validators__=validators,
            **field_definitions,
        )

    def _make_field_validator(self, field):
        def _validator(cls, value: List[StatementData], info: ValidationInfo):
            policy = "strict"
            if info.context and isinstance(info.context, dict):
                policy = info.context.get("policy", "strict")

            violations: List[str] = []
            reference_violations: List[str] = []

            if field.required and not value:
                violations.append("required statement missing")

            if field.max_count is not None and len(value) > field.max_count:
                violations.append(
                    f"max_count exceeded ({len(value)} > {field.max_count})"
                )

            for index, statement in enumerate(value):
                if statement.value.value_type != field.value.type:
                    violations.append(
                        f"statement {index} has value type {statement.value.value_type}"
                    )

                if field.value.fixed is not None:
                    if statement.value.value != field.value.fixed:
                        violations.append(
                            f"statement {index} does not match fixed value"
                        )

                for constraint in field.value.constraints:
                    if constraint.type == "integer_only":
                        if not _is_integer(statement.value.value):
                            violations.append(
                                f"statement {index} violates integer_only"
                            )

                for qualifier in field.qualifiers:
                    qvalues = statement.qualifiers.get(qualifier.wikidata_property, [])
                    if (
                        qualifier.min_count is not None
                        and len(qvalues) < qualifier.min_count
                    ):
                        message = (
                            "statement "
                            f"{index} missing qualifier "
                            f"{qualifier.wikidata_property}"
                        )
                        violations.append(message)
                    if (
                        qualifier.max_count is not None
                        and len(qvalues) > qualifier.max_count
                    ):
                        message = (
                            "statement "
                            f"{index} exceeds qualifier "
                            f"{qualifier.wikidata_property}"
                        )
                        violations.append(message)
                    if qualifier.value.fixed is not None and qvalues:
                        if any(q.value != qualifier.value.fixed for q in qvalues):
                            message = (
                                "statement "
                                f"{index} qualifier "
                                f"{qualifier.wikidata_property} fixed mismatch"
                            )
                            violations.append(message)

                references = field.references
                if references:
                    if (
                        references.min_count is not None
                        and len(statement.references) < references.min_count
                    ):
                        reference_violations.append(
                            f"statement {index} has too few references"
                        )
                    if references.required and not statement.references:
                        reference_violations.append(
                            f"statement {index} missing required references"
                        )

                    if references.target:
                        target_pid = references.target.wikidata_property
                        for ref_index, reference in enumerate(statement.references):
                            if target_pid not in reference.snaks:
                                message = (
                                    "statement "
                                    f"{index} reference {ref_index} missing "
                                    f"{target_pid}"
                                )
                                reference_violations.append(message)
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
                                    reference_violations.append(message)

                    if references.allowed:
                        allowed_pids = {a.wikidata_property for a in references.allowed}
                        for ref_index, reference in enumerate(statement.references):
                            if not allowed_pids.intersection(reference.snaks.keys()):
                                message = (
                                    "statement "
                                    f"{index} reference {ref_index} lacks "
                                    "allowed properties"
                                )
                                reference_violations.append(message)

            error_messages: List[str] = []
            if violations and _should_raise(field.validation_policy, policy):
                error_messages.extend(violations)

            references = field.references
            if references and reference_violations:
                if _should_raise(references.validation_policy, policy):
                    error_messages.extend(reference_violations)

            if error_messages:
                raise ValueError(
                    f"{field.id} validation failed: " + "; ".join(error_messages)
                )

            return value

        return _validator

    def _default_model_name(self) -> str:
        safe = self.profile.name.title().replace(" ", "")
        return f"{safe}ProfileModel"

    @staticmethod
    def _safe_field_name(field_id: str) -> str:
        safe = field_id.replace("-", "_")
        if safe and safe[0].isdigit():
            return f"field_{safe}"
        return safe


class _ProfileModelBase(BaseModel):
    """Base class for generated profile validation models.

    Plain meaning: Shared base for all generated profile validators.
    """

    model_config = ConfigDict(extra="forbid")


def _should_raise(field_policy: str, validation_policy: str) -> bool:
    if validation_policy == "strict":
        return True
    return field_policy == "strict"


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
