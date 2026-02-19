import asyncio
import warnings
from config.settings import Settings

warnings.filterwarnings("ignore")

_faster_model = None
settings = Settings()

def _init_faster_model_if_needed():
    global _faster_model
    if _faster_model is not None:
        return _faster_model

    try:
        from faster_whisper import WhisperModel
    except Exception:
        WhisperModel = None

    try:
        import torch
    except Exception:
        torch = None

    device = settings.DEVICE
    compute_type = settings.COMPUTE_TYPE
    if torch is not None and torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"

    if WhisperModel is None:
        raise RuntimeError("faster_whisper is not available in this environment")

    _faster_model = WhisperModel(settings.WHISPER_MODEL, device=device, compute_type=compute_type)
    return _faster_model

def transcribe_audio_library(path: str) -> list:
    model = _init_faster_model_if_needed()
    segments_gen, _ = model.transcribe(path, word_timestamps=True)
    return list(segments_gen)


async def transcribe_audio_async(path: str) -> list:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transcribe_audio_library, path)
