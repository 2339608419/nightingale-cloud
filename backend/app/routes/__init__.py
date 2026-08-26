from app.routes.ai_scribe import router as ai_scribe_router
from app.routes.collaboration import router as collaboration_router
from app.routes.conflicts import router as conflicts_router
from app.routes.entries import router as entries_router
from app.routes.health import router as health_router
from app.routes.highlights import router as highlights_router
from app.routes.patients import router as patients_router

__all__ = [
    "ai_scribe_router",
    "collaboration_router",
    "conflicts_router",
    "entries_router",
    "health_router",
    "highlights_router",
    "patients_router",
]
