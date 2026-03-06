import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

async function forward(request: NextRequest, path: string[]) {
  const session = await getSession();
  if (!session.userId || !session.tenantId) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const target = new URL(`/api/v1/${path.join("/")}${request.nextUrl.search}`, backendUrl);
  const body =
    request.method === "GET" || request.method === "HEAD" ? undefined : Buffer.from(await request.arrayBuffer());

  const forwardHeaders = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    forwardHeaders.set("Content-Type", contentType);
  }
  const accept = request.headers.get("accept");
  if (accept) {
    forwardHeaders.set("Accept", accept);
  }
  forwardHeaders.set("X-User-Id", session.userId);
  forwardHeaders.set("X-Tenant-Id", session.tenantId);
  forwardHeaders.set("X-Request-Id", crypto.randomUUID());

  const response = await fetch(target, {
    method: request.method,
    headers: forwardHeaders,
    body,
    cache: "no-store",
  });

  const upstreamType = response.headers.get("content-type") || "application/json";
  if (response.body && upstreamType.includes("text/event-stream")) {
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": upstreamType,
        "Cache-Control": "no-cache",
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

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return forward(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return forward(request, path);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return forward(request, path);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return forward(request, path);
}
