-- Database schema for the RAG system. See docs/7_rag_architecture.md.
-- Safe to run more than once.

CREATE EXTENSION IF NOT EXISTS vector;

-- One row per product (22 rows).
CREATE TABLE IF NOT EXISTS products (
    id               TEXT PRIMARY KEY,              -- 'bellabot-pro' (same ID as shared/products.json)
    name             TEXT NOT NULL,                 -- 'BellaBot Pro'
    kind             TEXT NOT NULL,                 -- robot | accessory
    family           TEXT NOT NULL,                 -- delivery | cleaning | industrial | charging | docking | call_system | water
    aliases          TEXT[] NOT NULL DEFAULT '{}',  -- other names and model codes
    langs            TEXT[] NOT NULL,               -- languages the manual exists in
    folder           TEXT NOT NULL,                 -- manual folder, relative to the data directory
    related_products TEXT[] NOT NULL DEFAULT '{}',  -- robot <-> accessory links
    overview         JSONB NOT NULL DEFAULT '{}',   -- {"en": "...", "de": "..."} first overview paragraph
    specs            JSONB NOT NULL DEFAULT '{}',   -- filled by a later step
    extra_meta       JSONB NOT NULL DEFAULT '{}'
);

-- One row per numbered manual section, per language.
CREATE TABLE IF NOT EXISTS chunks (
    id            SERIAL PRIMARY KEY,
    product_id    TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    lang          TEXT NOT NULL,                    -- en | de | it
    section_key   TEXT NOT NULL,                    -- '2.4', '5.1~2', '0' (same keys as the backend)
    section_title TEXT,
    section_kind  TEXT,                             -- safety | overview | components | specs | usage | maintenance | troubleshooting | compatibility | compliance | warranty | front_matter | other
    block_type    TEXT NOT NULL,                    -- text | table
    seq           INT NOT NULL,                     -- order inside the manual
    page          INT,                              -- printed page
    pdf_page      INT,                              -- page in the original multilingual PDF
    content       TEXT NOT NULL,                    -- section Markdown as in the manual
    figures       JSONB NOT NULL DEFAULT '[]',      -- [{id, path, caption, labels, has_ai_description}]
    embedding     VECTOR(1536),                     -- text-embedding-3-small; NULL until embedded
    search_tsv    TSVECTOR GENERATED ALWAYS AS
                  (to_tsvector('simple', coalesce(section_title, '') || ' ' || content)) STORED,
    UNIQUE (product_id, lang, section_key)
);

CREATE INDEX IF NOT EXISTS chunks_product_lang_idx ON chunks (product_id, lang);
CREATE INDEX IF NOT EXISTS chunks_search_tsv_idx ON chunks USING GIN (search_tsv);

-- Supabase exposes the public schema through its REST API. With row level security on
-- and no policies, only our own database connection can read or write these tables.
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
