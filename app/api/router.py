from fastapi import APIRouter

from app.api.routes.catalog import router as catalog_router
from app.api.routes.companies import router as companies_router
from app.api.routes.health import router as health_router
from app.api.routes.public_facade import router as public_facade_router
from app.api.routes.story import router as story_router
from app.editorial.api.routes import router as editorial_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(catalog_router)
api_router.include_router(companies_router)
api_router.include_router(story_router)
api_router.include_router(public_facade_router)
api_router.include_router(editorial_router)
