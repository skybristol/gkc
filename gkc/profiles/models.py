"""
Profile models for YAML-defined SpiritSafe entity profiles.

These Pydantic models define the internal representation of YAML profile
structures, covering fields, qualifiers, references, and value constraints.

Plain meaning: The typed Python shape of a YAML profile.
"""

from __future__ import annotations

import re
from typing import List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

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
WIKIDATA_ENTITY_PREFIX = "https://www.wikidata.org/entity/"
_PID_PATTERN = re.compile(r"^P\d+$", re.IGNORECASE)


def _extract_property_id_from_identifier(identifier: str) -> Optional[str]:
    value = identifier.strip()
    if _PID_PATTERN.match(value):
        return value.upper()
    segment = value.rstrip("/").split("/")[-1]
    if _PID_PATTERN.match(segment):
        return segment.upper()
    return None


def _resolve_property_id_from_io_map(
    io_map: List["IOMapEntry"],
    *,
    system_prefix: Optional[str] = None,
) -> Optional[str]:
    for route in io_map:
        if not route.to:
            continue
        if system_prefix and not route.to.startswith(system_prefix):
            continue
        property_id = _extract_property_id_from_identifier(route.to)
        if property_id:
            return property_id
    return None


class IOMapEntry(BaseModel):
    """Define one directional IO routing entry.

    Plain meaning: One inbound (`from`) or outbound (`to`) mapping route.
    """

    to: Optional[str] = Field(default=None, description="Outbound route identifier")
    from_: Optional[str] = Field(
        default=None,
        alias="from",
        description="Inbound route identifier",
    )
    value_transform: Optional[str] = Field(
        default=None,
        description="Resolver key/identifier for route value transformation",
    )

    @model_validator(mode="after")
    def _validate_direction(self):
        has_to = bool(self.to)
        has_from = bool(self.from_)
        if has_to == has_from:
            raise ValueError("IOMapEntry must define exactly one of 'to' or 'from'")
        return self


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
        io_map: Directional I/O mapping routes.
        type: Datatype for the reference value.
        label: Human-readable label.
        input_prompt: Optional short prompt shown in data-entry UIs.
        description: Optional description.
        value_source: Optional value source hint (e.g., "statement_value").
        allowed_items: Optional choice list for allowed values.

    Example:
        >>> ReferenceTargetDefinition(
        ...     id="stated_in",
        ...     io_map=[{"to": "https://www.wikidata.org/entity/P248"}],
        ...     type="item",
        ...     label="Stated in"
        ... )

    Plain meaning: A reference property allowed or required on a statement.
    """

    id: str = Field(..., description="Reference entry identifier")
    io_map: List[IOMapEntry] = Field(..., description="Directional IO map entries")
    type: ValueType = Field(..., description="Reference value datatype")
    label: str = Field(..., description="Reference entry label")
    input_prompt: str = Field(
        default="", description="Short prompt shown in input widgets"
    )
    description: str = Field(default="", description="Reference entry description")
    value_source: Optional[str] = Field(default=None, description="Value source hint")
    allowed_items: Optional[ChoiceListSpec] = Field(
        default=None, description="Optional choice list"
    )

    def property_id_for_system(self, system_prefix: str) -> Optional[str]:
        return _resolve_property_id_from_io_map(
            self.io_map, system_prefix=system_prefix
        )

    def property_id(self) -> Optional[str]:
        return _resolve_property_id_from_io_map(self.io_map)

    def wikidata_property_id(self) -> Optional[str]:
        return self.property_id_for_system(WIKIDATA_ENTITY_PREFIX)


class MetadataDefinition(BaseModel):
    """Define metadata for a single language (labels, descriptions, aliases, sitelinks).

    Args:
        label: Field label for curation.
        input_prompt: Short prompt shown in data-entry fields.
        required: Whether this language variant is required.
        guidance: Curator guidance text.

    Example:
        >>> MetadataDefinition(
        ...     label="Label",
        ...     input_prompt="Enter the primary English name",
        ...     required=True,
        ...     guidance="Use the tribe's self-designation"
        ... )

    Plain meaning: A single language's metadata definition with curator guidance.
    """

    label: str = Field(..., description="Metadata field label")
    input_prompt: str = Field(
        default="", description="Short prompt shown in input widgets"
    )
    required: bool = Field(default=False, description="Is this variant required?")
    guidance: str = Field(default="", description="Curator guidance text")


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
        input_prompt: Optional short prompt for reference entry guidance.
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
    input_prompt: str = Field(
        default="", description="Short prompt shown when collecting references"
    )
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
        input_prompt: Optional short prompt shown in data-entry UIs.
        io_map: Directional I/O mapping routes.
        required: Whether the qualifier is required.
        min_count: Minimum number of qualifier values.
        max_count: Maximum number of qualifier values.
        value: Value definition for the qualifier.

    Example:
        >>> QualifierDefinition(
        ...     id="point_in_time",
        ...     label="Point in time",
        ...     io_map=[{"to": "https://www.wikidata.org/entity/P585"}],
        ...     required=True,
        ...     value=ValueDefinition(type="time")
        ... )

    Plain meaning: A required or optional detail attached to a statement.
    """

    id: str = Field(..., description="Qualifier identifier")
    label: str = Field(..., description="Qualifier label")
    input_prompt: str = Field(
        default="", description="Short prompt shown in input widgets"
    )
    io_map: List[IOMapEntry] = Field(..., description="Directional IO map entries")
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

    def property_id_for_system(self, system_prefix: str) -> Optional[str]:
        return _resolve_property_id_from_io_map(
            self.io_map, system_prefix=system_prefix
        )

    def property_id(self) -> Optional[str]:
        return _resolve_property_id_from_io_map(self.io_map)

    def wikidata_property_id(self) -> Optional[str]:
        return self.property_id_for_system(WIKIDATA_ENTITY_PREFIX)


