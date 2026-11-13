# 🤖 Telmekom Robot Documentation Assistant

**NOI Hackathon Bolzano 2026 — Telmekom Challenge**  
Conversational, source-grounded RAG system that turns technical robot manuals, datasheets, and accessory guides into accurate answers for both field technicians and non-technical sales/business users.

## 🎯 Key Features
- **Dual-Persona Routing**: Adapts responses for **Technicians** (exact parameters, specs, wiring, troubleshooting) and **Non-Technical / Sales Users** (matching robot capabilities to real-world business environments like restaurants, hotels, or logistics).
- **Hybrid Retrieval + Strict Grounding**: Combines semantic vector search and keyword matching (BM25) over Markdown manuals and image transcriptions, citing exact source files to prevent hallucinations.
- **API-First Architecture (Bonus)**: Decoupled retrieval engine exposed via REST API, ready to power web interfaces, chatbots, or voice assistants.
- **Multilingual Support (Bonus)**: Query in your preferred language and get coherent answers regardless of the source documentation's language.

## 🏗️ Architecture
1. **Ingestion Pipeline**: Structure-aware Markdown chunking preserving technical tables and metadata (`robot_model`, `doc_type`, `use_case`).
2. **Retrieval Engine**: Hybrid search + reranking layer exposed via FastAPI.
3. **Generation Layer**: Persona-aware prompt routing with mandatory source citations.
4. **Frontend**: Clean conversational UI displaying answers alongside verified source snippets.

## 🚀 Quick Start
*(Inserire qui i comandi per avviare backend e frontend, es. `docker-compose up` o `pip install -r requirements.txt`)*
