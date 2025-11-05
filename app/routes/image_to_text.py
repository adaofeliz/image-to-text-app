"""Image to text conversion route."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR
import numpy as np


from app.schemas import ResponseItem


router = APIRouter()


def convert_numpy_to_python(obj):
    """Convert numpy arrays and types to Python native types for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, (list, tuple)):
        return [convert_numpy_to_python(item) for item in obj]
    return obj


def convert_result_to_text(result):
    """Convert result to text."""
    if isinstance(result, list):
        return " ".join(result)
    if isinstance(result, dict):
        return " ".join(result.get("rec_texts", []))
    return ""


@router.post("/convert/image/text", response_model=ResponseItem, status_code=200)
async def convert_image_to_text(image: UploadFile = File(...)):
    """Convert uploaded image to text using OCR."""
    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_server_det",
        text_recognition_model_name="PP-OCRv5_server_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix) as tmp_file:
        content = await image.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Run OCR prediction on the uploaded image
        result = ocr.predict(tmp_file_path)
        
        # Extract only rec_texts from the result
        rec_texts = []
        if isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                rec_texts = first_item.get("rec_texts", [])
        elif isinstance(result, dict):
            dict_result: dict = result
            rec_texts = dict_result.get("rec_texts", [])
        
        # Convert numpy arrays to Python native types for JSON serialization
        serializable_texts = convert_numpy_to_python(rec_texts)
        
        return JSONResponse(
            status_code=200, content={"message": convert_result_to_text(serializable_texts)}
        )
    finally:
        # Clean up temporary file
        Path(tmp_file_path).unlink(missing_ok=True)
