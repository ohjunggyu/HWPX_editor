import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..service.editor_service import EditorService
from ..domain.models import HwpxReadResponse

router = APIRouter()
editor_service = EditorService()


@router.post("/read", response_model=HwpxReadResponse)
async def read_hwpx(file: UploadFile = File(...)):
    """Uploads a HWPX file and returns its texts as flattened blocks with IDs."""
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are supported.")

    # Save the uploaded file to a temporary location
    fd, temp_path = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        response = editor_service.process_read_request(temp_path, file.filename)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/modify")
async def modify_hwpx(
    file: UploadFile = File(...),
    modifications: str = Form(...),  # Expect JSON string
):
    """Applies modifications to a HWPX file and returns the modified file."""
    if not file.filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are supported.")

    import json

    try:
        mods_data = json.loads(modifications)
        # Validate using pydantic
        from ..domain.models import HwpxModifyRequest

        req = HwpxModifyRequest(modifications=mods_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid modifications JSON: {e}")

    # Save the uploaded file to a temporary location
    fd_in, temp_in_path = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd_in)

    fd_out, temp_out_path = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd_out)

    try:
        with open(temp_in_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        editor_service.process_modify_request(
            file_path=temp_in_path,
            modifications=[m.dict() for m in req.modifications],
            output_filepath=temp_out_path,
        )

        from fastapi.responses import FileResponse

        # Return the modified file
        return FileResponse(
            temp_out_path,
            media_type="application/octet-stream",
            filename=f"modified_{file.filename}",
            background=None,  # Ideally use a background task to delete temp_out_path, but keeping it simple for now
        )
    except Exception as e:
        if os.path.exists(temp_out_path):
            os.remove(temp_out_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_in_path):
            os.remove(temp_in_path)
