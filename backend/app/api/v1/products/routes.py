from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.security import RequestContext, get_request_context
from app.services.clients import get_client_or_none
from app.schemas.products import ProductAssetResponse, ProductCreateRequest, ProductResponse, ProductUpdateRequest
from app.services.products import (
    create_product,
    create_product_asset,
    get_product_or_none,
    list_products,
    soft_delete_product,
    update_product,
)
from app.services.uploads import persist_upload

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def get_products(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ProductResponse]:
    products = await list_products(db, context.tenant_id)
    return [ProductResponse.model_validate(item) for item in products]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def post_product(
    payload: ProductCreateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    client = await get_client_or_none(db, context.tenant_id, payload.client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client for tenant")
    product = await create_product(db, context.tenant_id, payload)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: str,
    payload: ProductUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    product = await get_product_or_none(db, context.tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    updated = await update_product(db, product, payload)
    return ProductResponse.model_validate(updated)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    product = await get_product_or_none(db, context.tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    await soft_delete_product(db, product)


@router.post("/{product_id}/assets/upload", response_model=ProductAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_asset(
    product_id: str,
    file: UploadFile,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ProductAssetResponse:
    product = await get_product_or_none(db, context.tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    path, checksum, size, _mime = await persist_upload(file)
    asset = await create_product_asset(
        db=db,
        tenant_id=context.tenant_id,
        product_id=product_id,
        created_by_user_id=context.user_id,
        title=file.filename or "asset",
        storage_path=path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        checksum_sha256=checksum,
    )
    return ProductAssetResponse(
        id=asset.id,
        product_id=asset.product_id,
        storage_path=asset.storage_path or "",
        checksum_sha256=asset.checksum_sha256 or "",
        size_bytes=asset.size_bytes or 0,
    )
