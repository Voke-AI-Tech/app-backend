import uuid
import time
from typing import Optional

# In-memory store: session_id -> session dict
_sessions: dict[str, dict] = {}

def create_session(name: str, duration_minutes: int) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "name": name,
        "duration_seconds": duration_minutes * 60,
        "started_at": time.time(),
        "turns": [],          # list of {"role": "user"|"system", "text": str}
        "segments_all": [],   # accumulated Whisper segments across turns
        "audio_chunks": [],   # raw audio bytes per turn (for pronunciation)
        "turn_number": 0,
        "ended": False,
    }
    return session_id

def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)

def add_turn(session_id: str, role: str, text: str, segments: list = None, audio_bytes: bytes = None):
    session = _sessions[session_id]
    session["turns"].append({"role": role, "text": text})
    session["turn_number"] += 1 if role == "user" else 0
    if segments:
        session["segments_all"].extend(segments)
    if audio_bytes:
        session["audio_chunks"].append(audio_bytes)

def end_session(session_id: str):
    if session_id in _sessions:
        _sessions[session_id]["ended"] = True

def delete_session(session_id: str):
    _sessions.pop(session_id, None)

def is_expired(session_id: str) -> bool:
    session = _sessions.get(session_id)
    if not session:
        return True
    elapsed = time.time() - session["started_at"]
    return elapsed >= session["duration_seconds"]
