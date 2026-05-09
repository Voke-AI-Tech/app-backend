from config.settings import Settings
import re
import random
import logging

settings = Settings()
logger = logging.getLogger(__name__)

client = None

def _get_client():
    global client
    if client is not None:
        return client
    if settings.GOOGLE_API_KEY:
        try:
            from google.genai import Client
            client = Client(api_key=settings.GOOGLE_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
    return client

def get_gemini_response(prompt: str) -> str | None:
    current_client = _get_client()
    if not current_client:
        logger.warning("Gemini client not initialized. Skipping AI call.")
        return None
    try:
        logger.info("Starting Gemini AI call...")
        response = current_client.models.generate_content(
            model=settings.MODEL,
            contents=prompt
        )
        logger.info("Gemini AI call completed successfully.")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        return None

def generate_hints(topic: str) -> list[str]:
    raw_response = get_gemini_response(
        f"""You are a smart hint generator. Generate 5 concise hints related to the topic "{topic.strip()}".
Respond strictly with the 5 hints as a numbered list. No extra text.

Example:
1. What are AVs? (self-driving cars)
2. AI decisions (navigation, sensors)
3. Benefits (safety, traffic)
4. Challenges (laws, accidents)
5. Future use (public roads)"""
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
    if not _get_client():
        return [{"original": line, "improved": line, "boost": 0.0} for line in lines]

    prompt = "Revise the following sentences to sound more fluent and natural while preserving the meaning. Avoid repeating the input. Return each improved sentence on its own line, in the same order:\n\n"
    for i, line in enumerate(lines, start=1):
        prompt += f"{i}. {line}\n"

    try:
        response = get_gemini_response(prompt)
        improved_lines = response.strip().splitlines() if response else lines
    except Exception:
        improved_lines = lines

    result = []
    for original, improved in zip(lines, improved_lines):
        score_boost = round(random.uniform(2, 8), 2)
        result.append({
            "original": original,
            "improved": improved.lstrip("1234567890. ").strip(),
            "boost": score_boost
        })
    return result

def is_filler_in_context(sentence: str, phrase: str) -> bool:
    if not _get_client():
        return False
    prompt = f"""Analyze the sentence: "{sentence}"
Is the phrase "{phrase}" used as a conversational filler (a word that adds no meaning)?
For example, in "It was, like, cold," 'like' is a filler. But in "I like cold weather," 'like' is not.
Answer with only 'Yes' or 'No'."""
    try:
        response = get_gemini_response(prompt)
        return (response or "").strip().lower() == "yes"
    except Exception as e:
        logger.error(f"Gemini filler check error: {e}")
        return False

def generate_live_opening() -> str:
    """Generate the system's opening line for a Live conversation."""
    prompt = """You are starting a casual, friendly real-life English conversation with someone who wants to practice speaking.
Say a natural, short opening line (1-2 sentences) like you would say to someone you just met or are having a daily chat with.
Keep it simple and open-ended so they have something to respond to.
Only return the opening line, nothing else."""
    response = get_gemini_response(prompt)
    return response if response else "Hey! How's your day going so far?"

def generate_live_reply(conversation_history: list[dict]) -> str:
    """Generate the system's next reply given the full conversation history.

    conversation_history: list of {"role": "user"|"system", "text": str}
    """
    current_client = _get_client()
    if not current_client:
        logger.error("generate_live_reply: Gemini client not initialized — check GOOGLE_API_KEY.")
        return "[AI unavailable: API key missing]"

    history_text = ""
    for turn in conversation_history:
        label = "You" if turn["role"] == "system" else "User"
        history_text += f"{label}: {turn['text']}\n"

    prompt = f"""You are having a casual, friendly real-life English conversation with someone practicing speaking.
Here is the conversation so far:

{history_text}
Now respond naturally as "You" in 1-2 sentences. Keep it conversational, engaging, and ask a follow-up question or make a comment that keeps the conversation going.
Only return your reply, nothing else."""

    try:
        response = current_client.models.generate_content(
            model=settings.MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"generate_live_reply Gemini error: {e}")
        return f"[AI error: {str(e)}]"

# ---------------------------------------------------------------------------
# Companion mode — scenario catalogue & role-aware Gemini functions
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "airport_stranger": {
        "id": "airport_stranger",
        "title": "Stranger at the Airport",
        "description": "You're sitting next to a friendly stranger at an airport waiting lounge. Strike up a casual chat.",
        "formality": "informal",
        "system_persona": "You are a friendly traveller sitting in an airport waiting lounge. You just noticed the user sitting next to you and decided to start a casual conversation. Stay in character — be warm, curious, and natural. Ask about their destination, travel stories, or anything light.",
    },
    "professor_office": {
        "id": "professor_office",
        "title": "Meeting a Professor",
        "description": "You've gone to your professor's office to discuss your assignment or ask for guidance.",
        "formality": "formal",
        "system_persona": "You are a university professor in your office. A student has come to speak with you. Be polite but formal — ask about their coursework, offer academic advice, and respond as a knowledgeable but approachable professor would.",
    },
    "job_interview": {
        "id": "job_interview",
        "title": "Job Interview",
        "description": "You're being interviewed for a job. The interviewer asks questions about your background and goals.",
        "formality": "formal",
        "system_persona": "You are a professional interviewer conducting a job interview. Ask common interview questions — about the candidate's background, strengths, goals, and why they want the role. Be polite, professional, and encouraging but evaluative.",
    },
    "coffee_shop_friend": {
        "id": "coffee_shop_friend",
        "title": "Catching Up with a Friend",
        "description": "You're meeting a friend at a coffee shop. Catch up on life, plans, and recent events.",
        "formality": "informal",
        "system_persona": "You are an old friend meeting the user at a coffee shop after a long time. Be warm, casual, and excited to catch up. Ask about their life, share anecdotes, and keep the conversation light and fun.",
    },
    "hotel_checkin": {
        "id": "hotel_checkin",
        "title": "Hotel Check-in",
        "description": "You're checking into a hotel. The receptionist helps you with your booking and answers questions.",
        "formality": "formal",
        "system_persona": "You are a polite hotel receptionist at the front desk. Greet the guest warmly, ask for their booking details, explain hotel facilities, and handle any requests professionally.",
    },
    "doctor_appointment": {
        "id": "doctor_appointment",
        "title": "Doctor's Appointment",
        "description": "You're visiting a doctor for a routine check-up or to discuss a health concern.",
        "formality": "formal",
        "system_persona": "You are a friendly but professional doctor. Ask the patient about their symptoms, health history, and concerns. Offer general advice and reassurance. Keep the tone calm and clinical.",
    },
    "restaurant_order": {
        "id": "restaurant_order",
        "title": "Ordering at a Restaurant",
        "description": "You're at a restaurant. The waiter takes your order and helps with menu questions.",
        "formality": "informal",
        "system_persona": "You are a cheerful waiter at a mid-range restaurant. Greet the customer, describe the specials, take their order, and respond naturally to any questions about the menu.",
    },
    "new_colleague": {
        "id": "new_colleague",
        "title": "Meeting a New Colleague",
        "description": "It's your first day at a new job and you're meeting a colleague for the first time.",
        "formality": "semi-formal",
        "system_persona": "You are a friendly colleague at a workplace, welcoming someone on their first day. Ask about their background, explain the work culture, and make them feel at ease. Keep the tone professional but warm.",
    },
}

def get_all_scenarios() -> list[dict]:
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "formality": s["formality"],
        }
        for s in SCENARIOS.values()
    ]

