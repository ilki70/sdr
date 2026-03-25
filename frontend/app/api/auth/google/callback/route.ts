import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

interface GoogleTokenResponse {
  access_token?: string;
  token_type?: string;
}

interface GoogleUserInfoResponse {
  email?: string;
  email_verified?: boolean;
  name?: string;
}

interface BackendGoogleLoginResponse {
  user_id: string;
  tenant_id: string;
  role: string;
  email: string;
  full_name: string;
}

const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
const googleClientId = process.env.GOOGLE_CLIENT_ID || "";
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET || "";

function appBaseUrl(request: NextRequest): string {
  return process.env.NEXT_PUBLIC_APP_URL || request.nextUrl.origin;
}

function loginRedirect(request: NextRequest, message: string) {
  const url = new URL("/login", appBaseUrl(request));
  url.searchParams.set("error", message);
  return NextResponse.redirect(url);
}

export async function GET(request: NextRequest) {
  const session = await getSession();
  const state = request.nextUrl.searchParams.get("state") || "";
  const code = request.nextUrl.searchParams.get("code") || "";
  const oauthState = session.oauthState || "";
  const tenantId = session.oauthTenantId || "";
  const nextPath = session.oauthNext || "/dashboard";

  delete session.oauthState;
  delete session.oauthTenantId;
  delete session.oauthNext;

  if (!googleClientId || !googleClientSecret) {
    await session.save();
    return loginRedirect(request, "Google login nao configurado");
  }

  if (!code || !state || !oauthState || state !== oauthState || !tenantId) {
    await session.save();
    return loginRedirect(request, "Falha ao validar o retorno do Google");
  }

  const redirectUri = `${appBaseUrl(request)}/api/auth/google/callback`;
  const tokenBody = new URLSearchParams({
    code,
    client_id: googleClientId,
    client_secret: googleClientSecret,
    redirect_uri: redirectUri,
    grant_type: "authorization_code",
  });

  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString(),
  });
  if (!tokenResponse.ok) {
    await session.save();
    return loginRedirect(request, "Falha ao trocar o codigo do Google");
  }

  const tokenPayload = (await tokenResponse.json()) as GoogleTokenResponse;
  if (!tokenPayload.access_token) {
    await session.save();
    return loginRedirect(request, "Token do Google ausente");
  }

  const profileResponse = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
    headers: {
      Authorization: `Bearer ${tokenPayload.access_token}`,
    },
  });
  if (!profileResponse.ok) {
    await session.save();
    return loginRedirect(request, "Falha ao carregar o perfil Google");
  }

  const profile = (await profileResponse.json()) as GoogleUserInfoResponse;
  if (!profile.email || profile.email_verified === false || !profile.name) {
    await session.save();
    return loginRedirect(request, "Conta Google sem email valido");
  }

  const backendResponse = await fetch(`${backendUrl}/api/v1/auth/google/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: profile.email,
      full_name: profile.name,
      tenant_id: tenantId,
    }),
  });
  if (!backendResponse.ok) {
    let message = "Falha ao concluir login com Google";
    try {
      const payload = (await backendResponse.json()) as { detail?: string; message?: string };
      message = payload.detail || payload.message || message;
    } catch {
      // keep default message
    }
    await session.save();
    return loginRedirect(request, message);
  }

  const auth = (await backendResponse.json()) as BackendGoogleLoginResponse;
  session.userId = auth.user_id;
  session.tenantId = auth.tenant_id;
  session.email = auth.email;
  session.role = auth.role;
  session.fullName = auth.full_name;
  await session.save();

  return NextResponse.redirect(new URL(nextPath.startsWith("/") ? nextPath : "/dashboard", appBaseUrl(request)));
}
