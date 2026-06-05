# HR Talent Intelligence Swarm — Project Context

## Overview
Microsoft Build AI 2026 Hackathon — Agent Swarms Track.
AI-powered hiring system with 6 agents on Azure AI Foundry.
Developer: Jefri Jebason (jefrijebason@gmail.com)

## Architecture
- Backend: FastAPI (Python) on localhost:8000
- Dashboard: React on localhost:3000 (HR view)
- Apply Portal: React on localhost:3001 (Candidate view, Aurora theme)
- Coding Portal: React on localhost:3002
- AI Interview: ARIA text chat (inside Apply Portal)
- Public URL: https://hrswarm.loca.lt (via localtunnel)

## Azure Resources
- AI Foundry: hr-swarm-hub-jefri (eastus)
- Cosmos DB: hr-swarm-cosmos (database: hr-swarm)
- Service Bus: hr-swarm-bus (8 queues)
- Blob Storage: hrswarmblob2026
- ACS Email: hr-swarm-acs
- Graph API: hr-swarm-app (Teams meetings)

## Cosmos DB Containers
candidates, jobs, audit, talent_pool, interviewers, interview_assignments, hr_users

## Pipeline Flow
1. HR posts JD on Dashboard → JD Quality Scorer → configure interview mode
2. Candidate applies on Apply Portal → uploads PDF resume
3. Screener agent scores resume (threshold: 60)
4. If passes → AI interview link emailed to candidate
5. PIPELINE PAUSES — waits for real candidate interview
6. Candidate takes ARIA interview (3 rounds, real AI evaluation)
7. On completion → pipeline resumes automatically
8. Interviewer Pool matches best interviewer (skill matching)
9. PIS escalation: primary → backup1 → backup2 → HR alert
10. Technical interview (human gate 1)
11. HR interview (human gate 2)
12. Evaluator → Communicator → offer/rejection email
13. HR who posted JD notified at every stage

## Key Files
- main.py — FastAPI backend with all endpoints
- agents/orchestrator/agent.py — Pipeline orchestrator (run_ai_pipeline, resume_pipeline_after_interview)
- agents/screener/agent.py — Resume scoring
- agents/interviewer/agent.py — AI interview (server-side, used for background scoring)
- agents/interviewer_pool/agent.py — Interviewer management
- agents/interviewer_pool/escalation.py — PIS escalation system
- agents/interviewer_pool/matcher.py — Skill matching engine
- agents/evaluator/agent.py — Final scoring
- agents/communicator/agent.py — Email via ACS
- agents/scheduler/agent.py — Calendar via Graph API
- shared/config.py — Environment config
- shared/cosmos_client.py — Database operations
- shared/openai_client.py — GPT calls with content filter handling

## Frontend Structure
- frontend/dashboard/src/App.js — HR dashboard (Post Job, Pipeline, Interviewers, Analytics)
- frontend/apply-portal/src/App.js — Candidate portal (Aurora theme, Browse, Detail, Apply, Track)
- frontend/apply-portal/src/interview/ — AI Interview (ARIA chat, Quiet Focus theme)
- frontend/coding-portal/src/App.js — Monaco code editor

## Design Themes
- Apply Portal: "Aurora" — dark purple, cyan/violet/magenta aurora, glass morphism
- AI Interview: "Quiet Focus" — midnight slate background, white cards, indigo accent
- Dashboard: Light theme with sidebar navigation

## Interview Modes
- standard: Screen → AI → Technical → HR → Decision
- executive: Screen → N human rounds (skip AI)
- express: Screen → AI → 1 combined human round
- custom: Fully configurable

## Current Status
- All agents built and tested
- Apply Portal with Aurora theme complete
- AI Interview (ARIA) chat working with real GPT evaluation
- Dashboard with Job posting, Pipeline, Interviewers
- Interviewer Pool with PIS escalation
- Email sending via ACS confirmed working
- Tracker page with dynamic stages
- Pipeline pauses at AI interview, resumes on completion

## .env Required Keys
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, COSMOS_ENDPOINT, COSMOS_KEY,
SERVICE_BUS_CONNECTION, BLOB_CONNECTION, ACS_CONNECTION, ACS_EMAIL_SENDER,
GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, PUBLIC_URL

## Commands to Run
Terminal 1: venv\Scripts\activate && python main.py
Terminal 2: npx localtunnel --port 8000 --subdomain hrswarm
Terminal 3: cd frontend\dashboard && npm start
Terminal 4: cd frontend\apply-portal && npm start (port 3001)