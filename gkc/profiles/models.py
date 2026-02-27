"""
Profile models for YAML-defined SpiritSafe entity profiles.

These Pydantic models define the internal representation of YAML profile
structures, covering fields, qualifiers, references, and value constraints.

Plain meaning: The typed Python shape of a YAML profile.
"""

from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

ValidationPolicy = Literal["allow_existing_nonconforming", "strict"]
FormPolicy = Literal["target_only", "show_all"]
ValueType = Literal[
    "item",
    "url",
    "string",
    "quantity",
    "time",
    "monolingualtext",
    "globecoordinate",
    "external-id",
    "commonsMedia",
]
ChoiceRefreshPolicy = Literal["manual", "daily", "weekly", "on_release"]


class ConstraintDefinition(BaseModel):
    """Define a validation constraint applied to a value.

    Args:
        type: Constraint identifier (e.g., "integer_only").
        description: Optional human-readable description.

    Example:
        >>> ConstraintDefinition(type="integer_only")

    Plain meaning: A named rule that value entries must satisfy.
    """

    type: str = Field(..., description="Constraint identifier")
    description: str = Field(default="", description="Constraint description")


class ChoiceItem(BaseModel):
    """Define a selectable item for choice lists.

    Args:
        id: Item identifier (e.g., "Q123").
        label: Human-readable label.

    Example:
        >>> ChoiceItem(id="Q42", label="Douglas Adams")

    Plain meaning: A single choice option for forms.
    """

    id: str = Field(..., description="Choice item identifier")
    label: str = Field(..., description="Choice item label")


class ChoiceListSpec(BaseModel):
    """Define a choice list backed by SPARQL or other sources.

    Args:
        source: Choice list source type (currently only "sparql").
        query: Optional inline SPARQL query text.
        query_ref: Optional named query reference path.
        query_params: Optional parameter map used to render query templates.
        refresh: Refresh cadence for cached results.
        fallback_items: Static fallback choices when query is unavailable.

    Example:
        >>> ChoiceListSpec(source="sparql", query="SELECT ...", refresh="manual")
        >>> ChoiceListSpec(
        ...     source="sparql",
        ...     query_ref="queries/wikidata_language_items_en.sparql",
        ...     query_params={"lang": "en"},
        ... )

    Plain meaning: A reusable list of recommended or allowed values.
    """

    source: Literal["sparql"] = Field(..., description="Choice list source")
    query: Optional[str] = Field(default=None, description="Inline SPARQL query text")
    query_ref: Optional[str] = Field(
        default=None,
        description="Named SPARQL query reference path (e.g., queries/file.sparql)",
    )
    query_params: dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict,
        description="Template parameters for referenced queries",
    )
    refresh: ChoiceRefreshPolicy = Field(
        default="manual", description="Refresh cadence"
    )
    fallback_items: List[ChoiceItem] = Field(
        default_factory=list, description="Fallback items"
    )

    @model_validator(mode="after")
    def _require_query_or_ref(self):
        if not self.query and not self.query_ref:
            raise ValueError("ChoiceListSpec requires either 'query' or 'query_ref'")
        return self


class ValueDefinition(BaseModel):
    """Define the value type and constraints for a field or qualifier.

    Args:
        type: Value datatype (item, url, string, quantity, time).
        fixed: Fixed value constraint (e.g., a required QID).
        label: Optional label for fixed values.
        constraints: Additional validation constraints.

    Example:
        >>> ValueDefinition(type="item", fixed="Q5")

    Plain meaning: The expected datatype and rules for a value.
    """

    type: ValueType = Field(..., description="Value datatype")
    fixed: Optional[Union[str, int, float]] = Field(
        default=None, description="Fixed value constraint"
    )
    label: str = Field(default="", description="Optional label for fixed values")
    constraints: List[ConstraintDefinition] = Field(
        default_factory=list, description="Value constraints"
    )


class ReferenceTargetDefinition(BaseModel):
    """Define an allowed or target reference entry.

    Args:
        id: Identifier for the reference entry.
        wikidata_property: Wikidata property ID.
        type: Datatype for the reference value.
        label: Human-readable label.
        description: Optional description.
        value_source: Optional value source hint (e.g., "statement_value").
        allowed_items: Optional choice list for allowed values.

    Example:
        >>> ReferenceTargetDefinition(
        ...     id="stated_in",
        ...     wikidata_property="P248",
        ...     type="item",
        ...     label="Stated in"
        ... )

    Plain meaning: A reference property allowed or required on a statement.
    """

    id: str = Field(..., description="Reference entry identifier")
    wikidata_property: str = Field(..., description="Wikidata property ID")
    type: ValueType = Field(..., description="Reference value datatype")
    label: str = Field(..., description="Reference entry label")
    description: str = Field(default="", description="Reference entry description")
    value_source: Optional[str] = Field(default=None, description="Value source hint")
    allowed_items: Optional[ChoiceListSpec] = Field(
        default=None, description="Optional choice list"
    )


