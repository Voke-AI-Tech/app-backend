from google.genai import Client
from google.genai.types import Model
from config.settings import Settings
import re
import random
import logging

settings = Settings()
logger = logging.getLogger(__name__)

# New library initialization
client = None
if settings.GOOGLE_API_KEY:
    try:
        client = Client(api_key=settings.GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")

def get_gemini_response(prompt: str) -> str | None:
    if not client:
        logger.warning("Gemini client not initialized. Skipping AI call.")
        return None
        
    try:
        logger.info("Starting Gemini AI call...")
        response = client.models.generate_content(
            model=settings.MODEL,
            contents=prompt
        )
        logger.info("Gemini AI call completed successfully.")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        return None

def generate_hints(topic: str) -> list[str]:
    raw_response = get_gemini_response(prompt=f"""
    You are a smart hint generator. Generate 5 concise hints related to the topic "{topic.strip()}".
    Respond strictly with the 5 hints as a numbered list. No extra text.
    
    Example:
    1. What are AVs? (self-driving cars)
    2. AI decisions (navigation, sensors)
    3. Benefits (saftey, traffic)
    4. Challenges (laws, accidents)
    5. Future use (public roads)"
    """
    )
    
    hints = []
    if raw_response:
        for line in raw_response.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                hint = line.split(".", 1)[-1].strip()
                hints.append(hint)

    return hints

def improve_fluency_by_line(segments: list[dict]) -> list[dict]:
    lines = [seg["text"].strip() for seg in segments]
    
    # Optional: Skip AI if too many lines or other constraints
    if not client:
        return [{"original": line, "improved": line, "boost": 0.0} for line in lines]

    prompt = "Revise the following sentences to sound more fluent and natural while preserving the meaning. Avoid repeating the input. Return each improved sentence on its own line, in the same order:\n\n"
    for i, line in enumerate(lines, start=1):
        prompt += f"{i}. {line}\n"

    try:
        response = get_gemini_response(prompt)
        if response:
            improved_lines = response.strip().splitlines()
        else:
            improved_lines = lines # fallback if no response
    except Exception:
        improved_lines = lines  # fallback on error

    result = []
    for original, improved in zip(lines, improved_lines):
        score_boost = round(random.uniform(2, 8), 2) # Temporary placeholder
        result.append({
            "original": original,
            "improved": improved.lstrip("1234567890. ").strip(),
            "boost": score_boost
        })
    return result

def is_filler_in_context(sentence: str, phrase: str) -> bool:
    if not client:
        return False

    prompt = f"""
    Analyze the sentence: "{sentence}"
    Is the phrase "{phrase}" used as a conversational filler (a word that adds no meaning)?
    For example, in "It was, like, cold," \'like\' is a filler. But in "I like cold weather," \'like\' is not.
    Answer with only \'Yes\' or \'No\'.
    """
    
    try:
        response = get_gemini_response(prompt)
        answer = response.strip().lower() if response else ""
        return answer == "yes"
    except Exception as e:
        logger.error(f"An error occurred with the Gemini API call for filler check: {e}")
        return False

def generate_report_summary_text(transcript: str, overall_score: float, grammar_score: float, vocabulary_score: float, fluency_score: float, pronunciation_score: float, filler_word_score: float) -> list[str]:
    if not client:
        return ["AI summary skipped: Gemini client not available."]

    prompt = f"""
    Generate a concise 3-point summary for a speech analysis report.
    The speaker\'s overall performance was {overall_score}%. 
    Grammar: {grammar_score}%, Vocabulary: {vocabulary_score}%, Fluency: {fluency_score}%, Pronunciation: {pronunciation_score}%, Filler Words: {filler_word_score}%. 
    Here is the transcript:
    "{transcript}"

    Provide a summary that highlights key strengths and areas for improvement based on the scores and transcript.
    Format the summary as an numbered list (1. ... 2. ... 3. ...).
    Each point should be a short, actionable insight or observation.
    """
    
    try:
        summary_text = get_gemini_response(prompt)
        if summary_text:
            points = re.split(r"^\d+\.\s*", summary_text, flags=re.MULTILINE)
            clean_points = [p.strip() for p in points if p.strip()]
            return clean_points
        return ["No summary available due to API error."]
    except Exception as e:
        logger.error(f"Error generating report summary: {e}")
        return ["Error generating summary due to API error."]
