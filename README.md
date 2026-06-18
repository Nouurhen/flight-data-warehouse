# HRAi Backend

FastAPI backend for the AI-powered recruitment platform. Handles authentication, data management, the 7-agent AI pipeline, and real-time voice interviews via LiveKit.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required:
- `SUPABASE_URL` — Your Supabase project URL
- `SUPABASE_ANON_KEY` — Publishable/anon key
- `SUPABASE_SERVICE_ROLE_KEY` — Service role key (Dashboard → Settings → API)
- `OPENAI_API_KEY` — For AI agents, TTS, Vision OCR

Optional:
- `GROQ_API_KEY` — Fallback LLM (Llama 3.3 70B)
- `GEMINI_API_KEY` — Fallback LLM (Gemini 2.0 Flash)
- `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — For real-time voice interviews

## Run

```bash
# API server
uvicorn app.main:app --reload --port 8000

# Voice interview agent (separate terminal, optional)
python -m app.livekit.agent_worker dev
```

API docs: http://localhost:8000/docs

---

## API Endpoints

### Jobs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/jobs` | Public | List all active jobs |
| GET | `/api/v1/jobs/{id}` | Public | Get job details |
| POST | `/api/v1/jobs` | Required | Create job posting |
| PATCH | `/api/v1/jobs/{id}` | Owner | Update job |
| DELETE | `/api/v1/jobs/{id}` | Owner | Delete job |

### Candidates
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/candidates` | Required | List candidates |
| GET | `/api/v1/candidates/{id}` | Required | Get candidate details |
| POST | `/api/v1/candidates` | Public | Create candidate (apply) |

### Applications
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/applications` | Required | List applications |
| POST | `/api/v1/applications` | Public | Submit application |
| PATCH | `/api/v1/applications/{id}` | Required | Update status |

### Interviews
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/interviews` | Required | List interviews |
| POST | `/api/v1/interviews` | Required | Create interview |

### AI Agents
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/agents/run/{application_id}` | Required | Run full 7-agent pipeline |
| POST | `/api/v1/agents/run/{application_id}/step/{n}` | Required | Run single agent step |
| GET | `/api/v1/agents/status/{application_id}` | Required | Get pipeline status |

### LiveKit (Voice Interviews)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/livekit/start/{application_id}` | Required | Create room + get token |
| POST | `/api/v1/livekit/end/{application_id}` | Required | End interview + save |
| GET | `/api/v1/livekit/status/{application_id}` | Required | Check room status |
| POST | `/api/v1/livekit/tts` | Required | Text-to-speech (OpenAI TTS) |

---

## AI Agent Pipeline

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentPipeline.run()                       │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐ │
│  │ 1. CV    │──▶│ 2. Skill │──▶│ 3. Ques- │──▶│ 4. Int │ │
│  │ Screening│   │ Matching │   │   tions   │   │  Eval  │ │
│  └──────────┘   └──────────┘   └──────────┘   └────────┘ │
│       │              │              │              │        │
│       ▼              ▼              ▼              ▼        │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────┐   │
│  │ 5. Rank- │──▶│ 6. Bias  │──▶│ 7. Coordinator       │   │
│  │   ing    │   │Detection │   │ (Final Recommendation)│   │
│  └──────────┘   └──────────┘   └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### LLM Fallback Chain

Each agent tries providers in order:
1. **OpenAI** (gpt-4o-mini) — Primary
2. **Groq** (llama-3.3-70b) — Fallback
3. **Gemini** (2.0-flash) — Last resort
4. **Rule-based** — Always works, no API needed

### Agent Outputs

| Agent | Key Metadata |
|-------|-------------|
| CV Screening | skills, experience, education, career_trajectory, achievements, red_flags |
| Skill Matching | match_score, skill_categories, transferable_skills, learning_potential |
| Interview Questions | 6 personalized questions (technical + behavioral) |
| Interview Evaluation | scores (communication, technical, confidence, job_fit), per_question_scores |
| Candidate Ranking | rank, percentile, weighted_score, comparative analysis |
| Bias Detection | status (passed/flagged), fairness_score, checks, concerns |
| Coordinator | recommendation, ai_summary, strengths, weaknesses, next_steps, salary_recommendation, hiring_risk |

### CV Vision OCR

For image-based PDFs (e.g., Canva exports):
1. Tries text extraction with PyPDF2
2. If no text found → converts PDF to images (PyMuPDF)
3. Sends images to OpenAI Vision API (gpt-4o-mini) for OCR
4. Returns extracted text for normal processing

---

## Voice Interview Agent Worker

Separate process that handles real-time voice conversations:

```bash
python -m app.livekit.agent_worker dev
```

### Pipeline: STT → LLM → TTS

| Component | Technology | Model |
|-----------|-----------|-------|
| STT | OpenAI Whisper | whisper-1 |
| LLM | OpenAI | gpt-4o-mini |
| TTS | OpenAI | tts-1 (voice: alloy) |

### How it works

1. Worker registers with LiveKit Cloud on startup
2. When candidate joins a room, LiveKit dispatches the agent
3. Agent fetches personalized questions from Supabase
4. Conducts real-time voice interview (greets → asks questions → acknowledges → closes)
5. Conversation handled automatically by LiveKit's VoicePipelineAgent

---

## Dependencies

```
fastapi==0.115.0          # Web framework
uvicorn[standard]         # ASGI server
supabase==2.9.1           # Database client
httpx==0.27.2             # HTTP client (for LLM APIs)
PyPDF2==3.0.1             # PDF text extraction
PyMuPDF>=1.24.0           # PDF to image conversion
livekit-api>=0.7.0        # LiveKit room/token management
livekit-agents>=0.12.0    # Voice pipeline agent
livekit-plugins-openai    # OpenAI STT/LLM/TTS plugins
crewai>=0.86.0            # Multi-agent framework (legacy)
```
