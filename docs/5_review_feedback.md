# Review: Challenge Fit, Data Model and Image Handling (v2)

> Second review, Sat 14 Nov (night). It covers:
> - [2_system_overview.md](./2_system_overview.md) and [3_architecture_deep_dive.md](./3_architecture_deep_dive.md) (unchanged since v1)
> - **new:** [4_database_and_generalizability.md](./4_database_and_generalizability.md) (commit `928fa20`)
> - **new:** the `origin/backend-api` branch (commit `a9dc008`, FastAPI backend), read but not run
>
> Everything is checked against the real files in `data/PUDU-PDF-MD` (64 Markdown files, 476 images).
> This file was `4_review_feedback.md` in v1. It is renamed to `5_…` because doc 4 now exists.

---

## 1. Verdict

**Closer, but not yet good to go.** The new doc adds image handling and a concrete schema, and the backend branch already serves images, PDFs and citations. Three things now block a correct, demo-ready system:

| # | Issue | Severity | Section |
|---|---|---|---|
| 1 | The corpus is still not in the repo (`data` is ignored on both branches) | **Blocker** | 2 |
| 2 | The two branches have **no common history** and disagree on data path, product IDs and where specs live | **Blocker for integration** | 3 |
| 3 | The `specs` JSONB shape loses data and cannot hold variants or conditions | High (answer correctness) | 4.2 |
| 4 | Images are attached to answers by section, not by relevance; the doc assumes every figure has a description and labels | High ("images when necessary") | 5 |
| 5 | Postgres + pgvector is more infrastructure than 22 products need, with ~13 h to code freeze | Medium (risk) | 4.1 |
| 6 | Two examples in doc 4 are not in the manuals | Medium (faithfulness) | 4.4 |

### What happened to the v1 findings

| v1 finding | Status |
|---|---|
| Data not in the repo | **Open** (section 2) |
| No database schema | **Addressed** by doc 4; needs the fixes in section 4 |
| Images have no place in the design | **Partly addressed** by doc 4 and by the backend; needs the rules in section 5 |
| Spec tables are not clean | **Open**; doc 4 and the backend both assume clean tables (section 6) |
| PDF page link is wrong | **Resolved by the backend's choice**: it links to the original multilingual PDF, where `PDF page N` is correct. This only holds if those PDFs are available at demo time (section 2) |
| Languages are not parallel | **Handled** by the backend (falls back to English and says so) |
| Scope too large | **Open** (section 8) |

---

## 2. Blocker: the data is not in the repo

`azam/initial-planning` ignores `data/*`. `backend-api` ignores `/data`. The jury evaluates only what is in the official repository.

| Content | Size | Recommendation |
|---|---|---|
| Markdown (64 files) | 1.2 MB | Commit |
| Images (476 PNG) | 22 MB | Commit (needed to show figures) |
| Per-language PDFs (`en.pdf` …) | 144 MB | Skip |
| Original multilingual PDFs | 419 MB | Needed for the backend's "open the PDF page" link. Too large for normal Git: ask the organisers, or drop the PDF link from the demo and link to the section text (`/api/sources/…`) instead |

**Action:** ask Telmekom whether the dataset may be committed. Then ignore only `*.pdf`, or add a setup step in the README.

---

## 3. The two branches do not fit together yet

### 3.1 No shared Git history

`azam/initial-planning` (root `0764c79`) and `main` / `backend-api` (root `d1a6773`) have no common commit. A normal merge or pull request will be refused. Someone must merge once with `git merge --allow-unrelated-histories` (the `.gitignore` files will conflict). **Do this now, not at 14:00.**

### 3.2 Decisions that differ between doc 4 and the backend

| Topic | Doc 4 | `backend-api` | Recommendation |
|---|---|---|---|
| Data folder | `data/PUDU-PDF-MD/manuals/…` | `data/manuals/…` (from `shared/products.json`) | Set `DATA_DIR=../data/PUDU-PDF-MD` in `backend/.env`, or move the folders. Write the choice in the README |
| Product ID | integer `id` + slug `bellabot_pro` | string `bellabot-pro` | Use the IDs in `shared/products.json` as the slug everywhere. The backend rejects unknown IDs |
| Product registry | `products` table: `category` = `delivery_robot` …, `aliases` | `shared/products.json`: `category` = `robot` / `accessory`, no aliases | One registry. Add `family` (delivery / cleaning / industrial / charging / docking / call system) and `aliases` to `shared/products.json`; load the table from it |
| Spec label mapping | `dataset_config.yaml` → `spec_synonyms` | `SPEC_FIELDS` in `backend/app/catalog.py` (19 keys, regex) | One source. Move the mapping to a file under `shared/` that both read |
| Spec values | `products.specs` JSONB (numbers + raw) | in-memory, raw strings only, used by `/api/products` and `/api/compare` | One source. Otherwise the compare page and the chat can show different values for the same robot |
| Section key | `section_title` text | `key` = heading number (`2.4`, `5.1~2`, `0`) | Add `section_key` to `chunks`, produced by the backend's `app/manuals.py` parser (it uses only the standard library so the RAG can import it) |
| Page | text label `Page 3 (PDF page 4, left)` | two integers: `page`, `pdf_page` | Store the two integers |
| Database | PostgreSQL | none (in-memory catalog, built at start in about 1 s) | See 4.1 |

