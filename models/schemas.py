from pydantic import BaseModel
from typing import Optional

class EvaluateTopicalRequest(BaseModel):
    audio_url: str
    name: str = "Guest"

class EvaluateTopicalResponse(BaseModel):
    overall_score: float
    grammar_score: float
    vocabulary_score: float
    fluency_score: float
    pronunciation_score: float
    filler_score: float
    improved_lines: list[dict]
    mispronounced_words: list[tuple]
    summary_points: list[str]
    pdf_filename: str

# Live mode schemas
class LiveStartRequest(BaseModel):
    name: str = "Guest"
    duration_minutes: int = 2  # 1–5 minutes

class LiveStartResponse(BaseModel):
    session_id: str
    system_message: str  # The opening line the system says

class LiveTurnRequest(BaseModel):
    session_id: str
    audio_url: str

class LiveTurnResponse(BaseModel):
    system_message: str  # System's reply to the user
    user_transcript: str  # What the user said this turn
    turn_number: int

class LiveEndRequest(BaseModel):
    session_id: str

class LiveEndResponse(BaseModel):
    scores: dict
    feedback: dict
    metrics: dict
    transcription: str
    pdf_filename: Optional[str] = None
    warnings: list[str] = []

# Companion mode schemas
class ScenarioListResponse(BaseModel):
    scenarios: list[dict]  # list of {id, title, description, formality}

class CompanionStartRequest(BaseModel):
    name: str = "Guest"
    duration_minutes: int = 2  # 1–5 minutes
    scenario_id: str  # e.g. "airport_stranger"

class CompanionStartResponse(BaseModel):
    session_id: str
    scenario_title: str
    scenario_description: str
    system_message: str  # The character's opening line

class CompanionTurnRequest(BaseModel):
    session_id: str
    audio_url: str

class CompanionTurnResponse(BaseModel):
    system_message: str
    user_transcript: str
    turn_number: int

class CompanionEndRequest(BaseModel):
    session_id: str

class CompanionEndResponse(BaseModel):
    scores: dict
    feedback: dict
    metrics: dict
    transcription: str
    pdf_filename: Optional[str] = None
    warnings: list[str] = []
