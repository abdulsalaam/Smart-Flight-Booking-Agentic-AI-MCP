"""
Smart Flight Booking with Agentic AI
Author: Abdul : Full Stack - AI Engineer

Agentic workflow:
1. Flight intelligence agent
2. Hotel research agent
3. Itinerary agent
4. Booking advisor / final response agent
"""
import os
import operator
import uuid
from threading import Lock
from typing import Annotated, TypedDict

import certifi
from dotenv import load_dotenv
from psycopg.rows import dict_row
import psycopg

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from tools.flight_tool import search_flights
from tools.tavily_tool import tavily_search

load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

_CHECKPOINT_LOCK = Lock()
_TRAVEL_GRAPH = None


def get_database_url() -> str:
    """Return a PostgreSQL URL with TLS enabled for hosted databases."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is missing. Add it to .env or your hosting environment.")

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"
    return database_url


def create_llm() -> ChatGroq:
    """Create the LLM only when the workflow is actually requested."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to .env or your hosting environment.")

    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=api_key,
        temperature=0.2,
    )


class TravelState(TypedDict):
    """Shared state passed between Agentic AI nodes."""
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


def flight_intelligence_agent(state: TravelState):
    """Collect live/available flight intelligence from AviationStack."""
    try:
        flight_data = search_flights(state["user_query"])
    except Exception as exc:
        flight_data = f"Flight search was unavailable: {exc}"

    return {
        "flight_results": flight_data,
        "messages": [AIMessage(content="Flight intelligence collected.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def hotel_research_agent(state: TravelState):
    """Research hotel and destination information through Tavily."""
    try:
        query = f"Best hotels and accommodation options for {state['user_query']}"
        hotel_data = tavily_search(query)
    except Exception as exc:
        hotel_data = f"Hotel research was unavailable: {exc}"

    return {
        "hotel_results": hotel_data,
        "messages": [AIMessage(content="Hotel research completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def itinerary_planning_agent(state: TravelState, llm: ChatGroq):
    """Turn flight and hotel evidence into a practical itinerary."""
    prompt = f"""
Create a practical travel itinerary from the information below.

USER REQUEST:
{state['user_query']}

FLIGHT INTELLIGENCE:
{state['flight_results']}

HOTEL RESEARCH:
{state['hotel_results']}

Requirements:
- Respect dates, duration, origin, destination and budget when present.
- Clearly distinguish live/search data from estimates.
- Do not invent confirmed bookings, prices or availability.
- Keep the itinerary easy to scan.
"""
    response = llm.invoke([
        SystemMessage(content="You are an expert travel itinerary planning agent."),
        HumanMessage(content=prompt),
    ])
    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def booking_advisor_agent(state: TravelState, llm: ChatGroq):
    """Produce the final booking-oriented response with transparent caveats."""
    prompt = f"""
You are the final Booking Advisor for Smart Flight Booking with Agentic AI.

USER REQUEST:
{state['user_query']}

FLIGHT INTELLIGENCE:
{state['flight_results']}

HOTEL RESEARCH:
{state['hotel_results']}

ITINERARY:
{state['itinerary']}

Return a polished answer using these sections:
1. Trip Overview
2. Flight Options
3. Hotel Recommendations
4. Day-by-Day Plan
5. Estimated Budget
6. Booking Checklist
7. Important Notes

Rules:
- Never claim a ticket, room, price or seat is confirmed unless the source explicitly confirms it.
- Clearly label estimates.
- If the live flight source does not provide ticket pricing, say so.
- Prefer concise tables and bullet points where helpful.
- Be useful to a traveler making a real booking decision.
"""
    response = llm.invoke([
        SystemMessage(content="You are a professional AI flight booking and travel advisor."),
        HumanMessage(content=prompt),
    ])
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def build_booking_graph():
    """Build and compile the LangGraph workflow once per application process."""
    llm = create_llm()

    graph = StateGraph(TravelState)
    graph.add_node("flight_intelligence", flight_intelligence_agent)
    graph.add_node("hotel_research", hotel_research_agent)
    graph.add_node("itinerary_planning", lambda state: itinerary_planning_agent(state, llm))
    graph.add_node("booking_advisor", lambda state: booking_advisor_agent(state, llm))

    graph.add_edge(START, "flight_intelligence")
    graph.add_edge("flight_intelligence", "hotel_research")
    graph.add_edge("hotel_research", "itinerary_planning")
    graph.add_edge("itinerary_planning", "booking_advisor")
    graph.add_edge("booking_advisor", END)

    connection = psycopg.connect(
        get_database_url(),
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=10,
    )
    checkpointer = PostgresSaver(connection)
    checkpointer.setup()
    return graph.compile(checkpointer=checkpointer)


def get_booking_graph():
    """Lazily initialize the workflow so /health can work without API secrets."""
    global _TRAVEL_GRAPH
    if _TRAVEL_GRAPH is None:
        with _CHECKPOINT_LOCK:
            if _TRAVEL_GRAPH is None:
                _TRAVEL_GRAPH = build_booking_graph()
    return _TRAVEL_GRAPH


def run_booking_agent(user_input: str, thread_id: str | None = None):
    """Run one persisted Agentic AI conversation."""
    message = user_input.strip()
    if not message:
        raise ValueError("Travel request cannot be empty.")

    thread_id = thread_id or f"user_{uuid.uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}

    result = get_booking_graph().invoke(
        {
            "messages": [HumanMessage(content=message)],
            "user_query": message,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0,
        },
        config=config,
    )

    return {
        "thread_id": thread_id,
        "answer": result["messages"][-1].content,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }


# Backward-compatible alias for existing scripts.
run_travel_agent = run_booking_agent