class MetadataDefinition(BaseModel):
    """Define metadata for a single language (labels, descriptions, aliases, sitelinks).

    Args:
        label: Field label for curation.
        description: Description explaining what should go here.
        required: Whether this language variant is required.
        guidance: Curator guidance text.
        examples: Optional list of example values.

    Example:
        >>> MetadataDefinition(
        ...     label="Label",
        ...     description="Primary name in English",
        ...     required=True,
        ...     guidance="Use the tribe's self-designation"
        ... )

    Plain meaning: A single language's metadata definition with curator guidance.
    """

    label: str = Field(..., description="Metadata field label")
    description: str = Field(..., description="What this metadata contains")
    required: bool = Field(default=False, description="Is this variant required?")
    guidance: str = Field(default="", description="Curator guidance text")
    examples: List[str] = Field(default_factory=list, description="Example values")


class SitelinkLanguageDefinition(BaseModel):
    """Define a sitelink for a specific language/project.

    Args:
        project: Wikimedia project name (wikipedia, commons, etc.).
        description: Description of the sitelink.
        required: Whether this language variant is required.
        guidance: Curator guidance text.

    Example:
        >>> SitelinkLanguageDefinition(
        ...     project="wikipedia",
        ...     description="English Wikipedia article",
        ...     required=False,
        ...     guidance="Add if article exists"
        ... )

    Plain meaning: Links to Wikipedia/Commons articles in a specific language.
    """

    project: str = Field(..., description="Wikimedia project name")
    description: str = Field(..., description="Sitelink description")
    required: bool = Field(default=False, description="Is this variant required?")
    guidance: str = Field(default="", description="Curator guidance text")


class SitelinksDefinition(BaseModel):
    """Define all sitelinks for an item.

    Args:
        required: Whether sitelinks are required.
        validation_policy: Validation policy for existing items.
        guidance: General curator guidance for sitelinks.
        languages: Per-language sitelink definitions.

    Example:
        >>> SitelinksDefinition(
        ...     required=False,
        ...     guidance="Check for uniqueness conflicts",
        ...     languages={"en": SitelinkLanguageDefinition(...)}
        ... )

    Plain meaning: Configuration for all wiki article links on an item.
    """

    required: bool = Field(default=False, description="Are sitelinks required?")
    validation_policy: ValidationPolicy = Field(
        default="allow_existing_nonconforming",
        description="Sitelink validation policy",
    )
    guidance: str = Field(default="", description="General curator guidance")
    languages: dict[str, SitelinkLanguageDefinition] = Field(
        default_factory=dict, description="Per-language sitelink definitions"
    )


class ReferenceDefinition(BaseModel):
    """Define reference requirements for a field.

    Args:
        required: Whether references are required.
        min_count: Minimum number of references per statement.
        validation_policy: Validation policy for existing items.
        form_policy: Form visibility policy.
        allowed: Allowed reference property definitions.
        target: Required reference property definition.

    Example:
        >>> ReferenceDefinition(required=True, min_count=1)

    Plain meaning: Rules for how references must be supplied.
    """

    required: bool = Field(default=False, description="Reference required flag")
    min_count: Optional[int] = Field(default=None, description="Minimum references")
    validation_policy: ValidationPolicy = Field(
        default="allow_existing_nonconforming",
        description="Reference validation policy",
    )
    form_policy: FormPolicy = Field(
        default="target_only", description="Reference form policy"
    )
    allowed: List[ReferenceTargetDefinition] = Field(
        default_factory=list, description="Allowed reference properties"
    )
    target: Optional[ReferenceTargetDefinition] = Field(
        default=None, description="Required reference property"
    )

    @field_validator("min_count", mode="before")
    @classmethod
    def _default_min_count(cls, value, info):
        if value is None and info.data.get("required") is True:
            return 1
        return value

    @field_validator("allowed", mode="before")
    @classmethod
    def _normalize_allowed(cls, value):
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value


