# Entity Classes

The following SPARQL query is useful in developing a basic understanding of the entity class structure.

```sparql
PREFIX wd: <https://datadistillery.wikibase.cloud/entity/>
PREFIX wdt: <https://datadistillery.wikibase.cloud/prop/direct/>

SELECT ?item ?itemLabel ?itemDescription
WHERE {
  ?item wdt:P2* wd:Q1 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

# GKC Entity Profile

The primary entity we are building here is the "GKC Entity Profile" (Q3). These will always be `P1 == Q3` items. We are working with two prototypes in the development cycle.

- [Tribal Government in the United States](https://datadistillery.wikibase.cloud/wiki/Item:Q4)
- [Office Held by Head of Government](https://datadistillery.wikibase.cloud/wiki/Item:Q39)

## Wikibase Identification

Each profile will have a label (mul), label (en), and description (en) as identification within the Wikibase. Multilingual labeling will enable things like the GKC Wizard to present the profiles for users in different languages.

## Yielded Entity Identification

Each profile must have the following statements built with monolingual text properties to enable guidance information for users.

- [label prompt](https://datadistillery.wikibase.cloud/entity/P188)
- [label guidance](https://datadistillery.wikibase.cloud/entity/P185)
- [description prompt](https://datadistillery.wikibase.cloud/entity/P189)
- [description guidance](https://datadistillery.wikibase.cloud/entity/P186)
- [alias prompt](https://datadistillery.wikibase.cloud/entity/P190)
- [alias guidance](https://datadistillery.wikibase.cloud/entity/P187)

A valid profile must have these statements and they must include a `mul` language code value as the primary language instantiation. Additional statements in languages may be present. If all entity profile statements are available in a language beyond `mul`, then the profile is "multilingual compliant."

## Entity Profile Statements

A statement here is patterned on the same structure as a Wikidata statement, but statements will also eventually link to other knowledge systems. Statements are included in the profile via the `has statement` property (P157). They always link to an item of class, `GKC Entity Statement` (Q5).

### Statement Type

`GKC Entity Statement` items all have a `statement type` (P194) claim linking to a property classed as `Wikibase Property Template` (Q44). This specification essentially lays out the "primitive data type" (first order of validation/coercion) rules for statement values. The `statement type` always encodes a Wikibase datatype. The label (`mul` and `en`) values do correspond to the string identifier used in Wikibase (e.g., `wikibase-item`) and the property datatype in the DD Wikibase.

`statement type` properties will also include an `error message` statement in `mul` and potentially other languages. This is used for providing guidance when "primitive data type" validation fails.  

### Links to Other Knowledge Systems

A primary role of GKC Entity Statements is to enable distribution of data out to "Global Knowledge Commons Partners" - Wikidata, Wikipedia, Wikimedia Commons, OpenStreetMap, and eventually others. This is encoded at the statement level through specific properties that shape the linkage.

GKC Entity Statement items generally align with a Wikidata property ID. They link to a Wikidata property via the `to wikidata` property (P5), which is a URL type property. For instance:

- `instance of` (Q16) > `to wikidata` (P5) > http://www.wikidata.org/entity/P31

This establishes one aspect of the `io_map` concept for the JSON Entity Profile/Curation Packet translation.

### Number of statements

A core underlying philosophy for the profile structure is that all statements and statement elements (qualifiers, references) specified in the profiles are required/expected. We "accept" entries that are not complete and point out explicit areas that can be improved. This follows the overall Wikidata/Wikipedia/OpenStreetMap philosophy and practice.

The DD Wikibase uses the `max count` property (P182) to declare an intent in a qualifier on a statement. The special `no value` value translates to "1+" while an explicit `+n` value means that exact number of statements is expected.

### Statement Values

I've adjusted the structure and property language for parity between value, reference, and qualifier specifications. Values are specified using a `has value` (P161) qualifier that links to an item in the Wikibase with further specifications.

`has value` will show up within `has statement` qualifiers for a `GKC Entity Profile` and as a claim on `GKC Entity Statement` items. If present in both places, the `has value` qualifier within profiles overrides a statement at the item level.

So far, the following options are being used for `has value` claims:

- Link to an item classified as a `Wikidata Entity` (Q52) indicates that a very specific value is expected. Those items will have a `same as` (P212) claim linking to a Wikidata QID value in a URL (e.g., http://www.wikidata.org/entity/Q7840353). This is what now accomplishes the "fixed value" concept we had been looking at previously.
- `has value` may also link to another item classed as a `GKC Entity Profile`. This accomplishes what we had previously indicated with the `linked profile` property. It essentially means that the property value can be fulfilled by creating a new entity using that profile or by an existing entity that conforms with that profile.
- `has value` may also link to another item classed as a `GKC Value List` (Q7). Our goal is to have a value list backing any statement that should link to a Wikidata item such that we provide a reasonable pick list in UI capabilities and for bulk operators. (See discussion on value lists below)

#### Default Value

A `GKC Entity Statement` item may have a `default value` (P202) claim with a URL linking to an identifier value that should be used as a default. This claim will have a `default label` (P203) qualifier with a string value to be used with the identifier when needing to present human-readable content.

For instance:

```
language of work or name > default value (http://www.wikidata.org/entity/Q1860) > default label (English)
```

#### Value Lists

The list of allowed values property constraint in Wikidata is one of the most important and useful constructs in the system, but it can be difficult to fulfill. For the Data Distillery/GKC work, we are striving to provide an data curator experience that is better than the Wikidata UI because it is more tightly focused with an ability to deliver a custom form for any entity type. One of the primary usability challenges we have to meet is the ability to quickly choose a target object for a `wikibase-item` claim with type-ahead efficiency. Cached and optimized value lists are how we are working to achieve this.

Items classed as `GKC Value List` (Q7) will have a SPARQL query in their discussion page meant to be operated on either the Wikidata Query Service or [Qlever](https://qlever.dev/wikidata/). We are developing the cache hydration technology to run these queries and build out cached value lists in the SpiritSafe repo.

`GKC Value List` items may be referenced as the target object of a `has statement` > `has value` qualfier within a `GKC Entity Profile` item. They may also be referenced using a `has value` claim on a `GKC Entity Statement` item. In the latter case, these `has value` claims must always include a `applies to profile` (P205) qualifier linking to the applicable profile. Any given `has value` statement at a `GKC Entity Statement` level that is backed by a value list may include many different lists that are applicable in different profiles.

##### Profiles and Value Lists

Most if not all `GKC Entity Profile` items will also also be classed as `GKC Value List` and include a SPARQL query that provides an the necessary logic to pull all those items. This will almost always correspond directly to the specifications for `instance of` classification on the items. This supports behavior in a wizard interface of presenting users with a type-ahead list for existing values or generating a new entity based on the profile.

##### Refresh Policy

Items classed as `GKC Value List` must have a statement using the `refresh policy` property (P210) linking to an item representing the refresh rate or method. Current values are all `manual refresh` (Q50) at this stage of development. We will end up determining if other refresh policies are needed and will implement a scheduler of some kind in the SpiritSafe repo.

#### Guidance Statements

Similar to labels/aliases/descriptions, statements have the following monolingual text guidance claims:

- [statement prompt](https://datadistillery.wikibase.cloud/entity/P171)
- [statement guidance](https://datadistillery.wikibase.cloud/entity/P169)

Statements may also have the following additional guidance:

- [consequences message](https://datadistillery.wikibase.cloud/entity/P170)
- [error message](https://datadistillery.wikibase.cloud/entity/P168)

Any or all of these guidance statements may be used at the claim level as qualifiers for a `has statement` claim in a `GKC Entity Profile` or at the underlying `GKC Entity Statement` level as an independent claim. In practice, the qualifier level is used first because it will provide more detailed contextual information.

### Statement Qualifiers

Qualifiers are specified for `has statement` claims in profiles using `has qualifier` (P158) qualifiers. Qualifiers are statements (about a statement) like any other statements. They link to items classed as `GKC Entity Statement` just like `has statement` claims do and all of the same rules and configuration details apply.

### Statement References

References are now specified for `has statement` claims in profiles using `has reference` (P211) qualifiers. Similar to `has qualifier`, `has reference` now links to a `GKC Entity Statement` item designating the type of reference expected. When multiple `has reference` qualifiers are included for a `has statement` claim, the rule is always an `or` relationship between these - at least one reference using any of the provided `GKC Entity Statement` types is expected.