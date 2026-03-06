import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const response = await fetch(`${backendUrl}/api/v1/public/marketing/leads`, {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      Accept: "application/json",
    },
    body,
    cache: "no-store",
  });

  const upstreamType = response.headers.get("content-type") || "application/json";
  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": upstreamType },
  });
}
