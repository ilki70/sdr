import { NextResponse } from "next/server";

export async function GET() {
  const googleEnabled = Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);

  return NextResponse.json(
    {
      credentials: {
        id: "credentials",
        name: "Credentials",
        type: "credentials",
        signinUrl: "/login",
        callbackUrl: "/login",
      },
      ...(googleEnabled
        ? {
            google: {
              id: "google",
              name: "Google",
              type: "oauth",
              signinUrl: "/api/auth/google/start",
              callbackUrl: "/api/auth/google/callback",
            },
          }
        : {}),
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
