from tempfile import SpooledTemporaryFile

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
from src.routers.Files.utils import (
    normalize_content_type,
    validate_upload_metadata,
    validate_upload_size,
)
from src.schemas import ResponseEnvelope, success_response


PREFIX = "/files"


router = APIRouter(prefix=PREFIX, tags=["Files"])

_UPLOAD_CHUNK_SIZE = 1024 * 1024


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
        content_type = normalize_content_type(file.content_type)
        safe_filename = validate_upload_metadata(
            filename=file.filename,
            content_type=content_type,
        )
        object_key = build_storage_object_key(
            filename=safe_filename,
            namespace="uploads",
        )
        total_size = 0

        with SpooledTemporaryFile(max_size=_UPLOAD_CHUNK_SIZE, mode="w+b") as spool:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)
                validate_upload_size(total_size)
                spool.write(chunk)

            spool.seek(0)

            s3_client = get_s3_client()
            stored_object = await s3_client.upload_fileobj(
                fileobj=spool,
                key=object_key,
                bucket_name=CONFIG.FILES_BUCKET_NAME,
                content_type=content_type,
                metadata={"original_filename": safe_filename},
                size=total_size,
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