class QualifierDefinition(BaseModel):
    """Define qualifier requirements for a field.

    Args:
        id: Qualifier identifier.
        label: Human-readable label.
        wikidata_property: Wikidata property ID.
        required: Whether the qualifier is required.
        min_count: Minimum number of qualifier values.
        max_count: Maximum number of qualifier values.
        value: Value definition for the qualifier.

    Example:
        >>> QualifierDefinition(
        ...     id="point_in_time",
        ...     label="Point in time",
        ...     wikidata_property="P585",
        ...     required=True,
        ...     value=ValueDefinition(type="time")
        ... )

    Plain meaning: A required or optional detail attached to a statement.
    """

    id: str = Field(..., description="Qualifier identifier")
    label: str = Field(..., description="Qualifier label")
    wikidata_property: str = Field(..., description="Wikidata property ID")
    required: bool = Field(default=False, description="Qualifier required flag")
    min_count: Optional[int] = Field(
        default=None, description="Minimum qualifier values"
    )
    max_count: Optional[int] = Field(
        default=None, description="Maximum qualifier values"
    )
    value: ValueDefinition = Field(..., description="Qualifier value definition")

    @field_validator("min_count", mode="before")
    @classmethod
    def _default_min_count(cls, value, info):
        if value is None and info.data.get("required") is True:
            return 1
        return value


class ProfileFieldDefinition(BaseModel):
    """Define a field in a YAML profile.

    Args:
        id: Field identifier.
        label: Human-readable label.
        wikidata_property: Wikidata property ID.
        type: Field type (currently only "statement").
        required: Whether the statement is required.
        max_count: Maximum number of statements (None = unlimited).
        validation_policy: Validation policy for existing items.
        form_policy: Form visibility policy.
        value: Value definition for the statement.
        qualifiers: Qualifier definitions.
        references: Reference definition.

    Example:
        >>> ProfileFieldDefinition(
        ...     id="instance_of",
        ...     label="Instance of",
        ...     wikidata_property="P31",
        ...     type="statement",
        ...     required=True,
        ...     value=ValueDefinition(type="item", fixed="Q5")
        ... )

    Plain meaning: A single statement definition in the profile.
    """

    id: str = Field(..., description="Field identifier")
    label: str = Field(..., description="Field label")
    wikidata_property: str = Field(..., description="Wikidata property ID")
    type: Literal["statement"] = Field(default="statement", description="Field type")
    required: bool = Field(default=False, description="Field required flag")
    max_count: Optional[int] = Field(default=None, description="Max statement count")
    validation_policy: ValidationPolicy = Field(
        default="allow_existing_nonconforming",
        description="Field validation policy",
    )
    form_policy: FormPolicy = Field(
        default="target_only", description="Field form policy"
    )
    value: ValueDefinition = Field(..., description="Value definition")
    qualifiers: List[QualifierDefinition] = Field(
        default_factory=list, description="Qualifier definitions"
    )
    references: Optional[ReferenceDefinition] = Field(
        default=None, description="Reference definition"
    )


class ProfileDefinition(BaseModel):
    """Define a YAML profile and its fields.

    Attributes:
        name: Profile name.
        description: Profile description.
        labels: Per-language label definitions.
        descriptions: Per-language description definitions.
        aliases: Per-language alias definitions.
        sitelinks: Sitelink definitions for wiki projects.
        fields: List of field definitions.

    Example:
        >>> ProfileDefinition(name="Example", description="Demo", fields=[])

    Plain meaning: The complete YAML profile definition.
    """

    name: str = Field(..., description="Profile name")
    description: str = Field(..., description="Profile description")
    labels: dict[str, MetadataDefinition] = Field(
        default_factory=dict, description="Per-language labels"
    )
    descriptions: dict[str, MetadataDefinition] = Field(
        default_factory=dict, description="Per-language descriptions"
    )
    aliases: dict[str, MetadataDefinition] = Field(
        default_factory=dict, description="Per-language aliases"
    )
    sitelinks: Optional[SitelinksDefinition] = Field(
        default=None, description="Sitelinks configuration"
    )
    fields: List[ProfileFieldDefinition] = Field(
        default_factory=list, description="Profile fields"
    )

    def field_by_id(self, field_id: str) -> Optional[ProfileFieldDefinition]:
        """Get a field definition by its identifier.

        Args:
            field_id: Field identifier to locate.

        Returns:
            Matching ProfileFieldDefinition or None if not found.

        Side effects:
            None.

        Example:
            >>> profile.field_by_id("instance_of")

        Plain meaning: Find a field configuration by its ID.
        """
        for field in self.fields:
            if field.id == field_id:
                return field
        return None

    def field_by_property(self, property_id: str) -> Optional[ProfileFieldDefinition]:
        """Get a field definition by its Wikidata property ID.

        Args:
            property_id: Wikidata property ID.

        Returns:
            Matching ProfileFieldDefinition or None if not found.

        Side effects:
            None.

        Example:
            >>> profile.field_by_property("P31")

        Plain meaning: Find the field that maps to a Wikidata property.
        """
        for field in self.fields:
            if field.wikidata_property == property_id:
                return field
        return None
