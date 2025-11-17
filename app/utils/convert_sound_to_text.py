import librosa
import numpy as np
from fastapi import HTTPException, UploadFile

from app.utils.logger import logger


_MODEL_NAME = "openai/whisper-medium"
_processor = None
_model = None
_device = None


def _load_model():
    """Lazy load the Whisper model and processor."""
    global _processor, _model, _device

    if _processor is None or _model is None:
        import torch
        from transformers import WhisperProcessor, WhisperForConditionalGeneration

        _processor = WhisperProcessor.from_pretrained(_MODEL_NAME)
        _model = WhisperForConditionalGeneration.from_pretrained(_MODEL_NAME)
        _model.eval()
        _device = torch.device("cpu")
        _model.to(_device)  # type: ignore[method-call]

    return _processor, _model, _device


def chunk_audio(audio: np.ndarray, chunk_size: int = 30_000):
    """
    Splits audio into overlapping chunks to avoid memory issues.
    chunk_size is in samples (~2s at 16kHz = 32_000 samples)
    """
    chunks = []
    for start in range(0, len(audio), chunk_size):
        end = min(start + chunk_size, len(audio))
        chunks.append(audio[start:end])
    return chunks


def convert_sound_to_text(file: UploadFile) -> str:
    """
    Converts audio to text using the Whisper model.
    """
    try:
        # Lazy load model and processor
        processor, model, device = _load_model()

        # Load audio and resample to 16 kHz
        audio_np, sr = librosa.load(file.file, sr=16000)
        logger.info("Loaded audio with sample rate %d", sr)

        # Split into chunks
        audio_chunks = chunk_audio(audio_np, chunk_size=32_000)
        logger.info("Split audio into %d chunks", len(audio_chunks))

        # Lazy import torch for no_grad context
        import torch

        transcription = ""
        for chunk in audio_chunks:
            inputs = processor(chunk, sampling_rate=sr, return_tensors="pt")
            input_features = inputs.input_features.to(device)
            attention_mask = (
                inputs.attention_mask.to(device) if "attention_mask" in inputs else None
            )

            with torch.no_grad():
                predicted_ids = model.generate(
                    input_features,
                    attention_mask=attention_mask,
                    task="transcribe",
                    language="en",
                )

            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            transcription += text + " "

        return transcription.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
