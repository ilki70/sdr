from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow_naive
from app.models.entities import Product, ProductAsset
from app.schemas.products import ProductCreateRequest, ProductUpdateRequest


def _product_select(tenant_id: str) -> Select[tuple[Product]]:
    return select(Product).where(Product.tenant_id == tenant_id, Product.deleted_at.is_(None))


async def list_products(db: AsyncSession, tenant_id: str) -> list[Product]:
    result = await db.execute(_product_select(tenant_id).order_by(Product.created_at.desc()))
    return list(result.scalars().all())


async def create_product(db: AsyncSession, tenant_id: str, payload: ProductCreateRequest) -> Product:
    product = Product(id=str(uuid4()), tenant_id=tenant_id, **payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product_or_none(db: AsyncSession, tenant_id: str, product_id: str) -> Product | None:
    result = await db.execute(_product_select(tenant_id).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def update_product(db: AsyncSession, product: Product, payload: ProductUpdateRequest) -> Product:
    data = payload.model_dump(exclude_none=True)
    if data:
        data["version_no"] = product.version_no + 1
    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


async def soft_delete_product(db: AsyncSession, product: Product) -> None:
    product.deleted_at = utcnow_naive()
    await db.commit()


async def create_product_asset(
    db: AsyncSession,
    tenant_id: str,
    product_id: str,
    created_by_user_id: str,
    title: str,
    storage_path: str,
    mime_type: str,
    size_bytes: int,
    checksum_sha256: str,
) -> ProductAsset:
    asset = ProductAsset(
        id=str(uuid4()),
        tenant_id=tenant_id,
        product_id=product_id,
        created_by_user_id=created_by_user_id,
        asset_type="document",
        title=title,
        storage_path=storage_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        checksum_sha256=checksum_sha256,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset
