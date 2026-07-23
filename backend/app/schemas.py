from pydantic import BaseModel


class GenerateResponse(BaseModel):
    image_url: str
    description: str = ""
    request_id: str = ""


class ErrorResponse(BaseModel):
    error: str
    message: str
