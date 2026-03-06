from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.clients.routes import router as clients_router
from app.api.v1.commissions.routes import router as commissions_router
from app.api.v1.dashboard.routes import router as dashboard_router
from app.api.v1.knowledge.routes import router as knowledge_router
from app.api.v1.messages.routes import router as messages_router
from app.api.v1.personas.routes import router as personas_router
from app.api.v1.public.routes import router as public_router
from app.api.v1.products.routes import router as products_router
from app.api.v1.integrations.routes import router as integrations_router
from app.api.v1.sales.routes import router as sales_router
from app.api.v1.tenants.routes import router as tenants_router
from app.api.v1.whatsapp.routes import router as whatsapp_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(public_router)
api_router.include_router(tenants_router)
api_router.include_router(clients_router)
api_router.include_router(products_router)
api_router.include_router(personas_router)
api_router.include_router(dashboard_router)
api_router.include_router(knowledge_router)
api_router.include_router(integrations_router)
api_router.include_router(whatsapp_router)
api_router.include_router(commissions_router)
api_router.include_router(messages_router)
api_router.include_router(sales_router)
