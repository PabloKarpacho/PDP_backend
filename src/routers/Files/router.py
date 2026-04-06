from fastapi import APIRouter, HTTPException, UploadFile

from src.config import CONFIG
from src.database_control.s3 import (
    build_storage_object_key,
    get_s3_client,
    StorageError,
)
from src.logger import logger
from src.routers.Files.schemas import FileUploadSchema
from src.routers.Files.utils import normalize_content_type, validate_upload_input
from src.schemas import ResponseEnvelope, success_response


PREFIX = "/files"


router = APIRouter(prefix=PREFIX, tags=["Files"])


@router.post(
    "/file_upload",
    response_model=ResponseEnvelope[FileUploadSchema],
)
async def upload_file(file: UploadFile) -> ResponseEnvelope[FileUploadSchema]:
    """
    ### Purpose
    Upload a file into the shared storage layer.

    ### Parameters
    - **file** (UploadFile): The incoming file object provided by FastAPI.

    ### Returns
    - **ResponseEnvelope[FileUploadSchema]**: Structured metadata about the stored
    file, including its object key and a temporary download URL.
    """
    try:
        file_content = await file.read()
        content_type = normalize_content_type(file.content_type)
        safe_filename = validate_upload_input(
            filename=file.filename,
            content_type=content_type,
            size=len(file_content),
        )
        object_key = build_storage_object_key(
            filename=safe_filename,
            namespace="uploads",
        )

        s3_client = get_s3_client()
        stored_object = await s3_client.upload_bytes(
            data=file_content,
            key=object_key,
            bucket_name=CONFIG.FILES_BUCKET_NAME,
            content_type=content_type,
            metadata={"original_filename": safe_filename},
        )
        url = await s3_client.generate_presigned_download_url(
            key=stored_object.key,
            bucket_name=stored_object.bucket_name,
            url_expiry=CONFIG.FILE_UPLOAD_URL_EXPIRY_SECONDS,
        )

        return success_response(
            FileUploadSchema(
                url=url,
                key=stored_object.key,
                bucket_name=stored_object.bucket_name,
                original_filename=safe_filename,
                content_type=stored_object.content_type or content_type,
                size=stored_object.size,
            )
        )

    except HTTPException:
        raise
    except StorageError as error:
        logger.error(f"File upload failed due to storage error: {error}")
        raise HTTPException(status_code=500, detail="File upload failed") from error
    except Exception as error:
        logger.error(f"File upload failed: {error}")
        raise HTTPException(status_code=500, detail="File upload failed") from error
