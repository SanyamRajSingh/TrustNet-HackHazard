# TrustNet - Complete Engineering Handbook

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Repository Structure](#repository-structure)
4. [Technology Stack](#technology-stack)
5. [Database Design](#database-design)
6. [API Specification](#api-specification)
7. [Trust Engine](#trust-engine)
8. [Sarvam AI Integration](#sarvam-ai-integration)
9. [Neo4j Intelligence Engine](#neo4j-intelligence-engine)
10. [Blockchain Layer](#blockchain-layer)
11. [Frontend Design](#frontend-design)
12. [Testing Strategy](#testing-strategy)
13. [Deployment Guide](#deployment-guide)
14. [Environment Variables](#environment-variables)
15. [Development Workflow](#development-workflow)

---

## 1. Project Overview

TrustNet is a real-time job offer fraud investigation platform built for Indian job seekers. It accepts unstructured input (WhatsApp messages, screenshots, PDFs, spoken Hindi/English), extracts entities using Sarvam AI, verifies against government databases and OSINT sources, maps relationships via Neo4j, produces a transparent trust score, generates bilingual reports, and writes confirmed HIGH RISK entities to a public scam registry on Base blockchain.

### Key Metrics
- **Target Response Time**: < 8 seconds (p95)
- **Languages Supported**: English, Hindi, Hinglish, Tamil, Telugu
- **Trust Score Range**: 0-100 (5 verdict categories)
- **Confidence Score**: 0-100 (data availability indicator)

---

## 2. Architecture

```
User Input (Text/Voice/Screenshot)
  |
  v
React PWA (Mobile-first)  -->  HTTPS  -->  FastAPI Backend
                                              |
                    +-------------------------+-------------------------+
                    |                         |                         |
                    v                         v                         v
               PostgreSQL               Sarvam AI API           External APIs
               (Relational)             (Entity Extract)        (WHOIS, MCA, etc.)
                    |                         |                         |
                    v                         v                         v
               Neo4j (Graph)           Hindi Report              Trust Engine
               (AuraDB)                Generation                (5-Category Score)
                                                                   |
                    +-------------------------+-------------------------+
                    |                         |                         |
                    v                         v                         v
               Redis Cache              Base Blockchain         Render Workflows
               (Rate Limit)             (Scam Registry)         (Background Jobs)
```

### Request Flow
1. User pastes text or speaks offer details
2. Frontend sends POST /investigate with raw text
3. FastAPI validates, creates investigation record
4. Sarvam AI extracts entities (async, <2s target)
5. Parallel async calls: WHOIS, MCA, Safe Browsing, PhishTank, URLhaus, NumVerify, DNS
6. Neo4j queried for pattern match and ring connections
7. Trust Engine aggregates 5 category scores
8. Confidence score computed
9. If HIGH_RISK: Base blockchain write initiated
10. Sarvam generates Hindi explanation
11. Full result returned (target: <8s)
12. Frontend renders verdict card, categories, graph, Hindi report

---

## 3. Repository Structure

```
trustnet/
├── frontend/                          # React 18 + Vite + Tailwind
│   ├── src/
│   │   ├── pages/                     # Route pages
│   │   │   ├── HomePage.tsx           # Landing + input
│   │   │   ├── ResultPage.tsx         # Investigation results
│   │   │   ├── EntityPage.tsx         # Entity profile
│   │   │   ├── CommunityPage.tsx      # Community reports
│   │   │   └── AboutPage.tsx          # About + tech stack
│   │   ├── components/                # Reusable components
│   │   │   ├── Navigation.tsx         # Top nav bar
│   │   │   ├── Layout.tsx             # Page layout wrapper
│   │   │   ├── HeroInput.tsx          # Text input form
│   │   │   ├── VoiceRecorder.tsx      # Audio recording
│   │   │   ├── VerdictCard.tsx        # Verdict display
│   │   │   ├── CategoryBreakdown.tsx  # Category scores
│   │   │   ├── EvidenceList.tsx       # Evidence details
│   │   │   ├── HindiReport.tsx        # Hindi explanation
│   │   │   ├── GraphViz.tsx           # D3 graph visualization
│   │   │   └── StatsCounter.tsx       # Animated counters
│   │   ├── store/                     # Zustand state
│   │   │   └── useStore.ts            # Global store
│   │   ├── lib/
│   │   │   └── api.ts                 # HTTP client
│   │   ├── App.tsx                    # Router setup
│   │   ├── main.tsx                   # Entry point
│   │   └── index.css                  # Global styles
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/                           # FastAPI + Python 3.11
│   ├── app/
│   │   ├── api/                       # REST routers
│   │   │   ├── investigate.py         # POST /investigate
│   │   │   ├── voice.py              # POST /voice
│   │   │   ├── graph.py              # GET /graph/{entity}
│   │   │   ├── community.py          # Community reports
│   │   │   ├── stats.py              # Stats + entity lookup
│   │   │   └── auth.py               # JWT auth
│   │   ├── core/                      # Core algorithms
│   │   │   └── trust_engine.py        # Scoring + verdict
│   │   ├── services/                  # External integrations
│   │   │   ├── sarvam_service.py      # Sarvam AI API
│   │   │   ├── mca_service.py         # MCA company lookup
│   │   │   ├── whois_service.py       # WHOIS + DNS auth
│   │   │   ├── safebrowsing.py        # Google + PhishTank + URLhaus
│   │   │   ├── phone_service.py       # NumVerify
│   │   │   ├── neo4j_service.py       # Graph operations
│   │   │   └── blockchain.py          # Base blockchain
│   │   ├── models/                    # Data layer
│   │   │   ├── postgres.py            # SQLAlchemy models
│   │   │   ├── schemas.py             # Pydantic schemas
│   │   │   └── database.py            # Async connection
│   │   └── workers/                   # Celery tasks
│   │       ├── celery_app.py          # Celery config
│   │       └── tasks.py               # Background jobs
│   ├── workflows/                     # Render cron scripts
│   │   ├── daily_refresh.py
│   │   ├── community_recalc.py
│   │   └── blockchain_sync.py
│   ├── alembic/                       # Database migrations
│   ├── tests/
│   │   ├── unit/                      # Unit tests
│   │   │   └── test_trust_engine.py   # 15 test cases
│   │   └── integration/               # API tests
│   │       └── test_api.py            # Full endpoint tests
│   ├── main.py                        # FastAPI app
│   ├── config.py                      # Settings (Pydantic)
│   ├── Dockerfile                     # Container build
│   ├── docker-compose.yml             # Local stack
│   ├── render.yaml                    # Render deploy config
│   └── requirements.txt
│
├── contracts/                         # Solidity smart contracts
│   ├── contracts/
│   │   └── TrustNetRegistry.sol       # Main contract
│   ├── test/
│   │   └── TrustNetRegistry.test.js   # Hardhat tests
│   ├── scripts/
│   │   └── deploy.js                  # Deployment script
│   ├── hardhat.config.js
│   └── package.json
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml                  # GitHub Actions
│
├── .env.example                       # Environment template
├── IMPLEMENTATION_ROADMAP.md          # 15-day roadmap
└── ENGINEERING_HANDBOOK.md            # This document
```

---

## 4. Technology Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18 | UI framework |
| Vite | 5.x | Build tool |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.4 | Styling |
| Zustand | 4.x | State management |
| React Router | 6.x | Routing |
| Lucide React | latest | Icons |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109 | API framework |
| SQLAlchemy | 2.0 (async) | ORM |
| Pydantic | 2.5 | Validation |
| Celery | 5.3 | Task queue |
| structlog | 23.x | Structured logging |

### Databases
| Technology | Purpose |
|------------|---------|
| PostgreSQL 16 | Relational data |
| Neo4j 5 (AuraDB) | Graph intelligence |
| Redis 7 (Upstash) | Cache, sessions, rate limit |

### External APIs
| Service | Data | Free Tier |
|---------|------|-----------|
| Sarvam AI | NLP, STT, Hindi | API key |
| WhoisXML | Domain WHOIS | 500 req/mo |
| Google Safe Browsing | URL reputation | 10K req/day |
| PhishTank | Phishing DB | Unlimited |
| URLhaus | Malware URLs | Unlimited |
| NumVerify | Phone validation | 100 req/mo |
| DNS (dnspython) | SPF/DKIM/DMARC | Unlimited |

### Blockchain
| Technology | Purpose |
|------------|---------|
| Base (Coinbase L2) | Scam registry |
| Solidity 0.8.20 | Smart contract |
| Hardhat | Development |
| Ethers.js v6 | Blockchain interaction |

---

## 5. Database Design

### PostgreSQL Tables

#### `users`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| phone_hash | VARCHAR(64) | NULLABLE |
| password_hash | VARCHAR(255) | NOT NULL |
| is_trusted_reporter | BOOLEAN | DEFAULT FALSE |
| investigation_count | INTEGER | DEFAULT 0 |

#### `investigations` (PRIMARY TABLE)
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| raw_input | TEXT | NOT NULL |
| input_type | VARCHAR(20) | NOT NULL (paste\|screenshot\|pdf\|voice) |
| entities_json | JSONB | NOT NULL |
| trust_score | SMALLINT | 0-100 |
| confidence_score | SMALLINT | 0-100 |
| verdict | VARCHAR(20) | NOT NULL |
| category_scores_json | JSONB | NOT NULL |
| evidence_json | JSONB | NOT NULL |
| hindi_explanation | TEXT | NULLABLE |
| blockchain_tx_hash | VARCHAR(66) | NULLABLE |
| neo4j_connections_json | JSONB | NULLABLE |
| processing_ms | INTEGER | NULLABLE |
| fee_amount_inr | INTEGER | NULLABLE |

#### `entities`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| entity_type | VARCHAR(20) | NOT NULL |
| entity_value | VARCHAR(500) | NOT NULL |
| entity_hash | VARCHAR(64) | UNIQUE |
| aggregate_score | SMALLINT | NULLABLE |
| on_chain | BOOLEAN | DEFAULT FALSE |
| ring_name | VARCHAR(100) | NULLABLE |

#### `community_reports`
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| entity_id | UUID | FK entities.id |
| report_type | VARCHAR(20) | SCAM\|LEGITIMATE\|SUSPICIOUS |
| loss_amount_inr | INTEGER | NULLABLE |
| verified_by_admin | BOOLEAN | DEFAULT FALSE |

#### `company_master` (MCA data)
| Column | Type | Constraints |
|--------|------|-------------|
| cin | VARCHAR(21) | PK |
| company_name | VARCHAR(500) | NOT NULL, INDEX |
| status | VARCHAR(50) | NULLABLE |
| registration_date | TIMESTAMPTZ | NULLABLE |
| directors_json | JSONB | NULLABLE |

### Neo4j Schema

#### Node Labels
- `:Domain` - value, age_days, registrar, is_flagged, risk_score, ring_name
- `:Email` - value, domain, provider_type, is_disposable, risk_score
- `:Phone` - value, country_code, line_type, carrier, risk_score
- `:Company` - name, mca_cin, mca_status, mca_age_years, risk_score
- `:Person` - name, is_director, associated_company_cin
- `:ScamRing` - name, discovered_date, entity_count, is_active

#### Relationship Types
- `SHARES_INFRASTRUCTURE` (Domain -> Domain)
- `USES_EMAIL_DOMAIN` (Email -> Domain)
- `LISTED_PHONE` (Company -> Phone)
- `IMPERSONATES` (Domain -> Company)
- `BELONGS_TO_RING` (Entity -> ScamRing)
- `REPORTED_WITH` (Entity -> Entity)
- `DIRECTED_BY` (Company -> Person)

---

## 6. API Specification

### POST /api/v1/investigate
Submit text/screenshot/PDF for investigation.

**Request:**
```json
{
  "raw_input": "string (max 10000 chars, min 10)",
  "input_type": "paste|screenshot|pdf|voice",
  "source_language": "optional string"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "trust_score": 0-100,
  "confidence_score": 0-100,
  "verdict": "HIGH_RISK|SUSPICIOUS|UNVERIFIED|LIKELY_LEGITIMATE|VERIFIED|INSUFFICIENT_DATA",
  "verdict_label": "DO NOT RESPOND",
  "verdict_color": "#DC2626",
  "entities": {
    "company_name": "string|null",
    "email": "string|null",
    "phone_number": "string|null",
    "website_url": "string|null",
    "recruiter_name": "string|null",
    "salary_mentioned": "integer|null",
    "fee_amount": "integer|null",
    "urgency_indicators": "boolean",
    "language_detected": "english|hindi|hinglish|tamil|telugu",
    "red_flags": ["string"]
  },
  "category_scores": { "identity_company": {...}, ... },
  "evidence": [{ "category": "string", "finding": "string", "severity": "critical|warning|info|positive" }],
  "hindi_explanation": "string|null",
  "processing_ms": 5342
}
```

### POST /api/v1/voice
Submit audio for STT + investigation.

**Request:**
```json
{
  "audio_base64": "base64-encoded-audio",
  "mime_type": "audio/wav"
}
```

**Response (200):** Same as /investigate + `transcript` field.

### GET /api/v1/graph/{entity_value}
Get graph connections for entity.

**Response (200):**
```json
{
  "nodes": [{ "id": 1, "labels": ["Domain"], "properties": {}, "risk_score": 12 }],
  "edges": [{ "source": 1, "target": 2, "type": "BELONGS_TO_RING" }],
  "flagged_count": 3,
  "rings": ["Infosys Impersonation Ring"]
}
```

### POST /api/v1/community/report
Submit community report.

**Request:**
```json
{
  "entity_id": "uuid",
  "report_type": "SCAM|LEGITIMATE|SUSPICIOUS",
  "loss_amount_inr": 2500,
  "description": "string"
}
```

### GET /api/v1/stats
Platform statistics.

**Response:**
```json
{
  "total_investigations": 12847,
  "total_entities_flagged": 3421,
  "total_inr_protected": 8525000,
  "total_on_chain_records": 892,
  "high_risk_percentage": 26.6,
  "avg_processing_ms": 5342
}
```

### POST /api/v1/auth/register
**Request:** `{ "email": "string", "password": "string (min 8)", "phone": "optional" }`
**Response:** `{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }`

### POST /api/v1/auth/token
**Request:** `{ "email": "string", "password": "string" }`
**Response:** Same as register.

---

## 7. Trust Engine

### Category Weights
| Category | Weight | Measures |
|----------|--------|----------|
| Identity & Company Verification | 25% | MCA registration, company age, CIN validity |
| Domain & Infrastructure Intelligence | 20% | WHOIS age, registrar, blacklist status |
| Communication Channel Integrity | 15% | Email auth (SPF/DKIM/DMARC), disposable check |
| Content Analysis & Red Flags | 20% | Fee requests, urgency language, salary realism |
| Community Intelligence | 20% | Graph connections, community reports, ring membership |

### Score Formula
```
trust_score = (
  identity_score * 0.25 +
  domain_score * 0.20 +
  communication_score * 0.15 +
  content_score * 0.20 +
  community_score * 0.20
) * confidence_multiplier

confidence_multiplier = max(0.5, data_points_available / max_possible_data_points)
```

### Confidence Points
| Data Point | Points |
|------------|--------|
| Company found in MCA | 20 |
| WHOIS data available | 15 |
| DNS records resolved | 15 |
| Sarvam extraction OK | 20 |
| Community reports exist | 15 |
| Phone verified | 10 |
| Email auth checked | 5 |
| **Maximum** | **100** |

### Verdict Thresholds
| Trust Score | Confidence | Verdict | Color |
|-------------|------------|---------|-------|
| < 25 | Any | HIGH_RISK | #DC2626 (Red) |
| 25-44 | >= 25% | SUSPICIOUS | #D97706 (Orange) |
| 45-64 | >= 25% | UNVERIFIED | #CA8A04 (Yellow) |
| 65-79 | >= 50% | LIKELY_LEGITIMATE | #2563EB (Blue) |
| >= 80 | >= 60% | VERIFIED | #16A34A (Green) |
| Any | < 25% | INSUFFICIENT_DATA | #64748B (Gray) |

---

## 8. Sarvam AI Integration

### Extraction Prompt
System prompt defines 11 fields to extract: company_name, email, phone_number, website_url, recruiter_name, salary_mentioned, fee_amount, urgency_indicators, personal_email_for_corp_contact, language_detected, red_flags.

### Fallback Strategy
| Failure Mode | Detection | Fallback |
|-------------|-----------|----------|
| API timeout (>4s) | asyncio timeout | Regex extraction: email, phone, URL patterns |
| Invalid JSON | JSON parse error | Attempt partial JSON; regex fallback |
| Language unsupported | language_detected='other' | English extraction only; reduce confidence 5% |
| Rate limit (429) | HTTP status | Queue, retry after 1s, max 3 retries |

### Salary Normalization
- "3 LPA" -> 25,000/month
- "5.5 CTC" -> 45,833/month
- "40k/month" -> 40,000/month
- "2.5 lakhs per annum" -> 20,833/month

---

## 9. Neo4j Intelligence Engine

### Graph Write Trigger
Every investigation with confidence >= 25% triggers graph write operations. Entities are merged (MERGE on unique value) to avoid duplicates. Relationships are created between co-occurring entities.

### Key Cypher Queries

**Upsert Entity:**
```cypher
MERGE (d:Domain {value: $domain_value})
ON CREATE SET d.first_seen = datetime(), d.investigation_count = 1
ON MATCH SET d.investigation_count = d.investigation_count + 1
```

**Ring Detection (3-hop subgraph):**
```cypher
MATCH (start {value: $entity_value})
CALL apoc.path.subgraphAll(start, {
  maxLevel: 3,
  relationshipFilter: 'SHARES_INFRASTRUCTURE|REPORTED_WITH|USES_EMAIL_DOMAIN'
}) YIELD nodes, relationships
```

**Brand Impersonation:**
```cypher
MATCH (legit:Domain) WHERE legit.is_legitimate_brand = true
MATCH (suspect:Domain) WHERE suspect.value <> legit.value
WITH legit, suspect, apoc.text.levenshteinDistance(legit.value, suspect.value) AS dist
WHERE dist <= 2 AND dist > 0
MERGE (suspect)-[r:IMPERSONATES]->(legit)
```

**Louvain Community Detection:**
```cypher
CALL gds.louvain.write('scam-graph', {
  writeProperty: 'communityId', maxIterations: 10
}) YIELD communityCount, modularity
```

---

## 10. Blockchain Layer

### TrustNetRegistry.sol

**Key Features:**
- Stores flagged entities by keccak256 hash
- Backend-only writes via EIP-191 signature verification
- Supports 4 entity types: domain(1), email(2), phone(3), company(4)
- Batch read via `batchCheck()`
- Owner can unflag entities

**Events:**
```solidity
event EntityFlagged(bytes32 indexed entityHash, uint8 entityType, uint32 trustScore, uint64 timestamp);
event EntityUnflagged(bytes32 indexed entityHash, uint64 timestamp);
```

**Deployment:**
```bash
cd contracts
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network base_sepolia
npx hardhat verify --network base_sepolia <ADDRESS> <BACKEND_SIGNER>
```

### Backend Integration
```python
# Sign and submit
entity_hash = w3.keccak(text=f'{entity_type}:{entity_value}')
msg_hash = w3.keccak(entity_hash + type_bytes + score_bytes + count_bytes)
signed = Account.sign_message(encode_defunct(msg_hash), private_key)
tx_hash = await contract.flagEntity(entity_hash, type_int, score, count, signature)
```

---

## 11. Frontend Design

### Pages
| Route | Page | Key Components |
|-------|------|----------------|
| `/` | Home | HeroInput, VoiceRecorder, StatsCounter, FeatureGrid |
| `/result/:id` | Result | VerdictCard, CategoryBreakdown, EvidenceList, GraphViz, HindiReport |
| `/entity/:hash` | Entity | EntityCard, InvestigationHistory, RingAlert |
| `/community` | Community | ReportForm, ReportList |
| `/about` | About | ProcessFlow, TechStack, CTASection |

### Mobile-First Design Constraints
- Maximum input area: full-width textarea, large font, paste-optimized
- Voice CTA: floating microphone button, bottom-right
- Result card: scrollable, no horizontal scroll, single column
- Graph viz: pinch-to-zoom enabled, tap to select node
- Hindi text: Noto Sans Devanagari font

### State Management (Zustand)
```typescript
interface AppState {
  rawInput: string;
  isLoading: boolean;
  currentResult: InvestigationResult | null;
  investigationHistory: InvestigationResult[];
  isRecording: boolean;
  audioBase64: string | null;
  transcript: string | null;
  activeTab: string;
  // Actions
  setRawInput, setIsLoading, setCurrentResult, addToHistory,
  setIsRecording, setAudioBase64, setTranscript, setActiveTab, clearResult
}
```

---

## 12. Testing Strategy

### Unit Tests (pytest)
- Trust Engine: 15 test cases covering all verdict bands
- Sarvam Extraction: 10 Hinglish, 5 Tamil/Telugu, salary normalization
- Category Scorers: domain age, MCA found/not found, fee detection
- WHOIS Service: new domain, old domain, privacy-protected
- Smart Contract: Hardhat tests for access control and signatures

### Integration Tests
| Scenario | Expected Result | Pass Criteria |
|----------|----------------|---------------|
| Infosys phishing input | HIGH_RISK, score < 25 | Score < 25, Hindi non-empty |
| Legitimate TCS offer | LIKELY_LEGITIMATE or VERIFIED | Score >= 65, no fee flag |
| Unknown company | UNVERIFIED | Confidence < 25% or score 45-64 |
| Tamil language input | Entities extracted | language_detected='tamil' |
| Voice input (Hindi) | Transcript + investigation | Processing < 12s total |

### Performance Targets
- Entity extraction (Sarvam): < 2 seconds
- All external API calls (parallel): < 4 seconds
- Neo4j graph query: < 500ms
- Trust score calculation: < 50ms
- Total investigation (p95): < 8 seconds
- Frontend time to interactive: < 2 seconds
- Mobile Lighthouse score: >= 85

---

## 13. Deployment Guide

### Prerequisites
- Render.com account (free tier)
- Neo4j AuraDB free instance
- Upstash Redis (free tier)
- Sarvam AI API key
- Cloudinary account

### Environment Setup
```bash
# 1. Clone repo
git clone <repo-url>
cd trustnet

# 2. Copy env
cp backend/.env.example backend/.env
# Edit with your credentials

# 3. Deploy PostgreSQL on Render
# 4. Deploy Redis on Upstash
# 5. Create Neo4j AuraDB instance

# 6. Deploy via Render Blueprint
# Push to GitHub, connect to Render, use render.yaml
```

### Local Development
```bash
# Start all services
docker-compose up -d

# Run migrations
cd backend
alembic upgrade head

# Start API
uvicorn main:app --reload

# Start worker
celery -A app.workers.celery_app worker --loglevel=info

# Start frontend
cd ../frontend
npm install
npm run dev
```

### Production Checklist
- [ ] All env vars set in Render dashboard
- [ ] Database migrations applied
- [ ] Neo4j seed data loaded
- [ ] Smart contract deployed to Base Sepolia
- [ ] Contract address set in env
- [ ] CORS origins configured
- [ ] Rate limiting enabled
- [ ] Sentry monitoring configured
- [ ] SSL certificate active
- [ ] Health check endpoint responding

---

## 14. Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `NEO4J_URI` | Neo4j AuraDB connection URI | Yes |
| `NEO4J_USERNAME` | Neo4j username | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `REDIS_URL` | Upstash Redis URL | Yes |
| `SARVAM_API_KEY` | Sarvam AI API key | Yes |
| `SECRET_KEY` | JWT signing secret | Yes |
| `WHOIS_API_KEY` | WhoisXML API key | Yes |
| `GOOGLE_SAFE_BROWSING_KEY` | Safe Browsing API key | Yes |
| `NUMVERIFY_API_KEY` | NumVerify API key | Yes |
| `BASE_SEPOLIA_RPC` | Base Sepolia RPC endpoint | Yes |
| `BACKEND_WALLET_PRIVATE_KEY` | Wallet for contract writes | Yes |
| `TRUSTNET_CONTRACT_ADDRESS` | Deployed contract address | Yes |
| `BLOCKCHAIN_ENABLED` | Enable blockchain writes | No (default: true) |
| `PHISHTANK_API_KEY` | PhishTank API key | No |
| `CLOUDINARY_URL` | Cloudinary connection | No |

---

## 15. Development Workflow

### Git Branching
```
main (production)
  └── develop (integration)
        └── feature/* (individual features)
```

### CI/CD Pipeline (GitHub Actions)
1. **On PR**: Run pytest (unit + integration), ESLint, TypeScript check
2. **On merge to main**: Deploy to Render, run migrations

### Code Quality
```bash
# Backend formatting & linting
black app/ tests/
isort app/ tests/
mypy app/

# Frontend formatting
npx eslint src/
npx prettier --check src/
```

### Monitoring
- Render metrics: CPU, memory, response times
- Sentry: Error tracking and performance
- PostgreSQL: Query performance, slow queries
- Neo4j: Query execution times
- Blockchain: Transaction confirmation times

---

*TrustNet - Built for India's Job Seekers*
*End of Engineering Handbook*