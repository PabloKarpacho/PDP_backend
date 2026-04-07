from fastapi import APIRouter, Depends, HTTPException, UploadFile

from src.config import CONFIG
from src.database_control.s3 import (
    build_storage_object_key,
    get_s3_client,
    StorageError,
)
from src.dependencies import get_user
from src.logger import logger
from src.models import UserDAO
from src.routers.Files.schemas import FileUploadSchema
from src.routers.Files.utils import normalize_content_type, validate_upload_input
from src.schemas import ResponseEnvelope, success_response


PREFIX = "/files"


router = APIRouter(prefix=PREFIX, tags=["Files"])


@router.post(
    "/file_upload",
    response_model=ResponseEnvelope[FileUploadSchema],
)
async def upload_file(
    file: UploadFile,
    user: UserDAO = Depends(get_user),
) -> ResponseEnvelope[FileUploadSchema]:
    """
    ### Purpose
    Upload a file into the shared storage layer.

    ### Access
    Available to any authenticated application user.

    ### Parameters
    - **file** (UploadFile): The incoming file object provided by FastAPI.
    - **user** (UserDAO): The current authenticated application user.

    ### Returns
    - **ResponseEnvelope[FileUploadSchema]**: Structured metadata about the stored
    file, including a short-lived download URL.
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
                download_url=url,
                original_filename=safe_filename,
                content_type=stored_object.content_type or content_type,
                size=stored_object.size,
            )
        )

    except HTTPException:
        raise
    except StorageError as error:
        logger.error(
            "File upload failed due to storage error.",
            extra={"user_id": user.id},
        )
        raise HTTPException(status_code=500, detail="File upload failed") from error
    except Exception as error:
        logger.error(
            "File upload failed.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(status_code=500, detail="File upload failed") from error
