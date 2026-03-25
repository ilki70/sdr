import asyncio
from types import SimpleNamespace

from app.schemas.auth import GoogleLoginRequest
from app.services import auth as auth_service


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.flush_count = 0
        self.commit_count = 0

    async def execute(self, _statement):
        if not self._results:
            raise AssertionError("Unexpected execute() call")
        return FakeResult(self._results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1


def test_authenticate_google_user_creates_user_and_membership(monkeypatch):
    captured = {}

    async def fake_ensure_default_agent_for_tenant(db, tenant_id, user_id):
        captured["tenant_id"] = tenant_id
        captured["user_id"] = user_id

    monkeypatch.setattr(auth_service, "ensure_default_agent_for_tenant", fake_ensure_default_agent_for_tenant)

    tenant = SimpleNamespace(id="tenant-1", slug="tenant-lab")
    db = FakeSession([tenant, None, None])

    payload = GoogleLoginRequest(
        email="ilki70@gmail.com",
        full_name="Ilki Amaro",
        tenant_id="tenant-lab",
    )

    authenticated = asyncio.run(auth_service.authenticate_google_user(db, payload))

    assert authenticated.email == "ilki70@gmail.com"
    assert authenticated.tenant_id == "tenant-1"
    assert authenticated.role == "operator"
    assert authenticated.full_name == "Ilki Amaro"
    assert db.commit_count == 1
    assert len(db.added) == 2
    assert captured == {"tenant_id": "tenant-1", "user_id": authenticated.user_id}


def test_authenticate_google_user_updates_existing_user_name(monkeypatch):
    async def fake_ensure_default_agent_for_tenant(_db, _tenant_id, _user_id):
        return None

    monkeypatch.setattr(auth_service, "ensure_default_agent_for_tenant", fake_ensure_default_agent_for_tenant)

    tenant = SimpleNamespace(id="tenant-1", slug="tenant-lab")
    user = SimpleNamespace(
        id="user-1",
        email="ilki70@gmail.com",
        password_hash="hash",
        full_name="Ilki",
        is_active=False,
    )
    membership = SimpleNamespace(role="owner")
    db = FakeSession([tenant, user, membership])

    payload = GoogleLoginRequest(
        email="ilki70@gmail.com",
        full_name="Ilki Amaro",
        tenant_id="tenant-lab",
    )

    authenticated = asyncio.run(auth_service.authenticate_google_user(db, payload))

    assert authenticated.user_id == "user-1"
    assert authenticated.role == "owner"
    assert user.is_active is True
    assert user.full_name == "Ilki Amaro"
    assert db.commit_count == 1
    assert db.added == []
