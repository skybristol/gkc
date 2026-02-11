This document provides background and motivation on the Global Knowledge Commons (GKC) project.

# Background

I initially built a tool called [wbmaker](https://github.com/skybristol/wbmaker) when working with a Wikibase instance on the wikibase.cloud project. It provided a minimal abstraction on the [WikibaseIntegrator](https://github.com/LeMyst/WikibaseIntegrator) project, which is quite excellent for what it does. However, I'm also working toward a broader slate of open data contributions across multiple platforms.

I started the gkc project from the standpoint of Wikidata, with additional modules and functionality for other Wikimedia projects and OpenStreetMap to follow. I came at this from the perspective of entity schemas as the basis for source data processing into Wikidata items - essentially pushing toward schema-driven data development. While there are limitations in the shape expression (ShEx) approach to documenting schemas, it is what Wikidata (sort of) supports and offers a reasonable building block.

My initial focus in the project is on building an end-to-end workflow from source data about federally recognized tribes in the U.S. into representative Wikidata items and Wikipedia articles. At the outset, there were many missing tribes and a great deal of variation in how Wikidata items were documented and Wikipedia articles structured. The basic sequence of the workflow I started with to build this project includes:

* spreadsheet of source information (tribe names and aliases, properties about tribes, etc.) assembled through a variety or manual and code-assisted means
* [entity schema](https://www.wikidata.org/wiki/EntitySchema:E502) in ShExC (work in progress)
* conversion of entity schema into a JSON-based mapping of source data to target Wikidata item structure
* transformation of source data to Wikidata's JSON structure

# Why a new package

I've worked with both WikibaseIntegrator and pyWikiBot over the years. The WBI project is much more functional, and I've used it to create and modify thousands of items in both Wikidata and other Wikibase instances. For a variety of reasons, I kept ending up in a usage pattern with WBI where I was building one-off scripts that essentially mixed data, configuration, and processing logic all together. I wanted something for Wikidata that was based in entity schemas and clearly separated data mapping/configuration logic from processing.

At the end of the day, WBI is a Python wrapper on the Wikimedia APIs (mostly REST). It puts together a JSON packet aligned with what the REST API requires and submits it. What I've come up with here is a different approach toward the same end goal that works better with the data processing mode I work with. It may or may not prove useful for others.

I am also working to harmonize data and information about the same things between multiple best-fit technologies in the Commons and want a package that helps me make the connections and get content online in the most efficient ways possible. For instance, when contributing things like headquarters locations for tribes in the U.S., I want those showing up as both claims in Wikidata and as point features in OpenStreetMap with links between. When working on Wikipedia articles and filling out info boxes, I want to ensure alignment of facts with what's in Wikidata.

# Code writing with Copilot

I've been writing Python code for well over a decade as part of my professional career, but I'm a biologist and incidental data scientist and not a software engineer. Copilot and code-forward AI agents are the best thing to come along in my lifetime to help make up for that lacking skillset. I know what needs to be done and mostly how to go about it, but I've never been able to match the speed and efficiency in turning wishes and dreams (aka requirements) into working software that is robust, reliable, maintainable, and truly able to be used and contributed to by others. Now that we have these capabilities, I'm making good use of them here. A quick look through my GitHub account will show a marked distinction in the sophistication of this project.

You will see several documentation artifacts in this project that are the result of the conversational way I've built the code in VSCode with Microsoft's Copilot and various models/agents (mostly Claude Sonnet). I'm keeping those intact because they are both good documentation of the functionality built into the code and a curated view into the way the code is developing.

Before committing, merging, and publishing (to PyPi), I am iteratively working through real-world examples to ensure that the code all does exactly what it is designed to do. I have many projects in the works in the Commons, and so I can fully exercise all the features and functionality I'm building on real data. In most cases, I am incorporating them here into the project as examples. You will see examples show up in my [Indian Country Data](https://github.com/skybristol/indian_country_data) project where I mostly have workflows in notebooks.

I'm also giving the code itself a pretty thorough review as well as validating the end results. I'm learning a lot by looking carefully through what the code-writing models are doing and how they are approaching system architecture. Hands down, though, there's no way I could possibly generate this kind of high-quality code, tests, and feature documentation in anywhere near the time Copilot is able to get it done from a simple statement about what I want the end result to be and some iterative testing with real data.