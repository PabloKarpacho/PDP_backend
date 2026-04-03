from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile
from src.database_control.s3 import get_s3_client
from src.config import CONFIG

PREFIX = "/files"


router = APIRouter(prefix=PREFIX, tags=["Files"])


@router.post("/file_upload")
async def upload_file(file: UploadFile):
    try:
        s3_client = get_s3_client()

        # Получаем содержимое файла
        file_content = await file.read()
        file_name = file.filename or "uploaded-file"

        # Загружаем файл в MinIO и получаем ссылку
        url = await s3_client.upload_file(
            fileobj=BytesIO(file_content),
            key=file_name,
            bucket_name=CONFIG.MINIO_FILES_BUCKET_NAME,
        )

        return {"url": url}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}"
        )
