"""
Entity JSON Schema Validator

Validates GKC Entity JSON objects against schema constraints and calculates completeness.
See docs/gkc/entity-json-schema.md for specification.
"""

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Issue found during entity JSON validation."""

    severity: Literal["error", "warning", "info"]
    field: str  # Which field/object (e.g., "labels.en", "statements.member_count[0]")
    message: str
    suggestion: Optional[str] = None


class EntityJSONValidationResult(BaseModel):
    """Result of entity JSON validation."""

    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)

    def add_issue(
        self, severity: str, field: str, message: str, suggestion: Optional[str] = None
    ):
        """Convenience method to add an issue."""
        self.issues.append(
            ValidationIssue(
                severity=severity, field=field, message=message, suggestion=suggestion
            )
        )


class CompletenessInfo(BaseModel):
    """Completeness metrics for an entity."""

    required_fields_total: int
    completed_fields: int
    missing_fields: List[str] = Field(default_factory=list)
    progress_percentage: float
    progress_text: str
    required_languages: List[str]
    completed_languages: List[str]
    missing_languages: List[str]


class EntityJSONValidator:
    """
    Validates GKC Entity JSON objects and calculates completeness.

    Key responsibilities:
    1. Schema compliance: all required fields present and correct types
    2. Multilingual validation: labels/descriptions conform to profile language requirements
    3. Datatype validation: statement values match expected types
    4. Completeness calculation: progress toward fully curated entity
    5. Cross-entity integrity: references valid within packet
    """

    # Regular expressions for validation
    QID_PATTERN = re.compile(r"^Q\d+$")
    ISO_8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$")
    LANGUAGE_CODE_PATTERN = re.compile(
        r"^[a-z]{2}(-[a-z]{2})?$"
    )  # en, chr, zh-min-nan, etc.

    @staticmethod
    def validate_schema(entity_json: Dict[str, Any]) -> EntityJSONValidationResult:
        """
        Validate that entity JSON conforms to schema structure.

        Returns: EntityJSONValidationResult with list of compliance issues
        """
        result = EntityJSONValidationResult(is_valid=True)

        # Check required metadata fields
        required_metadata = [
            "packet_id",
            "profile_name",
            "username",
            "status",
            "created_at",
            "creation_path",
        ]
        for field in required_metadata:
            if field not in entity_json:
                result.add_issue(
                    "error", field, f"Required metadata field '{field}' missing"
                )
                result.is_valid = False
            elif entity_json[field] is None:
                result.add_issue(
                    "error", field, f"Required metadata field '{field}' cannot be null"
                )
                result.is_valid = False

        # Validate metadata field types
        if "packet_id" in entity_json and not isinstance(entity_json["packet_id"], str):
            result.add_issue("error", "packet_id", "packet_id must be string")
            result.is_valid = False

        if "profile_name" in entity_json and not isinstance(
            entity_json["profile_name"], str
        ):
            result.add_issue("error", "profile_name", "profile_name must be string")
            result.is_valid = False

        if "username" in entity_json and not isinstance(entity_json["username"], str):
            result.add_issue("error", "username", "username must be string")
            result.is_valid = False

        if "status" in entity_json:
            valid_statuses = ["in_progress", "ready_to_resolve_refs", "waiting_for_qid"]
            if entity_json["status"] not in valid_statuses:
                result.add_issue(
                    "warning",
                    "status",
                    f"Unexpected status value '{entity_json['status']}'",
                )

        if "created_at" in entity_json:
            timestamp_str = entity_json["created_at"]
            if not EntityJSONValidator.ISO_8601_PATTERN.match(timestamp_str):
                result.add_issue(
                    "error",
                    "created_at",
                    f"created_at must be ISO 8601 format, got '{timestamp_str}'",
                )
                result.is_valid = False

        # Validate text field structures
        EntityJSONValidator._validate_multilingual_fields(entity_json, result)

        # Validate statements structure
        if "statements" in entity_json:
            if not isinstance(entity_json["statements"], dict):
                result.add_issue(
                    "error",
                    "statements",
                    "statements must be object keyed by property ID",
                )
                result.is_valid = False
            else:
                EntityJSONValidator._validate_statements(
                    entity_json["statements"], result
                )

        # Validate sitelinks structure
        if "sitelinks" in entity_json:
            if not isinstance(entity_json["sitelinks"], dict):
                result.add_issue(
                    "error", "sitelinks", "sitelinks must be object keyed by site code"
                )
                result.is_valid = False
            else:
                for site_code, title in entity_json["sitelinks"].items():
                    if not isinstance(title, str):
                        result.add_issue(
                            "error",
                            f"sitelinks.{site_code}",
                            f"Sitelink value must be string, got {type(title)}",
                        )
                        result.is_valid = False

        return result

    @staticmethod
    def _validate_multilingual_fields(
        entity_json: Dict[str, Any], result: EntityJSONValidationResult
    ) -> None:
        """Validate labels, descriptions, aliases structure."""

        for field_name in ["labels", "descriptions", "aliases"]:
            if field_name not in entity_json:
                # These should exist (defaulted to empty)
                result.add_issue(
                    "warning",
                    field_name,
                    f"{field_name} field missing; should default to empty",
                )
                continue

            field_value = entity_json[field_name]
            if not isinstance(field_value, dict):
                result.add_issue("error", field_name, f"{field_name} must be an object")
                result.is_valid = False
                continue

            # Validate each language entry
            for lang_code, value in field_value.items():
                if not EntityJSONValidator.LANGUAGE_CODE_PATTERN.match(lang_code):
                    result.add_issue(
                        "warning",
                        f"{field_name}.{lang_code}",
                        f"Unexpected language code format: '{lang_code}'",
                    )

                if field_name == "aliases":
                    if not isinstance(value, list):
                        result.add_issue(
                            "error",
                            f"{field_name}.{lang_code}",
                            f"Aliases must be array, got {type(value)}",
                        )
                        result.is_valid = False
                    else:
                        for idx, alias in enumerate(value):
                            if not isinstance(alias, str):
                                result.add_issue(
                                    "error",
                                    f"{field_name}.{lang_code}[{idx}]",
                                    f"Alias must be string, got {type(alias)}",
                                )
                                result.is_valid = False
                else:  # labels or descriptions
                    if not isinstance(value, str):
                        result.add_issue(
                            "error",
                            f"{field_name}.{lang_code}",
                            f"{field_name} value must be string, got {type(value)}",
                        )
                        result.is_valid = False

    @staticmethod
    def _validate_statements(
        statements: Dict[str, Any], result: EntityJSONValidationResult
    ) -> None:
        """Validate statements object structure."""

        for prop_id, stmt_array in statements.items():
            if not isinstance(stmt_array, list):
                result.add_issue(
                    "error",
                    f"statements.{prop_id}",
                    f"Statement values must be array, got {type(stmt_array)}",
                )
                result.is_valid = False
                continue

            for idx, stmt in enumerate(stmt_array):
                if not isinstance(stmt, dict):
                    result.add_issue(
                        "error",
                        f"statements.{prop_id}[{idx}]",
                        f"Statement must be object, got {type(stmt)}",
                    )
                    result.is_valid = False
                    continue

                # Check required statement fields
                if "value" not in stmt:
                    result.add_issue(
                        "warning",
                        f"statements.{prop_id}[{idx}]",
                        "Statement missing 'value' field",
                    )

                # qualifiers and references should be present
                if "qualifiers" not in stmt:
                    result.add_issue(
                        "info",
                        f"statements.{prop_id}[{idx}]",
                        "Statement should have 'qualifiers' field (can be empty)",
                    )

                if "references" not in stmt:
                    result.add_issue(
                        "info",
                        f"statements.{prop_id}[{idx}]",
                        "Statement should have 'references' field (can be empty)",
                    )

                # Validate qualifiers structure
                if "qualifiers" in stmt:
                    if not isinstance(stmt["qualifiers"], dict):
                        result.add_issue(
                            "error",
                            f"statements.{prop_id}[{idx}].qualifiers",
                            f"qualifiers must be object, got {type(stmt['qualifiers'])}",
                        )
                        result.is_valid = False

                # Validate references structure
                if "references" in stmt:
                    if not isinstance(stmt["references"], list):
                        result.add_issue(
                            "error",
                            f"statements.{prop_id}[{idx}].references",
                            f"references must be array, got {type(stmt['references'])}",
                        )
                        result.is_valid = False

    @staticmethod
    def calculate_completeness(
        entity_json: Dict[str, Any],
        profile: Any,
        required_languages: Optional[List[str]] = None,
    ) -> CompletenessInfo:
        """
        Calculate completeness metrics for an entity against its profile.

        Args:
            entity_json: The GKC Entity JSON object
            profile: The EntityProfile this entity is being curated against
            required_languages: Override required languages (default: from profile)

        Returns: CompletenessInfo with progress metrics
        """

        # Determine required languages (default to 1 for MVP, actual from profile eventually)
        if required_languages is None:
            required_languages = getattr(profile, "required_languages", ["en"])

        # Count required fields: 2 base + (2 * languages) + statements
        num_languages = len(required_languages)
        num_statements = (
            len(profile.statements) if hasattr(profile, "statements") else 0
        )
        required_fields_total = 2 + (2 * num_languages) + num_statements

        # Count completed fields
        completed_fields = 0
        missing_fields: List[str] = []
        completed_languages: List[str] = []
        missing_languages: List[str] = []

        labels = entity_json.get("labels", {})
        descriptions = entity_json.get("descriptions", {})

        for lang in required_languages:
            has_label = bool(labels.get(lang, "").strip())
            has_description = bool(descriptions.get(lang, "").strip())

            if has_label:
                completed_fields += 1
            else:
                missing_fields.append(f"labels[{lang}]")
                missing_languages.append(lang)

            if has_description:
                completed_fields += 1
            else:
                missing_fields.append(f"descriptions[{lang}]")
                missing_languages.append(lang)

            if has_label and has_description:
                completed_languages.append(lang)

        # Count completed statements (at least one value per statement)
        statements = entity_json.get("statements", {})
        for stmt_def in profile.statements:
            stmt_id = stmt_def.id
            if stmt_id in statements and len(statements[stmt_id]) > 0:
                # Check if at least one value is present
                has_value = any(
                    stmt.get("value") is not None for stmt in statements[stmt_id]
                )
                if has_value:
                    completed_fields += 1
                else:
                    missing_fields.append(f"statements[{stmt_id}]")
            else:
                missing_fields.append(f"statements[{stmt_id}]")

        # Calculate percentage
        progress_percentage = (
            (completed_fields / required_fields_total * 100)
            if required_fields_total > 0
            else 0
        )
        progress_text = (
            f"{completed_fields} of {required_fields_total} required elements"
        )

        return CompletenessInfo(
            required_fields_total=required_fields_total,
            completed_fields=completed_fields,
            missing_fields=missing_fields,
            progress_percentage=progress_percentage,
            progress_text=progress_text,
            required_languages=required_languages,
            completed_languages=completed_languages,
            missing_languages=missing_languages,
        )

    @staticmethod
    def validate_cross_entity_references(
        packet: Dict[str, Any], result: Optional[EntityJSONValidationResult] = None
    ) -> EntityJSONValidationResult:
        """
        Validate that cross-entity references within a curation packet are resolvable.

        Args:
            packet: The curation packet with 'entities' array
            result: Existing validation result to append to (or None to create new)

        Returns: EntityJSONValidationResult with reference integrity issues
        """
        if result is None:
            result = EntityJSONValidationResult(is_valid=True)

        # Collect all entity packet IDs
        entities = packet.get("entities", [])
        _ = {e.get("packet_id") for e in entities}

        # TODO: Scan through all statements looking for cross-entity references
        # This requires profile-driven detection of which properties are entity links
        # For now, placeholder for future implementation

        return result
