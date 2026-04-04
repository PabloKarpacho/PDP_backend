from pydantic import BaseModel


class FileUploadSchema(BaseModel):
    url: str
