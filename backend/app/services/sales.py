from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Sale


async def list_sales(db: AsyncSession, tenant_id: str) -> list[Sale]:
    result = await db.execute(
        select(Sale).where(Sale.tenant_id == tenant_id, Sale.deleted_at.is_(None)).order_by(Sale.created_at.desc())
    )
    return list(result.scalars().all())