class LinkageRelationship(BaseModel):
    """Define the relationship type between profiles.

    Args:
        type: Relationship type identifier (e.g., "office_of_head_of_state").
        direction: Relationship directionality (unidirectional or bidirectional).
        reverse_statement_hint: Optional statement ID hint for reverse traversal.

    Example:
        >>> LinkageRelationship(
        ...     type="office_of_head_of_state",
        ...     direction="bidirectional",
        ...     reverse_statement_hint="applies_to_jurisdiction"
        ... )

    Plain meaning: How this statement connects to another profile's entity.
    """

    type: str = Field(..., description="Relationship type identifier")
    direction: Literal["unidirectional", "bidirectional"] = Field(
        ..., description="Relationship directionality"
    )
    reverse_statement_hint: Optional[str] = Field(
        default=None, description="Statement ID hint for reverse traversal"
    )


class LinkageCardinality(BaseModel):
    """Define cardinality constraints for linked entities.

    Args:
        min: Minimum required linked entities (0 = optional).
        max: Maximum allowed linked entities.

    Example:
        >>> LinkageCardinality(min=0, max=1)

    Plain meaning: How many linked entities are required or allowed.
    """

    min: int = Field(default=0, ge=0, description="Minimum linked entities")
    max: int = Field(default=1, ge=1, description="Maximum linked entities")

    @model_validator(mode="after")
    def _validate_min_max(self):
        if self.min > self.max:
            raise ValueError(
                f"Cardinality min ({self.min}) cannot exceed max ({self.max})"
            )
        return self


class LinkageWorkflowPolicy(BaseModel):
    """Define allowed workflow actions for linked entities.

    Args:
        create: Whether new linked entities can be created.
        select_existing: Whether existing entities can be selected.

    Example:
        >>> LinkageWorkflowPolicy(create=True, select_existing=True)
        >>> LinkageWorkflowPolicy(create="allowed", select_existing="allowed")

    Plain meaning: What curator actions are allowed for this link.
    """

    create: bool = Field(
        default=False,
        description="Allow creating new linked entities",
    )
    select_existing: bool = Field(
        default=True, description="Allow selecting existing entities"
    )

    @field_validator("create", "select_existing", mode="before")
    @classmethod
    def _normalize_policy(cls, value):
        """Convert 'allowed'/'disallowed' strings to boolean."""
        if isinstance(value, str):
            if value.lower() == "allowed":
                return True
            elif value.lower() == "disallowed":
                return False
            else:
                raise ValueError(f"Invalid workflow policy value: {value}")
        return value


