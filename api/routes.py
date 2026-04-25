from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import (
    EvaluateTopicalRequest,
    LiveStartRequest, LiveStartResponse,
    LiveTurnRequest, LiveTurnResponse,
    LiveEndRequest, LiveEndResponse,
    ScenarioListResponse,
    CompanionStartRequest, CompanionStartResponse,
    CompanionTurnRequest, CompanionTurnResponse,
    CompanionEndRequest, CompanionEndResponse,
)
import os
import httpx
import tempfile
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def _cleanup_audio_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Successfully deleted temporary file: {path}")
    except Exception as e:
        logger.warning(f"Failed to delete temporary file {path}: {e}")

@router.post("/evaluate/topical")
async def evaluate_topical(request: EvaluateTopicalRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received evaluation request for: {request.name}")
    tmp_audio_path = None
    try:
        # Preserve original extension so Whisper detects the format correctly
        audio_url_path = request.audio_url.split("?")[0]
        ext = os.path.splitext(audio_url_path)[-1] or ".m4a"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_audio_file:
            tmp_audio_path = tmp_audio_file.name
            logger.info(f"Downloading audio to {tmp_audio_path}...")
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(request.audio_url, timeout=30.0)
                    if response.status_code != 200:
                        raise HTTPException(status_code=400, detail=f"Failed to download audio. Status: {response.status_code}")
                    tmp_audio_file.write(response.content)
                except httpx.RequestError as e:
                    raise HTTPException(status_code=400, detail=f"Network error while downloading audio: {str(e)}")
            tmp_audio_file.close() 
            
        # Transcribe audio
        logger.info("Starting transcription...")
        from services.audio_utils import transcribe_audio_async
        segments = await transcribe_audio_async(tmp_audio_path)
        if not segments:
            logger.warning("No speech detected in audio.")
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        logger.info("Transcription completed.")
        
        duration_seconds = segments[-1].end if segments else 0
        
        # Run pipeline
        logger.info("Running evaluation pipeline...")
        from pipelines.topical_speech import topical_speech_pipeline
        results = await topical_speech_pipeline(
            name=request.name,
            audio_path=tmp_audio_path,
            segments=segments,
            duration_seconds=duration_seconds
        )
        
        # Format response contract
        response_data = {
            "scores": {
                "overall": results["overall_score"],
                "grammar": results["grammar_score"],
                "vocabulary": results["vocabulary_score"],
                "fluency": results["fluency_score"],
                "pronunciation": results["pronunciation_score"],
                "filler_words": results["filler_score"]
            },
            "feedback": {
                "improved_lines": results["improved_lines"],
                "mispronounced_words": results["mispronounced_words"],
                "summary_points": results["summary_points"]
            },
            "metrics": {
                "words_per_minute": results["words_per_minute"],
                "word_count": results["word_count"],
                "pause_count": results["pause_count"],
                "filler_words_data": results["filler_words_data"],
                "fluency_over_time": results["fluency_over_time"],
            },
            "transcription": " ".join([getattr(seg, "text", "") for seg in segments]),
            "pdf_filename": results.get("pdf_filename"),
            "warnings": []
        }
        
        if not results.get("pdf_filename"):
            response_data["warnings"].append("PDF report generation failed, but scores are available.")

        logger.info(f"Evaluation request for {request.name} processed successfully.")
        return response_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Internal server error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during processing.")
    finally:
        if tmp_audio_path:
            background_tasks.add_task(_cleanup_audio_file, tmp_audio_path)


# ---------------------------------------------------------------------------
# Live Mode
# ---------------------------------------------------------------------------

@router.post("/live/start", response_model=LiveStartResponse)
async def live_start(request: LiveStartRequest):
    """Start a Live conversation session. Returns a session_id and the system's opening line."""
    if not (1 <= request.duration_minutes <= 5):
        raise HTTPException(status_code=400, detail="duration_minutes must be between 1 and 5.")

    from services.session_store import create_session, add_turn
    from services.llm import generate_live_opening

    session_id = create_session(request.name, request.duration_minutes)
    opening = generate_live_opening()
    add_turn(session_id, role="system", text=opening)

    logger.info(f"Live session started: {session_id} for {request.name}")
    return LiveStartResponse(session_id=session_id, system_message=opening)


@router.post("/live/turn", response_model=LiveTurnResponse)
async def live_turn(request: LiveTurnRequest, background_tasks: BackgroundTasks):
    """Submit a user audio turn. Returns the transcription and system's reply."""
    from services.session_store import get_session, add_turn, is_expired

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session["ended"]:
        raise HTTPException(status_code=400, detail="Session has already ended.")
    if is_expired(request.session_id):
        raise HTTPException(status_code=400, detail="Session time has expired. Please call /live/end.")

    tmp_audio_path = None
    try:
        # Preserve original extension so Whisper and pydub detect the format correctly
        audio_url_path = request.audio_url.split("?")[0]
        ext = os.path.splitext(audio_url_path)[-1] or ".m4a"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp_audio_path = tmp.name
            async with httpx.AsyncClient() as client:
                response = await client.get(request.audio_url, timeout=30.0)
                if response.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to download audio. Status: {response.status_code}")
                audio_bytes = response.content
                tmp.write(audio_bytes)

        from services.audio_utils import transcribe_audio_async
        segments = await transcribe_audio_async(tmp_audio_path)
        if not segments:
            raise HTTPException(status_code=400, detail="No speech detected in audio.")

        user_text = " ".join(getattr(seg, "text", "") for seg in segments).strip()
        add_turn(request.session_id, role="user", text=user_text, segments=segments, audio_bytes=audio_bytes)

        from services.llm import generate_live_reply
        reply = generate_live_reply(session["turns"])
        add_turn(request.session_id, role="system", text=reply)

        logger.info(f"Live turn {session['turn_number']} for session {request.session_id}")
        return LiveTurnResponse(
            system_message=reply,
            user_transcript=user_text,
            turn_number=session["turn_number"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in live turn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    finally:
        if tmp_audio_path:
            background_tasks.add_task(_cleanup_audio_file, tmp_audio_path)


@router.post("/live/end", response_model=LiveEndResponse)
async def live_end(request: LiveEndRequest):
    """End the Live session and return the full evaluation report."""
    from services.session_store import get_session, end_session, delete_session

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session["ended"]:
        raise HTTPException(status_code=400, detail="Session has already ended.")

    end_session(request.session_id)

    if not session["segments_all"]:
        delete_session(request.session_id)
        raise HTTPException(status_code=400, detail="No speech recorded in this session.")

    try:
        from pipelines.live_conversation import live_conversation_pipeline
        results = await live_conversation_pipeline(name=session["name"], session=session)

        if not results:
            raise HTTPException(status_code=500, detail="Evaluation pipeline returned no results.")

        response_data = LiveEndResponse(
            scores={
                "overall": results["overall_score"],
                "grammar": results["grammar_score"],
                "vocabulary": results["vocabulary_score"],
                "fluency": results["fluency_score"],
                "pronunciation": results["pronunciation_score"],
                "filler_words": results["filler_score"],
            },
            feedback={
                "improved_lines": results["improved_lines"],
                "mispronounced_words": results["mispronounced_words"],
                "summary_points": results["summary_points"],
            },
            metrics={
                "words_per_minute": results["words_per_minute"],
                "word_count": results["word_count"],
                "pause_count": results["pause_count"],
                "filler_words_data": results["filler_words_data"],
                "fluency_over_time": results["fluency_over_time"],
            },
            transcription=results["full_text"],
            pdf_filename=results.get("pdf_filename"),
            warnings=[] if results.get("pdf_filename") else ["PDF report generation failed, but scores are available."],
        )

        logger.info(f"Live session {request.session_id} evaluated successfully.")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating live session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during evaluation.")
    finally:
        delete_session(request.session_id)


# ---------------------------------------------------------------------------
# Companion Mode
# ---------------------------------------------------------------------------

@router.get("/companion/scenarios", response_model=ScenarioListResponse)
async def get_scenarios():
    """Return the list of available companion scenarios."""
    from services.llm import get_all_scenarios
    return ScenarioListResponse(scenarios=get_all_scenarios())


@router.post("/companion/start", response_model=CompanionStartResponse)
async def companion_start(request: CompanionStartRequest):
    """Start a Companion session with a specific scenario/role."""
    if not (1 <= request.duration_minutes <= 5):
        raise HTTPException(status_code=400, detail="duration_minutes must be between 1 and 5.")

    from services.llm import get_scenario, generate_companion_opening
    from services.session_store import create_session, add_turn

    scenario = get_scenario(request.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{request.scenario_id}' not found.")

    session_id = create_session(request.name, request.duration_minutes)
    # Store scenario on the session so turns can access it
    from services.session_store import get_session
    get_session(session_id)["scenario"] = scenario

    opening = generate_companion_opening(scenario)
    add_turn(session_id, role="system", text=opening)

    logger.info(f"Companion session started: {session_id}, scenario: {request.scenario_id}")
    return CompanionStartResponse(
        session_id=session_id,
        scenario_title=scenario["title"],
        scenario_description=scenario["description"],
        system_message=opening,
    )


@router.post("/companion/turn", response_model=CompanionTurnResponse)
async def companion_turn(request: CompanionTurnRequest, background_tasks: BackgroundTasks):
    """Submit a user audio turn in a Companion session."""
    from services.session_store import get_session, add_turn, is_expired

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session["ended"]:
        raise HTTPException(status_code=400, detail="Session has already ended.")
    if is_expired(request.session_id):
        raise HTTPException(status_code=400, detail="Session time has expired. Please call /companion/end.")
    if "scenario" not in session:
        raise HTTPException(status_code=400, detail="Session is not a Companion session.")

    tmp_audio_path = None
    try:
        # Preserve original extension so Whisper and pydub detect the format correctly
        audio_url_path = request.audio_url.split("?")[0]
        ext = os.path.splitext(audio_url_path)[-1] or ".m4a"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp_audio_path = tmp.name
            async with httpx.AsyncClient() as client:
                response = await client.get(request.audio_url, timeout=30.0)
                if response.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to download audio. Status: {response.status_code}")
                audio_bytes = response.content
                tmp.write(audio_bytes)

        from services.audio_utils import transcribe_audio_async
        segments = await transcribe_audio_async(tmp_audio_path)
        if not segments:
            raise HTTPException(status_code=400, detail="No speech detected in audio.")

        user_text = " ".join(getattr(seg, "text", "") for seg in segments).strip()
        add_turn(request.session_id, role="user", text=user_text, segments=segments, audio_bytes=audio_bytes)

        from services.llm import generate_companion_reply
        reply = generate_companion_reply(session["scenario"], session["turns"])
        add_turn(request.session_id, role="system", text=reply)

        logger.info(f"Companion turn {session['turn_number']} for session {request.session_id}")
        return CompanionTurnResponse(
            system_message=reply,
            user_transcript=user_text,
            turn_number=session["turn_number"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in companion turn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    finally:
        if tmp_audio_path:
            background_tasks.add_task(_cleanup_audio_file, tmp_audio_path)


@router.post("/companion/end", response_model=CompanionEndResponse)
async def companion_end(request: CompanionEndRequest):
    """End the Companion session and return the full evaluation report."""
    from services.session_store import get_session, end_session, delete_session

    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session["ended"]:
        raise HTTPException(status_code=400, detail="Session has already ended.")

    end_session(request.session_id)

    if not session["segments_all"]:
        delete_session(request.session_id)
        raise HTTPException(status_code=400, detail="No speech recorded in this session.")

    try:
        from pipelines.companion_conversation import companion_conversation_pipeline
        results = await companion_conversation_pipeline(name=session["name"], session=session)

        if not results:
            raise HTTPException(status_code=500, detail="Evaluation pipeline returned no results.")

        response_data = CompanionEndResponse(
            scores={
                "overall": results["overall_score"],
                "grammar": results["grammar_score"],
                "vocabulary": results["vocabulary_score"],
                "fluency": results["fluency_score"],
                "pronunciation": results["pronunciation_score"],
                "filler_words": results["filler_score"],
            },
            feedback={
                "improved_lines": results["improved_lines"],
                "mispronounced_words": results["mispronounced_words"],
                "summary_points": results["summary_points"],
            },
            metrics={
                "words_per_minute": results["words_per_minute"],
                "word_count": results["word_count"],
                "pause_count": results["pause_count"],
                "filler_words_data": results["filler_words_data"],
                "fluency_over_time": results["fluency_over_time"],
            },
            transcription=results["full_text"],
            pdf_filename=results.get("pdf_filename"),
            warnings=[] if results.get("pdf_filename") else ["PDF report generation failed, but scores are available."],
        )

        logger.info(f"Companion session {request.session_id} evaluated successfully.")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating companion session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during evaluation.")
    finally:
        delete_session(request.session_id)
