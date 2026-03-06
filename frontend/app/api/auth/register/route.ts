import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

interface RegisterPayload {
  email?: string;
  password?: string;
  tenantId?: string;
  fullName?: string;
  role?: string;
}

function isValid(payload: RegisterPayload): payload is Required<RegisterPayload> {
  return Boolean(
    payload.email &&
      payload.password &&
      payload.tenantId &&
      payload.fullName &&
      payload.role &&
      payload.password.length >= 8,
  );
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as RegisterPayload;
  if (!isValid(payload)) {
    return NextResponse.json({ message: "Invalid payload" }, { status: 400 });
  }

  const backendResponse = await fetch(`${backendUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      tenant_id: payload.tenantId,
      full_name: payload.fullName,
      role: payload.role,
    }),
  });

  const body = await backendResponse.text();
  return new NextResponse(body, {
    status: backendResponse.status,
    headers: { "Content-Type": backendResponse.headers.get("content-type") || "application/json" },
  });
}
