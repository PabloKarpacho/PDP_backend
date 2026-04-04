import time
import traceback

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import logger
from src.routers import files_router
from src.routers import homework_router
from src.routers import lesson_router
from src.routers import user_router
from src.schemas import (
    HealthStatusSchema,
    error_response,
    ResponseEnvelope,
    success_response,
)
from src.startup import create_lifespan


routers = [user_router, lesson_router, homework_router, files_router]


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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
                f"Unhandled exception while processing request: {tb_str}",
                extra={
                    "http_status_code": 500,
                    "time_taken": time_taken,
                    "method": request.method,
                    "host": request.url.netloc,
                    "path": request.url.path,
                },
            )
            logger.dump()
            raise

        end_time = time.time()
        time_taken = end_time - start_time

        logger.info(
            "\nЗакончили запрос",
            extra={
                "http_status_code": response.status_code,
                "time_taken": time_taken,
                "method": request.method,
                "host": request.url.netloc,
                "path": request.url.path,
            },
        )

        logger.dump()

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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"""Exception detail: {exc.detail}\nTraceback: {tb_str}""")
    message, details = _extract_error_message_and_details(exc.detail)
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
        f"Request validation error on {request.method} {request.url.path}: {exc}"
    )
    return JSONResponse(
        status_code=400,
        content=error_response(
            code="bad_request",
            message="Request validation failed",
            details=exc.errors(),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}\nTraceback: {tb_str}"
    )
    logger.dump()
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="internal_server_error",
            message="Internal Server Error",
        ).model_dump(mode="json"),
    )


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