### 3.3 What the RAG must return to the backend

The backend accepts `{"answer": …, "sources": […]}`. A source may be text only, and `citations.py` then looks for the chunk text inside the manuals. This breaks if the chunk has a context prefix (`BellaBot Pro › 2.4 Specifications`, as planned in the overview), because the text no longer matches.

**Always send the metadata** with each source: `product_id`, `lang`, `section_id`, `page`. Then no guessing is needed.

Two things the contract does not carry yet:

- **Which images to show** (section 5).
- **Answer status**: `answered` / `not_in_docs` / `needs_clarification`. Without it the UI cannot style "not in the documentation" or a clarifying question differently.

---

## 4. Review of doc 4 (database and generalizability)

### 4.1 PostgreSQL + pgvector: allowed, but not needed

The corpus is 22 products and about 1,500 chunks. The backend already holds everything in memory without a database.

| Option | Cost | Note |
|---|---|---|
| **Postgres + pgvector** (doc 4) | Docker or a local install on every laptop, a seed step, one more thing that can fail in the live demo | Good pitch line ("one database, structured + vector") |
| **SQLite file + FTS5, embeddings in a NumPy array** | No server. The built file can be committed | Same two tables, same queries |
| **No database**: JSON files + in-memory search | Smallest | Fits the current backend |

If the team keeps Postgres: use the `pgvector/pgvector` Docker image with a `docker-compose.yml`, commit a seed dump, and rehearse Plan B with the database stopped.

Two technical points if Postgres stays:

- `tsvector` needs a text-search configuration. The default English one stems German and Italian words wrongly. Use `'simple'`, or pick the configuration from the `language` column.
- `VECTOR(1536)` fixes the embedding model. Choose a multilingual model first, then set the dimension.

### 4.2 `products.specs`: the JSON shape must change

One key holding one object cannot represent what the tables contain:

| Real case | With the doc 4 shape |
|---|---|
| SwiftBot weight `SWFD01: 49 kg; SWFD11: 59 kg`; T300 `65 kg (WTID01); 81 kg (WTIDL1)` | One `min`/`max` range 49–59. The model is lost |
| T300 battery life `12 h (None load); 6 h (Max. load)` | Range 6–12. The condition is lost |
| `< 3 h`, `> 8 h`, `≥ 1 year`, `About 2 h` | No place for the operator; a filter gives wrong results |
| Repeated labels: `Frequency band range` (5 rows), `Dimensions` and `Weight` twice (Mobile Water Station, Self-Cleaning Base), SH1 `Operation time of batteries` (Normal / ECO) | Same key → the last row overwrites the others. This contradicts "nothing is ever lost" |
| SH1 runtime in **minutes**, robots in hours; dimensions in cm (FlashBot, MT1) and mm (others) | `unit` differs per product; sorting across products is wrong |
| `page` stored as text | Cannot build a link; the label is also language-specific |

Proposed shape: **each key holds a list of entries**, numbers are converted to one unit per parameter, and the raw text is kept for quoting.

```json
"specs": {
  "battery_runtime": [
    {"raw": "12 h (None load)", "variant": null, "condition": "no load",
     "op": "=", "min": 12, "max": 12, "unit": "h",
     "label": "Battery life", "page": 3, "pdf_page": 4, "reviewed": true},
    {"raw": "6 h (Max. load)", "variant": null, "condition": "max. load",
     "op": "=", "min": 6, "max": 6, "unit": "h",
     "label": "Battery life", "page": 3, "pdf_page": 4, "reviewed": true}
  ],
  "weight": [
    {"raw": "65 kg (WTID01)", "variant": "WTID01", "op": "=", "min": 65, "max": 65, "unit": "kg", "label": "Overall weight", "page": 3, "pdf_page": 4, "reviewed": true},
    {"raw": "81 kg (WTIDL1)", "variant": "WTIDL1", "op": "=", "min": 81, "max": 81, "unit": "kg", "label": "Overall weight", "page": 3, "pdf_page": 4, "reviewed": true}
  ],
  "_unmapped": [
    {"label": "Frequency band range", "raw": "Bluetooth: 2402–2480 MHz", "page": 3, "pdf_page": 4}
  ]
}
```

