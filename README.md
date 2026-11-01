# ✈️ Smart Flight Booking with Agentic AI

**Author: Abdul : Full Stack - AI Engineer**

A production-oriented Agentic AI travel platform that turns natural-language requests into flight intelligence, hotel research, itinerary planning and a booking-ready travel brief.

## What changed

- Project branding changed from **the previous project name** to **Smart Flight Booking with Agentic AI**.
- Author attribution standardized to **Abdul : Full Stack - AI Engineer**.
- Agent functions renamed to clearer production roles:
  - `flight_intelligence_agent`
  - `hotel_research_agent`
  - `itinerary_planning_agent`
  - `booking_advisor_agent`
- LangGraph initialization is now lazy, so the `/health` endpoint can start even before API/database dependencies are accessed.
- Backend no longer exposes raw internal exceptions to end users.
- Request validation was strengthened with Pydantic limits.
- Frontend Markdown output is sanitized with DOMPurify.
- Added persistent conversation reset / New trip control.
- Added workflow progress indicators and responsive production UI.
- Improved PDF export and user feedback.
- Uvicorn binds to `0.0.0.0` for container/cloud deployment.

## Architecture

```text
Browser
   │
   ▼
FastAPI / Jinja UI
   │
   ▼
POST /api/travel
   │
   ▼
LangGraph Agentic Workflow
   ├── Flight Intelligence Agent ──► AviationStack
   ├── Hotel Research Agent ───────► Tavily
   ├── Itinerary Planning Agent ───► Groq LLM
   └── Booking Advisor Agent ──────► Groq LLM
                    │
                    ▼
             PostgreSQL Checkpoint
```

## Local setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and provide:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
DEFAULT_ORIGIN_IATA=DEL
GROQ_MODEL=llama-3.3-70b-versatile
```

For production PostgreSQL, use the provider's TLS-enabled connection string.

### 4. Start

```bash
python app.py
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

### 5. Test the API

```bash
curl -X POST http://127.0.0.1:8000/api/travel   -H "Content-Type: application/json"   -d '{"message":"Plan a 5-day trip from Delhi to Dubai with flight options, hotels and sightseeing."}'
```

## Production deployment

The included `Dockerfile` is ready for container-based hosting.

Build:

```bash
docker build -t smart-flight-booking-agentic-ai .
```

Run:

```bash
docker run --env-file .env -p 8000:8000 smart-flight-booking-agentic-ai
```

For Render, create a **Web Service**, connect the repository, and use:

```text
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Add the required environment variables in Render. Use a managed PostgreSQL database and keep API keys only in environment variables.

## Production notes

- `/health` is intentionally lightweight and does not require external API calls.
- Flight availability, fare and hotel information must be verified with the provider before payment.
- Do not commit `.env` or API keys.
- For multiple application workers, each worker creates its own database/checkpointer connection.
- For enterprise deployment, add authentication, rate limiting, audit logging, secret management and provider-specific booking APIs before enabling actual payment/booking transactions.

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Production web console |
| GET | `/health` | Liveness check |
| POST | `/api/travel` | Execute Agentic AI travel workflow |

## License

See `LICENSE`.
