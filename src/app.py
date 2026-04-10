import time
import traceback
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import logger
from src.logger import sanitize_log_data
from src.routers import files_router
from src.routers import homework_router
from src.routers import lesson_router
from src.routers import relation_router
from src.routers import user_router
from src.schemas import (
    HealthStatusSchema,
    error_response,
    ResponseEnvelope,
    success_response,
)
from src.startup import create_lifespan


routers = [user_router, lesson_router, homework_router, relation_router, files_router]
REQUEST_ID_HEADER = "X-Request-ID"


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        logger.clear_context()
        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            host=request.url.netloc,
        )
        logger.info("Request started.")
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception as exc:
            end_time = time.time()
            time_taken = end_time - start_time
            tb_str = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            logger.error(
                "Unhandled exception while processing request.",
                extra={
                    "http_status_code": 500,
                    "time_taken": time_taken,
                    "error_type": type(exc).__name__,
                    "traceback": sanitize_log_data(tb_str),
                },
            )
            logger.dump()
            logger.clear_context()
            raise

        end_time = time.time()
        time_taken = end_time - start_time

        logger.info(
            "Request completed.",
            extra={
                "http_status_code": response.status_code,
                "time_taken": time_taken,
            },
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.dump()
        logger.clear_context()

        return response


app = FastAPI(
    title="PDP",
    root_path="/pdp",
    description="Сервис для управления рассписанием уроков",
    lifespan=create_lifespan(),
)
app.add_middleware(CustomMiddleware)

app.include_router(user_router)
app.include_router(lesson_router)
app.include_router(homework_router)
app.include_router(relation_router)
app.include_router(files_router)


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_code_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        500: "internal_server_error",
    }.get(status_code, "http_error")


def _extract_error_message_and_details(detail):
    if isinstance(detail, str):
        return detail, None

    return "Request failed", detail


def _serialize_validation_details(details):
    if isinstance(details, dict):
        return {
            key: _serialize_validation_details(value) for key, value in details.items()
        }

    if isinstance(details, list):
        return [_serialize_validation_details(item) for item in details]

    if isinstance(details, tuple):
        return [_serialize_validation_details(item) for item in details]

    if isinstance(details, Exception):
        return str(details)

    return details


def _request_log_extra(request: Request, **extra):
    request_id = getattr(request.state, "request_id", None)
    request_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    }
    request_extra.update(extra)
    return request_extra


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message, details = _extract_error_message_and_details(exc.detail)
    logger.error(
        "HTTP exception raised.",
        extra=_request_log_extra(
            request,
            http_status_code=exc.status_code,
            error_type=type(exc).__name__,
            error_detail=exc.detail,
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=_error_code_for_status(exc.status_code),
            message=message,
            details=details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    logger.error(
        "Request validation failed.",
        extra=_request_log_extra(
            request,
            http_status_code=400,
            error_type=type(exc).__name__,
            validation_errors=_serialize_validation_details(exc.errors()),
        ),
    )
    return JSONResponse(
        status_code=400,
        content=error_response(
            code="bad_request",
            message="Request validation failed",
            details=_serialize_validation_details(exc.errors()),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled server error.",
        extra=_request_log_extra(
            request,
            http_status_code=500,
            error_type=type(exc).__name__,
            traceback=sanitize_log_data(
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            ),
        ),
    )
    logger.dump()
    response = JSONResponse(
        status_code=500,
        content=error_response(
            code="internal_server_error",
            message="Internal Server Error",
        ).model_dump(mode="json"),
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


@app.get(
    "/actuator/health/liveness",
    status_code=200,
    response_model=ResponseEnvelope[HealthStatusSchema],
)
def liveness_check() -> ResponseEnvelope[HealthStatusSchema]:
    return success_response(HealthStatusSchema(status="alive"))


@app.get(
    "/actuator/health/readiness",
    status_code=200,
    response_model=ResponseEnvelope[HealthStatusSchema],
)
def readiness_check() -> ResponseEnvelope[HealthStatusSchema]:
    return success_response(HealthStatusSchema(status="ready"))
