# TrustNet - 15-Day Implementation Roadmap

## Day 1: Project Setup
- [ ] Create GitHub repository (public)
- [ ] Set up Render.com account and provision PostgreSQL
- [ ] Create Neo4j AuraDB free tier instance
- [ ] Set up Upstash Redis
- [ ] Configure Cloudinary for image uploads
- [ ] Create .env files for local and production
- [ ] Verify all external service connectivity
- **Deliverable**: All infrastructure provisioned, env vars documented

## Day 2: Database Init
- [ ] Deploy PostgreSQL schema via Alembic migrations
- [ ] Create all tables: users, investigations, entities, community_reports, company_master, stats_counters
- [ ] Set up Neo4j constraints (unique on Domain.value, Email.value, Phone.value, Company.mca_cin)
- [ ] Create Neo4j indexes (domain_risk, company_name fulltext)
- [ ] Seed Neo4j with 3 scam rings and 50 entities
- [ ] Load MCA bulk data CSV into company_master
- [ ] **Deliverable**: Both databases running with seed data

## Day 3: Sarvam Integration
- [ ] Implement Sarvam AI entity extraction endpoint
- [ ] Build regex fallback system for timeout scenarios
- [ ] Test on 10 sample Hinglish messages
- [ ] Implement language detection (Hindi/Hinglish/English/Tamil/Telugu)
- [ ] Add salary normalization (LPA, CTC, monthly, lakhs)
- [ ] Test error handling: timeout, invalid JSON, rate limit
- [ ] **Deliverable**: Entity extraction working, fallback tested

## Day 4: External APIs
- [ ] WHOIS integration (whoisxmlapi.com)
- [ ] Google Safe Browsing API integration
- [ ] PhishTank API integration
- [ ] URLhaus (abuse.ch) integration
- [ ] NumVerify phone validation
- [ ] DNS lookup (SPF/DKIM/DMARC)
- [ ] Implement parallel async calls using asyncio.gather
- [ ] Add mock responses for testing
- [ ] **Deliverable**: All 6 external APIs integrated, parallel calls working

## Day 5: Trust Engine
- [ ] Implement all 5 category scorers
- [ ] Build confidence score calculator
- [ ] Implement verdict thresholds
- [ ] Test worked example: Infosys phishing (score ~15)
- [ ] Test edge cases: zero confidence, single entity, no data
- [ ] Add 15 unit tests covering all verdict bands
- [ ] **Deliverable**: Trust engine passing all tests, verdicts correct

## Day 6: Neo4j Service
- [ ] Graph write on investigation completion
- [ ] Ring detection query (3-hop subgraph)
- [ ] Brand impersonation Cypher (Levenshtein distance)
- [ ] Community detection via GDS Louvain
- [ ] Seed legitimate brand domains
- [ ] Test graph queries with seeded data
- [ ] **Deliverable**: Graph operations working, ring detection verified

## Day 7: Smart Contract
- [ ] Complete TrustNetRegistry.sol
- [ ] Hardhat setup and compilation
- [ ] Deploy to Base Sepolia testnet
- [ ] Test flagEntity() with backend signatures
- [ ] Verify contract on Basescan
- [ ] Save contract address and ABI
- [ ] **Deliverable**: Contract deployed, flagEntity() tested

## Day 8: API Layer
- [ ] All 10 REST endpoints live
- [ ] Pydantic request/response validation
- [ ] JWT authentication (register/login)
- [ ] Rate limiting via Redis
- [ ] Error handling middleware
- [ ] CORS configuration
- [ ] Health check endpoint
- [ ] **Deliverable**: Full API spec, all endpoints tested

## Day 9: Frontend Foundation
- [ ] React + Vite + Tailwind project setup
- [ ] React Router configuration
- [ ] Zustand store setup
- [ ] API client with error handling
- [ ] Navigation component
- [ ] Layout wrapper
- [ ] Tailwind theme configuration
- [ ] **Deliverable**: Frontend skeleton, routing working

## Day 10: Investigate Page
- [ ] Hero section with gradient background
- [ ] Text input with character counter
- [ ] "Try Example" button with demo text
- [ ] Submit flow with loading state
- [ ] Voice recorder component
- [ ] Tab switching (Text/Voice)
- [ ] Stats counter with animated numbers
- [ ] Feature grid section
- [ ] **Deliverable**: Home page complete with input flow

## Day 11: Result Page
- [ ] Verdict card with colored header
- [ ] Circular trust score gauge (SVG)
- [ ] Category breakdown with progress bars
- [ ] Evidence list with severity badges
- [ ] Extracted entities summary
- [ ] Hindi report display (Noto Sans Devanagari)
- [ ] Graph visualization (D3 canvas)
- [ ] Blockchain verification badge
- [ ] **Deliverable**: Result page renders all investigation data

## Day 12: Graph + Hindi
- [ ] Force-directed graph visualization
- [ ] Node coloring by type and risk
- [ ] Edge labels for relationship types
- [ ] Ring connection highlighting
- [ ] Hindi font loading (Noto Sans Devanagari)
- [ ] Hindi text rendering test
- [ ] Mobile responsiveness for all components
- [ ] **Deliverable**: Graph viz and Hindi reports working

## Day 13: Render Workflows
- [ ] Daily intelligence refresh workflow
- [ ] Community score recalculation workflow
- [ ] Blockchain sync workflow
- [ ] Celery beat scheduler config
- [ ] Worker deployment on Render
- [ ] Test workflow execution
- [ ] **Deliverable**: 3 cron workflows deployed and running

## Day 14: Integration Testing
- [ ] End-to-end flow with 20 sample inputs
- [ ] Performance: verify p95 < 8 seconds
- [ ] Mobile testing (Chrome DevTools Pixel 7)
- [ ] Lighthouse audit (target >= 85)
- [ ] Cross-browser testing
- [ ] Voice input flow test
- [ ] Fix any bugs discovered
- [ ] **Deliverable**: All tests passing, performance verified

## Day 15: Demo Polish
- [ ] 5 demo scenarios prepared and tested
- [ ] Demo 1: Infosys phishing (HIGH_RISK, ring connected)
- [ ] Demo 2: Legitimate TCS offer (LIKELY_LEGITIMATE)
- [ ] Demo 3: Unknown company (UNVERIFIED)
- [ ] Demo 4: Voice input (Hindi)
- [ ] Demo 5: Graph traversal (ring discovery)
- [ ] Walkthrough video recorded (90-second backup)
- [ ] Documentation finalized
- [ ] README with setup instructions
- [ ] **Deliverable**: Demo-ready, documentation complete, all scenarios tested