class LinkageTraversal(BaseModel):
    """Define graph traversal depth for linked entities.

    Args:
        max_depth: Maximum traversal depth from source entity.

    Example:
        >>> LinkageTraversal(max_depth=1)

    Plain meaning: How far to traverse when loading related entities.
    """

    max_depth: int = Field(default=1, ge=1, description="Maximum traversal depth")


class StatementLinkage(BaseModel):
    """Define cross-profile linkage metadata for a statement.

    Args:
        target_profile: Profile name that this statement links to.
        relationship: Relationship metadata.
        cardinality: Cardinality constraints.
        workflow_policy: Workflow action permissions.
        traversal: Graph traversal configuration.

    Example:
        >>> StatementLinkage(
        ...     target_profile="OfficeHeldByHeadOfState",
        ...     relationship=LinkageRelationship(
        ...         type="office_of_head_of_state",
        ...         direction="bidirectional"
        ...     ),
        ...     cardinality=LinkageCardinality(min=0, max=1),
        ...     workflow_policy=LinkageWorkflowPolicy(create=True),
        ...     traversal=LinkageTraversal(max_depth=1)
        ... )

    Plain meaning: Complete linkage specification for multi-entity workflows.
    """

    target_profile: str = Field(..., description="Target profile name")
    relationship: LinkageRelationship = Field(..., description="Relationship metadata")
    cardinality: LinkageCardinality = Field(..., description="Cardinality constraints")
    workflow_policy: LinkageWorkflowPolicy = Field(
        ..., description="Workflow action permissions"
    )
    traversal: LinkageTraversal = Field(..., description="Traversal configuration")


class ProfileFieldDefinition(BaseModel):
    """Define a field in a YAML profile.

    Args:
        id: Field identifier.
        label: Human-readable label.
        input_prompt: Optional short prompt shown in data-entry UIs.
        io_map: Directional I/O mapping routes.
        type: Field type (currently only "statement").
        required: Whether the statement is required.
        max_count: Maximum number of statements (None = unlimited).
        validation_policy: Validation policy for existing items.
        form_policy: Form visibility policy.
        guidance: Optional curator guidance text.
        entity_profile: Optional linked entity profile name.
        linkage: Optional cross-profile linkage metadata.
        value: Value definition for the statement.
        qualifiers: Qualifier definitions.
        references: Reference definition.

    Example:
        >>> ProfileFieldDefinition(
        ...     id="instance_of",
        ...     label="Instance of",
        ...     io_map=[{"to": "https://www.wikidata.org/entity/P31"}],
        ...     type="statement",
        ...     required=True,
        ...     value=ValueDefinition(type="item", fixed="Q5")
        ... )

    Plain meaning: A single statement definition in the profile.
    """

    id: str = Field(..., description="Field identifier")
    label: str = Field(..., description="Field label")
    input_prompt: str = Field(
        default="", description="Short prompt shown in input widgets"
    )
    io_map: List[IOMapEntry] = Field(..., description="Directional IO map entries")
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
    guidance: str = Field(default="", description="Curator guidance text")
    entity_profile: Optional[str] = Field(
        default=None, description="Linked entity profile name"
    )
    linkage: Optional[StatementLinkage] = Field(
        default=None, description="Cross-profile linkage metadata"
    )
    value: ValueDefinition = Field(..., description="Value definition")
    qualifiers: List[QualifierDefinition] = Field(
        default_factory=list, description="Qualifier definitions"
    )
    references: Optional[ReferenceDefinition] = Field(
        default=None, description="Reference definition"
    )

    def property_id_for_system(self, system_prefix: str) -> Optional[str]:
        return _resolve_property_id_from_io_map(
            self.io_map, system_prefix=system_prefix
        )

    def property_id(self) -> Optional[str]:
        return _resolve_property_id_from_io_map(self.io_map)

    def wikidata_property_id(self) -> Optional[str]:
        return self.property_id_for_system(WIKIDATA_ENTITY_PREFIX)


