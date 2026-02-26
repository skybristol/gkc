# Filling in lots of blanks

The following is a data development narrative for the Global Knowledge Commons and the Data Distillery capability we are building here. It focuses on the work of bringing overall content in the Commons up to date on the federally recognized Tribal Governments in the U.S.

## Background

I finally finished up my work the other day getting the last of the missing Alaska Native Tribes that are recognized by the U.S. federal government into Wikidata. I had to finally make a call that we needed entities representing official tribal governments even in those cases where a village name showed up in Wikidata via processing of U.S. Census data.

This means we now have 575 total items in Wikidata classified as [federally recognized Native American tribes in the United States](https://www.wikidata.org/wiki/Q7840353) with the recent addition of the [Lumbee Tribe of North Carolina](https://www.wikidata.org/wiki/Q113715714).

```sparql
SELECT ?tribe ?tribeLabel ?native_label ?url
?officeHeldByHeadOfGovernmentLabel ?officeHeldByHeadOfStateLabel
?hqLocationLabel
WHERE {
  ?tribe wdt:P31 wd:Q7840353 .
  OPTIONAL {
    ?tribe wdt:P1705 ?nativeLabel .
  }
  OPTIONAL {
    ?tribe wdt:P856 ?url .
  }
  OPTIONAL {
    ?tribe wdt:P1313 ?officeHeldByHeadOfGovernment .
  }
  OPTIONAL {
    ?tribe wdt:P1906 ?officeHeldByHeadOfGovernment .
  }
  OPTIONAL {
    ?tribe wdt:P159 ?hqLocation .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

Now the challenge is digging into filling in the rest of the blanks in the still developing [Entity Schema for U.S. tribes](https://www.wikidata.org/wiki/EntitySchema:E502).

## What's important?

I included the query that I did above, because it highlights some of the major attributes I am working to fill in this work that is geared very much toward bolstering and explaining Tribal sovereighnty. Tribes fill a unique niche in U.S. politics, as sovereign nation states within the boundaries of the Unites States. Tribal sovereignty has been upheld time and time again as U.S. courts, all the way to the Supreme Court, recognizes that tribes existed as cohesive governmental/political entities well before the invention of the United States. We don't always win, but when the law is followed, we do.

By designing the schema for these tribal governments on a similar footing with other sovereign states, we can hopefully help to fill in some really important gaps in the U.S. education system that constantly has tribal leaders today having to provide basic education to government officialsa and politicians in other governments (Federal, State, local). For tribal citizens, there is often a whole lot going on in tribal politics. This may be especially true in larger tribes with many government services at stake, but even small villages with a couple dozen citizens are sovereign states deserving of an equal footing within the Global Knowledge Commons.

## Current state

Right now, if you run the query above (or go look at the [results](https://w.wiki/H$8j), you'll see a whole lot of missing values on these few basic fields. Starting right at the beginning, very few official web sites for tribal governments have been sussed out and recorded in Wikidata. Once we have those, though, we can usually track down things like whether the tribe refers to their head of government as Principle Chief, Council President, or any number of other titles. We have to create an item for the office, and then we can start building in logically flowing links like the person who holds that office now or past office holders who perhaps should also be recorded.

The most comprehensive source maintained anywhere for tribal leaders is the Bureau of Indian Affairs' "Tribal Leaders Directory" that has been maintained for many years. However, this information is often horribly out of date for smaller tribes (who sometimes don't give two shits about the BIA), and it is completely lacking in any kind of context like the title of the office itself. The existence of the office(s) held by head of government/state, and represented legitimately in the digital realm, are arguably a hell of a lot more important from a tribal sovereignty standpoint than the current office holder.

## How to go about it

This is the kind of case where having a form tuned to aid in developing this concept makes good sense. While I could also build a simple spreadsheet, spend time filling it out, and then run a batch process, it's also kind of nice to just sit down and work on one particular line of thinking and research when I can, get data on board, and make incremental progress.

Another similar case will be filling out headquarters locations. That one would be interesting in that we will be populating a claim/qualifiers/references in Wikidata but also getting these locations laid out in Open Street Maps, so it scratches the "distributing information to multiple parts of the Commons" itch.

In reality, a data curator is likely to encounter and need to work on several different pieces of information at the same time that need to be organized and distributed out across platforms. I might first track down a web site, meaning I need to put an official URL statement on the item representing the tribe/tribal government and state something about how I found it in a reference. From the website, I'll hopefully get a headquarters address that I can go check on a map. That's going to get me a geospatial coordinate that can find its way into both Wikidata and OSM. I'll hopefull track down information about the government, how they are organized, and who's involved.

From this exploration, I'm going to be developing lots of facts, some of which will require me to instantiate entire new items. There are lots of ways to accomplish this, but some type of fill-in-the-right-blanks form and have some software do the rest is what we're working to build in the gkc package. I'm also going to have just about everything I need to not only build structured data in Wikidata/OSM, but organize the appropriate bits of that into Wikipedia templates and do some writing on Wikipedia articles.

## How the gkc package can support this work

I initially worked up a Python notebook exploring the use of Pydantic as a admittedly Python-specific framework for encoding more of the useful details about what relatively complex data, bound for multiple systems and parts of systems should look like. We developed the idea of multi-profile framework, built within the metaphor-derived context of a Spirit Safe that will help validate and coerce data into the shapes we need across platforms.

The central figure in the "Profile Pantheon" is the GKC Entity Profile. These are the types of things that should really all have published Entity Schemas in the Wikidata ecosystem, and we may well get more of those filled out. However, ShEx falls short on a number of fronts and is not yet (and likely not to become) a full part of making Wikidata do what it does. Both a tribal government in the U.S. and an office held by head of government should be encoded into GKC Entity Profiles.

We also are developing the idea of Modulation Profiles, one or more of which go along with an Entity Profile. They spell out what exactly can be modulated (input, created, edited, etc.) for entities. As we can see in this use case, a Modulation Profile may also need to contain elements associated with more than one entity with content distributed across multiple platforms.

Mash Bills and Barrel Profiles form the other two ends of the input/output spectrum. Mash Bills describe, also with Pydantic modeling, what comes from a given data source like a spreadsheet or an API. Barrel Profiles specify exactly what the data need to look like that are getting barrelled and shipped to Wikidata, Wikimedia Commons, OSM, Wikipedia templates, etc.

In the Python notebook, we sketched out one specific example of a mult-part profile. The entity we used was a U.S. Federal Register notice, prompted by my need to create an item representing the latest 2026 listing in order to use it as a reference for re-classing the Lumbee a federally recognized tribe. We had the basics of an Entity Profile, a Modulation Profile, and a Barrel Profile all in one place. We added some code that used the details in these to generate an input form using ipywidgets. This followed some previous work where we supported a similar workflow using a command line and answering prompts.

We're now at the point where we need to formalize this notional architecture to build out the parts of the Spirit Safe that will house, manage, and provision the profiles. We think we'll move that to its own Python package and repository within the Data Distillery ecosystem, but we'll start within the gkc package itself to prove things out.