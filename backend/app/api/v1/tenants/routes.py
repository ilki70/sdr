from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import RequestContext, get_request_context

router = APIRouter(prefix="/tenants", tags=["tenants"])


class CurrentTenantResponse(BaseModel):
    tenant_id: str
    user_id: str
    role: str


@router.get("/current", response_model=CurrentTenantResponse)
async def current_tenant(context: RequestContext = Depends(get_request_context)) -> CurrentTenantResponse:
    return CurrentTenantResponse(tenant_id=context.tenant_id, user_id=context.user_id, role=context.role)