class ProfileDefinition(BaseModel):
    """Define a YAML profile and its statements.

    Attributes:
        name: Profile name.
        description: Profile description.
        labels: Per-language label definitions.
        descriptions: Per-language description definitions.
        aliases: Per-language alias definitions.
        sitelinks: Sitelink definitions for wiki projects.
        statements: List of statement definitions.

    Example:
        >>> ProfileDefinition(name="Example", description="Demo", statements=[])

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
    statements: List[ProfileFieldDefinition] = Field(
        default_factory=list,
        validation_alias=AliasChoices("statements", "fields"),
        serialization_alias="statements",
        description="Profile statements",
    )

    @property
    def fields(self) -> List[ProfileFieldDefinition]:
        """Backward-compatible alias for statements."""
        return self.statements

    def statement_by_id(self, statement_id: str) -> Optional[ProfileFieldDefinition]:
        """Get a statement definition by its identifier.

        Args:
            statement_id: Statement identifier to locate.

        Returns:
            Matching ProfileFieldDefinition or None if not found.

        Side effects:
            None.

        Example:
            >>> profile.statement_by_id("instance_of")

        Plain meaning: Find a statement configuration by its ID.
        """
        for statement in self.statements:
            if statement.id == statement_id:
                return statement
        return None

    def statement_by_property(
        self, property_id: str
    ) -> Optional[ProfileFieldDefinition]:
        """Get a statement definition by property ID from configured routes.

        Args:
            property_id: Property ID (e.g., ``P31``).

        Returns:
            Matching ProfileFieldDefinition or None if not found.

        Side effects:
            None.

        Example:
            >>> profile.statement_by_property("P31")

        Plain meaning: Find the statement that maps to a property ID.
        """
        for statement in self.statements:
            if statement.property_id() == property_id.upper():
                return statement
        return None

    def field_by_id(self, field_id: str) -> Optional[ProfileFieldDefinition]:
        """Backward-compatible alias for statement_by_id."""
        return self.statement_by_id(field_id)

    def field_by_property(self, property_id: str) -> Optional[ProfileFieldDefinition]:
        """Backward-compatible alias for statement_by_property."""
        return self.statement_by_property(property_id)

    def get_statement_linkages(self) -> List[ProfileFieldDefinition]:
        """Get all statements that have linkage metadata.

        Returns:
            List of ProfileFieldDefinition instances with linkage metadata.

        Side effects:
            None.

        Example:
            >>> linked_statements = profile.get_statement_linkages()
            >>> for stmt in linked_statements:
            ...     print(stmt.linkage.target_profile)

        Plain meaning: Find all statements that link to other profiles.
        """
        return [stmt for stmt in self.statements if stmt.linkage is not None]

    def get_linked_profile_names(self) -> List[str]:
        """Get a list of all profile names linked from this profile.

        Returns:
            List of unique profile names referenced in linkage metadata.

        Side effects:
            None.

        Example:
            >>> profile.get_linked_profile_names()
            ['OfficeHeldByHeadOfState']

        Plain meaning: Find all other profiles this one can link to.
        """
        names = {stmt.linkage.target_profile for stmt in self.get_statement_linkages()}
        return sorted(names)

    def get_link_definition(self, target_profile: str) -> Optional[StatementLinkage]:
        """Get linkage metadata for a specific target profile.

        Args:
            target_profile: Name of the target profile to find linkage for.

        Returns:
            StatementLinkage instance or None if no linkage to that profile.

        Side effects:
            None.

        Example:
            >>> linkage = profile.get_link_definition("OfficeHeldByHeadOfState")
            >>> linkage.cardinality.max
            1

        Plain meaning: Get the linkage rules for a specific connected profile.
        """
        for stmt in self.get_statement_linkages():
            if stmt.linkage.target_profile == target_profile:
                return stmt.linkage
        return None
