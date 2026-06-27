"""Typed, validated answer schemas for the Copilot (structured outputs).

The agent must fill one of these instead of replying with free prose, so the rest
of the app (UI cards, the map) gets clean, labeled data.
"""
from pydantic import BaseModel, Field


class Arrival(BaseModel):
    route: str
    eta_minutes: int | None = Field(None, description="Minutes until arrival, if known.")
    status: str = Field(description="Human-readable, e.g. 'on time', '~3 min late', '2 min early'.")


class ArrivalAnswer(BaseModel):
    """Use for questions about predicted arrivals / ETAs at a specific stop."""
    stop: str
    arrivals: list[Arrival]
    summary: str


class IncidentReport(BaseModel):
    """The Watchdog's structured finding about a detected anomaly."""
    kind: str = Field(description="'bunching', 'delay', or 'gap'.")
    route_id: str | None = Field(None, description="The affected MBTA route, if any.")
    severity: str = Field(description="'low', 'medium', or 'high'.")
    summary: str = Field(description="One or two sentences a rider would understand.")
    likely_cause: str = Field(description="The most plausible cause, given the evidence.")


class Answer(BaseModel):
    """Use for any other transit question (positions, alerts, general info)."""
    summary: str = Field(description="The natural-language answer.")
    routes: list[str] = Field(default_factory=list, description="MBTA routes referenced.")
    facts: list[str] = Field(default_factory=list, description="Concrete supporting data points.")
    sources: list[str] = Field(
        default_factory=list,
        description="Titles of any policy/alert documents cited (from search_docs).",
    )
