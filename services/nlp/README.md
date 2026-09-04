# NLP Extraction Service — Chakravyuha AI

Turns unstructured FIR / report text into graph-ready entities and relationships.

## Run

```bash
cd services/nlp
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
python -m spacy download en_core_web_trf

uvicorn app.main:app --reload --port 8100
```

Interactive docs: http://localhost:8100/docs

## Endpoints

| Method | Path             | Purpose                                  |
|--------|------------------|------------------------------------------|
| GET    | `/health`        | liveness + which spaCy model is loaded   |
| POST   | `/extract`       | one document -> contract JSON            |
| POST   | `/extract/batch` | many documents (use this for the demo)   |
| POST   | `/extract/file`  | .txt upload                              |

```bash
curl -X POST http://localhost:8100/extract \
  -H "Content-Type: application/json" \
  -d '{"text":"Rakesh Yadav called Imran Sheikh on 9830012345.","doc_id":"FIR-1"}'
```

## Output contract

`../../contracts/extraction_contract.json`. Do not change it without telling the
graph and API owners — three services read it.

## Pipeline

clean -> regex -> ner -> dedupe -> resolve -> relate -> emit

- **regex** (`extractors/regex_extractors.py`) — fixed-shape entities: phone,
  vehicle, IFSC, account, money, date, email. Confidence 0.90-0.99.
- **ner** (`extractors/ner.py`) — open vocabulary: PERSON, ORGANIZATION,
  LOCATION, WEAPON. Gazetteer (`extractors/gazetteer.py`) runs before the
  statistical model, so known Indian names beat the model's guess.
- **resolve** (`resolution.py`) — alias clustering. Merges at >=88, flags
  72-88 as `meta.review_suggestions` for a human. Biased to under-merge.
- **relate** (`relations.py`) — trigger lexicon + entity-type constraints +
  distance limits. Every edge carries the sentence that produced it.

## Known limitations (say these before a judge finds them)

- No coreference: "The accused fled in WB 02 AB 1234" produces no owner edge,
  because "the accused" is not a named entity.
- Relations are sentence-scoped; a relation stated across two sentences is missed.
- Hindi support is trigger-level only, not a full Hindi NER model.
- Recall is bounded by the trigger lexicon. Precision is prioritised.

## Demo fixtures (internal hackathon scope)

The service does NOT run at demo time. Build the frozen fixtures once, offline:

```bash
python -m scripts.build_demo_data
```

Writes `demo/`:

| File | Demo story step |
|------|-----------------|
| `ledger.json` | SHA-256 hash + tamper-evident chain per FIR |
| `extraction_steps.json` | "AI extracts entities and relationships" |
| `alias_review.json` | "possible alias is reviewed by officer" |
| `graph.json` | "network graph updates" |
| `analysis.json` | "link analysis identifies kingpin and middleman" |
| `alerts.json` | "alert ... is generated" — suspicious patterns |
| `timeline.json` | scrubber for animating the network over time |
| `report.md` | "intelligence report is generated" |

The frontend imports these. No Python, no model, nothing to fail on stage.

Regenerate after changing anything in `data/` — the network shape is
deliberately designed, so re-check that kingpin and middleman are still the
intended people before committing.

## Synthetic dataset

15 sources, all fictional. Unstructured go through the NLP pipeline; structured
bypass it (`app/sources.py`).

| File | Type | Notes |
|------|------|-------|
| `fir_001` … `fir_011` | FIR | theft, crew, aliases, Hindi, hawala, shell co., extortion, vehicle, arms, layering, social |
| `surveillance_001/002` | SURVEILLANCE | meetings, IMEI, co-location |
| `cdr_records.csv` | CDR | 95 call rows, 8 subscribers, tower locations |
| `transactions.csv` | TRANSACTION | 14 transfers across 6 accounts |

The network shape is **designed, not accidental** — Vikram Singh is the hub
(PageRank) and Imran Sheikh the sole bridge between the street crew and the
financial cluster (betweenness). Change `data/` and you may break that; the
build script prints both, so check before committing.

## Pattern detection (`app/patterns.py`)

| Detector | Fires on |
|----------|----------|
| `STRUCTURING` | 3+ transfers in 7 days, each 85-100% of the Rs. 5,00,000 threshold |
| `PASSTHROUGH` | funds in and out within 3 days, under 15% retained |
| `CALL_BURST` | 4+ calls between a pair within 60 minutes |
| `ODD_HOURS` | 60%+ of calls between 22:00 and 05:00, min 5 calls |
| `SHARED_IDENTIFIER` | one phone/account/vehicle linked to 2+ people |
| `BRIDGE` | betweenness above 0.2 |

Every alert names its threshold and lists the rows that triggered it. Rules,
not a black-box score — an unexplained anomaly number is useless to someone who
has to justify an arrest.

## Tests

```bash
pytest -q
python -m tests.test_golden --update    # regenerate fixtures, deliberately
```