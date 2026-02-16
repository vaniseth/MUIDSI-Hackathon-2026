# MUIDSI-Hackathon-2026

### Folder Structure 

```
mizzou-safe-ai/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
│
├─ app.py                         # Streamlit home + navigation
├─ pages/
│  ├─ 1_Safety_Copilot.py         # Screen 1 (RAG triage)
│  └─ 2_Safe_Route.py             # Screen 2 (routing + risk scoring)
│
├─ data/
│  ├─ raw/
│  │  ├─ crime_log.html           # optional snapshot
│  │  ├─ crime_log.csv            # scraped output (raw)
│  │  └─ docs/                    # PDFs / HTML saved locally
│  ├─ processed/
│  │  ├─ crime_log_clean.csv      # normalized + geocoded
│  │  ├─ poi_landmarks.csv        # campus POIs (lat/lon) for demo dropdowns
│  │  └─ risk_grid.parquet        # cached risk surface (optional)
│  └─ indexes/
│     ├─ faiss.index              # vector index
│     └─ docstore.jsonl           # chunk metadata + text
│
├─ src/
│  ├─ config.py                   # constants, paths, thresholds
│  ├─ utils/
│  │  ├─ geo.py                   # haversine, clustering helpers
│  │  ├─ text.py                  # chunking helpers
│  │  └─ cache.py                 # simple caching wrappers
│  │
│  ├─ ingest/
│  │  ├─ scrape_crime_log.py      # pulls daily crime log -> raw CSV
│  │  ├─ geocode_locations.py     # location -> lat/lon (or POI matching)
│  │  └─ ingest_docs.py           # PDF/HTML -> cleaned text chunks
│  │
│  ├─ rag/
│  │  ├─ build_index.py           # chunks -> embeddings -> FAISS
│  │  ├─ retriever.py             # top-k retrieval
│  │  ├─ prompts.py               # system + response templates
│  │  ├─ safety_router.py         # rule-based action mapping + guardrails
│  │  └─ llm_client.py            # wrapper for whichever LLM you use
│  │
│  └─ routing/
│     ├─ osrm_client.py           # route polyline + ETA
│     ├─ risk_model.py            # risk surface from incidents
│     ├─ route_ranker.py          # fastest vs safest route selection
│     └─ explain.py               # 1-2 line explanation generator
│
└─ tests/
   ├─ test_router.py
   └─ test_risk.py
```
