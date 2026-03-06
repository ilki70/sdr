import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.entities import Product, Tenant
from app.services.vinac_lab import build_vinac_report, run_vinac_lab, write_vinac_report
from scripts.seed_deep_test_data import main as seed_lab_data


async def _get_lab_ids() -> tuple[str, str]:
    settings = get_settings()
    async with SessionLocal() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == settings.seed_tenant_slug))
        tenant = tenant_result.scalar_one()
        product_result = await session.execute(
            select(Product).where(Product.tenant_id == tenant.id, Product.name == "Consorcio de carros VINAC")
        )
        product = product_result.scalar_one()
        return tenant.id, product.id


async def run_lab() -> list[dict]:
    await seed_lab_data()
    tenant_id, _product_id = await _get_lab_ids()
    return await run_vinac_lab(tenant_id)


async def main() -> None:
    results = await run_lab()
    report = build_vinac_report(results)
    report_path = write_vinac_report(report)
    print(report)
    print(f"report_path={report_path}")


if __name__ == "__main__":
    asyncio.run(main())
