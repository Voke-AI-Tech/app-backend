from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import EvaluateTopicalRequest
from backend.pipelines.topical_speech import topical_speech_pipeline
from backend.services.audio_utils import transcribe_audio_async
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
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio_file:
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
        segments = await transcribe_audio_async(tmp_audio_path)
        if not segments:
            logger.warning("No speech detected in audio.")
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        logger.info("Transcription completed.")
        
        duration_seconds = segments[-1].end if segments else 0
        
        # Run pipeline
        logger.info("Running evaluation pipeline...")
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
