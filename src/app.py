import time
import traceback

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import logger
from src.routers import homework_router
from src.routers import lesson_router
from src.routers import user_router
from src.startup import create_lifespan


routers = [user_router, lesson_router, homework_router]


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


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"""Exception detail: {exc.detail}\nTraceback: {tb_str}""")
    return JSONResponse(
        status_code=exc.status_code, content={"message": f"{exc.detail}"}
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
        content={"message": "Internal Server Error"},
    )


@app.get("/actuator/health/liveness", status_code=200)
def liveness_check():
    return "Liveness check succeeded."


@app.get("/actuator/health/readiness", status_code=200)
def readiness_check():
    return "Service is ready"
