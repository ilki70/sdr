import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const response = await fetch(`${backendUrl}/api/v1/public/demo/stream`, {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      Accept: request.headers.get("accept") || "text/event-stream",
    },
    body,
    cache: "no-store",
  });

  const upstreamType = response.headers.get("content-type") || "application/json";
  if (response.body && upstreamType.includes("text/event-stream")) {
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": upstreamType,
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": upstreamType },
  });
}