With 22 rows, JSONB is fine for "which robot…" questions: load all rows and filter in Python, or use `jsonb_array_elements`. Only entries with `reviewed: true` should be used for rankings and filters.

### 4.3 Other schema fixes

| Column | Problem | Fix |
|---|---|---|
| `products.components` | Duplicates the figure chunks, in English only. The labels exist in DE and IT too | Drop it. Keep labels on the figure chunk (section 5) |
| `products.accessories` | Compatibility is printed in the **accessory** manual (Charging Station Light §3.2) as a matrix: product × adapter → Recommended / Compatible / Not recommended | Store it on the accessory row as a list `{product, adapter, relation, page, pdf_page}`. Read it in both directions |
| `products.summary` | One language, written by an LLM | Use the first overview paragraph from the manual (the backend already extracts it per language) |
| `chunks` | No section key, no numeric page, no order | Add `section_key`, `page`, `pdf_page`, `seq` |
| `chunks.page_label` | Text | Replace with the two integers |
| `chunks.extra_meta` | Unspecified | For `block_type = 'figure'`: `{"labels": [{"n": "5", "text": "Lidar"}], "has_ai_description": true}` |

### 4.4 Examples in doc 4 that do not match the manuals

Fix these before anyone copies them into code or a slide:

- `accessories: [{charging_station_light, "Standard charger"}]` on **BellaBot Pro**. The BellaBot Pro manual does not mention a charging station, and the compatibility list has only FlashBot New, T300, KettyBot, KettyBot Pro, PuduBot 2 and SwiftBot.
- `components: [{number: 1, name: "Power switch"}]`. In the BellaBot Pro figure, **1 is "LCD screen"** and 2 is "Power switch".
- "Every image is already paired with an AI description and printed labels." Not true: 7 English figures have no description, 35 images have empty alt text, and a `*Labels:*` list exists about once per manual (the component overview).

The T300 figure example (1 Indicator light, 2 LCD screen, 5 Lidar) is correct.

### 4.5 Generalizability

The reader + config split is a clean idea and costs little if the code is organised that way from the start. Two cautions:

- It is **not a judging criterion** (answer quality, ease of use, faithfulness). Give it one sentence in the pitch, no build time.
- "0% changes" is too strong. The spec review (section 6), the compatibility data and the concept mapping ("narrow aisles" → passage width) are per dataset. Say "the schema, API and UI do not change".

---

## 5. Images: what works and what to change

### What already works

- Doc 4 stores figures as their own chunks with `image_paths`, and attaches inline figures to the text chunk.
- The backend serves files (`/files/{product}/{path}`, PNG/JPG/PDF only, with a path check), rewrites image links inside section Markdown, and adds `image_urls` to every citation.

### What to change

1. **Relevance.** Today a citation gets **all** images of its section (`section.images`), and doc 4 says "whenever a cited chunk has `image_paths`, include them". A spec question that cites a section with figures will show unrelated drawings. Let the RAG decide: add `image_paths` to each source it returns, and make the backend use that list when present (one line in `citations.py`, fall back to none rather than to the whole section).
2. **When to show.** Show a figure only if the question is about location or appearance ("where is", "which button", "what does it look like"), or the answer is a procedure whose cited chunk has figures. Maximum 3.
3. **The model never writes paths.** It chooses from the figure IDs in the retrieved evidence; the server drops anything else.
4. **Always show the legend with a numbered drawing.** The component figures are line drawings with callouts 1–21 and no text. "The emergency stop is number **20**" + the figure + the label list is a strong, fully grounded demo moment. Keep labels as data (`extra_meta.labels`) so the UI can highlight the number.
5. **Figures without a description.** For the 7 English figures with no AI text, build the chunk content from the section heading and the paragraph around the image. The description is sometimes placed after a paragraph, not directly under the image (SH1 §6.6–6.8): the parser must look ahead to the next image or heading.
6. **Faithfulness.** Labels come from the PDF and can be cited. The AI description is only for finding the figure. Do not show it as manual text.
7. **Language.** Figures differ per language (SH1: 30 EN / 39 DE / 38 IT; Mobile Water Station: 10 / 6 / 12). Show the figure from the same document as the cited chunk.

