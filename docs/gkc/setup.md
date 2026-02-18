# Setup and Orientation

This guide gets you ready to use GKC and points you to the Data Distillery Workflow. It is not a full tutorial yet; consider it a practical checklist plus a map to the next steps.

---

## 1. What You Need Before You Start

- A working Python environment (3.10+ recommended)
- Access to the data sources you want to ingest (CSV, JSON, API, RDF, etc.)
- Optional but recommended: credentials for Wikidata, Wikimedia Commons, Wikipedia, and OpenStreetMap

If you do not yet have credentials, you can still explore the workflow locally using dry runs.

---

## 2. Install the Package

### Option A: Install from PyPI (Recommended)

```bash
pip install gkc
```

### Option B: Install from Source (Development Mode)

If you want to contribute or work with the latest development version:

```bash
# Clone the repo
git clone https://github.com/skybristol/gkc.git
cd gkc

# Install dependencies (Poetry)
poetry install
```

---

## 3. Configure Language Settings (Optional)

GKC provides nominal support for multilingual data processing. Right now, this only includes filtering Wikidata labels, descriptions, and aliases. By default, the package uses English (`"en"`), but you can configure it to work with other languages.

### Setting the Language Configuration

```python
import gkc

# Use a single language (default: "en")
gkc.set_languages("en")

# Use multiple languages
gkc.set_languages(["en", "es", "fr"])

# Work with all available languages
gkc.set_languages("all")

# Check current language setting
current = gkc.get_languages()
print(current)  # Returns: "en" or ["en", "es", "fr"] or "all"
```

**When to configure:**
- Before loading Wikidata items if you need labels in specific languages
- When working with multilingual datasets
- When you want to filter or display data in languages other than English

**Plain meaning:** Tell GKC which languages you want to work with so it can filter and display labels appropriately.

---

## 4. Configure Credentials (Optional for Now)

If you intend to publish data to Wikidata, Wikimedia Commons, or OpenStreetMap, you will need credentials.

- [Authentication](authentication.md) walks through setting up API credentials.
- You can skip this for now if you are only running local transformations.

---

## 5. Choose a Starting Workflow

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

## 6. Locate the Stage Docs

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

## 7. What to Expect Next

As implementation work progresses, this setup guide will continue to expand with:

- A quickstart example with real data
- Configuration file templates for each stage
- CLI usage patterns
- How to run a full pipeline end-to-end

Check back as new releases are published to PyPI.

---

## 8. Need More Context?

- [Background](background.md) explains the project goals and history
- [Authentication](authentication.md) covers credentials and access

If you are ready to implement or contribute, check the GitHub issues associated with each stage label.
