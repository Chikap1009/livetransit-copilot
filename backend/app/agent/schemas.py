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


class Answer(BaseModel):
    """Use for any other transit question (positions, alerts, general info)."""
    summary: str = Field(description="The natural-language answer.")
    routes: list[str] = Field(default_factory=list, description="MBTA routes referenced.")
    facts: list[str] = Field(default_factory=list, description="Concrete supporting data points.")
