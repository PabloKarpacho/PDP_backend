from pydantic import BaseModel


class FileUploadSchema(BaseModel):
    url: str
    key: str
    bucket_name: str
    original_filename: str
    content_type: str
    size: int
