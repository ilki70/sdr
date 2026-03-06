import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "agente_vendedor_session";

function requiresAuth(pathname: string): boolean {
  return (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/clients") ||
    pathname.startsWith("/products") ||
    pathname.startsWith("/knowledge") ||
    pathname.startsWith("/personas") ||
    pathname.startsWith("/integrations") ||
    pathname.startsWith("/conversations") ||
    pathname.startsWith("/agent-lab") ||
    pathname.startsWith("/sales") ||
    pathname.startsWith("/commissions") ||
    pathname.startsWith("/settings")
  );
}

export function middleware(request: NextRequest) {
  if (!requiresAuth(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value);
  if (hasSession) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/clients/:path*",
    "/products/:path*",
    "/knowledge/:path*",
    "/personas/:path*",
    "/integrations/:path*",
    "/conversations/:path*",
    "/agent-lab/:path*",
    "/sales/:path*",
    "/commissions/:path*",
    "/settings/:path*",
  ],
};
