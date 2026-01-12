from pydantic import BaseModel

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
