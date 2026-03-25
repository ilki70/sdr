import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const googleClientId = process.env.GOOGLE_CLIENT_ID || "";

function appBaseUrl(request: NextRequest): string {
  return process.env.NEXT_PUBLIC_APP_URL || request.nextUrl.origin;
}

export async function GET(request: NextRequest) {
  const tenantId = request.nextUrl.searchParams.get("tenantId")?.trim() || "";
  const nextPath = request.nextUrl.searchParams.get("next")?.trim() || "/dashboard";

  if (!googleClientId) {
    return NextResponse.redirect(new URL("/login?error=Google%20login%20nao%20configurado", appBaseUrl(request)));
  }

  if (!tenantId) {
    return NextResponse.redirect(new URL("/login?error=Informe%20o%20tenant%20antes%20de%20usar%20Google", appBaseUrl(request)));
  }

  const state = crypto.randomUUID();
  const session = await getSession();
  session.oauthState = state;
  session.oauthTenantId = tenantId;
  session.oauthNext = nextPath.startsWith("/") ? nextPath : "/dashboard";
  await session.save();

  const redirectUri = `${appBaseUrl(request)}/api/auth/google/callback`;
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", googleClientId);
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", "openid email profile");
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("prompt", "select_account");

  return NextResponse.redirect(authUrl);
}