def get_scenario(scenario_id: str) -> dict | None:
    return SCENARIOS.get(scenario_id)

def generate_companion_opening(scenario: dict) -> str:
    """Generate the character's opening line for a Companion scenario."""
    prompt = f"""{scenario['system_persona']}

Start the conversation with a natural, short opening line (1-2 sentences) that fits your role and the situation.
Only return the opening line, nothing else."""
    response = get_gemini_response(prompt)
    return response if response else "Hello! How can I help you today?"

def generate_companion_reply(scenario: dict, conversation_history: list[dict]) -> str:
    """Generate the character's next reply staying in role."""
    current_client = _get_client()
    if not current_client:
        logger.error("generate_companion_reply: Gemini client not initialized — check GOOGLE_API_KEY.")
        return "[AI unavailable: API key missing]"

    history_text = ""
    for turn in conversation_history:
        label = "You" if turn["role"] == "system" else "User"
        history_text += f"{label}: {turn['text']}\n"

    prompt = f"""{scenario['system_persona']}

Here is the conversation so far:
{history_text}
Stay strictly in character. Respond naturally as "You" in 1-2 sentences. Keep the conversation going.
Only return your reply, nothing else."""

    try:
        response = current_client.models.generate_content(
            model=settings.MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"generate_companion_reply Gemini error: {e}")
        return f"[AI error: {str(e)}]"

def generate_report_summary_text(transcript: str, overall_score: float, grammar_score: float, vocabulary_score: float, fluency_score: float, pronunciation_score: float, filler_word_score: float) -> list[str]:
    if not _get_client():
        return ["AI summary skipped: Gemini client not available."]

    prompt = f"""Generate a concise 3-point summary for a speech analysis report.
The speaker's overall performance was {overall_score}%.
Grammar: {grammar_score}%, Vocabulary: {vocabulary_score}%, Fluency: {fluency_score}%, Pronunciation: {pronunciation_score}%, Filler Words: {filler_word_score}%.
Here is the transcript:
"{transcript}"

Provide a summary that highlights key strengths and areas for improvement based on the scores and transcript.
Format the summary as a numbered list (1. ... 2. ... 3. ...).
Each point should be a short, actionable insight or observation."""

    try:
        summary_text = get_gemini_response(prompt)
        if summary_text:
            points = re.split(r"^\d+\.\s*", summary_text, flags=re.MULTILINE)
            return [p.strip() for p in points if p.strip()]
        return ["No summary available due to API error."]
    except Exception as e:
        logger.error(f"Error generating report summary: {e}")
        return ["Error generating summary due to API error."]
