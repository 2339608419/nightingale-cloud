from app.routes.collaboration import router as collaboration_router
from app.routes.entries import router as entries_router
from app.routes.health import router as health_router
from app.routes.patients import router as patients_router

__all__ = ["collaboration_router", "entries_router", "health_router", "patients_router"]
