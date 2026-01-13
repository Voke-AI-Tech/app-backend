import nltk
import re
import io
from pydub import AudioSegment
from services.llm import is_filler_in_context

def extract_word_and_text(segments: list) -> tuple[list[str], str]:
    words = [w.word.strip() for seg in segments for w in seg.words]
    full_text = " ".join(words)
    return words, full_text

def analyze_pauses_for_fillers(audio_buffer: io.BytesIO, segments: list, pause_threshold: float = 0.3, energy_threshold: int = 250) -> tuple[list[tuple[float, float, float]], int]:
    audio_buffer.seek(0) # Reset buffer to start
    audio = AudioSegment.from_file(audio_buffer) # Load from buffer
    silent_pauses = []
    vocalized_filler_count = 0
    if not segments or len(segments) < 2:
        return [], 0
    for i in range(1, len(segments)):
        gap_start = float(segments[i - 1].end)
        gap_end = float(segments[i].start)
        gap_duration = gap_end - gap_start
        if gap_duration > pause_threshold:
            start_ms = int(gap_start * 1000)
            end_ms = int(gap_end * 1000)
            gap_audio = audio[start_ms:end_ms]
            if gap_audio.rms > energy_threshold:
                vocalized_filler_count += 1
            else:
                silent_pauses.append((gap_start, gap_end, gap_duration))
    return silent_pauses, vocalized_filler_count

def advanced_filler_analysis(full_text: str, vocalized_filler_count: int) -> tuple[dict, float]:
    POTENTIAL_FILLERS = {"like", "so", "right", "you know", "basically", "actually"}
    sentences = nltk.sent_tokenize(full_text)
    contextual_filler_count = 0
    filler_details = {}

    for phrase in POTENTIAL_FILLERS:
        for sentence in sentences:
            if re.search(r"\b" + re.escape(phrase) + r"\b", sentence, re.IGNORECASE):
                if is_filler_in_context(sentence, phrase):
                    contextual_filler_count += 1
                    filler_details[phrase] = filler_details.get(phrase, 0) + 1
    
    total_fillers = contextual_filler_count + vocalized_filler_count
    if vocalized_filler_count > 0:
        filler_details["uh/um (vocalized)"] = vocalized_filler_count

    total_words = len(full_text.split())
    filler_percent = round(100 * total_fillers / max(1, total_words), 2)
    return filler_details, filler_percent
