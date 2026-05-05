"""Worker functions for processing image-to-text jobs."""

import os
from pathlib import Path
from typing import Dict, Any

from PIL import Image
from paddleocr import PaddleOCR

from app.utils import (
    convert_numpy_to_python,
    convert_result_to_text,
    delete_temp_file,
    extract_rec_texts,
)
from app.utils.logger import logger

_OCR_MAX_SIDE = int(os.getenv("OCR_MAX_SIDE", "3500"))

# Lazy-loaded OCR instance
_OCR = None


def _get_ocr() -> PaddleOCR:
    global _OCR  # pylint: disable=global-statement
    if _OCR is None:
        logger.info("Initializing PaddleOCR...")
        _OCR = PaddleOCR(
            text_detection_model_name="PP-OCRv5_server_det",
            text_recognition_model_name="PP-OCRv5_server_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PaddleOCR initialized successfully")
    return _OCR


def _cap_image_size(image_file_path: str) -> None:
    path = Path(image_file_path)
    with Image.open(path) as img:
        w, h = img.size
        long_side = max(w, h)
        if long_side <= _OCR_MAX_SIDE:
            return
        scale = _OCR_MAX_SIDE / long_side
        new_w, new_h = int(w * scale), int(h * scale)
        logger.info(
            "Resizing image from %dx%d to %dx%d before OCR (max_side=%d)",
            w, h, new_w, new_h, _OCR_MAX_SIDE,
        )
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        resized.save(path)


def process_image_job_sync(job_data: Dict[str, Any]) -> Dict[str, Any]:
    image_file_path = job_data["image_file_path"]
    filename = job_data.get("filename", "image.png")

    logger.info("Processing image-to-text job for file: %s", filename)

    try:
        if not Path(image_file_path).exists():
            raise ValueError(f"Image file not found: {image_file_path}")

        _cap_image_size(image_file_path)

        ocr = _get_ocr()

        logger.info("Running OCR on file: %s", image_file_path)
        result = ocr.predict(image_file_path)

        rec_texts = extract_rec_texts(result)
        serializable_texts = convert_numpy_to_python(rec_texts)
        text_result = convert_result_to_text(serializable_texts)

        logger.info(
            "OCR conversion successful - Extracted %d text segments",
            len(rec_texts),
        )

        result = {
            "content": text_result,
            "filename": filename,
            "image_file_path": image_file_path,
            "segments_count": len(rec_texts),
        }

        if job_data.get("email") is not None:
            result["email"] = job_data["email"]
        if job_data.get("session_id") is not None:
            result["session_id"] = job_data["session_id"]

        return result
    except Exception as e:
        logger.error("Error processing image-to-text job: %s", e, exc_info=True)
        raise
    finally:
        delete_temp_file(image_file_path)
