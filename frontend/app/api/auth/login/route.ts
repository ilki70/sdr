import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

interface LoginPayload {
  email?: string;
  password?: string;
  tenantId?: string;
}

interface BackendLoginResponse {
  user_id: string;
  tenant_id: string;
  role: string;
  email: string;
  full_name: string;
  message: string;
}

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

function isValidPayload(payload: LoginPayload): payload is Required<LoginPayload> {
  return Boolean(payload.email && payload.password && payload.tenantId && payload.password.length >= 8);
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as LoginPayload;
  if (!isValidPayload(payload)) {
    return NextResponse.json({ message: "Invalid payload" }, { status: 400 });
  }

  const backendResponse = await fetch(`${backendUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      tenant_id: payload.tenantId,
    }),
  });

  if (!backendResponse.ok) {
    let message = "Login failed";
    try {
      const errorPayload = (await backendResponse.json()) as { detail?: string; message?: string };
      message = errorPayload.detail || errorPayload.message || message;
    } catch {
      const raw = await backendResponse.text();
      if (raw) {
        message = raw;
      }
    }
    return NextResponse.json({ message }, { status: backendResponse.status });
  }

  const auth = (await backendResponse.json()) as BackendLoginResponse;
  const session = await getSession();
  session.userId = auth.user_id;
  session.tenantId = auth.tenant_id;
  session.email = auth.email;
  session.role = auth.role;
  session.fullName = auth.full_name;
  await session.save();

  return NextResponse.json({ message: "ok" });
}
