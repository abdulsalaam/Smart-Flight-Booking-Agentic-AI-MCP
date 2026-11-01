"""
Smart Flight Booking with Agentic AI
Author: Abdul : Full Stack - AI Engineer
"""
from pathlib import Path
import logging
import traceback
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from backend import run_booking_agent

BASE_DIR = Path(__file__).resolve().parent
LOGGER = logging.getLogger("smart-flight-booking")

app = FastAPI(
    title="Smart Flight Booking with Agentic AI",
    description="Production-oriented Agentic AI flight and travel planning platform.",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class TravelRequest(BaseModel):
    """Validated request model for a booking/planning conversation."""
    message: str = Field(..., min_length=2, max_length=4000)
    thread_id: str | None = Field(default=None, max_length=128)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the production web console."""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.post("/api/travel")
async def travel_planner(request_data: TravelRequest):
    """Run the Agentic AI booking workflow and return a safe JSON response."""
    user_message = request_data.message.strip()

    if not user_message:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Travel request cannot be empty."},
        )

    try:
        result = run_booking_agent(
            user_input=user_message,
            thread_id=request_data.thread_id,
        )
        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "answer": result["answer"],
                "flight_results": result["flight_results"],
                "hotel_results": result["hotel_results"],
                "itinerary": result["itinerary"],
                "llm_calls": result["llm_calls"],
            }
        )
    except ValueError as exc:
        LOGGER.warning("Validation/configuration error: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": str(exc)},
        )
    except Exception:
        LOGGER.exception("Travel workflow failed")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "The booking workflow could not be completed. Please try again.",
            },
        )


@app.get("/health")
async def health_check():
    """Lightweight liveness endpoint suitable for Render and container probes."""
    return {
        "status": "ok",
        "service": "smart-flight-booking-agentic-ai",
        "version": app.version,
    }


@app.get("/favicon.ico")
async def favicon():
    """Return an empty response when no custom favicon is configured."""
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
