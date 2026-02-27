## Introduction

The **Global Knowledge Commons (GKC)** is a framework for understanding and working with structured knowledge that spans multiple open, public platforms. The initial design focuses on Wikidata, Wikimedia Commons, Wikipedia's infoboxes, and OpenStreetMap. Each of these systems captures part of the world, but none provides a unified, actionable representation of real‑world entities across platforms. The GKC fills that gap by defining cross‑platform entity models, transformation rules, and platform‑specific output structures that allow knowledge to move coherently through the entire ecosystem.

To make this underlying plumbing work a bit more compelling (and to have fun with things!), the GKC adopts the metaphor of a **data distillery**. Distillation provides a vivid way to describe how raw, heterogeneous inputs can be validated, transformed, refined, and ultimately bottled into the formats required by different Commons platforms. The metaphor is not decorative — it helps clarify the stages of the workflow, the roles of different components, and the logic behind the architecture. Mash Bills describe the structure of incoming data, Modulation Profiles guide how that data can be shaped, GKC Entity Profiles define the canonical form of an entity, and Barrel Profiles encode the exact structure required by downstream platforms. The Spirit Safe serves as the execution engine that validates and transforms data as it moves through these stages.

Together, the Global Knowledge Commons and the Data Distillery provide a coherent, extensible approach to building, maintaining, and publishing structured knowledge across the public open knowledge ecosystem.

----

## Profile Architecture
Each consituent system in the de facto Global Knowledge Commons (Wikidata, OpenStreetMap, etc.) has its own mechanism for validating data and checking conformance. As open public knowledge systems, everything is fairly open by default, generally relying on informal and sometimes more formal community consensus to decide what things should look like.

Wikidata has some of the more robust and prolific options where standardized schemas are concerned. The most developed and well used aspect of this comes with the [property constraints infrastructure](https://www.wikidata.org/wiki/Help:Property_constraints_portal). This is implemented with a combination of statements with what can be very detailed rules within Wikidata's Property suite and custom tools in Wikibase that flag non-conforming values. These are not strict rules but more notices to the community on areas for improvement.

The other mechanism Wikidata has in play are [Entity Schemas](https://www.wikidata.org/wiki/Wikidata:Schemas) comprised of published schemas in Shape Expression format. Entity Schemas are not widely adopted in any real way and have no impact on anything in Wikidata itself. The big thing that ShEx does in the Wikidata ecosystem that doesn't really exist anywhere else is identify and define logical entities that are comprised of a specific set of properties.

We experimented with both of these mechanisms in the development of gkc. We built a number of utility features for reading and validating against ShEx schemas. However, we ended up developing our own concept of a profile written in YAML to handle all the necessary specifications about what different types of "GKC Entities" should look like. These do take into account some aspects of property constraints that are actionable and useful at the point of data curation, including the development of "pick lists" of identifiers and labels for properties that need to link to another item.

Learn more about [building profiles](profiles.md).

---

### Spirit Safe
**Plain Meaning:** the execution and validation engine that ensures all Profiles behave as intended

The **Spirit Safe** is the operational heart of the GKC distillation pipeline. It is where Profiles become executable. Implemented through Pydantic models and custom validation logic, the Spirit Safe ensures that every transformation is correct, consistent, and aligned with both cross‑platform semantics and platform‑specific requirements.

The Spirit Safe provides:

- **Executable validation** of all Profile types, ensuring structural and semantic correctness.  
- **Controlled transformation** of raw input into fully realized GKC Entities.  
- **A consistent enforcement layer** that applies rules from Mash Bills, Modulation Profiles, and Barrel Profiles.  
- **A safe, inspectable environment** where data can be examined, corrected, or rejected before being bottled into Commons platforms.

In short:  
**The Spirit Safe is where the architecture becomes real — the place where Profiles are enforced, transformations occur, and data is prepared for publication.**

#### Future Trajectory
We are building the Spirit Safe concept as a distinct set of code and functionality within the gkc package for its initial phase. However, it will likely become a separate, fairly lightweight Python package and a profile repository where we can implement unique CI workflows that include review and approval steps and distinct versioning.

----

## Mash Tun
**Plain Meaning:** the interactive and programmatic workspace where raw data is clarified, aligned, and prepared for transformation into GKC Entities

The **Mash Tun** is the operational entry point of the Data Distillery. It is where raw inputs — whether harvested from Wikidata, extracted from spreadsheets or APIs, or supplied directly by a human user — are first gathered, clarified, and shaped into a form suitable for processing through the GKC architecture. The Mash Tun combines two equally important capabilities: **profile‑building** (understanding and harmonizing raw structures) and **data‑building** (collecting and preparing actual entity data).

The Mash Tun provides:

- **Programmatic ingestion and harmonization** of raw Wikidata items, properties, and Entity Schemas, using the `mash` module to extract structure, identify patterns, and align inputs toward the expectations of a GKC Entity Profile.  
- **Initial structural clarification**, performing early normalization, type inference, and field alignment to reduce ambiguity before deeper validation occurs.  
- **Interactive data‑entry experiences**, including CLI‑based prompts, notebook widget forms, and future web‑based interfaces, all driven by Modulation Profiles to ensure that user input is structured, complete, and semantically meaningful.  
- **A unified preparation layer** that supports both one‑off human edits and automated or semi‑automated batch processes, ensuring that all incoming data — regardless of source — enters the distillation pipeline in a predictable and inspectable form.  
- **A bridge between raw inputs and the Spirit Safe**, producing well‑formed intermediate representations that can be validated, transformed, and instantiated as GKC Entities.

In short:  
**The Mash Tun is where raw data meets structure — a workspace that harmonizes incoming material and guides human or automated contributors in preparing data for transformation into GKC Entities.**

### Bootstrapping the Knowledge Commons

The Global Knowledge Commons isn't actually a thing in any tangible sense. The term itself is something I just made up some time ago. But it is real insofar as the underlying components we are working with all contribute their bits and as much as we can improve the linkages between them.

Having landed on the use of Pydantic to provide deep actionable definitions for what data need to look like to be effectively distributed across The Commons, we built initial capabilities into the gkc package to go get the raw ingredients for GKC Entity Profiles, Modulation Profiles, and Barrel Profiles. These will be tuned and organized and then applied using some of the same tooling we built initially for a slightly different purpose.