# Chakravyuha AI

> Secure Graph Intelligence for Law Enforcement

Chakravyuha AI is an AI-powered criminal-network intelligence platform designed for NCRB and law-enforcement use cases. It transforms fragmented fictional evidence—FIRs, Call Detail Records, bank transactions, phones, locations, vehicles, and aliases—into an interactive knowledge graph for investigative link analysis.

> **Smart India Hackathon Project**  
> **Theme:** Blockchain & Cybersecurity  
> **Data Policy:** Synthetic demonstration data only

![Chakravyuha AI System Architecture](docs/system-architecture.png)

## Problem

Crime-related information often exists in disconnected systems. A suspect may appear by name in an FIR, by phone number in CDR data, by account number in banking records, and by an alias in another report.

Manual correlation is slow and makes multi-hop criminal connections difficult to identify.

Chakravyuha AI connects these records into a relationship graph to help investigators identify:

- Probable kingpins and key influencers
- Middlemen connecting separate criminal groups
- Suspicious money-transfer paths
- Hidden associations
- Potential aliases and duplicate identities
- Evidence-backed intelligence alerts

## Current Status

**Current phase:** Frontend-first interactive prototype using local synthetic data.

Implemented or in progress:

- Interactive criminal-network dashboard
- Evidence-ingestion simulation
- Graph filters and node-detail panel
- Link-analysis simulation
- Intelligence alerts
- Case intelligence report preview
- Tamper-evident evidence-ledger simulation
- GSAP-powered interface animations

Planned for the functional system:

- FastAPI backend
- Neo4j knowledge graph
- PostgreSQL metadata database
- AI/NLP entity and relationship extraction
- Entity resolution and human review workflow
- JWT authentication and RBAC
- SHA-256 evidence integrity verification
- Hash-chained audit ledger
- Optional Hyperledger Fabric proof of concept

## Key Differentiators

| Capability | Chakravyuha AI Approach |
|---|---|
| Multilingual FIR intelligence | Indic-language translation/transliteration before extraction |
| Relationship discovery | Graph-based link analysis instead of simple search |
| Explainable intelligence | PageRank, Betweenness Centrality, evidence references, and confidence scores |
| Alias detection | Fuzzy matching combined with shared contextual evidence |
| Human oversight | Officers approve or reject uncertain identity merges |
| Evidence integrity | SHA-256 evidence hashes and tamper-evident audit records |
| Graph usability | Two-hop view, filters, shortest path, and progressive expansion |
| Data security | RBAC, secure uploads, audit logging, and encrypted off-chain storage |

## System Flow

```text
Officer uploads FIR / CDR / Bank CSV
        ↓
File validation + SHA-256 evidence hash
        ↓
Secure object storage + tamper-evident audit event
        ↓
OCR + language processing + AI entity extraction
        ↓
Entity resolution + human review for uncertain aliases
        ↓
Graph Writer Service
        ↓
Neo4j Knowledge Graph
        ↓
Graph analytics and intelligence alerts
        ↓
Interactive relationship map + case intelligence report
```

## Core Graph Model

### Nodes

```text
Person
Phone
Account
Location
Vehicle
FIR
```

### Relationships

```text
CALLED
TRANSFERRED
OWNS
LOCATED_AT
MENTIONED_IN
```

`TRANSFERRED` relationships hold properties such as amount, timestamp, transaction ID, evidence source, and confidence score.

## Architecture

```text
Users
  → Secure Investigation Portal
  → Security & API Layer
  → Data Ingestion & AI Pipeline
  → Intelligence & Analytics Layer
  → Supporting Datastores
  → Intelligence Outputs
```

### Major Components

| Component | Responsibility |
|---|---|
| React Dashboard | Investigator interface, graph visualization, filters, alerts, reports |
| API Gateway / Backend | Connects frontend, data services, analytics, and security controls |
| NLP Pipeline | Extracts entities and relationships from evidence |
| Entity Resolution | Detects possible aliases and duplicate identities |
| Human Review Queue | Requires investigator approval for uncertain identity merges |
| Neo4j | Stores relationship graph and supports link analysis |
| Graph Analytics | Runs PageRank, Betweenness, communities, shortest path, and link prediction |
| PostgreSQL | Stores users, cases, roles, metadata, and report records |
| Object Storage | Stores raw fictional FIRs, CDRs, and banking files |
| Redis | Caches graph queries and session-related data |
| Audit / Ledger | Records evidence and investigator actions in a tamper-evident trail |

## Blockchain and Cybersecurity

Chakravyuha AI does not store sensitive FIRs, CDRs, bank data, or graph data on-chain.

Instead:

```text
Raw evidence → securely stored off-chain
SHA-256 hash + case ID + officer ID + timestamp + action
→ tamper-evident audit ledger
```

Example ledger events:

