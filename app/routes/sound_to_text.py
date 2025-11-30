from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from app.database import User
from app.dependencies.dependencies import get_current_active_user
from app.schemas import ResponseItem
from app.utils import convert_sound_to_text
from app.utils.logger import logger
from app.utils.utils import validate_sound_file

router = APIRouter()


@router.post("/convert/sound/text", response_model=ResponseItem, status_code=200)
def transcribe_sound_to_text(
    file: UploadFile = File(...), _current_user: User = Depends(get_current_active_user)
) -> ResponseItem:
    """Convert uploaded sound file to text."""
    logger.info(
        "Converting sound file to text request from user: %s (ID: %s) - File: %s",
        _current_user.email,
        _current_user.id,
        file.filename,
    )
    try:
        # Validate sound file
        if not validate_sound_file(file):
            logger.error("Invalid sound file: %s", file.filename)
            raise HTTPException(status_code=400, detail="Invalid sound file.")

        logger.info("Converting sound file: %s", file.filename)

        # Convert sound file to text
        text = convert_sound_to_text(file)

        logger.info("Converted sound file to text: %s", text)

        return ResponseItem(content=text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error converting sound to text: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
