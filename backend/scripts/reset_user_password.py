import argparse
import asyncio

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.schemas.auth import AdminResetUserPasswordRequest
from app.services.auth import reset_user_password


async def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user password inside a tenant.")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--role", default="operator")
    args = parser.parse_args()

    settings = get_settings()
    tenant_id = args.tenant_id or settings.seed_tenant_slug
    email = args.email or settings.seed_admin_email
    password = args.password or settings.seed_admin_password

    payload = AdminResetUserPasswordRequest(
        tenant_id=tenant_id,
        email=email,
        password=password,
        full_name=args.full_name,
        role=args.role,
    )

    async with SessionLocal() as session:
        result = await reset_user_password(session, payload)
        print(
            {
                "tenant_id": result.tenant_id,
                "email": result.email,
                "user_id": result.user_id,
                "role": result.role,
                "status": "reset",
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
