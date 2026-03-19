import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const payload = await request.json();
  const backendResponse = await fetch(`${backendUrl}/api/v1/auth/admin/reset-user-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Reset-Key": request.headers.get("X-Admin-Reset-Key") || "",
      "X-User-Id": request.headers.get("X-User-Id") || "",
      "X-Tenant-Id": request.headers.get("X-Tenant-Id") || "",
      "X-Request-Id": request.headers.get("X-Request-Id") || "generated-locally",
    },
    body: JSON.stringify(payload),
  });

  const body = await backendResponse.text();
  return new NextResponse(body, {
    status: backendResponse.status,
    headers: { "Content-Type": backendResponse.headers.get("content-type") || "application/json" },
  });
}
