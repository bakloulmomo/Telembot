# Progress: Database and Ingestion

> What is built and verified so far. Branch: `ingestion-db-embeddings`.
> Design: [7_rag_architecture.md](./7_rag_architecture.md). How to run: [ingest/README.md](../ingest/README.md).

---

## 1. Status

| Part | Status |
|---|---|
| Database schema (`products`, `chunks`) | Done |
| Manual sections and figures in the database | Done, all 22 manuals |
| Embeddings | Done, all sections |
| Product specifications (`products.specs`) | Done, all 22 products |
| Verification script | Done, all checks pass |
| RAG engine (question → answer) | **Not started: next step** |
| Product summaries written by an LLM | Not started (optional) |
| Merge with the `backend-api` branch | Not done |

---

## 2. What is in the database

PostgreSQL on Supabase, with the `pgvector` extension.

| | Count |
|---|---|
| Products | 22 (13 robots, 9 accessories) |
| Sections (`chunks` rows) | 922: English 347, German 305, Italian 270 |
| Figures attached to sections | 476, the same as the image files in the dataset |
| Figures with a label list | 59 |
| Embeddings | 922, model `text-embedding-3-small` (1536 dimensions) |
| Spec values | 223 on 22 standard parameters, 221 marked `reviewed` |

### `products` (one row per product)

Name, kind (robot or accessory), family (delivery, cleaning, industrial, charging, docking, call system, water), aliases and model codes, languages, related products, the overview paragraph quoted from the manual, and `specs`.

### `chunks` (one row per numbered manual section, per language)

The section text as printed, its section number, printed page and PDF page, a section kind (safety, specs, usage, troubleshooting, compliance, …), the figures that appear in it (with their printed labels), the embedding, and a keyword-search index.

### `products.specs`

Each parameter holds a list of entries, for example the T300 battery life:

```json
"battery_runtime": [
  {"raw": "12 h (None load)", "condition": "None load", "op": "=", "min": 12, "max": 12, "unit": "h",
   "label": "Battery life", "section": "2.4", "page": 3, "pdf_page": 4, "source": "auto", "reviewed": true},
  {"raw": "6 h (Max. load)", "condition": "Max. load", "op": "=", "min": 6, "max": 6, "unit": "h",
   "label": "Battery life", "section": "2.4", "page": 3, "pdf_page": 4, "source": "auto", "reviewed": true}
]
```

- `raw` is the value as printed; the answer must quote this.
- `min` / `max` are numbers in one unit per parameter (dimensions use `values`: length, width, height in mm).
- `variant` and `condition` say what a value applies to (a model code, a mode, "unloaded").
- Table rows that are not a standard parameter are kept under `_unmapped`.
- `reviewed: true` means the value was parsed completely or written by hand, **and** its text is found word for word in the manual. Filters and rankings must use only reviewed entries.

---

## 3. How it was built

| Step | Script | What it does |
|---|---|---|
| 1 | `ingest/load.py` | Creates the tables. Loads the products and one row per manual section, with pages and figures |
| 2 | `ingest/embed.py` | Creates an embedding for each section that has none. Text sent: product name + section title + section text |
| 3 | `ingest/load_specs.py` | Reads the specification table of each English manual into `products.specs` |
| 4 | `ingest/verify.py` | Compares the database with the manuals on disk |
| – | `ingest/search.py` | Vector search from the command line, for checking |

All scripts can be run again safely. A section is re-embedded only if its text changed.

Supporting files in `shared/`:

| File | Content |
|---|---|
| `products.json` | Product registry: id, name, folder (from the `backend-api` branch) |
| `product_extras.json` | Family, aliases and related products |
| `spec_parameters.json` | The 22 standard parameters: label patterns, unit, display labels in EN / DE / IT |
| `spec_overrides.json` | Hand-written fixes for specification rows the parser cannot read |

The Markdown parser is `backend/app/manuals.py`, copied unchanged from `backend-api`, so that section keys are the same in the database and in the API.

---

## 4. Verification

`ingest/verify.py` checks, for everything that is loaded:

