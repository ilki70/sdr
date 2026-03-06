import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.entities import BotPersona, Client, PersonaVersion, Product, Tenant, TenantUser, User
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


async def ensure_vinac_persona(tenant_id: str, user_id: str) -> None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(BotPersona).where(BotPersona.tenant_id == tenant_id, BotPersona.name == "VINAC Consultora Karina")
        )
        persona = result.scalar_one_or_none()
        if persona:
            return

        persona = BotPersona(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="VINAC Consultora Karina",
            description="Persona comercial inspirada na abordagem consultiva da VINAC para WhatsApp e fechamento assistido.",
            active_version_no=1,
            is_active=True,
        )
        session.add(persona)
        await session.flush()

        version = PersonaVersion(
            id=str(uuid4()),
            tenant_id=tenant_id,
            persona_id=persona.id,
            version_no=1,
            tone="consultiva, humana e segura",
            approach_rules_json={
                "rules": [
                    "Responda em frases curtas para WhatsApp.",
                    "Confirme sempre carro, faixa de parcela e urgencia.",
                    "Use somente fatos oficiais da VINAC para regras e condicoes.",
                    "Quando o lead estiver pronto para fechar, encaminhe para proposta e contrato digital.",
                ],
                "stage_playbook": {
                    "discovery": "Abra com empatia curta, entenda carro desejado, contexto e objetivo de compra.",
                    "qualification": "Confirme valor do bem, faixa de parcela, momento de compra e se o lead aceita ajustar o plano.",
                    "objection": "Trate juros, taxa, seguranca e comparacao com financiamento com fatos oficiais e sem prometer alem do contexto.",
                    "closing": "Conduza para proposta, contrato digital, pagamento da primeira parcela e inicio da concorrencia.",
                },
            },
            objection_playbook_json={
                "juros": "Explique que o contexto oficial trata consorcio sem juros e com taxa de administracao de 12 por cento.",
                "confianca": "Use Banco Central, certidao oficial e operacao da administradora como base de confianca.",
                "orcamento": "Se a parcela estiver abaixo da faixa, reconheca, mostre o minimo oficial e proponha simulacao ajustada.",
            },
            prompt_system=(
                "Voce e Karina, consultora comercial da VINAC. Fale em portugues do Brasil, de forma humana, objetiva e segura. "
                "Sua missao e conduzir o lead ate simulacao, proposta ou adesao sem inventar condicoes."
            ),
            is_published=True,
            created_by_user_id=user_id,
        )
        session.add(version)
        await session.commit()


async def main() -> None:
    settings = get_settings()
    await ensure_system_user()
    tenant_id, user_id = await ensure_admin_and_tenant()
    _client_id, product_id = await ensure_client_and_product(tenant_id)
    await ensure_vinac_persona(tenant_id, user_id)
    await ensure_vinac_knowledge(tenant_id, product_id)

    print("seed_done=true")
    print(f"tenant_slug={settings.seed_tenant_slug}")
    print(f"admin_email={settings.seed_admin_email}")
    print(f"admin_password={settings.seed_admin_password}")
    print("lab_case=VINAC Consorcios")
    print("note=login accepts tenant slug or tenant id")


if __name__ == "__main__":
    asyncio.run(main())
