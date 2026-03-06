import logging
import uuid
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("app")
settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = perf_counter()
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    response = await call_next(request)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "tenant_id": request.headers.get("X-Tenant-Id", ""),
            "user_id": request.headers.get("X-User-Id", ""),
        },
    )
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Elapsed-Ms"] = str(elapsed_ms)
    return response


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": settings.app_name})
