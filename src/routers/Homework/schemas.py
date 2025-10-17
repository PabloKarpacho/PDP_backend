from tkinter import NO
from typing import Literal, List
from pydantic import BaseModel
from datetime import datetime

class HomeworkBaseSchema(BaseModel):
    name : str | None
    description : str | None
    files_urls : List | None
    answer : str | None
    sent_files : List | None
    deadline : datetime | None
    is_deleted : bool
    updated_at : datetime
    created_at : datetime

class HomeworkGetSchema(HomeworkBaseSchema):
    id : int

class HomeworkCreateSchema(HomeworkBaseSchema):
    pass

class HomeworkUpdateSchema(HomeworkBaseSchema):
    pass