---

## 6. Spec tables: problems in the real data (still open)

Both doc 4 ("any spec … is saved automatically") and the backend (`SPEC_FIELDS` regex, first match wins) assume clean tables. I parsed all 22 English spec tables:

| Problem | Where | Effect |
|---|---|---|
| **Table broken**: label and value in one cell, second column empty | CC1 Series Self-Cleaning Docking Station (Main), EN and DE | No usable rows for this product |
| **Rows scrambled** in the radio part | HolaBot EN (DE is clean) | Wrong frequency / transmit power values |
| **Wrong label**: battery life per mode is printed under `Cleaning capabilities` | CC1, all languages | CC1 has no battery life in any comparison with CC1 Pro |
| Backend maps `Max. load` and `Load capacity` to the same key as `Tray load` | T300 (300 kg total), FlashBot (`20 kg (10 kg per tray)`) | The compare view puts 300 kg next to 10 kg/layer under one label. Split into `max_load` and `load_per_tray` |
| `battery_life` also matches the Pager (`≥ 1 year`) | Pager | Harmless in display, wrong in any ranking |
| `Cover Cleaning` / `Spot Cleaning` not mapped to productivity | CC1 Pro | Missing next to CC1 `Cleaning efficiency` |
| 3- and 4-column tables | KettyBot / KettyBot Pro, Charging Station Light (3 adapters) | Need `variant` |
| Second header row inside a table | SwiftBot | A fake `Feature / Description` row |
| Noise | `&nbsp;`, `<br>`, decimal commas, leftover `yr²/h`, missing units (`230 /200 /200 /180`), value with no number (`(adjustable)`) | Number parsing fails |
| Typos in the source | `5G: 5180-2825` (FlashBot), `Input vlotage`, `Seires` | Quote as printed |

**Recommendation (unchanged):** dump all rows raw, then fill and **check by hand** the 10–12 parameters used for comparison (passage width, max load, load per tray, trays, runtime, charging time, battery capacity, weight, dimensions, speed, IP rating, climbing angle / obstacle height). That is about 160 values for 13 robots, roughly one hour, and it is what makes "which robot…" answers correct. Fix the two broken tables by hand from the PDF.

---

## 7. What I verified as correct

| Claim | Result |
|---|---|
| 22 manuals, 64 Markdown files, 476 images, none missing or orphaned | Correct |
| BellaBot Pro: 25.6 Ah, 4.5 h, 11 h (unloaded), 65 cm, IP20, printed page 3 = PDF page 4 | Correct |
| BellaBot 12–24 h, 70 cm · KettyBot / Pro 55 cm · T300 60 cm, 300 kg · SwiftBot / PuduBot 2 80 cm | Correct |
| Charging Station Light: T300 → 15 A recommended; flashing yellow = more than one adapter or incompatible adapter | Correct |
| FlashBot, GW1, Pager have no Italian version; every manual has English | Correct |
| Backend: the `PDF page N` number matches the original multilingual PDF it links to | Correct by design (not opened in a viewer) |
| Backend: `shared/products.json` lists all 22 folders with the right names | Correct |

Not verified: I did not install or run the backend or its tests.

---

## 8. Scope for the time left

Code freeze Sat 14:05. A Must that is not ready by 08:00 gets simulated.

| Priority | Item |
|---|---|
| **Now** | Merge the two histories (3.1) · decide the data folder and commit Markdown + images (2) · agree on IDs, registry and one spec source (3.2) · decide Postgres vs SQLite vs no DB (4.1) |
| **Must (by 08:00)** | RAG engine plugged into the backend (`RAG_ENGINE=python`) returning metadata with each source · whole-manual context when the product is known (one manual is 3–8k tokens: no chunking errors, no BellaBot / BellaBot Pro mix-up) · reviewed spec values for comparison · "not in the documentation" answer · figures by relevance with legend |
| **Should (by 10:00)** | Compatibility data · DE / IT questions tested · 20-question test set with 3–4 questions that must return a figure and 3 that must return "not in the documentation" · `/api/search` (Bonus 1) |
| **Cut** | Re-ranking · LLM-written product summaries · ontology file · agent with tools · knowledge-graph view · generalization beyond the reader/config split |

---

## 9. Questions for the Telmekom team

1. May we commit the dataset (Markdown + images) to the official repo? What about the PDFs (563 MB)?
2. Will the judges ask their own questions, and in which languages?
3. Do they expect images in the answers, or is this our own goal?
4. Is there a constraint on the LLM provider (cloud allowed, or local only)?
