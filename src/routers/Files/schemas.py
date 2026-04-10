from pydantic import BaseModel


class FileUploadSchema(BaseModel):
    download_url: str
    original_filename: str
    content_type: str
    size: int