| Check | Result |
|---|---|
| Schema: `vector` extension, `vector(1536)` column, row level security | Pass |
| Product rows match the registry; related products are valid and two-way | Pass |
| Sections in the database equal the parser output, for all 64 files | Pass |
| Text, printed page and PDF page identical to the source | Pass |
| No line of any manual is missing | Pass |
| Every image is attached as a figure, in order, and the file exists | Pass |
| Every section has an embedding of unit length | Pass |
| A stored vector belongs to its own text (5 random sections re-embedded) | Pass |
| Every spec value is printed in the manual; the database equals a fresh parse | Pass |
| Example filter "delivery robots that pass a 60 cm aisle" → KettyBot, KettyBot Pro | Pass |

Test searches (vector search only):

| Query | Top result |
|---|---|
| "indicator light is flashing yellow and it does not charge" | Charging Station Light §3.4 Troubleshooting |
| "Welcher Roboter kann 300 kg transportieren?" | T300 overview (German) |
| "come si pulisce il serbatoio dell'acqua sporca" | SH1 §6.3 recovery tank cleaning (Italian) |
| "how do I pair the pager with the gateway" | Pager §3, then GW1 §3.2 |
| "minimum passage width" | No specification table found: this is why specs are stored as structured values |

---

## 5. Problems found in the data and how they are handled

| Problem | Handling |
|---|---|
| Supabase direct host is IPv6-only and did not resolve | Use the session pooler connection string |
| Italian manuals print the label list before the figure | Labels are attached to the next figure when the section has none yet |
| German Mobile Water Station: two label lists, one figure (the second drawing is missing) | Both lists are on the one figure; the section text is correct |
| CC1: battery life printed under the label "Cleaning capabilities" | Mapped by hand in `spec_overrides.json` |
| Self-Cleaning Docking Station (Main): broken specification table | Weight and dimensions written by hand |
| FlashBot: total load and load per tray in one cell; two charging times | Written by hand as separate entries |
| KettyBot / KettyBot Pro: "Two trays and one dish-return box" | Written by hand |
| CC1 Pro: tanks, productivity and dustbin in irregular cells | Written by hand |
| Mixed units (minutes and hours, cm and mm, g and kg) | Converted to one unit per parameter |
| Several values in one cell (models, modes, load conditions) | Split into separate entries with `variant` or `condition` |

---

## 6. Known limits

- **Specs come from the English manuals.** The page stored with a value is the English page.
- **`reviewed` is not a human review.** The values were checked by the script and read through once; nobody on the team has checked the table yet. `python ingest/load_specs.py --dry-run` prints it.
- **Two Pager values are not reviewed**: battery life "≥ 1 year" and dimensions "Φ76.8×25 mm".
- **FlashBot has no weight** in its manual.
- **Ten products have no overview text** (mostly accessories, plus FlashBot and SH1): their manuals have no "Overview" section.
- **45 sections have the kind `other`**, and a few safety sections are mislabelled. Compliance and warranty sections are recognised correctly, which is what search needs.
- **HolaBot radio rows are scrambled in the source.** They are stored as printed under `_unmapped` and not used.
- **The manuals are not in the repository** (`data/` is ignored). Ingestion needs them in `data/PUDU-PDF-MD/`.

---

## 7. Next step: the RAG engine

Build `rag/pipeline.py` with the `answer()` function described in [7_rag_architecture.md](./7_rag_architecture.md), section 5:

1. **Understand**: detect the language, find the product by alias (LLM only as fallback), add related products.
2. **Retrieve**: three tools on the existing tables: `search_manuals` (`chunks`), `get_specs` and `find_products` (`products.specs`).
3. **Generate**: answer in the user's language from the evidence only, with numbered citations and chosen figure IDs.
4. **Check**: drop figure IDs that are not in the evidence; make sure numbers in the answer appear in the evidence.

Suggested order: `search_manuals` + answer with citations first (works for how-to and troubleshooting), then the two spec tools, then figures, then the checks. Test with the questions listed in [6_project_plan.md](./6_project_plan.md), section 10.
