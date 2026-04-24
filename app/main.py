from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, register_exception_handlers
from app.core.rate_limit import maybe_add_rate_limit_middleware
from app.core.scheduler import start_scheduler, stop_scheduler
from app.editorial.ui.routes import router as editorial_ui_router

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
maybe_add_rate_limit_middleware(app)
register_exception_handlers(app)
app.include_router(api_router)
app.include_router(editorial_ui_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Spain data editorial backend"}
