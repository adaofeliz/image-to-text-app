"""Image to text conversion route."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

from app.dependencies import get_current_active_user
from app.database import User
from app.schemas import ResponseItem
from app.utils import (
    convert_numpy_to_python,
    convert_result_to_text,
    extract_rec_texts,
    validate_image_file,
)
from app.utils.logger import logger


router = APIRouter()


@router.post("/convert/image/text", response_model=ResponseItem, status_code=200)
async def convert_image_to_text(
    image: UploadFile = File(...),
    _current_user: User = Depends(get_current_active_user),
):
    """Convert uploaded image to text using OCR.

    Requires authentication with a valid access token.
    The _current_user dependency ensures the user is authenticated and verified.
    """
    try:
        logger.info(
            "Image to text conversion request from user: %s (ID: %s) - File: %s",
            _current_user.email,
            _current_user.id,
            image.filename,
        )

        # Validate that the uploaded file is an image
        validate_image_file(image)

        ocr = PaddleOCR(
            text_detection_model_name="PP-OCRv5_server_det",
            text_recognition_model_name="PP-OCRv5_server_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        # Save uploaded file temporarily
        # Handle case where filename might be None
        suffix = Path(image.filename).suffix if image.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await image.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Run OCR prediction on the uploaded image
            logger.debug("Running OCR on file: %s", tmp_file_path)
            result = ocr.predict(tmp_file_path)

            # Extract only rec_texts from the result
            rec_texts = extract_rec_texts(result)

            # Convert numpy arrays to Python native types for JSON serialization
            serializable_texts = convert_numpy_to_python(rec_texts)
            text_result = convert_result_to_text(serializable_texts)

            logger.info(
                "OCR conversion successful for user: %s - Extracted %d text segments",
                _current_user.email,
                len(rec_texts),
            )

            return JSONResponse(
                status_code=200,
                content={"message": text_result},
            )
        finally:
            # Clean up temporary file
            Path(tmp_file_path).unlink(missing_ok=True)
    except HTTPException as http_exc:
        logger.error(
            "HTTP error in image to text conversion for user %s (ID: %s) - File: %s - Status: %s - Detail: %s",
            _current_user.email,
            _current_user.id,
            image.filename,
            http_exc.status_code,
            http_exc.detail,
        )
        raise HTTPException(
            status_code=400,
            detail=http_exc.detail,
        ) from http_exc
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "Image to text conversion error for user %s: %s",
            _current_user.email,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Image conversion failed",
        ) from exc
