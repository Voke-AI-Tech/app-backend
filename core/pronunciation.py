import os
import re
import uuid
import io
from pydub import AudioSegment
from pathlib import Path

# Assuming a temporary directory for word clips, which should be managed by the application.
# For a production setup, consider a more robust way to handle temporary files/storage.
WORD_CLIPS_TEMP_DIR = Path("temp_word_clips")
# Moved mkdir call to a function that's called when needed, to avoid issues on import

def pronunciation_score_f(clips: list[tuple[str, str, float]]) -> float:
    if not clips:
        return 0.0
    avg_score = sum([score for _, _, score in clips]) / len(clips)
    return round(avg_score * 100, 2)

def find_mispronounced_words(clips: list[tuple[str, str, float]], threshold: float = 0.7) -> list[tuple[str, str]]:
    seen = set()
    unique_mispronounced = []
    for word, path, score in clips:
        if score < threshold and word.lower() not in seen:
            unique_mispronounced.append((word, path))
            seen.add(word.lower())
    return unique_mispronounced

def extract_word_audio_clips(audio_buffer: io.BytesIO, segments: list) -> list[tuple[str, str, float]]:
    os.makedirs(WORD_CLIPS_TEMP_DIR, exist_ok=True)
    audio_buffer.seek(0) # Reset buffer to start
    audio = AudioSegment.from_file(audio_buffer) # Load from buffer
    clips = []
    for seg in segments:
        for w in seg.words:
            if hasattr(w, "start") and hasattr(w, "end") and hasattr(w, "word") and hasattr(w, "probability"):
                start = int(float(w.start) * 1000)
                end = int(float(w.end) * 1000)
                word_audio = audio[start:end]
                safe_word = re.sub(r'[^a-zA-Z0-9_-]', '', w.word.strip())
                clip_name = f"{uuid.uuid4().hex[:8]}_{safe_word}.wav"
                out_path = WORD_CLIPS_TEMP_DIR / clip_name
                word_audio.export(out_path, format="wav")
                clips.append((w.word.strip(), str(out_path), float(w.probability)))
    return clips
