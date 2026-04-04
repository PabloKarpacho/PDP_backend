from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile
from src.database_control.s3 import get_s3_client
from src.config import CONFIG
from src.logger import logger
from src.routers.Files.schemas import FileUploadSchema
from src.schemas import ResponseEnvelope, success_response

PREFIX = "/files"


router = APIRouter(prefix=PREFIX, tags=["Files"])


@router.post("/file_upload", response_model=ResponseEnvelope[FileUploadSchema])
async def upload_file(file: UploadFile) -> ResponseEnvelope[FileUploadSchema]:
    try:
        s3_client = get_s3_client()

        file_content = await file.read()
        file_name = file.filename or "uploaded-file"

        url = await s3_client.upload_file(
            fileobj=BytesIO(file_content),
            key=file_name,
            bucket_name=CONFIG.MINIO_FILES_BUCKET_NAME,
        )

        return success_response(FileUploadSchema(url=url))

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail="File upload failed") from e
