from app.routes.entries import router as entries_router
from app.routes.health import router as health_router
from app.routes.patients import router as patients_router

__all__ = ["entries_router", "health_router", "patients_router"]
