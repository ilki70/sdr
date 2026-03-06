import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.entities import Client, Product, Tenant, TenantUser, User
from app.services.auth import hash_password
from app.services.vinac_lab import ensure_vinac_knowledge


SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


async def ensure_system_user() -> None:
    async with SessionLocal() as session:
        existing = await session.get(User, SYSTEM_USER_ID)
        if existing:
            return
        system = User(
            id=SYSTEM_USER_ID,
            email="system@agentevendedor.example.com",
            password_hash=hash_password("system-not-used"),
            full_name="System User",
            is_active=True,
        )
        session.add(system)
        await session.commit()


async def ensure_admin_and_tenant() -> tuple[str, str]:
    settings = get_settings()
    async with SessionLocal() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == settings.seed_tenant_slug))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                id=str(uuid4()),
                name="Tenant Lab",
                slug=settings.seed_tenant_slug,
                status="active",
            )
            session.add(tenant)
            await session.flush()

        user_result = await session.execute(select(User).where(User.email == settings.seed_admin_email))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                id=str(uuid4()),
                email=settings.seed_admin_email,
                password_hash=hash_password(settings.seed_admin_password),
                full_name="Admin Lab",
                is_active=True,
            )
            session.add(user)
            await session.flush()

        link_result = await session.execute(
            select(TenantUser).where(TenantUser.tenant_id == tenant.id, TenantUser.user_id == user.id)
        )
        if not link_result.scalar_one_or_none():
            session.add(
                TenantUser(
                    id=str(uuid4()),
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role="owner",
                )
            )
            await session.flush()

        await session.commit()
        return tenant.id, user.id


async def ensure_client_and_product(tenant_id: str) -> tuple[str, str]:
    async with SessionLocal() as session:
        client_result = await session.execute(select(Client).where(Client.tenant_id == tenant_id, Client.name == "VINAC Consorcios"))
        client = client_result.scalar_one_or_none()
        if not client:
            client = Client(
                id=str(uuid4()),
                tenant_id=tenant_id,
                name="VINAC Consorcios",
                segment="consorcio_de_veiculos",
                website_url="https://vinac.com.br/",
                status="active",
            )
            session.add(client)
            await session.flush()

        product_result = await session.execute(
            select(Product).where(Product.tenant_id == tenant_id, Product.name == "Consorcio de carros VINAC")
        )
        product = product_result.scalar_one_or_none()
        if not product:
            product = Product(
                id=str(uuid4()),
                tenant_id=tenant_id,
                client_id=client.id,
                name="Consorcio de carros VINAC",
                description="Consorcio de carros com adesao online, carta de credito e compra de veiculo novo ou seminovo.",
                base_price=Decimal("1000.00"),
                currency="BRL",
                sales_terms_json={
                    "taxa_administracao": "12%",
                    "duracao_grupo": "60 meses",
                    "grupos": "120 pessoas",
                    "contemplacao": "um por sorteio e outro por lance por mes",
                    "seminovos": "ate 3 anos",
                },
                is_active=True,
                version_no=1,
            )
            session.add(product)
            await session.flush()

        await session.commit()
        return client.id, product.id


async def main() -> None:
    settings = get_settings()
    await ensure_system_user()
    tenant_id, _user_id = await ensure_admin_and_tenant()
    _client_id, product_id = await ensure_client_and_product(tenant_id)
    await ensure_vinac_knowledge(tenant_id, product_id)

    print("seed_done=true")
    print(f"tenant_slug={settings.seed_tenant_slug}")
    print(f"admin_email={settings.seed_admin_email}")
    print(f"admin_password={settings.seed_admin_password}")
    print("lab_case=VINAC Consorcios")
    print("note=login accepts tenant slug or tenant id")


if __name__ == "__main__":
    asyncio.run(main())
