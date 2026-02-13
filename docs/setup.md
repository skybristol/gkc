# Setup and Orientation

This guide gets you ready to use GKC and points you to the Data Distillery Workflow. It is not a full tutorial yet; consider it a practical checklist plus a map to the next steps.

---

## 1. What You Need Before You Start

- A working Python environment (3.10+ recommended)
- Access to the data sources you want to ingest (CSV, JSON, API, RDF, etc.)
- Optional but recommended: credentials for Wikidata, Wikimedia Commons, Wikipedia, and OpenStreetMap

If you do not yet have credentials, you can still explore the workflow locally using dry runs.

---

## 2. Install the Package (Development Mode)

This project currently focuses on documentation and architecture. When the install workflow is finalized, this section will expand.

```bash
# Clone the repo
git clone https://github.com/skybristol/gkc.git
cd gkc

# Install dependencies (Poetry)
poetry install
```

---

## 3. Configure Credentials (Optional for Now)

If you intend to publish data to Wikidata, Wikimedia Commons, or OpenStreetMap, you will need credentials.

- [Authentication](authentication.md) walks through setting up API credentials.
- You can skip this for now if you are only running local transformations.

---

## 4. Choose a Starting Workflow

Most users begin with one of these paths:

### Path A: Link my data to Wikidata
- Mash Tun -> Fermentation -> Distillation -> Bottling
- Good for basic reconciliation and export

### Path B: Integrate multiple sources first
- Mash Tun (multiple sources) -> Fermentation -> Distillation -> Refinement -> Proofing -> Blending -> Bottling
- Good for multi-source consolidation

### Path C: Explore without publishing
- Mash Tun -> Fermentation -> Distillation
- Stop before output; focus on data cleaning and linking

---

## 5. Locate the Stage Docs

Start here for the full pipeline:
- [Pipeline Overview](pipeline_overview.md)

Then dive into each stage as needed:
- [Mash Tun](mash_tun.md)
- [Fermentation](fermentation.md)
- [Distillation](distillation.md)
- [Refinement](refinement.md)
- [Proofing](proofing.md)
- [Blending](blending.md)
- [Bottling](bottling.md)

---

## 6. What to Expect Next

As implementation work progresses, this setup guide will include:

- A quickstart example with real data
- Configuration file templates for each stage
- CLI usage patterns
- How to run a full pipeline end-to-end

---

## 7. Need More Context?

- [Background](background.md) explains the project goals and history
- [Authentication](authentication.md) covers credentials and access

If you are ready to implement or contribute, check the GitHub issues associated with each stage label.
