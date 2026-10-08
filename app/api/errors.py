from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    error_code: str
    message: str


class APIHTTPException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str):
        super().__init__(status_code=status_code, detail={"error_code": error_code, "message": message})


def session_not_found(session_id: str) -> APIHTTPException:
    return APIHTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="SESSION_NOT_FOUND",
        message=f"Session with ID '{session_id}' was not found.",
    )


def validation_error(message: str) -> APIHTTPException:
    return APIHTTPException(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message=message,
    )

