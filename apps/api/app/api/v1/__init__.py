from fastapi import APIRouter

from app.api.v1 import (
    auth,
    clients,
    communications,
    health,
    knowledge,
    operations,
    organizations,
    portal,
    queues,
    tags,
    ticket_categories,
    tickets,
    workspaces,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(organizations.router)
api_router.include_router(clients.router)
api_router.include_router(queues.router)
api_router.include_router(ticket_categories.router)
api_router.include_router(tags.router)
api_router.include_router(tickets.router)
api_router.include_router(communications.router)
api_router.include_router(knowledge.router)
api_router.include_router(operations.router)
api_router.include_router(portal.router)