```text
EVIDENCE_UPLOADED
EVIDENCE_HASH_VERIFIED
ALIAS_MERGE_APPROVED
ALIAS_MERGE_REJECTED
REPORT_GENERATED
REPORT_EXPORTED
```

Security controls include:

- JWT authentication
- Role-Based Access Control
- Secure file-upload validation
- Encryption in transit and at rest
- Sensitive-data masking
- Audit logging
- SHA-256 evidence-integrity verification

## Screens

### Command Center

- Interactive criminal relationship graph
- Entity, relationship, date, and risk filters
- Two-hop network view
- Shortest-path search
- Selected-entity details
- `Run Link Analysis` action
- Kingpin, middleman, money-trail, and hidden-link highlights

### Evidence Ingestion

```text
Upload
→ SHA-256 Hash
→ Ledger Entry
→ OCR & Validation
→ Language Processing
→ AI Extraction
→ Entity Resolution
→ Human Review
→ Graph Updated
```

### Network Analysis

- PageRank for probable kingpins
- Betweenness Centrality for middlemen
- Community Detection for suspected groups
- Link Prediction for potential hidden associations

### Intelligence Alerts

- Probable Kingpin
- Suspicious Financial Flow
- High-Betweenness Middleman
- Potential Hidden Link

### Evidence Ledger

- Evidence hash
- Ledger event ID
- Case ID
- Officer ID
- Timestamp
- Integrity verification status

### Case Intelligence Report

- Case overview
- Key suspects
- Network findings
- Financial trail
- Evidence integrity status
- Recommended investigative actions

## Tech Stack

### Current Prototype

- React
- TypeScript
- Tailwind CSS
- Cytoscape.js or React Force Graph
- GSAP
- Local mock-data service
- Lucide icons

### Target Functional Stack

- FastAPI
- Python
- Neo4j + Cypher + Graph Data Science
- PostgreSQL
- Redis
- spaCy / Hugging Face / regex-based extraction
- RapidFuzz for entity resolution
- Tesseract OCR
- Bhashini / Indic NLP
- SHA-256 hash-chained audit ledger
- Optional Hyperledger Fabric

## Getting Started

### Prerequisites

- Node.js 20 or later
- npm

### Installation

```bash
git clone https://github.com/<your-github-username>/chakravyuha-ai.git
cd chakravyuha-ai
npm install
npm run dev
```

Open the local URL shown in the terminal.

> If the project uses a different script, use the commands listed in `package.json`.

## Suggested Project Structure

```text
chakravyuha-ai/
├── docs/
│   ├── system-architecture.png
│   └── screenshots/
├── src/
│   ├── components/
│   ├── pages/
│   ├── data/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── assets/
├── public/
├── README.md
└── package.json
```

## Development Roadmap

- [x] Define system architecture
- [x] Define UI/UX and frontend roadmap
- [ ] Build Command Center with synthetic graph data
- [ ] Build Evidence Ingestion workflow
- [ ] Build Intelligence Alerts and Reports
- [ ] Build Evidence Ledger simulation
- [ ] Add GSAP animation system
- [ ] Set up Neo4j graph schema
- [ ] Build FastAPI backend
- [ ] Connect frontend to APIs
- [ ] Build AI/NLP extraction pipeline
- [ ] Add entity-resolution and human-review workflow
- [ ] Add JWT/RBAC and secure upload validation
- [ ] Build hash-chained audit ledger
- [ ] Add Hyperledger Fabric proof of concept
- [ ] Test and deploy the full prototype

## Team Roles

| Role | Responsibility |
|---|---|
| Team Lead / Cybersecurity + Blockchain Engineer | Security architecture, evidence hashing, RBAC, audit ledger, project integration |
| UI/UX + Frontend Engineer | Dashboard design, graph UI, GSAP animations, responsive frontend, PPT visuals |
| Data Engineer | Neo4j schema, synthetic graph data, Cypher queries, graph analytics |
| Backend Engineer | FastAPI APIs, uploads, PostgreSQL, Neo4j integration |
| AI/NLP Engineer | OCR, entity extraction, relationship extraction, alias resolution |

## Safety and Ethics

- Use only synthetic and fictional data.
- Do not upload real FIRs, CDRs, banking records, phone numbers, or personal data.
- AI recommendations must remain explainable and subject to human review.
- Uncertain identity matches must never be merged automatically.
- Evidence integrity records must not expose sensitive evidence content.

## Demo Flow

```text
Open Operation Trinetra
→ Upload fictional FIR
→ Verify SHA-256 evidence hash
→ Show AI-extracted entities
→ Review possible alias match
→ Open relationship graph
→ Run Link Analysis
→ Identify kingpin and middleman
→ View suspicious money trail
→ Generate report
→ Verify evidence ledger history
```

### License

Licensed under the [Apache License 2.0](LICENSE).

© 2026 Chakravyuha AI Contributors.
